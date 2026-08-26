"""Exception handlers that turn raised exceptions into
`contracts.errors.v1.envelope.ErrorEnvelope` JSON responses.

Registered on the app in `main.create_app()`. Scoped to exactly what
this task's routes raise: `ApiError` (401/403/400 cases from
`apps/api/deps.py` and `apps/api/routers/auth.py`), FastAPI's own
`RequestValidationError` (422), and
`routers.auth.LogoutCacheDeleteFailedError` (502) -- not a generic
exception taxonomy for error cases that don't exist yet.
"""

import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from jobact.apps.api.routers.auth import LogoutCacheDeleteFailedError
from jobact.contracts.errors.v1.envelope import ApiError, ErrorDetail, ErrorEnvelope
from jobact.shared.application.authorization import AuthorizationError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthorizationError)
    async def _handle_authorization_error(
        request: Request, exc: AuthorizationError
    ) -> JSONResponse:
        envelope = ErrorEnvelope(
            type="forbidden",
            title="Forbidden",
            status=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
            correlation_id=str(uuid.uuid4()),
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN, content=envelope.model_dump()
        )

    @app.exception_handler(ApiError)
    async def _handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        envelope = ErrorEnvelope(
            type=exc.type,
            title=exc.title,
            status=exc.status,
            detail=exc.detail,
            correlation_id=str(uuid.uuid4()),
            errors=exc.errors,
        )
        return JSONResponse(status_code=exc.status, content=envelope.model_dump())

    @app.exception_handler(LogoutCacheDeleteFailedError)
    async def _handle_logout_cache_delete_failed(
        request: Request, exc: LogoutCacheDeleteFailedError
    ) -> JSONResponse:
        """Postgres was already revoked by the time this fires (see the
        docstring on `LogoutCacheDeleteFailedError`) -- only the Redis
        cache cleanup failed. Still clear the client's cookie so their
        own subsequent requests can't present the stale, still-cached
        session id; that leaves only a request that independently
        obtained/replayed the id able to hit the stale cache entry.
        """
        envelope = ErrorEnvelope(
            type="session-cache-unavailable",
            title="Bad Gateway",
            status=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Session was revoked but its cache entry could not be "
                "deleted. Please try again."
            ),
            correlation_id=str(uuid.uuid4()),
        )
        response = JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY, content=envelope.model_dump()
        )
        response.delete_cookie(key=exc.session_cookie_name, path="/")
        return response

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        envelope = ErrorEnvelope(
            type="validation-error",
            title="Unprocessable Entity",
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request validation failed.",
            correlation_id=str(uuid.uuid4()),
            errors=[
                ErrorDetail(
                    loc=[str(part) for part in error["loc"]], message=error["msg"]
                )
                for error in exc.errors()
            ],
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=envelope.model_dump(),
        )
