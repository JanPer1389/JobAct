"""Integration tests for `SignInWithGoogleHandler` against real Postgres.

Deliberately exercises the real `SqlAlchemyUnitOfWork` + repository stack
(not mocked) -- same reasoning as `test_unit_of_work.py` and
`test_infrastructure.py`. Only the identity-provider side is faked
(`FakeIdentityProvider`), since Task 1.2's real `GoogleIdentityProvider`
needs a live Google OIDC round trip that has no place in this test.

Run with:
    docker compose up -d
    uv run alembic upgrade head
    uv run pytest tests/integration/test_sign_in_with_google.py
"""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from jobact.contexts.identity.application.sign_in_with_google import (
    InvalidNonceError,
    SignInWithGoogleHandler,
)
from jobact.shared.application.ports import ExternalIdentity
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
from tests.fakes import FakeClock, FakeIdentityProvider, FakeIdGenerator


@pytest.fixture
async def clean_identity_tables() -> AsyncIterator[None]:
    """Keep the identity schema empty before and after each test."""
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


def _make_handler() -> tuple[SignInWithGoogleHandler, FakeIdentityProvider, FakeClock]:
    identity_provider = FakeIdentityProvider()
    clock = FakeClock()
    handler = SignInWithGoogleHandler(
        uow=SqlAlchemyUnitOfWork(),
        identity_provider=identity_provider,
        clock=clock,
        id_generator=FakeIdGenerator(),
    )
    return handler, identity_provider, clock


async def _users_rows_for_subject(subject: str) -> list:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        result = await session.execute(
            select(users_table)
            .select_from(users_table.join(identities_table))
            .where(identities_table.c.provider_subject == subject)
        )
        return list(result.mappings().all())


async def _organizations_count() -> int:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        result = await session.execute(select(organizations_table))
        return len(result.mappings().all())


async def test_two_sign_ins_with_same_subject_yield_one_user_and_one_organization(
    clean_identity_tables: None,
) -> None:
    handler, identity_provider, _clock = _make_handler()
    subject = f"google-subject-{uuid4()}"
    identity_provider.identities["code-1"] = ExternalIdentity(
        subject=subject,
        email="ada@example.com",
        email_verified=True,
        name="Ada Lovelace",
        picture=None,
        nonce="expected-nonce",
    )
    identity_provider.identities["code-2"] = ExternalIdentity(
        subject=subject,
        email="ada@example.com",
        email_verified=True,
        name="Ada Lovelace",
        picture=None,
        nonce="expected-nonce",
    )

    result1 = await handler.handle("code-1", expected_nonce="expected-nonce")
    result2 = await handler.handle("code-2", expected_nonce="expected-nonce")

    assert result1.user_id == result2.user_id
    assert result1.organization_id == result2.organization_id

    rows = await _users_rows_for_subject(subject)
    assert len(rows) == 1


async def test_changed_email_updates_the_user_without_creating_a_second_one(
    clean_identity_tables: None,
) -> None:
    handler, identity_provider, _clock = _make_handler()
    subject = f"google-subject-{uuid4()}"
    identity_provider.identities["code-1"] = ExternalIdentity(
        subject=subject,
        email="old@example.com",
        email_verified=True,
        name="Ada Lovelace",
        picture=None,
        nonce="expected-nonce",
    )
    identity_provider.identities["code-2"] = ExternalIdentity(
        subject=subject,
        email="new@example.com",
        email_verified=True,
        name="Ada Lovelace",
        picture=None,
        nonce="expected-nonce",
    )

    await handler.handle("code-1", expected_nonce="expected-nonce")
    await handler.handle("code-2", expected_nonce="expected-nonce")

    rows = await _users_rows_for_subject(subject)
    assert len(rows) == 1
    assert rows[0]["email"] == "new@example.com"


async def test_invalid_nonce_raises_and_persists_nothing(
    clean_identity_tables: None,
) -> None:
    handler, identity_provider, _clock = _make_handler()
    subject = f"google-subject-{uuid4()}"
    identity_provider.identities["code-1"] = ExternalIdentity(
        subject=subject,
        email="ada@example.com",
        email_verified=True,
        name="Ada Lovelace",
        picture=None,
        nonce="actual-nonce",
    )

    with pytest.raises(InvalidNonceError):
        await handler.handle("code-1", expected_nonce="different-nonce")

    rows = await _users_rows_for_subject(subject)
    assert rows == []
    assert await _organizations_count() == 0
