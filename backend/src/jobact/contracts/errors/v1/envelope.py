"""The v1 HTTP error envelope shape, and a small exception type routes
can raise to produce it.

Pydantic-only (plus stdlib): no FastAPI imports here, no route logic --
the actual exception handler that turns `ApiError` into an HTTP
response lives in `apps/api` (the outermost layer), not here.
"""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """One item of the envelope's `errors` list -- e.g. a single field
    validation failure. Kept generic (`loc`/`message`) so it covers both
    FastAPI's own `RequestValidationError` items and any future
    domain-specific validation error this codebase adds.
    """

    loc: list[str | int] = []
    message: str


class ErrorEnvelope(BaseModel):
    """The error-response body shape used by every route in this API:
    `{ type, title, status, detail, correlation_id, errors }`.
    """

    type: str
    title: str
    status: int
    detail: str
    correlation_id: str
    errors: list[ErrorDetail] = []


class ApiError(Exception):
    """Raise this from route/dependency code to produce an
    `ErrorEnvelope` response via the handler registered in
    `apps/api/main.py`.

    `type` is a short machine-readable slug (e.g. `"unauthenticated"`,
    `"forbidden-origin"`), not a URI -- this codebase has no error-type
    documentation to link to yet, so a slug is a reasonable minimum.
    """

    def __init__(
        self,
        *,
        status: int,
        type: str,
        title: str,
        detail: str,
        errors: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.type = type
        self.title = title
        self.detail = detail
        self.errors = errors or []
