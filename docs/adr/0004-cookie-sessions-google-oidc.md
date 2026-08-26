# ADR-0004: Opaque cookie sessions, Google OIDC behind an IdentityProvider port

## Status

Accepted, implemented (Milestone 1).

## Context

PAPERCUT calls for cookie-based sessions rather than a client-held JWT, and for the identity
provider to sit behind a port. Worth flagging explicitly: PAPERCUT commits to a Russian
launch with in-country data residency, and Google as an identity provider is an external
dependency with its own availability and cross-border-data-transfer questions in that
context. The port exists specifically so a Russian identity provider (e.g. Yandex ID) can
replace Google later without touching session logic — this milestone proceeds with Google as
chosen, deliberately not treating the port as a hypothetical to defer.

## Decision

- `shared/application/ports.py` declares `IdentityProvider`; `shared/infrastructure/
  identity_provider/google.py` implements it via Authlib + Google's JWKS
  (`authorization_url(state, nonce)`, `exchange(code) -> ExternalIdentity`).
- Sessions are opaque IDs (`identity.sessions.id`, a `Text` primary key — not a JWT) stored in
  Postgres and cached in Redis, set as an `HttpOnly`, `SameSite=Lax` cookie
  (`jobact_session`, `Secure` in production).
- `SignInWithGoogleHandler` upserts `identity.users` + `identity.identities` keyed on
  `(provider, provider_subject)`; the first sign-in for a subject also creates a personal
  `Organization` and an `owner` `Membership` in the same transaction.
- Dev runs same-origin through the Next.js rewrite (`/api/*` → the backend), so there is no
  CORS and no third-party-cookie problem to work around.
- An `Origin` allowlist dependency rejects mutating requests from a foreign origin, as a CSRF
  defense alongside `SameSite=Lax`.

## Consequences

- Revoking a session is a database write (`revoked_at`) and a Redis cache delete, not "wait
  for a JWT to expire" — logout is immediate everywhere the session is checked.
- A tampered `nonce` or an expired `exp` in the ID token is rejected before any user/session
  row is touched — verified by `tests/contract/test_google_identity_provider.py` against a
  stubbed JWKS/token endpoint.
- Because the OIDC exchange lives entirely behind `IdentityProvider`, `SignInWithGoogleHandler`
  and everything downstream of it (session creation, membership, the `CurrentPrincipal`
  dependency) has no Google-specific code to change if a second or replacement provider is
  added — only a new `IdentityProvider` implementation and a routing decision for which
  provider a given sign-in request uses.
