"""Exception handlers that turn raised exceptions into
`contracts.errors.v1.envelope.ErrorEnvelope` JSON responses.

Registered on the app in `main.create_app()`. Scoped to exactly what
this task's routes raise: `ApiError` (401/403/400 cases from
`apps/api/deps.py` and `apps/api/routers/auth.py`) and FastAPI's own
`RequestValidationError` (422) -- not a generic exception taxonomy for
error cases that don't exist yet.
"""

import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from jobact.contracts.errors.v1.envelope import ApiError, ErrorDetail, ErrorEnvelope


def register_error_handlers(app: FastAPI) -> None:
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
