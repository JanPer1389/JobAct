# Default authentication: implementation handoff

## Purpose

Add a clear default authentication experience that lets a person choose either:

- email and password; or
- Continue with Google.

The experience must support two modes:

| Mode | Required inputs | Alternative |
| --- | --- | --- |
| Create account | email, password, repeat password | Continue with Google |
| Sign in | email, password | Continue with Google |

"Gmail" means a normal email address field. Do not restrict it to the `gmail.com` domain.

This is a design-and-implementation handoff. Preserve the existing Google OIDC, session, tenant, report, visual-audit, signature, and PDF behavior.

## Mandatory reading before changing code

Read these files in this order. Do not start implementation until their boundaries are understood.

1. `backend/CLAUDE.md` - backend layering and dependency rules.
2. `docs/architecture/overview.md` - bounded contexts and request flow.
3. `backend/src/jobact/contexts/identity/domain/user.py` - `User`, profile, and linked external identities.
4. `backend/src/jobact/contexts/identity/application/sign_in_with_google.py` - the current first-login lifecycle: user, organization, owner membership, and session.
5. `backend/src/jobact/apps/api/routers/auth.py` - Google OAuth endpoints, cookie settings, session lookup, and logout behavior.
6. `backend/src/jobact/contexts/identity/infrastructure/user_repository.py` and `backend/src/jobact/shared/infrastructure/postgres/identity_tables.py` - repository and schema conventions.
7. `backend/src/jobact/shared/application/ports.py`, `backend/src/jobact/shared/application/uow.py`, and `backend/src/jobact/shared/infrastructure/config.py` - ports, transactions, and configuration.
8. `backend/tests/integration/test_auth_routes.py`, identity domain tests, and Google-provider contract tests - existing authentication guarantees.
9. `frontend/components/jobact/screens/onboarding.tsx`, `frontend/lib/jobact/api.ts`, and `frontend/lib/jobact/store.tsx` - current unauthenticated flow and session navigation.
10. `PAPERCUT.md` - project diary. Add a dated result after each completed implementation section.

Also inspect the nearest comparable migration and test fixtures before adding persistence or endpoints.

## Existing behavior to preserve

- Google OAuth starts at `GET /api/v1/auth/google/start` and completes through its callback.
- The Google handler validates the OIDC nonce, finds a user by the stable `(provider, subject)` identity, and creates a session.
- On a first Google login it creates one `User`, one personal `Organization`, one owner `Membership`, and one `Session` in the identity flow.
- The browser receives the existing session cookie; `GET /api/v1/auth/session` remains the source of the signed-in principal and organization.
- Logout revokes the persisted session and clears its cache/cookie safely.

Do not replace Google OAuth with a client-side token flow. Do not change cookie security semantics casually.

## Required user-facing behavior

### Entry and mode switching

Replace the Google-only entry card with a straightforward authentication screen:

- Default visible action: **Create account**.
- A clear link switches to **Sign in**; Sign in has a clear link back to Create account.
- Create account shows labelled email, password, and repeat-password inputs plus **Create account**.
- Sign in shows labelled email and password inputs plus **Sign in**.
- Both modes show a clearly separated **Continue with Google** action.
- Show field-level validation for malformed email and mismatched passwords. Password confirmation is never sent or stored as a credential.
- Preserve useful loading, disabled-submit, error, keyboard, and accessible-label behavior.

On success, use the same session-backed navigation path as the existing Google flow.

### Email/password registration and sign-in

- Registration must normalize and uniquely identify email addresses consistently at the domain/application boundary.
- A successful email/password registration creates the same initial tenancy shape as Google first login: user, personal organization, owner membership, then session, in one transaction.
- Password sign-in finds the local credential, verifies it, and creates a new session using the existing lifetime/cookie conventions.
- Failed email/password sign-in returns one generic invalid-credentials result. Do not disclose whether an email address exists.
- Registration must handle an existing email without leaking more information than necessary. Use a clear, safe UX such as "An account already exists; sign in instead."

### Google identities and account linking

- Keep stable Google provider subject as the identity lookup key. Do not use display name as identity.
- Never automatically merge or link accounts merely because their email strings match, even when Google says the email is verified. A local password account may not have proven control of that email.
- Let a signed-in user explicitly add a second method through an authenticated account-security/linking flow. The server must require proof of control of the current session and complete the provider callback with a binding request state; it may then attach the Google `(provider, subject)` identity to that same user.
- Likewise, a Google-only user may set a password only while authenticated (and after appropriate recent-session checks if the existing security model supports them).
- If an unauthenticated Google sign-in returns an email that already belongs to an unlinked local account, do not create a second user and do not silently link it. Return the user to a safe next step explaining that they must sign in to the existing account and link Google there.
- If the provider subject is already linked, it always signs in to that linked user, independent of changes in the provider display name.

