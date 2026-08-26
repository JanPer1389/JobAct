"""`SessionRepository`: manual Core-statement mapping between the
`Session` aggregate and the `identity.sessions` table.

Task 1.3 only needed `add()`. Task 1.4 adds `get_by_id` (the auth
dependency's cookie lookup, source of truth over Redis's cache) and
`save` (persists `revoked_at` after `POST /auth/logout` revokes a
session).
"""

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from jobact.contexts.identity.domain.session import Session
from jobact.shared.infrastructure.postgres.identity_tables import sessions_table


class SessionRepository:
    """Persists and reconstructs `Session` aggregates."""

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

    async def get_by_id(self, session_id: str) -> Session | None:
        row = (
            (
                await self._session.execute(
                    select(sessions_table).where(sessions_table.c.id == session_id)
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            return None

        return Session(
            id=row["id"],
            user_id=row["user_id"],
            organization_id=row["organization_id"],
            device_id=row["device_id"],
            created_at=row["created_at"],
            last_seen_at=row["last_seen_at"],
            expires_at=row["expires_at"],
            revoked_at=row["revoked_at"],
            ip=row["ip"],
            user_agent=row["user_agent"],
        )

    async def save(self, session: Session) -> None:
        """UPDATE an existing session's mutable fields (currently only
        `revoked_at`/`last_seen_at` ever change after creation).
        """
        await self._session.execute(
            update(sessions_table)
            .where(sessions_table.c.id == session.id)
            .values(
                last_seen_at=session.last_seen_at,
                revoked_at=session.revoked_at,
            )
        )
