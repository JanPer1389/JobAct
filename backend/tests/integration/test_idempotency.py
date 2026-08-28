"""Integration tests for `IdempotencyMiddleware` against real Postgres
and Redis.

Two scenarios, per the task brief:

1. Replay: an identical mutating request sent twice with the same
   `Idempotency-Key` must execute the route handler exactly ONCE -- the
   second call gets back the byte-identical first response without the
   handler running again. Proven with a tiny test-only route with an
   observable side effect (an in-memory counter) rather than `/auth/logout`,
   since logout already tolerates being called twice at the domain level
   (calling it on an already-revoked session is a graceful no-op) -- that
   would mask a broken idempotency middleware that let the handler run
   twice, so it isn't decisive proof on its own.
2. Conflict: the same `Idempotency-Key` reused with a genuinely different
   request body gets a 409, without executing the route a second time
   either. `/auth/logout` has no request body to vary, so this also uses
   the test-only route.

The test-only route is mounted on a small dedicated `FastAPI()` app
wrapping `IdempotencyMiddleware` directly (per the brief's suggested
approach (b)) rather than added to the real router -- it exists purely to
observe the middleware's behavior and has no place in the real API surface.
Authentication for it reuses a real session cookie obtained by signing in
through the real app's `/auth/google/callback` (via `FakeIdentityProvider`),
since `try_resolve_principal` reads the cookie against real Redis/Postgres
session storage regardless of which ASGI app made the request.

Run with:
    docker compose up -d
    uv run alembic upgrade head
    uv run pytest tests/integration/test_idempotency.py
"""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from jobact.apps.api.deps import CurrentPrincipal, get_current_principal
from jobact.apps.api.main import create_app
from jobact.apps.api.middleware.idempotency import IdempotencyMiddleware
from jobact.apps.api.routers.auth import get_identity_provider
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
from jobact.shared.infrastructure.postgres.tables import idempotency_keys_table
from jobact.shared.infrastructure.redis.client import OAuthStateStore, get_redis_client
from tests.fakes import FakeIdentityProvider


@dataclass
class Handlers:
    """Observable side effects for the test-only route: `calls` records
    every invocation, so a test can assert the handler ran exactly once
    despite two identical requests reaching the middleware.
    """

    calls: list[dict]


def _make_test_app() -> tuple[FastAPI, Handlers]:
    app = FastAPI()
    app.add_middleware(IdempotencyMiddleware)
    handlers = Handlers(calls=[])

    @app.post("/test/echo")
    async def echo(
        body: dict,
        principal: CurrentPrincipal = Depends(get_current_principal),
    ) -> dict:
        handlers.calls.append(body)
        return {"received": body, "call_count": len(handlers.calls)}

    return app, handlers


def _make_anonymous_test_app() -> tuple[FastAPI, Handlers]:
    """Like `_make_test_app`, but the route takes no principal -- models
    the unauthenticated mutations the middleware must also protect
    (`/auth/register`, `/auth/login`): no session cookie exists yet for
    `try_resolve_principal` to resolve.
    """
    app = FastAPI()
    app.add_middleware(IdempotencyMiddleware)
    handlers = Handlers(calls=[])

    @app.post("/test/anonymous-echo")
    async def echo(body: dict) -> dict:
        handlers.calls.append(body)
        return {"received": body, "call_count": len(handlers.calls)}

    return app, handlers


@pytest.fixture
async def clean_tables() -> AsyncIterator[None]:
    session_factory = get_sessionmaker()

    async def _truncate() -> None:
        async with session_factory() as session, session.begin():
            await session.execute(delete(idempotency_keys_table))
            await session.execute(delete(sessions_table))
            await session.execute(delete(memberships_table))
            await session.execute(delete(identities_table))
            await session.execute(delete(organizations_table))
            await session.execute(delete(user_profiles_table))
            await session.execute(delete(users_table))

    await _truncate()
    yield
    await _truncate()


async def _sign_in_and_get_session_cookie(clean_tables: None) -> str:
    """Signs in through the real app (real Redis + Postgres session
    storage) and returns the raw session cookie value, for reuse against
    the dedicated test-only app below.
    """
    app = create_app()
    fake_identity_provider = FakeIdentityProvider()
    app.dependency_overrides[get_identity_provider] = lambda: fake_identity_provider

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
    fake_identity_provider.identities["test-code"] = external_identity

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="https://testserver", follow_redirects=False
    ) as http:
        response = await http.get(
            "/api/v1/auth/google/callback", params={"state": state, "code": "test-code"}
        )
        assert response.status_code == 302
        settings = get_settings()
        session_cookie = response.cookies.get(settings.session_cookie_name)
        assert session_cookie is not None
        return session_cookie