This explicit-link rule is the secure interpretation of offering both choices while preventing account takeover. Do not weaken it for convenience.

## Domain, persistence, and application boundaries

- Keep password rules, credential types, and account transitions in the identity bounded context. Pydantic, FastAPI, SQLAlchemy, environment access, password libraries, and HTTP cookies stay outside the domain.
- Model a local credential separately from public `User` profile data. Persist only a slow, versioned password hash and minimum required metadata; never a raw password, reversible encryption, or password-confirmation value.
- Reuse the `User` aggregate's linked-identity behavior for Google. Do not create a second user merely to represent a password credential.
- Add repositories and migrations following the existing tenant/identity schema conventions. Enforce unique normalized email and unique local credential ownership at database level as well as application level.
- Add explicit application handlers for registration, password sign-in, password setup/change, and identity linking as needed. Handlers own orchestration; repositories own SQL; adapters own password hashing and external provider calls.
- Preserve atomicity: a failed credential/identity operation must not leave an orphan user, organization, membership, credential, or session.

## Security requirements

- Use a maintained password-hashing implementation configured for Argon2id. Store only its encoded hash; use the library verifier rather than custom cryptography.
- Never log passwords, repeat passwords, password hashes, authorization codes, OAuth state/nonce, session identifiers, or credentials. Ensure validation and exception messages do not expose them.
- Enforce an explicit, documented password policy. Keep it reasonable and user-facing; do not invent obscure composition rules.
- Rate-limit or otherwise throttle registration and password sign-in at the API boundary using project conventions. Make the behavior testable without network calls.
- Preserve CSRF/OIDC state and nonce protections for Google. Linking must bind OAuth state to the authenticated account and intended operation, not just the browser.
- Set/clear the session cookie through the existing server-side mechanism. Do not expose tokens to frontend storage.
- Avoid user enumeration in sign-in, recovery-like messages, and API errors.
- Password reset, email verification, MFA, social providers other than Google, and organization invitations are out of scope unless the product owner separately approves them. Do not claim an email/password account has a verified email merely because it was typed during registration.

## Suggested HTTP/API shape

Fit names and response models to existing v1 conventions; do not introduce a parallel auth stack. A reasonable minimal shape is:

- `POST /api/v1/auth/register` - email, password, repeat password; returns/sets a normal session.
- `POST /api/v1/auth/login` - email and password; returns/sets a normal session.
- existing Google start/callback endpoints - unchanged for sign-in.
- authenticated endpoints or explicit OAuth operation state for linking Google and setting/changing a local password.

Use Pydantic request/response contracts at the HTTP boundary, mapping them into application commands. Do not return password-related persistence data.

## Focused acceptance tests

Implement sections fully, then run only their focused checks. Do not use a test-first loop or unrelated legacy suites unless a focused check shows a regression.

1. **Domain and migration checkpoint**
   - password credential invariants and no-plaintext persistence;
   - normalized-email and unique-credential rules;
   - migration/schema smoke test.
2. **Application and provider checkpoint**
   - registration creates user, organization, owner membership, and session atomically;
   - correct and incorrect password behavior;
   - explicit Google-link behavior; collision never auto-merges;
   - existing Google nonce/subject behavior remains covered.
3. **HTTP/UI checkpoint**
   - registration/login happy paths, generic failed-login response, and tenant/session isolation;
   - accessible Create account/Sign in switching, repeat-password validation, Google action, loading/error states;
   - TypeScript check and one production frontend build.
4. **Final focused verification**
   - all new authentication tests together;
   - Ruff only on changed Python files;
   - one local user happy path for each configured auth method that can be exercised without exposing secrets.

## Completion criteria

- A new user can create an email/password account and enter the app.
- A returning user can sign in with email/password and receives the normal server-managed session.
- A user can choose Google from either auth mode, and existing Google sign-in still works.
- No duplicate users or silent cross-method merges are created.
- Sensitive values are not persisted or exposed.
- Existing visual-audit and report workflow remains unaffected.
- `PAPERCUT.md` contains a short result for every completed section.
- Preserve the unrelated `.claude/launch.json` deletion; do not restore or include it in this work.

## Copy/paste assignment for the implementation agent

> Implement the default authentication design in `docs/superpowers/specs/2026-08-27-default-authentication-design.md`. Read every mandatory file first and follow existing DDD boundaries. Add Create account (email, password, repeat password) and Sign in (email, password), with Continue with Google available from both. Preserve Google OIDC and server-side sessions. Model local credentials separately, hash with Argon2id, never store/log raw secrets, create the normal user/organization/owner-membership/session lifecycle transactionally, and never auto-link accounts by email alone. Use explicit authenticated account linking for a second sign-in method. Work section-by-section, record each completed section in `PAPERCUT.md`, run only the specified focused checks, and do not touch unrelated `.claude/launch.json` deletion or visual-audit behavior.
