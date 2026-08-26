"""`MembershipRepository`: manual Core-statement mapping between the
`Membership` aggregate and the `identity.memberships` table.
"""

from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from jobact.contexts.identity.domain.membership import Membership
from jobact.shared.infrastructure.postgres.identity_tables import memberships_table


class MembershipRepository:
    """Persists and reconstructs `Membership` aggregates."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, membership: Membership) -> None:
        await self._session.execute(
            insert(memberships_table).values(
                id=membership.id,
                user_id=membership.user_id,
                organization_id=membership.organization_id,
                role=membership.role,
                joined_at=membership.joined_at,
                revoked_at=membership.revoked_at,
            )
        )

    async def get_by_user_id(self, user_id: UUID) -> Membership | None:
        """The user's first (owner) membership, used by the sign-in
        handler to recover their organization/role on an existing-user
        sign-in without a full membership-listing feature yet.
        """
        row = (
            await self._session.execute(
                select(memberships_table)
                .where(memberships_table.c.user_id == user_id)
                .order_by(memberships_table.c.joined_at.asc())
                .limit(1)
            )
        ).mappings().first()
        if row is None:
            return None

        return Membership(
            id=row["id"],
            user_id=row["user_id"],
            organization_id=row["organization_id"],
            role=row["role"],
            joined_at=row["joined_at"],
            revoked_at=row["revoked_at"],
        )
