"""`/api/v1/auth/*` routes: Google OAuth sign-in, session lookup, logout.

Kept thin per the layering rule: routes read/write HTTP concerns
(cookies, redirects, query params) and delegate everything else to
`SignInWithGoogleHandler`, the identity repositories, and the two small
Redis helpers (`OAuthStateStore`, `SessionCache`) -- no business logic
lives here.
"""

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
    """
    now = SystemClock().now()
    async with SqlAlchemyUnitOfWork() as uow:
        session_repo = SessionRepository(uow.session)
        session = await session_repo.get_by_id(principal.session_id)
        if session is not None:
            session.revoke(now)
            await session_repo.save(session)

    cache = SessionCache(get_redis_client())
    await cache.delete(principal.session_id)

    response = Response(status_code=204)
    response.delete_cookie(key=settings.session_cookie_name, path="/")
    return response
