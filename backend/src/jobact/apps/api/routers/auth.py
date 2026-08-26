"""`/api/v1/auth/*` routes: Google OAuth sign-in, session lookup, logout.

Kept thin per the layering rule: routes read/write HTTP concerns
(cookies, redirects, query params) and delegate everything else to
`SignInWithGoogleHandler`, the identity repositories, and the two small
Redis helpers (`OAuthStateStore`, `SessionCache`) -- no business logic
lives here.
"""

import asyncio
import secrets

from fastapi import APIRouter, Depends, Response
from fastapi.responses import RedirectResponse

from jobact.apps.api.deps import (
    CurrentPrincipal,
    get_current_principal,
    require_allowed_origin,
)
from jobact.contexts.identity.application.sign_in_with_google import (
    InvalidNonceError,
    SignInWithGoogleHandler,
)
from jobact.contexts.identity.infrastructure.session_repository import SessionRepository
from jobact.contracts.errors.v1.envelope import ApiError
from jobact.contracts.http.v1.auth import SessionResponse
from jobact.shared.application.ports import IdentityProvider
from jobact.shared.infrastructure.clock import SystemClock
from jobact.shared.infrastructure.config import Settings, get_settings
from jobact.shared.infrastructure.id_generator import UuidIdGenerator
from jobact.shared.infrastructure.identity_provider.google import GoogleIdentityProvider
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from jobact.shared.infrastructure.redis.client import (
    OAuthStateStore,
    SessionCache,
    get_redis_client,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_CACHE_DELETE_ATTEMPTS = 3
_CACHE_DELETE_RETRY_DELAY_SECONDS = 0.1


class LogoutCacheDeleteFailedError(Exception):
    """Raised by `logout` when deleting the session's Redis cache entry
    keeps failing after retries.

    Postgres (the source of truth) has already been revoked by the time
    this is raised -- this only means the Redis fast-path cache used by
    `deps.get_current_principal` may still hold a stale, still-trusted
    copy of the session for up to the remainder of its TTL. That has to
    be surfaced as a real failure (not a silent 204) so it's visible to
    monitoring/logs instead of quietly leaving a stale cache entry
    unnoticed.

    Carries `session_cookie_name` so the dedicated handler in
    `apps/api/error_handlers.py` can still clear the client's cookie on
    the resulting error response -- once the client's own cookie is
    gone, the only way the stale cache entry could be presented to
    `get_current_principal` is by a request that independently obtained
    or replayed that session id, not by the legitimate client's own
    subsequent requests.
    """

    def __init__(self, session_cookie_name: str) -> None:
        super().__init__(
            "Failed to delete the session's Redis cache entry after retries."
        )
        self.session_cookie_name = session_cookie_name


def get_identity_provider(
    settings: Settings = Depends(get_settings),
) -> IdentityProvider:
    """Constructs the real `GoogleIdentityProvider` from `Settings`.

    A FastAPI dependency (not a module-level singleton) specifically so
    tests can swap in `FakeIdentityProvider` via
    `app.dependency_overrides[get_identity_provider]` without touching
    real Google endpoints.
    """
    return GoogleIdentityProvider(settings)


@router.get("/google/start")
async def google_start(
    identity_provider: IdentityProvider = Depends(get_identity_provider),
) -> RedirectResponse:
    """Start the Google OAuth flow: generate `state`/`nonce`, stash the
    expected nonce in Redis for 5 minutes keyed by `state`, and redirect
    the caller to Google's authorization endpoint.
    """
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)

    state_store = OAuthStateStore(get_redis_client())
    await state_store.put(state, nonce)

    authorization_url = identity_provider.authorization_url(state, nonce)
    return RedirectResponse(url=authorization_url, status_code=302)


