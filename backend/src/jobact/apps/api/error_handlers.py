"""Exception handlers that turn raised exceptions into
`contracts.errors.v1.envelope.ErrorEnvelope` JSON responses.

Registered on the app in `main.create_app()`. Every envelope carries the
request's own correlation id (see `middleware/correlation.py`), so an
error a user reports can be traced to its request and, for anything that
started a workflow, to the worker logs for that job.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from jobact.apps.api.middleware.correlation import get_correlation_id
from jobact.apps.api.routers.auth import LogoutCacheDeleteFailedError
from jobact.contexts.media.application.media_handlers import MediaUploadValidationError
from jobact.contexts.media.domain.media_asset import MediaVerificationError
from jobact.contexts.reports.application.report_handlers import (
    ReportEvidenceIncompleteError,
)
from jobact.contexts.reports.domain.report import ReportStateError
from jobact.contexts.visual_audits.domain.visual_audit import (
    VisualAuditStateError,
    VisualAuditValidationError,
)
from jobact.contracts.errors.v1.envelope import ApiError, ErrorDetail, ErrorEnvelope
from jobact.shared.application.authorization import AuthorizationError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ReportEvidenceIncompleteError)
    async def _handle_report_evidence_incomplete(
        request: Request, exc: ReportEvidenceIncompleteError
    ) -> JSONResponse:
        """409, not 422: the request body is well-formed -- it is the
        referenced visit's state that is not ready for analysis.
        """
        envelope = ErrorEnvelope(
            type="report-evidence-incomplete",
            title="Conflict",
            status=status.HTTP_409_CONFLICT,
            detail=str(exc),
            correlation_id=str(get_correlation_id(request)),
            errors=[
                ErrorDetail(loc=["evidence", item], message=f"{item} is required")
                for item in exc.missing
            ],
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT, content=envelope.model_dump()
        )

    @app.exception_handler(VisualAuditValidationError)
    async def _handle_visual_audit_validation(
        request: Request, exc: VisualAuditValidationError
    ) -> JSONResponse:
        envelope = ErrorEnvelope(
            type="visual-audit-validation",
            title="Unprocessable Entity",
            status=422,
            detail=str(exc),
            correlation_id=str(get_correlation_id(request)),
        )
        return JSONResponse(status_code=422, content=envelope.model_dump())

    @app.exception_handler(VisualAuditStateError)
    @app.exception_handler(ReportStateError)
    async def _handle_state_conflict(request: Request, exc: Exception) -> JSONResponse:
        envelope = ErrorEnvelope(
            type="state-conflict",
            title="Conflict",
            status=409,
            detail=str(exc),
            correlation_id=str(get_correlation_id(request)),
        )
        return JSONResponse(status_code=409, content=envelope.model_dump())

    @app.exception_handler(MediaVerificationError)
    async def _handle_media_verification_error(
        request: Request, exc: MediaVerificationError
    ) -> JSONResponse:
        envelope = ErrorEnvelope(
            type="media-verification-failed",
            title="Unprocessable Entity",
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
            correlation_id=str(get_correlation_id(request)),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=envelope.model_dump(),
        )

    @app.exception_handler(MediaUploadValidationError)
    async def _handle_media_upload_validation_error(
        request: Request, exc: MediaUploadValidationError
    ) -> JSONResponse:
        envelope = ErrorEnvelope(
            type="media-upload-validation",
            title="Unprocessable Entity",
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
            correlation_id=str(get_correlation_id(request)),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=envelope.model_dump(),
        )

    @app.exception_handler(AuthorizationError)
    async def _handle_authorization_error(
        request: Request, exc: AuthorizationError
    ) -> JSONResponse:
        envelope = ErrorEnvelope(
            type="forbidden",
            title="Forbidden",
            status=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
            correlation_id=str(get_correlation_id(request)),
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
            correlation_id=str(get_correlation_id(request)),
            errors=exc.errors,
        )
        return JSONResponse(
            status_code=exc.status,
            content=envelope.model_dump(),
            headers=exc.headers,
        )

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
            correlation_id=str(get_correlation_id(request)),
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
