"""Focused real-Postgres tests for local authentication and explicit linking."""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from jobact.contexts.identity.application.link_google_identity import (
    LinkGoogleIdentityHandler,
)
from jobact.contexts.identity.application.register_with_password import (
    RegisterWithPasswordHandler,
)
from jobact.contexts.identity.application.sign_in_with_google import (
    GoogleAccountLinkRequiredError,
    SignInWithGoogleHandler,
)
from jobact.contexts.identity.application.sign_in_with_password import (
    InvalidCredentialsError,
    SignInWithPasswordHandler,
)
from jobact.shared.application.ports import ExternalIdentity
from jobact.shared.infrastructure.id_generator import UuidIdGenerator
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.identity_tables import (
    identities_table,
    local_credentials_table,
    memberships_table,
    organizations_table,
    sessions_table,
    user_profiles_table,
    users_table,
)
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from tests.fakes import (
    FakeClock,
    FakeIdentityProvider,
    FakeIdGenerator,
    FakePasswordHasher,
)

PASSWORD = "correct horse battery staple"


@pytest.fixture
async def clean_identity_tables() -> AsyncIterator[None]:
    session_factory = get_sessionmaker()

    async def _truncate() -> None:
        async with session_factory() as session, session.begin():
            await session.execute(delete(sessions_table))
            await session.execute(delete(memberships_table))
            await session.execute(delete(local_credentials_table))
            await session.execute(delete(identities_table))
            await session.execute(delete(organizations_table))
            await session.execute(delete(user_profiles_table))
            await session.execute(delete(users_table))

    await _truncate()
    yield
    await _truncate()


def _register_handler() -> RegisterWithPasswordHandler:
    return RegisterWithPasswordHandler(
        SqlAlchemyUnitOfWork(), FakePasswordHasher(), FakeClock(), UuidIdGenerator()
    )


async def test_registration_creates_full_tenancy_and_hashed_credential(
    clean_identity_tables: None,
) -> None:
    result = await _register_handler().handle(" Ada@Example.COM ", PASSWORD)

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        user = (await session.execute(select(users_table))).mappings().one()
        credential = (
            await session.execute(select(local_credentials_table))
        ).mappings().one()
        assert len((await session.execute(select(organizations_table))).all()) == 1
        assert len((await session.execute(select(memberships_table))).all()) == 1
        assert len((await session.execute(select(sessions_table))).all()) == 1
    assert user["id"] == result.user_id
    assert user["email"] == "ada@example.com"
    assert user["email_verified"] is False
    assert credential["password_hash"] != PASSWORD
    assert credential["password_hash"].startswith("$argon2id$")


async def test_password_sign_in_accepts_correct_and_rejects_wrong_password(
    clean_identity_tables: None,
) -> None:
    registered = await _register_handler().handle("ada@example.com", PASSWORD)
    handler = SignInWithPasswordHandler(
        SqlAlchemyUnitOfWork(), FakePasswordHasher(), FakeClock(), UuidIdGenerator()
    )

    signed_in = await handler.handle("ADA@example.com", PASSWORD)
    assert signed_in.user_id == registered.user_id
    with pytest.raises(InvalidCredentialsError):
        await handler.handle("ada@example.com", "definitely-wrong")


async def test_google_collision_requires_explicit_link_and_creates_no_duplicate(
    clean_identity_tables: None,
) -> None:
    registered = await _register_handler().handle("ada@example.com", PASSWORD)
    provider = FakeIdentityProvider()
    provider.identities["code"] = ExternalIdentity(
        subject=f"google-{uuid4()}",
        email="ADA@example.com",
        email_verified=True,
        name="Ada Lovelace",
        picture=None,
        nonce="nonce",
    )
    google_handler = SignInWithGoogleHandler(
        SqlAlchemyUnitOfWork(), provider, FakeClock(), FakeIdGenerator()
    )
    with pytest.raises(GoogleAccountLinkRequiredError):
        await google_handler.handle("code", "nonce")

    await LinkGoogleIdentityHandler(SqlAlchemyUnitOfWork(), provider).handle(
        registered.user_id, "code", "nonce"
    )
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        assert len((await session.execute(select(users_table))).all()) == 1
        identity = (await session.execute(select(identities_table))).mappings().one()
    assert identity["user_id"] == registered.user_id
