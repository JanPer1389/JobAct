"""Integration tests for the `/api/v1/auth/*` routes against the real
FastAPI app, real Postgres, and real Redis.

Only the identity-provider side is faked (`FakeIdentityProvider`, swapped
in via `app.dependency_overrides`) -- same reasoning as
`test_sign_in_with_google.py`: Task 1.2's real `GoogleIdentityProvider`
needs a live Google OIDC round trip that has no place here. Everything
else (OAuth state storage, session storage, session cache, cookies) is
exercised for real.

Run with:
    docker compose up -d
    uv run alembic upgrade head
    uv run pytest tests/integration/test_auth_routes.py
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import delete

from jobact.apps.api.main import create_app
from jobact.apps.api.routers.auth import get_identity_provider
from jobact.contexts.identity.infrastructure.session_repository import SessionRepository
from jobact.shared.application.ports import ExternalIdentity
from jobact.shared.infrastructure.config import get_settings
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.identity_tables import (
    identities_table,
    memberships_table,
    organizations_table,
    sessions_table,
    user_profiles_table,
    users_table,
)
from jobact.shared.infrastructure.redis.client import (
    OAuthStateStore,
    SessionCache,
    get_redis_client,
)
from tests.fakes import FakeIdentityProvider

ALLOWED_ORIGIN = "http://localhost:3000"
FOREIGN_ORIGIN = "https://evil.example.com"


@dataclass
class AuthTestClient:
    http: AsyncClient
    identity_provider: FakeIdentityProvider


@pytest.fixture
async def clean_identity_tables() -> AsyncIterator[None]:
    session_factory = get_sessionmaker()

    async def _truncate() -> None:
        async with session_factory() as session, session.begin():
            await session.execute(delete(sessions_table))
            await session.execute(delete(memberships_table))
            await session.execute(delete(identities_table))
            await session.execute(delete(organizations_table))
            await session.execute(delete(user_profiles_table))
            await session.execute(delete(users_table))

    await _truncate()
    yield
    await _truncate()


@pytest.fixture
async def client(clean_identity_tables: None) -> AsyncIterator[AuthTestClient]:
    app = create_app()
    fake_identity_provider = FakeIdentityProvider()
    app.dependency_overrides[get_identity_provider] = lambda: fake_identity_provider

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="https://testserver", follow_redirects=False
    ) as http:
        yield AuthTestClient(http=http, identity_provider=fake_identity_provider)


async def _complete_google_sign_in(
    client: AuthTestClient,
) -> tuple[ExternalIdentity, Response]:
    """Seed Redis with the `state`->`nonce` mapping the way
    `/auth/google/start` would (simpler here than following a real
    redirect to Google), then hit the callback to complete sign-in.
    """
    state = "test-state"
    nonce = "test-nonce"
    await OAuthStateStore(get_redis_client()).put(state, nonce)

    external_identity = ExternalIdentity(
        subject=f"google-subject-{uuid4()}",
        email="ada@example.com",
        email_verified=True,
        name="Ada Lovelace",
        picture=None,
        nonce=nonce,
    )
    client.identity_provider.identities["test-code"] = external_identity

    response = await client.http.get(
        "/api/v1/auth/google/callback", params={"state": state, "code": "test-code"}
    )
    assert response.status_code == 302
    return external_identity, response


async def test_unseeded_oauth_state_is_rejected(client: AuthTestClient) -> None:
    response = await client.http.get(
        "/api/v1/auth/google/callback",
        params={"state": "never-seeded", "code": "unused"},
    )
    assert response.status_code == 400


async def test_callback_sets_httponly_session_cookie(client: AuthTestClient) -> None:
    settings = get_settings()

    _, response = await _complete_google_sign_in(client)

    set_cookie_headers = response.headers.get_list("set-cookie")
    session_cookie_headers = [
        header
        for header in set_cookie_headers
        if header.startswith(f"{settings.session_cookie_name}=")
    ]
    assert len(session_cookie_headers) == 1
    assert "HttpOnly" in session_cookie_headers[0]


async def test_get_session_returns_the_signed_in_user(client: AuthTestClient) -> None:
    await _complete_google_sign_in(client)

    response = await client.http.get("/api/v1/auth/session")

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "owner"
    assert "user_id" in body
    assert "organization_id" in body


async def test_logout_revokes_session_and_subsequent_session_lookup_401s(
    client: AuthTestClient,
) -> None:
    await _complete_google_sign_in(client)

    logout_response = await client.http.post(
        "/api/v1/auth/logout", headers={"origin": ALLOWED_ORIGIN}
    )
    assert logout_response.status_code == 204

    session_response = await client.http.get("/api/v1/auth/session")
    assert session_response.status_code == 401


async def test_logout_surfaces_error_and_still_revokes_session_when_cache_delete_fails(
    client: AuthTestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When Redis's `SessionCache.delete` keeps failing (simulated here by
    monkeypatching it to always raise -- the cleanest seam given the route
    instantiates `SessionCache(get_redis_client())` itself rather than via
    a FastAPI dependency), logout must NOT report success: Postgres is
    still the source of truth and its revoke must have landed, but the
    response must surface as an error rather than a silent 204 so a stale,
    still-cached session entry doesn't go unnoticed.
    """
    settings = get_settings()
    await _complete_google_sign_in(client)
    session_id = client.http.cookies.get(settings.session_cookie_name)
    assert session_id is not None

    async def _always_fails(self: SessionCache, session_id: str) -> None:
        raise ConnectionError("simulated Redis outage")

    monkeypatch.setattr(SessionCache, "delete", _always_fails)

    response = await client.http.post(
        "/api/v1/auth/logout", headers={"origin": ALLOWED_ORIGIN}
    )

    assert response.status_code != 204
    assert response.status_code >= 500

    session_factory = get_sessionmaker()
    async with session_factory() as pg_session:
        session = await SessionRepository(pg_session).get_by_id(session_id)
    assert session is not None
    assert session.revoked_at is not None


async def test_logout_with_foreign_origin_is_rejected(client: AuthTestClient) -> None:
    await _complete_google_sign_in(client)

    response = await client.http.post(
        "/api/v1/auth/logout", headers={"origin": FOREIGN_ORIGIN}
    )

    assert response.status_code == 403