async def test_identical_request_with_same_idempotency_key_replays_without_rerunning_handler(
    clean_tables: None,
) -> None:
    session_cookie = await _sign_in_and_get_session_cookie(clean_tables)
    settings = get_settings()
    test_app, handlers = _make_test_app()

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="https://testserver") as http:
        http.cookies.set(settings.session_cookie_name, session_cookie)
        idempotency_key = f"key-{uuid4()}"
        payload = {"amount": 42}

        first = await http.post(
            "/test/echo", json=payload, headers={"Idempotency-Key": idempotency_key}
        )
        second = await http.post(
            "/test/echo", json=payload, headers={"Idempotency-Key": idempotency_key}
        )

    assert first.status_code == 200
    assert second.status_code == 200
    # Byte-identical response.
    assert first.content == second.content
    assert first.headers.get("content-type") == second.headers.get("content-type")

    # The decisive proof: the route handler body executed exactly ONCE.
    # If the middleware were broken and let the second request through,
    # `call_count` in the second response would read 2, and `handlers.calls`
    # would have two entries -- not "looks the same", but "didn't run twice".
    assert handlers.calls == [payload]
    assert second.json()["call_count"] == 1

    # And exactly one row was persisted for this key.
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        result = await session.execute(
            select(idempotency_keys_table).where(
                idempotency_keys_table.c.key == idempotency_key
            )
        )
        rows = result.fetchall()
    assert len(rows) == 1


async def test_same_idempotency_key_with_different_body_returns_409_and_does_not_rerun_handler(
    clean_tables: None,
) -> None:
    session_cookie = await _sign_in_and_get_session_cookie(clean_tables)
    settings = get_settings()
    test_app, handlers = _make_test_app()

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="https://testserver") as http:
        http.cookies.set(settings.session_cookie_name, session_cookie)
        idempotency_key = f"key-{uuid4()}"

        first = await http.post(
            "/test/echo",
            json={"amount": 42},
            headers={"Idempotency-Key": idempotency_key},
        )
        second = await http.post(
            "/test/echo",
            json={"amount": 999},
            headers={"Idempotency-Key": idempotency_key},
        )

    assert first.status_code == 200
    assert second.status_code == 409
    body = second.json()
    assert body["type"] == "idempotency-key-conflict"
    assert body["status"] == 409

    # The conflicting second call must not have reached the route handler.
    assert handlers.calls == [{"amount": 42}]


async def test_request_without_idempotency_key_header_is_unaffected(
    clean_tables: None,
) -> None:
    """Sanity check that the header stays opt-in: two identical requests
    with NO `Idempotency-Key` header both execute the handler normally.
    """
    session_cookie = await _sign_in_and_get_session_cookie(clean_tables)
    settings = get_settings()
    test_app, handlers = _make_test_app()

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="https://testserver") as http:
        http.cookies.set(settings.session_cookie_name, session_cookie)
        payload = {"amount": 1}

        first = await http.post("/test/echo", json=payload)
        second = await http.post("/test/echo", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(handlers.calls) == 2


async def test_unauthenticated_request_is_also_protected_by_idempotency(
    clean_tables: None,
) -> None:
    """Regression test: the middleware used to skip idempotency entirely
    for any request it couldn't resolve a principal for
    (`if principal is None: return await call_next(request)`), which left
    genuinely unauthenticated mutations -- `/auth/register`, `/auth/login`
    -- completely unprotected, including from the very race this whole
    middleware exists to prevent. Unauthenticated requests are now scoped
    under a shared anonymous organization id instead of skipping the
    middleware.
    """
    test_app, handlers = _make_anonymous_test_app()

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="https://testserver") as http:
        idempotency_key = f"key-{uuid4()}"
        payload = {"email": "new-user@example.com"}

        first = await http.post(
            "/test/anonymous-echo",
            json=payload,
            headers={"Idempotency-Key": idempotency_key},
        )
        second = await http.post(
            "/test/anonymous-echo",
            json=payload,
            headers={"Idempotency-Key": idempotency_key},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.content == second.content
    assert handlers.calls == [payload]
    assert second.json()["call_count"] == 1


async def test_concurrent_same_key_requests_execute_the_handler_once(
    clean_tables: None,
) -> None:
    session_cookie = await _sign_in_and_get_session_cookie(clean_tables)
    settings = get_settings()
    app = FastAPI()
    app.add_middleware(IdempotencyMiddleware)
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    @app.post("/test/concurrent")
    async def concurrent_handler(
        principal: CurrentPrincipal = Depends(get_current_principal),
    ) -> dict:
        nonlocal calls
        calls += 1
        entered.set()
        await release.wait()
        return {"call_count": calls}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://testserver") as http:
        http.cookies.set(settings.session_cookie_name, session_cookie)
        headers = {"Idempotency-Key": f"key-{uuid4()}"}
        first_task = asyncio.create_task(http.post("/test/concurrent", headers=headers))
        await entered.wait()
        second_task = asyncio.create_task(http.post("/test/concurrent", headers=headers))
        await asyncio.sleep(0.05)
        release.set()
        first, second = await asyncio.gather(first_task, second_task)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.content == second.content
    assert calls == 1
