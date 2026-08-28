"""Authentication routes for local credentials, Google OIDC, and sessions."""

import asyncio
import secrets
from functools import lru_cache
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse

from jobact.apps.api.deps import (
    CurrentPrincipal,
    get_current_principal,
    require_allowed_origin,
    try_resolve_principal,
)
from jobact.contexts.identity.application.authentication import AuthenticationResult
from jobact.contexts.identity.application.link_google_identity import (
    GoogleIdentityAlreadyLinkedError,
    LinkGoogleIdentityHandler,
)
from jobact.contexts.identity.application.register_with_password import (
    AccountAlreadyExistsError,
    RegisterWithPasswordHandler,
)
from jobact.contexts.identity.application.set_or_change_password import (
    CurrentPasswordRequiredError,
    SetOrChangePasswordHandler,
)
from jobact.contexts.identity.application.sign_in_with_google import (
    GoogleAccountLinkRequiredError,
    InvalidNonceError,
    SignInWithGoogleHandler,
)
from jobact.contexts.identity.application.sign_in_with_password import (
    InvalidCredentialsError,
    SignInWithPasswordHandler,
)
from jobact.contexts.identity.domain.local_credential import PasswordPolicyError
from jobact.contexts.identity.infrastructure.local_credential_repository import (
    LocalCredentialRepository,
)
from jobact.contexts.identity.infrastructure.password_hasher import (
    Argon2idPasswordHasher,
)
from jobact.contexts.identity.infrastructure.session_repository import SessionRepository
from jobact.contexts.identity.infrastructure.user_repository import UserRepository
from jobact.contracts.errors.v1.envelope import ApiError
from jobact.contracts.http.v1.auth import (
    AuthMethodsResponse,
    CurrencyUpdateRequest,
    LocaleUpdateRequest,
    LoginRequest,
    PasswordUpdateRequest,
    RegisterRequest,
    SessionResponse,
)
from jobact.shared.application.ports import IdentityProvider, PasswordHasher
from jobact.shared.infrastructure.clock import SystemClock
from jobact.shared.infrastructure.config import Settings, get_settings
from jobact.shared.infrastructure.id_generator import UuidIdGenerator
from jobact.shared.infrastructure.identity_provider.google import GoogleIdentityProvider
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from jobact.shared.infrastructure.redis.client import (
    AuthRateLimiter,
    OAuthAttempt,
    OAuthStateStore,
    SessionCache,
    get_redis_client,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_SESSION_TTL_SECONDS = 30 * 24 * 60 * 60
_CACHE_DELETE_ATTEMPTS = 3
_CACHE_DELETE_RETRY_DELAY_SECONDS = 0.1


class LogoutCacheDeleteFailedError(Exception):
    def __init__(self, session_cookie_name: str) -> None:
        super().__init__(
            "Failed to delete the session's Redis cache entry after retries."
        )
        self.session_cookie_name = session_cookie_name


def get_identity_provider(
    settings: Settings = Depends(get_settings),
) -> IdentityProvider:
    return GoogleIdentityProvider(settings)


@lru_cache
def get_password_hasher() -> PasswordHasher:
    return Argon2idPasswordHasher()


def get_auth_rate_limiter() -> AuthRateLimiter:
    return AuthRateLimiter(get_redis_client())


async def _enforce_rate_limit(
    request: Request,
    limiter: AuthRateLimiter,
    *,
    action: str,
    limit: int,
    window_seconds: int,
) -> None:
    client_host = request.client.host if request.client else "unknown"
    try:
        retry_after = await limiter.check(
            f"{action}:{client_host}", limit=limit, window_seconds=window_seconds
        )
    except Exception as exc:
        raise ApiError(
            status=503,
            type="auth-throttle-unavailable",
            title="Service Unavailable",
            detail="Authentication is temporarily unavailable. Please try again.",
        ) from exc
    if retry_after is not None:
        raise ApiError(
            status=429,
            type="rate-limit-exceeded",
            title="Too Many Requests",
            detail="Too many authentication attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


async def _establish_session(
    response: Response,
    result: AuthenticationResult,
    settings: Settings,
) -> SessionResponse:
    await SessionCache(get_redis_client()).put(
        result.session_id,
        user_id=str(result.user_id),
        organization_id=str(result.organization_id),
        role=result.role,
        ttl_seconds=_SESSION_TTL_SECONDS,
    )
    response.set_cookie(
        key=settings.session_cookie_name,
        value=result.session_id,
        httponly=True,
        samesite="lax",
        secure=True,
        path="/",
        max_age=_SESSION_TTL_SECONDS,
    )
    async with SqlAlchemyUnitOfWork() as uow:
        user = await UserRepository(uow.session).get_by_id(result.user_id)
    assert user is not None
    return SessionResponse(
        user_id=result.user_id,
        organization_id=result.organization_id,
        role=result.role,
        locale=user.locale,
        currency=user.currency,
    )


@router.post(
    "/register",
    response_model=SessionResponse,
    status_code=201,
    dependencies=[Depends(require_allowed_origin)],
)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    limiter: AuthRateLimiter = Depends(get_auth_rate_limiter),
) -> SessionResponse:
    await _enforce_rate_limit(
        request, limiter, action="register", limit=5, window_seconds=60 * 60
    )
    handler = RegisterWithPasswordHandler(
        SqlAlchemyUnitOfWork(), password_hasher, SystemClock(), UuidIdGenerator()
    )
    try:
        result = await handler.handle(str(body.email), body.password)
    except AccountAlreadyExistsError as exc:
        raise ApiError(
            status=409,
            type="account-exists",
            title="Account Exists",
            detail="An account already exists; sign in instead.",
        ) from exc
    except PasswordPolicyError as exc:
        raise ApiError(
            status=422,
            type="password-policy",
            title="Unprocessable Entity",
            detail=str(exc),
        ) from exc
    return await _establish_session(response, result, settings)


@router.post(
    "/login",
    response_model=SessionResponse,
    dependencies=[Depends(require_allowed_origin)],
)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    limiter: AuthRateLimiter = Depends(get_auth_rate_limiter),
) -> SessionResponse:
    await _enforce_rate_limit(
        request, limiter, action="login", limit=10, window_seconds=5 * 60
    )
    handler = SignInWithPasswordHandler(
        SqlAlchemyUnitOfWork(), password_hasher, SystemClock(), UuidIdGenerator()
    )
    try:
        result = await handler.handle(str(body.email), body.password)
    except InvalidCredentialsError as exc:
        raise ApiError(
            status=401,
            type="invalid-credentials",
            title="Unauthenticated",
            detail="Invalid email or password.",
        ) from exc
    return await _establish_session(response, result, settings)