@router.get("/google/callback")
async def google_callback(
    state: str,
    code: str,
    identity_provider: IdentityProvider = Depends(get_identity_provider),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """Complete the Google OAuth flow: consume the one-time `state`,
    exchange `code` for a verified identity, sign the user in, and set
    the session cookie.

    Judgment call: an unknown/expired/already-consumed `state` returns
    400 (malformed client request), while a verified-but-mismatched
    `nonce` (an `InvalidNonceError` from the handler -- a possible
    replay/CSRF attempt) returns 401, since that is genuinely an
    authentication failure rather than a bad request shape.
    """
    state_store = OAuthStateStore(get_redis_client())
    expected_nonce = await state_store.pop(state)
    if expected_nonce is None:
        raise ApiError(
            status=400,
            type="invalid-oauth-state",
            title="Bad Request",
            detail="OAuth state is missing, expired, or has already been used.",
        )

    handler = SignInWithGoogleHandler(
        uow=SqlAlchemyUnitOfWork(),
        identity_provider=identity_provider,
        clock=SystemClock(),
        id_generator=UuidIdGenerator(),
    )
    try:
        result = await handler.handle(code, expected_nonce=expected_nonce)
    except InvalidNonceError as exc:
        raise ApiError(
            status=401,
            type="invalid-oauth-nonce",
            title="Unauthenticated",
            detail="ID token nonce did not match the expected value for this sign-in attempt.",
        ) from exc

    ttl_seconds = 30 * 24 * 60 * 60
    cache = SessionCache(get_redis_client())
    await cache.put(
        result.session_id,
        user_id=str(result.user_id),
        organization_id=str(result.organization_id),
        role=result.role,
        ttl_seconds=ttl_seconds,
    )

    frontend_origin = settings.app_origins_list[0] if settings.app_origins_list else "/"
    response = RedirectResponse(url=frontend_origin, status_code=302)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=result.session_id,
        httponly=True,
        samesite="lax",
        secure=True,
        path="/",
        max_age=ttl_seconds,
    )
    return response


@router.get("/session", response_model=SessionResponse)
async def get_session(
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> SessionResponse:
    return SessionResponse(
        user_id=principal.user_id,
        organization_id=principal.organization_id,
        role=principal.role,
    )


@router.post("/logout", status_code=204, dependencies=[Depends(require_allowed_origin)])
async def logout(
    principal: CurrentPrincipal = Depends(get_current_principal),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Revoke the current session (Postgres is the record of truth),
    drop its Redis cache entry, and clear the cookie.

    The Postgres revoke is the security-relevant state and always
    happens first, unconditionally. Deleting the Redis cache entry is
    then retried a few times before giving up: if it still fails, this
    raises `LogoutCacheDeleteFailedError` instead of returning 204, so
    the failure is loud rather than silently leaving a stale-but-trusted
    cache entry in place. The cookie is cleared either way -- on the
    happy path directly below, and on total cache-delete failure by the
    dedicated exception handler in `apps/api/error_handlers.py` (the
    route itself no longer controls the response once it raises).
    """
    now = SystemClock().now()
    async with SqlAlchemyUnitOfWork() as uow:
        session_repo = SessionRepository(uow.session)
        session = await session_repo.get_by_id(principal.session_id)
        if session is not None:
            session.revoke(now)
            await session_repo.save(session)

    cache = SessionCache(get_redis_client())
    delay_seconds = _CACHE_DELETE_RETRY_DELAY_SECONDS
    last_error: Exception | None = None
    for attempt in range(_CACHE_DELETE_ATTEMPTS):
        try:
            await cache.delete(principal.session_id)
            last_error = None
            break
        except Exception as exc:  # noqa: BLE001 -- retried below, re-raised if exhausted
            last_error = exc
            if attempt < _CACHE_DELETE_ATTEMPTS - 1:
                await asyncio.sleep(delay_seconds)
                delay_seconds *= 2

    if last_error is not None:
        raise LogoutCacheDeleteFailedError(settings.session_cookie_name) from last_error

    response = Response(status_code=204)
    response.delete_cookie(key=settings.session_cookie_name, path="/")
    return response
