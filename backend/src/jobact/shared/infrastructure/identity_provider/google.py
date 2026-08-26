"""Concrete `IdentityProvider` implementation over Google's real
OAuth2/OpenID Connect endpoints.

This is the ONE place allowed to import Authlib and httpx for talking to
Google -- `shared/infrastructure/` is where third-party/network
integrations live, never `contexts/identity/domain/`.

Security note: `exchange()` treats the ID token Google's token endpoint
hands back as untrusted input until its signature, expiry, issuer, and
audience have all been positively verified against Google's published
JWKS. Nothing derived from an unverified token is ever returned.
"""

from urllib.parse import urlencode

import httpx
from authlib.jose import JoseError, JsonWebKey, jwt

from jobact.shared.application.ports import ExternalIdentity
from jobact.shared.infrastructure.config import Settings

AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
JWKS_ENDPOINT = "https://www.googleapis.com/oauth2/v3/certs"

# Google's ID tokens use either form depending on how the token was minted;
# both are legitimate and must be accepted.
EXPECTED_ISSUERS = ["https://accounts.google.com", "accounts.google.com"]


class InvalidIdentityTokenError(Exception):
    """Raised when a Google ID token fails signature, expiry, issuer, or
    audience verification. Deliberately carries no token contents or
    secrets in its message -- callers should not log the raw exception
    args as if they were safe, but the message itself never contains raw
    token/claim data.
    """


class GoogleIdentityProvider:
    """`IdentityProvider` implementation backed by Google's OAuth2/OIDC
    endpoints (authorization-code flow).
    """

    def __init__(self, settings: Settings) -> None:
        self._client_id = settings.google_client_id
        self._client_secret = settings.google_client_secret
        self._redirect_url = settings.google_redirect_url

    def authorization_url(self, state: str, nonce: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": self._redirect_url,
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
        }
        return f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"

    async def exchange(self, code: str) -> ExternalIdentity:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                TOKEN_ENDPOINT,
                data={
                    "code": code,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self._redirect_url,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            token_payload = token_response.json()

            id_token = token_payload.get("id_token")
            if not id_token:
                raise InvalidIdentityTokenError(
                    "Google token response did not include an id_token"
                )

            jwks_response = await client.get(JWKS_ENDPOINT)
            jwks_response.raise_for_status()
            jwks = JsonWebKey.import_key_set(jwks_response.json())

        claims_options = {
            "iss": {"essential": True, "values": EXPECTED_ISSUERS},
            "aud": {"essential": True, "value": self._client_id},
            "exp": {"essential": True},
            "sub": {"essential": True},
        }

        try:
            claims = jwt.decode(id_token, jwks, claims_options=claims_options)
            claims.validate()
        except JoseError as exc:
            raise InvalidIdentityTokenError(
                "Google ID token failed verification"
            ) from exc
        except ValueError as exc:
            # e.g. KeySet.find_by_kid() raising ValueError("Key not found")
            # when the token's `kid` doesn't match any published JWK.
            raise InvalidIdentityTokenError(
                "Google ID token failed verification"
            ) from exc

        return ExternalIdentity(
            subject=claims["sub"],
            email=claims.get("email", ""),
            email_verified=bool(claims.get("email_verified", False)),
            name=claims.get("name", ""),
            picture=claims.get("picture"),
            nonce=claims.get("nonce", ""),
        )
