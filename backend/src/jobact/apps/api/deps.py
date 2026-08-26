"""FastAPI dependencies shared across `apps/api` routes.

`get_current_principal` is the auth dependency every protected route
uses: reads the session cookie, checks Redis's session cache as a fast
path, and falls back to Postgres (`SessionRepository` +
`MembershipRepository`) -- the source of truth -- on a cache miss.
`require_allowed_origin` is the `Origin` allowlist dependency applied to
mutating routes.
"""

from dataclasses import dataclass
from uuid import UUID

from fastapi import Request

from jobact.contexts.identity.infrastructure.membership_repository import (
    MembershipRepository,
)
from jobact.contexts.identity.infrastructure.session_repository import SessionRepository
from jobact.contracts.errors.v1.envelope import ApiError
from jobact.shared.infrastructure.clock import SystemClock
from jobact.shared.infrastructure.config import get_settings
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from jobact.shared.infrastructure.redis.client import SessionCache, get_redis_client


@dataclass(frozen=True)
class CurrentPrincipal:
    """The authenticated caller of the current request, resolved by
    `get_current_principal` from the session cookie.
    """

    session_id: str
    user_id: UUID
    organization_id: UUID
    role: str


def _unauthenticated(detail: str) -> ApiError:
    return ApiError(
        status=401, type="unauthenticated", title="Unauthenticated", detail=detail
    )


async def get_current_principal(request: Request) -> CurrentPrincipal:
    """Resolve the caller's session from the `session_cookie_name` cookie.

    Fast path: Redis's `SessionCache`, keyed by session id -- present only
    while the session is both unexpired and un-revoked (logout explicitly
    deletes the entry, so a cache hit is safe to trust without an extra
    Postgres round trip). Cache miss (never cached, expired TTL, or
    deleted on logout) falls back to Postgres, the source of truth:
    `SessionRepository.get_by_id` + `Session.is_active(now)`.
    """
    settings = get_settings()
    session_id = request.cookies.get(settings.session_cookie_name)
    if not session_id:
        raise _unauthenticated("No session cookie present.")

    cache = SessionCache(get_redis_client())
    cached = await cache.get(session_id)
    if cached is not None:
        return CurrentPrincipal(
            session_id=session_id,
            user_id=UUID(cached["user_id"]),
            organization_id=UUID(cached["organization_id"]),
            role=cached["role"],
        )

    async with SqlAlchemyUnitOfWork() as uow:
        session = await SessionRepository(uow.session).get_by_id(session_id)
        if session is None or not session.is_active(SystemClock().now()):
            raise _unauthenticated("Session not found, expired, or revoked.")

        membership = await MembershipRepository(uow.session).get_by_user_id(
            session.user_id
        )
        role = membership.role if membership is not None else ""

    principal = CurrentPrincipal(
        session_id=session.id,
        user_id=session.user_id,
        organization_id=session.organization_id,
        role=role,
    )
    remaining_ttl = int((session.expires_at - SystemClock().now()).total_seconds())
    await cache.put(
        session_id,
        user_id=str(principal.user_id),
        organization_id=str(principal.organization_id),
        role=principal.role,
        ttl_seconds=remaining_ttl,
    )
    return principal


async def require_allowed_origin(request: Request) -> None:
    """Reject mutating requests whose `Origin` header is missing or not
    in `Settings.app_origins_list`.
    """
    settings = get_settings()
    origin = request.headers.get("origin")
    if origin is None or origin not in settings.app_origins_list:
        raise ApiError(
            status=403,
            type="forbidden-origin",
            title="Forbidden",
            detail="Request Origin is missing or not allowed.",
        )
