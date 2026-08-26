"""Contract test for `GoogleIdentityProvider` against a stubbed Google
token endpoint and JWKS endpoint -- no real network calls.

We generate our own RSA keypair, sign a Google-shaped ID token with the
private key, publish only the public key as a JWKS document (as Google's
`https://www.googleapis.com/oauth2/v3/certs` would), and use `respx` to
make httpx return our fixtures instead of hitting the real network.

Three cases matter here:
  * a validly-signed, non-expired token -> `exchange()` succeeds and
    returns a fully-populated `ExternalIdentity`.
  * a token whose payload was tampered with AFTER signing (the `nonce`
    claim is changed but the signature is left as originally computed
    over the untampered payload) -> `exchange()` must raise, because the
    signature no longer matches the payload. This is the test that
    actually exercises signature verification: if the adapter merely
    base64-decoded the JWT without checking the signature, this case
    would incorrectly succeed and return the attacker-chosen nonce.
  * a validly-signed but expired token -> `exchange()` must raise.
"""

import base64
import json
import time

import httpx
import pytest
import respx
from authlib.jose import JsonWebKey, jwt

from jobact.shared.infrastructure.config import Settings
from jobact.shared.infrastructure.identity_provider.google import (
    GoogleIdentityProvider,
    InvalidIdentityTokenError,
)

TEST_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
TEST_CLIENT_SECRET = "test-client-secret"
TEST_REDIRECT_URL = "http://localhost:8000/auth/google/callback"
KID = "test-signing-key"

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
JWKS_ENDPOINT = "https://www.googleapis.com/oauth2/v3/certs"


def _settings() -> Settings:
    return Settings(
        google_client_id=TEST_CLIENT_ID,
        google_client_secret=TEST_CLIENT_SECRET,
        google_redirect_url=TEST_REDIRECT_URL,
    )


def _keypair():
    key = JsonWebKey.generate_key("RSA", 2048, is_private=True, options={"kid": KID})
    return key


def _jwks_for(key) -> dict:
    return {"keys": [key.as_dict(is_private=False)]}


def _claims(**overrides) -> dict:
    now = int(time.time())
    base = {
        "iss": "https://accounts.google.com",
        "aud": TEST_CLIENT_ID,
        "sub": "1234567890",
        "email": "user@example.com",
        "email_verified": True,
        "name": "Test User",
        "picture": "https://example.com/pic.jpg",
        "nonce": "expected-nonce-value",
        "iat": now,
        "exp": now + 3600,
    }
    base.update(overrides)
    return base


def _sign(key, claims: dict) -> str:
    header = {"alg": "RS256", "kid": KID}
    token = jwt.encode(header, claims, key)
    return token.decode("ascii") if isinstance(token, bytes) else token


def _tamper_nonce(token: str, new_nonce: str) -> str:
    """Flip the `nonce` claim in the payload segment WITHOUT re-signing --
    the signature segment is left untouched, so it now covers a payload
    that no longer matches. Any real signature verification must reject
    this.
    """
    header_b64, payload_b64, signature_b64 = token.split(".")

    def _b64url_decode(segment: str) -> bytes:
        padding = "=" * (-len(segment) % 4)
        return base64.urlsafe_b64decode(segment + padding)

    def _b64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

    payload = json.loads(_b64url_decode(payload_b64))
    payload["nonce"] = new_nonce
    tampered_payload_b64 = _b64url_encode(json.dumps(payload).encode("utf-8"))

    return f"{header_b64}.{tampered_payload_b64}.{signature_b64}"


def _mock_endpoints(respx_mock, id_token: str, jwks: dict) -> None:
    respx_mock.post(TOKEN_ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "fake-access-token",
                "id_token": id_token,
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )
    )
    respx_mock.get(JWKS_ENDPOINT).mock(return_value=httpx.Response(200, json=jwks))


@pytest.mark.asyncio
@respx.mock
async def test_exchange_returns_identity_for_validly_signed_token() -> None:
    key = _keypair()
    token = _sign(key, _claims())
    _mock_endpoints(respx.mock, token, _jwks_for(key))

    provider = GoogleIdentityProvider(_settings())
    identity = await provider.exchange("auth-code")

    assert identity.subject == "1234567890"
    assert identity.email == "user@example.com"
    assert identity.email_verified is True
    assert identity.name == "Test User"
    assert identity.picture == "https://example.com/pic.jpg"
    assert identity.nonce == "expected-nonce-value"


@pytest.mark.asyncio
@respx.mock
async def test_exchange_rejects_token_with_tampered_nonce() -> None:
    key = _keypair()
    token = _sign(key, _claims())
    tampered = _tamper_nonce(token, "attacker-chosen-nonce")
    _mock_endpoints(respx.mock, tampered, _jwks_for(key))

    provider = GoogleIdentityProvider(_settings())

    with pytest.raises(InvalidIdentityTokenError):
        await provider.exchange("auth-code")


@pytest.mark.asyncio
@respx.mock
async def test_exchange_rejects_expired_token() -> None:
    key = _keypair()
    now = int(time.time())
    token = _sign(key, _claims(iat=now - 7200, exp=now - 3600))
    _mock_endpoints(respx.mock, token, _jwks_for(key))

    provider = GoogleIdentityProvider(_settings())

    with pytest.raises(InvalidIdentityTokenError):
        await provider.exchange("auth-code")


@pytest.mark.asyncio
@respx.mock
async def test_exchange_rejects_token_with_wrong_audience() -> None:
    key = _keypair()
    token = _sign(key, _claims(aud="some-other-client-id.apps.googleusercontent.com"))
    _mock_endpoints(respx.mock, token, _jwks_for(key))

    provider = GoogleIdentityProvider(_settings())

    with pytest.raises(InvalidIdentityTokenError):
        await provider.exchange("auth-code")


@pytest.mark.asyncio
@respx.mock
async def test_exchange_rejects_token_with_wrong_issuer() -> None:
    key = _keypair()
    token = _sign(key, _claims(iss="https://evil.example.com"))
    _mock_endpoints(respx.mock, token, _jwks_for(key))

    provider = GoogleIdentityProvider(_settings())

    with pytest.raises(InvalidIdentityTokenError):
        await provider.exchange("auth-code")


def test_authorization_url_includes_expected_parameters() -> None:
    provider = GoogleIdentityProvider(_settings())

    url = provider.authorization_url(state="state-123", nonce="nonce-456")

    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "response_type=code" in url
    assert f"client_id={TEST_CLIENT_ID.replace(':', '%3A')}" in url or "client_id=" in url
    assert "state=state-123" in url
    assert "nonce=nonce-456" in url
    assert "scope=openid" in url or "scope=openid+email+profile" in url
