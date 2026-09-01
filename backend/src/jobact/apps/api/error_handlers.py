"""Exception handlers that turn raised exceptions into
`contracts.errors.v1.envelope.ErrorEnvelope` JSON responses.

Registered on the app in `main.create_app()`. Every envelope carries the
request's own correlation id (see `middleware/correlation.py`).
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from jobact.apps.api.middleware.correlation import get_correlation_id
from jobact.contracts.errors.v1.envelope import ApiError, ErrorDetail, ErrorEnvelope


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        envelope = ErrorEnvelope(
            type=exc.type,
            title=exc.title,
            status=exc.status,
            detail=exc.detail,
            correlation_id=str(get_correlation_id(request)),
            errors=exc.errors,
        )
        return JSONResponse(
            status_code=exc.status,
            content=envelope.model_dump(),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        envelope = ErrorEnvelope(
            type="validation-error",
            title="Unprocessable Entity",
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request validation failed.",
            correlation_id=str(get_correlation_id(request)),
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
