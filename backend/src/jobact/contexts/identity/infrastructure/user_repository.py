"""`UserRepository`: manual Core-statement mapping between the `User`
aggregate (plus its nested `UserProfile`/`LinkedIdentity` value data) and
the `identity.users` / `identity.user_profiles` / `identity.identities`
tables.

No SQLAlchemy declarative ORM/session dirty-tracking is used anywhere in
this project -- everything is explicit `select`/`insert`/`update`
statements against Core `Table` objects (Task 0.3's established style).
"""

from uuid import uuid4

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from jobact.contexts.identity.domain.user import LinkedIdentity, User, UserProfile
from jobact.shared.infrastructure.postgres.identity_tables import (
    identities_table,
    user_profiles_table,
    users_table,
)


class UserRepository:
    """Persists and reconstructs `User` aggregates."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_linked_identity(
        self, provider: str, provider_subject: str
    ) -> User | None:
        result = await self._session.execute(
            select(users_table.c.id)
            .select_from(
                identities_table.join(
                    users_table, identities_table.c.user_id == users_table.c.id
                )
            )
            .where(
                identities_table.c.provider == provider,
                identities_table.c.provider_subject == provider_subject,
            )
        )
        user_id_row = result.first()
        if user_id_row is None:
            return None

        return await self._load(user_id_row.id)

    async def _load(self, user_id: object) -> User | None:
        user_row = (
            await self._session.execute(
                select(users_table).where(users_table.c.id == user_id)
            )
        ).mappings().first()
        if user_row is None:
            return None

        profile_row = (
            await self._session.execute(
                select(user_profiles_table).where(
                    user_profiles_table.c.user_id == user_id
                )
            )
        ).mappings().first()
        assert profile_row is not None, f"user {user_id} has no user_profiles row"

        identity_rows = (
            await self._session.execute(
                select(identities_table).where(identities_table.c.user_id == user_id)
            )
        ).mappings().all()

        return User(
            id=user_row["id"],
            email=user_row["email"],
            email_verified=user_row["email_verified"],
            status=user_row["status"],
            locale=user_row["locale"],
            timezone=user_row["timezone"],
            registered_at=user_row["registered_at"],
            activated_at=user_row["activated_at"],
            last_seen_at=user_row["last_seen_at"],
            profile=UserProfile(
                display_name=profile_row["display_name"],
                given_name=profile_row["given_name"],
                family_name=profile_row["family_name"],
                avatar_url=profile_row["avatar_url"],
            ),
            linked_identities=[
                LinkedIdentity(
                    provider=row["provider"], provider_subject=row["provider_subject"]
                )
                for row in identity_rows
            ],
        )

    async def add(self, user: User) -> None:
        """INSERT a brand-new user (and its profile and linked identities)."""
        await self._session.execute(
            insert(users_table).values(
                id=user.id,
                email=user.email,
                email_verified=user.email_verified,
                status=user.status,
                locale=user.locale,
                timezone=user.timezone,
                registered_at=user.registered_at,
                activated_at=user.activated_at,
                last_seen_at=user.last_seen_at,
            )
        )
        await self._session.execute(
            insert(user_profiles_table).values(
                user_id=user.id,
                display_name=user.profile.display_name,
                given_name=user.profile.given_name,
                family_name=user.profile.family_name,
                avatar_url=user.profile.avatar_url,
            )
        )
        for linked in user.linked_identities:
            await self._insert_linked_identity(user.id, linked)

    async def save(self, user: User) -> None:
        """UPDATE an existing user's mutable fields, and INSERT any linked
        identities that don't already exist yet (added since load).
        """
        await self._session.execute(
            update(users_table)
            .where(users_table.c.id == user.id)
            .values(
                email=user.email,
                email_verified=user.email_verified,
                last_seen_at=user.last_seen_at,
                activated_at=user.activated_at,
                status=user.status,
            )
        )
        await self._session.execute(
            update(user_profiles_table)
            .where(user_profiles_table.c.user_id == user.id)
            .values(
                display_name=user.profile.display_name,
                given_name=user.profile.given_name,
                family_name=user.profile.family_name,
                avatar_url=user.profile.avatar_url,
            )
        )

        existing_rows = (
            await self._session.execute(
                select(
                    identities_table.c.provider, identities_table.c.provider_subject
                ).where(identities_table.c.user_id == user.id)
            )
        ).all()
        existing = {(row.provider, row.provider_subject) for row in existing_rows}

        for linked in user.linked_identities:
            if (linked.provider, linked.provider_subject) not in existing:
                await self._insert_linked_identity(user.id, linked)

    async def _insert_linked_identity(self, user_id: object, linked: LinkedIdentity) -> None:
        await self._session.execute(
            insert(identities_table).values(
                id=uuid4(),
                user_id=user_id,
                provider=linked.provider,
                provider_subject=linked.provider_subject,
            )
        )
