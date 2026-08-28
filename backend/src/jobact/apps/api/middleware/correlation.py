"""Request-scoped correlation id.

One id per request, echoed back to the caller and carried into the
workflow run a request starts, so worker-side logs for that job can be
tied back to the HTTP request that triggered it.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

HEADER_NAME = "X-Correlation-Id"

_correlation_id: ContextVar[uuid.UUID | None] = ContextVar(
    "correlation_id", default=None
)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        correlation_id = _parse(request.headers.get(HEADER_NAME))
        request.state.correlation_id = correlation_id
        token = _correlation_id.set(correlation_id)
        try:
            response = await call_next(request)
        finally:
            _correlation_id.reset(token)
        response.headers[HEADER_NAME] = str(correlation_id)
        return response


def get_correlation_id(request: Request) -> uuid.UUID:
    """The current request's correlation id, minting one if the middleware
    did not run (e.g. a route exercised directly in a test).
    """
    existing = getattr(request.state, "correlation_id", None)
    if isinstance(existing, uuid.UUID):
        return existing
    return _correlation_id.get() or uuid.uuid4()


def _parse(raw: str | None) -> uuid.UUID:
    # A client may send any string; only a real UUID is usable, since the
    # workflow run stores it in a UUID column.
    try:
        return uuid.UUID(raw) if raw else uuid.uuid4()
    except ValueError:
        return uuid.uuid4()
