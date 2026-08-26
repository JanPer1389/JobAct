"""HTTP-layer Pydantic response DTOs for the `/api/v1/auth/*` routes.

Deliberately separate from `contexts.identity.domain.session.Session`
(a domain aggregate) and `contexts.identity.application
.sign_in_with_google.SignInResult` (an application-layer dataclass) --
this module is the ONLY place the actual JSON shape returned to HTTP
clients is defined. Pydantic-only (plus stdlib): no FastAPI, no
SQLAlchemy.
"""

from uuid import UUID

from pydantic import BaseModel


class SessionResponse(BaseModel):
    """Body of a successful `GET /api/v1/auth/session` response.

    Mirrors `apps.api.deps.CurrentPrincipal` exactly -- the fields
    available on every authenticated request without an extra Postgres
    lookup for the `User` aggregate (e.g. email). Extending this to
    include profile fields is a later task's job if/when a route
    actually needs them.
    """

    user_id: UUID
    organization_id: UUID
    role: str