@router.get("/methods", response_model=AuthMethodsResponse)
async def auth_methods(
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> AuthMethodsResponse:
    async with SqlAlchemyUnitOfWork() as uow:
        user = await UserRepository(uow.session).get_by_id(principal.user_id)
        credential = await LocalCredentialRepository(uow.session).get_by_user_id(
            principal.user_id
        )
    return AuthMethodsResponse(
        password=credential is not None,
        google=user is not None and user.has_linked_identity("google"),
    )


@router.put(
    "/password",
    status_code=204,
    dependencies=[Depends(require_allowed_origin)],
)
async def update_password(
    body: PasswordUpdateRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> Response:
    handler = SetOrChangePasswordHandler(
        SqlAlchemyUnitOfWork(), password_hasher, SystemClock(), UuidIdGenerator()
    )
    try:
        await handler.handle(
            principal.user_id, body.current_password, body.new_password
        )
    except CurrentPasswordRequiredError as exc:
        raise ApiError(
            status=401,
            type="invalid-current-password",
            title="Unauthenticated",
            detail="The current password is incorrect.",
        ) from exc
    except PasswordPolicyError as exc:
        raise ApiError(
            status=422,
            type="password-policy",
            title="Unprocessable Entity",
            detail=str(exc),
        ) from exc
    return Response(status_code=204)


@router.put("/locale", status_code=204, dependencies=[Depends(require_allowed_origin)])
async def update_locale(
    body: LocaleUpdateRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> Response:
    async with SqlAlchemyUnitOfWork() as uow:
        repository = UserRepository(uow.session)
        user = await repository.get_by_id(principal.user_id)
        if user is None:
            raise ApiError(status=401, type="unauthenticated", title="Unauthenticated", detail="User not found.")
        user.change_locale(body.locale)
        await repository.save(user)
    return Response(status_code=204)


@router.put("/currency", status_code=204, dependencies=[Depends(require_allowed_origin)])
async def update_currency(
    body: CurrencyUpdateRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> Response:
    async with SqlAlchemyUnitOfWork() as uow:
        repository = UserRepository(uow.session)
        user = await repository.get_by_id(principal.user_id)
        if user is None:
            raise ApiError(status=401, type="unauthenticated", title="Unauthenticated", detail="User not found.")
        user.change_currency(body.currency)
        await repository.save(user)
    return Response(status_code=204)


@router.get("/google/start")
async def google_start(
    identity_provider: IdentityProvider = Depends(get_identity_provider),
) -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    await OAuthStateStore(get_redis_client()).put(state, nonce)
    return RedirectResponse(
        url=identity_provider.authorization_url(state, nonce), status_code=302
    )


@router.get("/google/link/start")
async def google_link_start(
    principal: CurrentPrincipal = Depends(get_current_principal),
    identity_provider: IdentityProvider = Depends(get_identity_provider),
) -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    await OAuthStateStore(get_redis_client()).put(
        state,
        nonce,
        operation="link_google",
        user_id=str(principal.user_id),
        session_id=principal.session_id,
    )
    return RedirectResponse(
        url=identity_provider.authorization_url(state, nonce), status_code=302
    )


def _frontend_redirect(settings: Settings, **params: str) -> str:
    origin = settings.app_origins_list[0] if settings.app_origins_list else "/"
    return f"{origin}?{urlencode(params)}" if params else origin


@router.get("/google/callback")
async def google_callback(
    request: Request,
    state: str,
    code: str,
    identity_provider: IdentityProvider = Depends(get_identity_provider),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    attempt = await OAuthStateStore(get_redis_client()).pop(state)
    if attempt is None:
        raise ApiError(
            status=400,
            type="invalid-oauth-state",
            title="Bad Request",
            detail="OAuth state is missing, expired, or has already been used.",
        )
    if attempt.operation == "link_google":
        return await _complete_google_link(
            request, attempt, code, identity_provider, settings
        )

    handler = SignInWithGoogleHandler(
        SqlAlchemyUnitOfWork(),
        identity_provider,
        SystemClock(),
        UuidIdGenerator(),
    )
    try:
        result = await handler.handle(code, expected_nonce=attempt.nonce)
    except InvalidNonceError as exc:
        raise ApiError(
            status=401,
            type="invalid-oauth-nonce",
            title="Unauthenticated",
            detail="ID token nonce did not match the expected value.",
        ) from exc
    except GoogleAccountLinkRequiredError:
        return RedirectResponse(
            _frontend_redirect(settings, auth_error="google-link-required"),
            status_code=302,
        )

    response = RedirectResponse(_frontend_redirect(settings), status_code=302)
    await _establish_session(response, result, settings)
    return response


async def _complete_google_link(
    request: Request,
    attempt: OAuthAttempt,
    code: str,
    identity_provider: IdentityProvider,
    settings: Settings,
) -> RedirectResponse:
    principal = await try_resolve_principal(request)
    if (
        principal is None
        or str(principal.user_id) != attempt.user_id
        or principal.session_id != attempt.session_id
    ):
        return RedirectResponse(
            _frontend_redirect(settings, auth_link="session-mismatch"),
            status_code=302,
        )
    try:
        await LinkGoogleIdentityHandler(
            SqlAlchemyUnitOfWork(), identity_provider
        ).handle(principal.user_id, code, attempt.nonce)
    except InvalidNonceError:
        return RedirectResponse(
            _frontend_redirect(settings, auth_link="invalid-nonce"), status_code=302
        )
    except GoogleIdentityAlreadyLinkedError:
        return RedirectResponse(
            _frontend_redirect(settings, auth_link="already-linked"), status_code=302
        )
    return RedirectResponse(
        _frontend_redirect(settings, auth_link="google-success"), status_code=302
    )


@router.get("/session", response_model=SessionResponse)
async def get_session(
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> SessionResponse:
    async with SqlAlchemyUnitOfWork() as uow:
        user = await UserRepository(uow.session).get_by_id(principal.user_id)
    if user is None:
        raise ApiError(status=401, type="unauthenticated", title="Unauthenticated", detail="User not found.")
    return SessionResponse(
        user_id=principal.user_id,
        organization_id=principal.organization_id,
        role=principal.role,
        locale=user.locale,
        currency=user.currency,
    )


@router.post("/logout", status_code=204, dependencies=[Depends(require_allowed_origin)])
async def logout(
    principal: CurrentPrincipal = Depends(get_current_principal),
    settings: Settings = Depends(get_settings),
) -> Response:
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
    for attempt_number in range(_CACHE_DELETE_ATTEMPTS):
        try:
            await cache.delete(principal.session_id)
            last_error = None
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt_number < _CACHE_DELETE_ATTEMPTS - 1:
                await asyncio.sleep(delay_seconds)
                delay_seconds *= 2

    if last_error is not None:
        raise LogoutCacheDeleteFailedError(settings.session_cookie_name) from last_error

    response = Response(status_code=204)
    response.delete_cookie(key=settings.session_cookie_name, path="/")
    return response
