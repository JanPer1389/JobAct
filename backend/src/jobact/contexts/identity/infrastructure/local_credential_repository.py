"""SQLAlchemy Core persistence for local password credentials."""

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from jobact.contexts.identity.domain.local_credential import LocalCredential
from jobact.shared.infrastructure.postgres.identity_tables import (
    local_credentials_table,
)


class LocalCredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: object) -> LocalCredential | None:
        row = (
            await self._session.execute(
                select(local_credentials_table).where(
                    local_credentials_table.c.user_id == user_id
                )
            )
        ).mappings().first()
        if row is None:
            return None
        return LocalCredential(
            id=row["id"],
            user_id=row["user_id"],
            password_hash=row["password_hash"],
            hash_version=row["hash_version"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def add(self, credential: LocalCredential) -> None:
        await self._session.execute(
            insert(local_credentials_table).values(
                id=credential.id,
                user_id=credential.user_id,
                password_hash=credential.password_hash,
                hash_version=credential.hash_version,
                created_at=credential.created_at,
                updated_at=credential.updated_at,
            )
        )

    async def save(self, credential: LocalCredential) -> None:
        await self._session.execute(
            update(local_credentials_table)
            .where(local_credentials_table.c.id == credential.id)
            .values(
                password_hash=credential.password_hash,
                hash_version=credential.hash_version,
                updated_at=credential.updated_at,
            )
        )
