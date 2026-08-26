"""`Membership` aggregate: a user's role within one organization.

Kept as its own `AggregateRoot` (not nested inside `User` or
`Organization`) so a later task's authorization check can look up a
membership by `(user_id, organization_id)` cheaply, without loading a
full `User` aggregate.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from jobact.shared.domain import AggregateRoot

Role = Literal["owner", "technician"]


class Membership(AggregateRoot):
    """A user's (revocable) role within one organization."""

    def __init__(
        self,
        *,
        id: UUID,
        user_id: UUID,
        organization_id: UUID,
        role: Role,
        joined_at: datetime,
        revoked_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self.id = id
        self.user_id = user_id
        self.organization_id = organization_id
        self.role = role
        self.joined_at = joined_at
        self.revoked_at = revoked_at

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def revoke(self, at: datetime) -> None:
        """Revoke this membership, blocking further access as of `at`.

        One-way: revoking an already-revoked membership raises
        `ValueError` rather than silently no-op'ing, so a caller can't
        accidentally push `revoked_at` forward (or lose track of the
        original revocation time) by revoking twice.
        """
        if self.revoked_at is not None:
            raise ValueError("membership is already revoked")
        self.revoked_at = at
