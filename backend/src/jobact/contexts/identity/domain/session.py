"""`Session` aggregate: an authenticated session bound to one user and
one organization.

Kept as its own `AggregateRoot` (not nested inside `User`) so a later
task's auth dependency can look up a session by its opaque cookie value
on every request without loading a full `User` aggregate.

Note on identity: `Session.id` is a `str` (an opaque token/cookie value),
not a `UUID` like every other aggregate in this context -- `Entity`'s
identity-based equality/hash (`shared.domain.entity.Entity`) works for
any hashable `id` type, it's never assumed to be a `UUID`.
"""

from datetime import datetime
from uuid import UUID

from jobact.shared.domain import AggregateRoot


class Session(AggregateRoot):
    """An authenticated session, identified by an opaque token string."""

    def __init__(
        self,
        *,
        id: str,
        user_id: UUID,
        organization_id: UUID,
        device_id: str | None,
        created_at: datetime,
        last_seen_at: datetime,
        expires_at: datetime,
        revoked_at: datetime | None,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        super().__init__()
        self.id = id
        self.user_id = user_id
        self.organization_id = organization_id
        self.device_id = device_id
        self.created_at = created_at
        self.last_seen_at = last_seen_at
        self.expires_at = expires_at
        self.revoked_at = revoked_at
        self.ip = ip
        self.user_agent = user_agent

    def is_active(self, now: datetime) -> bool:
        return self.revoked_at is None and now < self.expires_at
