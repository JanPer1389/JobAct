from httpx import ASGITransport, AsyncClient

from jobact.apps.api.main import create_app
from jobact.apps.api.routers.auth import get_auth_rate_limiter
from tests.fakes import FakeAuthRateLimiter

ALLOWED_ORIGIN = "http://localhost:3000"
LOCAL_IP_ORIGIN = "http://127.0.0.1:3000"


def test_openapi_exposes_local_authentication_and_linking_endpoints() -> None:
    paths = create_app().openapi()["paths"]
    assert set(paths["/api/v1/auth/register"]) == {"post"}
    assert set(paths["/api/v1/auth/login"]) == {"post"}
    assert set(paths["/api/v1/auth/methods"]) == {"get"}
    assert set(paths["/api/v1/auth/password"]) == {"put"}
    assert set(paths["/api/v1/auth/google/link/start"]) == {"get"}


async def test_rate_limit_returns_envelope_and_retry_after_without_network() -> None:
    app = create_app()
    app.dependency_overrides[get_auth_rate_limiter] = lambda: FakeAuthRateLimiter(42)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            headers={"origin": ALLOWED_ORIGIN},
            json={"email": "user@example.com", "password": "not-a-real-secret"},
        )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "42"
    assert response.json()["type"] == "rate-limit-exceeded"


async def test_local_ip_origin_reaches_the_authentication_route() -> None:
    app = create_app()
    app.dependency_overrides[get_auth_rate_limiter] = lambda: FakeAuthRateLimiter(42)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            headers={"origin": LOCAL_IP_ORIGIN},
            json={"email": "user@example.com", "password": "not-a-real-secret"},
        )

    assert response.status_code == 429
    assert response.json()["type"] == "rate-limit-exceeded"
