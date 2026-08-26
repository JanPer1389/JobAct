"""`SessionRepository`: manual Core-statement mapping between the
`Session` aggregate and the `identity.sessions` table.

Only `add()` is needed for Task 1.3 -- Task 1.4 adds a `get_by_id` for the
auth dependency's cookie lookup.
"""

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from jobact.contexts.identity.domain.session import Session
from jobact.shared.infrastructure.postgres.identity_tables import sessions_table


class SessionRepository:
    """Persists `Session` aggregates."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, session: Session) -> None:
        await self._session.execute(
            insert(sessions_table).values(
                id=session.id,
                user_id=session.user_id,
                organization_id=session.organization_id,
                device_id=session.device_id,
                created_at=session.created_at,
                last_seen_at=session.last_seen_at,
                expires_at=session.expires_at,
                revoked_at=session.revoked_at,
                ip=session.ip,
                user_agent=session.user_agent,
            )
        )
