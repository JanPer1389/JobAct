"""`OrganizationRepository`: manual Core-statement mapping between the
`Organization` aggregate and the `identity.organizations` table.

Only `add()` is needed for Task 1.3 -- nothing reads an organization back
or updates one yet.
"""

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from jobact.contexts.identity.domain.organization import Organization
from jobact.shared.infrastructure.postgres.identity_tables import organizations_table


class OrganizationRepository:
    """Persists `Organization` aggregates."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, organization: Organization) -> None:
        await self._session.execute(
            insert(organizations_table).values(
                id=organization.id,
                name=organization.name,
                created_at=organization.created_at,
            )
        )
