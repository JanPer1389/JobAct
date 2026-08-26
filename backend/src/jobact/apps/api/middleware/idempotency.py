"""`Idempotency-Key` middleware for mutating HTTP requests.

Lets a client safely retry a POST/PUT/PATCH/DELETE (e.g. after a dropped
connection) without double-executing it: send the same `Idempotency-Key`
header on the retry and, instead of the route running again, this
middleware replays the exact response captured the first time. The same
key reused with a genuinely different request body is rejected with 409
instead of being silently replayed or re-executed -- that combination
(key reused, body changed) almost certainly means a bug on the caller's
side, not a legitimate retry.

Implemented as `BaseHTTPMiddleware` rather than a `Depends()` dependency
because it needs to capture the ROUTE'S RESPONSE after it runs (to
persist it for future replay) as well as act before the route runs (to
replay-or-409 without running it a second time). A plain FastAPI
dependency only gets the "before" half of that; `call_next` is Starlette's
standard hook for wrapping the whole request/response cycle.

Scoped to whoever opts in by sending the header -- routes that don't send
it behave exactly as before.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import insert, select
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from jobact.apps.api.deps import try_resolve_principal
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.tables import idempotency_keys_table

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# No TTL was specified by the plan; 24h is a reasonable default per common
# idempotency-key conventions (e.g. Stripe's). Enforcing/purging expired
# keys is out of scope for this task -- this only records the value.
_KEY_TTL = timedelta(hours=24)

_CONFLICT_BODY = {
    "type": "idempotency-key-conflict",
    "title": "Conflict",
    "status": 409,
    "detail": "This Idempotency-Key was already used with a different request body.",
}


@dataclass(frozen=True)
class _IdempotencyRecord:
    request_hash: str
    response_status: int
    response_body: Any


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method not in _MUTATING_METHODS:
            return await call_next(request)

        idempotency_key = request.headers.get("idempotency-key")
        if not idempotency_key:
            return await call_next(request)

        # Resolving the caller's organization is this middleware's only
        # use for the principal -- an unauthenticated mutating request is
        # rejected by the route's own `get_current_principal` dependency
        # regardless, so pass through rather than raising here.
        principal = await try_resolve_principal(request)
        if principal is None:
            return await call_next(request)

        # Starlette caches the body after the first `.body()` read, so
        # downstream route handlers (which may call `.json()`/`.body()`
        # themselves) still see the same bytes.
        request_body = await request.body()
        request_hash = _compute_request_hash(
            endpoint=request.url.path,
            organization_id=principal.organization_id,
            body=request_body,
        )

        existing = await _get_idempotency_record(idempotency_key, principal.organization_id)
        if existing is not None:
            return _replay_or_conflict(existing, request_hash)

        response = await call_next(request)
        # `call_next` is typed as returning the public `Response`, but at
        # runtime `BaseHTTPMiddleware` always hands back its internal
        # `_StreamingResponse`, which does carry `body_iterator` -- mypy
        # can't see that subclass, hence the explicit ignore rather than
        # widening the type used everywhere else in this function.
        # `body_iterator` is typed to allow `str`/`memoryview` chunks too
        # (Starlette's general streaming contract), even though every route
        # in this codebase renders bytes today -- normalize defensively
        # rather than assume, so `b"".join(...)` can't raise on a chunk
        # type it doesn't expect.
        chunks: list[bytes] = []
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            elif isinstance(chunk, memoryview):
                chunk = bytes(chunk)
            chunks.append(chunk)
        response_body_bytes = b"".join(chunks)

        parsed_ok, parsed_body = _parse_response_body(response_body_bytes)
        if parsed_ok:
            await _store_idempotency_record(
                key=idempotency_key,
                organization_id=principal.organization_id,
                endpoint=request.url.path,
                request_hash=request_hash,
                response_status=response.status_code,
                response_body=parsed_body,
            )
        # else: response body wasn't JSON-decodable. Every route built so
        # far returns JSON (Pydantic models or error envelopes), so this
        # shouldn't happen in practice; if it ever does, don't crash the
        # request over it -- just skip persisting and return normally.

        return Response(
            content=response_body_bytes,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )


def _replay_or_conflict(existing: _IdempotencyRecord, request_hash: str) -> Response:
    if existing.request_hash != request_hash:
        return JSONResponse(status_code=409, content=_CONFLICT_BODY)

    if existing.response_body is None:
        # Covers e.g. a stored 204 No Content -- returning a JSONResponse
        # here would serialize `None` as a literal `b"null"` body, which
        # would not be byte-identical to the original empty body.
        return Response(status_code=existing.response_status)

    return JSONResponse(status_code=existing.response_status, content=existing.response_body)


def _compute_request_hash(*, endpoint: str, organization_id: UUID, body: bytes) -> str:
    hasher = hashlib.sha256()
    hasher.update(endpoint.encode("utf-8"))
    hasher.update(str(organization_id).encode("utf-8"))
    hasher.update(body)
    return hasher.hexdigest()


def _parse_response_body(raw: bytes) -> tuple[bool, Any]:
    """Returns `(ok, value)`. `ok` is False only when `raw` is non-empty
    and not valid JSON -- an empty body (e.g. a 204) is valid and parses
    to `None`.
    """
    if raw == b"":
        return True, None
    try:
        return True, json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False, None


async def _get_idempotency_record(key: str, organization_id: UUID) -> _IdempotencyRecord | None:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        result = await session.execute(
            select(
                idempotency_keys_table.c.request_hash,
                idempotency_keys_table.c.response_status,
                idempotency_keys_table.c.response_body,
            ).where(
                idempotency_keys_table.c.key == key,
                idempotency_keys_table.c.organization_id == organization_id,
            )
        )
        row = result.first()
    if row is None:
        return None
    return _IdempotencyRecord(
        request_hash=row.request_hash,
        response_status=row.response_status,
        response_body=row.response_body,
    )


async def _store_idempotency_record(
    *,
    key: str,
    organization_id: UUID,
    endpoint: str,
    request_hash: str,
    response_status: int,
    response_body: Any,
) -> None:
    now = datetime.now(UTC)
    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        await session.execute(
            insert(idempotency_keys_table).values(
                key=key,
                organization_id=organization_id,
                endpoint=endpoint,
                request_hash=request_hash,
                response_status=response_status,
                response_body=response_body,
                created_at=now,
                expires_at=now + _KEY_TTL,
            )
        )
