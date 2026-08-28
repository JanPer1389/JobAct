from dataclasses import dataclass, field
from typing import Any, Self
from uuid import UUID

import pytest

import jobact.contexts.identity.application.authentication as lifecycle_module
import jobact.contexts.identity.application.link_google_identity as link_module
import jobact.contexts.identity.application.register_with_password as register_module
import jobact.contexts.identity.application.set_or_change_password as password_module
import jobact.contexts.identity.application.sign_in_with_google as google_module
import jobact.contexts.identity.application.sign_in_with_password as login_module
from jobact.contexts.identity.application.link_google_identity import (
    LinkGoogleIdentityHandler,
)
from jobact.contexts.identity.application.register_with_password import (
    RegisterWithPasswordHandler,
)
from jobact.contexts.identity.application.set_or_change_password import (
    CurrentPasswordRequiredError,
    SetOrChangePasswordHandler,
)
from jobact.contexts.identity.application.sign_in_with_google import (
    GoogleAccountLinkRequiredError,
    SignInWithGoogleHandler,
)
from jobact.contexts.identity.application.sign_in_with_password import (
    InvalidCredentialsError,
    SignInWithPasswordHandler,
)
from jobact.contexts.identity.domain.local_credential import LocalCredential
from jobact.contexts.identity.domain.membership import Membership
from jobact.contexts.identity.domain.organization import Organization
from jobact.contexts.identity.domain.session import Session
from jobact.contexts.identity.domain.user import User
from jobact.shared.application.ports import ExternalIdentity
from tests.fakes import (
    FakeClock,
    FakeIdentityProvider,
    FakeIdGenerator,
    FakePasswordHasher,
)

PASSWORD = "correct horse battery staple"
NEW_PASSWORD = "a completely different password"


@dataclass
class FakeIdentityDb:
    users: dict[UUID, User] = field(default_factory=dict)
    credentials: dict[UUID, LocalCredential] = field(default_factory=dict)
    organizations: dict[UUID, Organization] = field(default_factory=dict)
    memberships: dict[UUID, Membership] = field(default_factory=dict)
    sessions: dict[str, Session] = field(default_factory=dict)


class FakeUow:
    def __init__(self, db: FakeIdentityDb) -> None:
        self.session = db
        self.registered: list[Any] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    def register(self, aggregate: Any) -> None:
        self.registered.append(aggregate)


class FakeUserRepository:
    def __init__(self, db: FakeIdentityDb) -> None:
        self.db = db

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self.db.users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((user for user in self.db.users.values() if user.email == email), None)

    async def get_by_linked_identity(
        self, provider: str, provider_subject: str
    ) -> User | None:
        return next(
            (
                user
                for user in self.db.users.values()
                if any(
                    item.provider == provider
                    and item.provider_subject == provider_subject
                    for item in user.linked_identities
                )
            ),
            None,
        )

    async def add(self, user: User) -> None:
        self.db.users[user.id] = user

    async def save(self, user: User) -> None:
        self.db.users[user.id] = user


class FakeCredentialRepository:
    def __init__(self, db: FakeIdentityDb) -> None:
        self.db = db

    async def get_by_user_id(self, user_id: UUID) -> LocalCredential | None:
        return self.db.credentials.get(user_id)

    async def add(self, credential: LocalCredential) -> None:
        self.db.credentials[credential.user_id] = credential

    async def save(self, credential: LocalCredential) -> None:
        self.db.credentials[credential.user_id] = credential


class FakeOrganizationRepository:
    def __init__(self, db: FakeIdentityDb) -> None:
        self.db = db

    async def add(self, organization: Organization) -> None:
        self.db.organizations[organization.id] = organization


class FakeMembershipRepository:
    def __init__(self, db: FakeIdentityDb) -> None:
        self.db = db

    async def add(self, membership: Membership) -> None:
        self.db.memberships[membership.user_id] = membership

    async def get_by_user_id(self, user_id: UUID) -> Membership | None:
        return self.db.memberships.get(user_id)


class FakeSessionRepository:
    def __init__(self, db: FakeIdentityDb) -> None:
        self.db = db

    async def add(self, session: Session) -> None:
        self.db.sessions[session.id] = session


@pytest.fixture(autouse=True)
def fake_repositories(monkeypatch: pytest.MonkeyPatch) -> None:
    for module in (register_module, login_module, google_module, link_module):
        monkeypatch.setattr(module, "UserRepository", FakeUserRepository)
    for module in (register_module, login_module, password_module):
        monkeypatch.setattr(
            module, "LocalCredentialRepository", FakeCredentialRepository
        )
    monkeypatch.setattr(lifecycle_module, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(
        lifecycle_module, "OrganizationRepository", FakeOrganizationRepository
    )
    monkeypatch.setattr(
        lifecycle_module, "MembershipRepository", FakeMembershipRepository
    )
    monkeypatch.setattr(lifecycle_module, "SessionRepository", FakeSessionRepository)


async def test_register_login_and_change_password_orchestrate_identity_lifecycle() -> None:
    db = FakeIdentityDb()
    ids = FakeIdGenerator()
    clock = FakeClock()
    hasher = FakePasswordHasher()
    registered = await RegisterWithPasswordHandler(
        FakeUow(db), hasher, clock, ids
    ).handle(" Ada@Example.COM ", PASSWORD)

    assert len(db.users) == 1
    assert len(db.organizations) == 1
    assert len(db.memberships) == 1
    assert len(db.sessions) == 1
    assert len(db.credentials) == 1
    assert db.users[registered.user_id].email == "ada@example.com"

    signed_in = await SignInWithPasswordHandler(
        FakeUow(db), hasher, clock, ids
    ).handle("ADA@example.com", PASSWORD)
    assert signed_in.user_id == registered.user_id
    with pytest.raises(InvalidCredentialsError):
        await SignInWithPasswordHandler(FakeUow(db), hasher, clock, ids).handle(
            "missing@example.com", PASSWORD
        )

    password_handler = SetOrChangePasswordHandler(FakeUow(db), hasher, clock, ids)
    with pytest.raises(CurrentPasswordRequiredError):
        await password_handler.handle(registered.user_id, "wrong", NEW_PASSWORD)
    await password_handler.handle(registered.user_id, PASSWORD, NEW_PASSWORD)
    relogin = await SignInWithPasswordHandler(
        FakeUow(db), hasher, clock, ids
    ).handle("ada@example.com", NEW_PASSWORD)
    assert relogin.user_id == registered.user_id


async def test_google_collision_requires_explicit_link_then_uses_stable_subject() -> None:
    db = FakeIdentityDb()
    ids = FakeIdGenerator()
    clock = FakeClock()
    provider = FakeIdentityProvider()
    registered = await RegisterWithPasswordHandler(
        FakeUow(db), FakePasswordHasher(), clock, ids
    ).handle("ada@example.com", PASSWORD)
    provider.identities["code"] = ExternalIdentity(
        subject="stable-google-subject",
        email="ADA@example.com",
        email_verified=True,
        name="Ada Lovelace",
        picture=None,
        nonce="nonce",
    )

    with pytest.raises(GoogleAccountLinkRequiredError):
        await SignInWithGoogleHandler(FakeUow(db), provider, clock, ids).handle(
            "code", "nonce"
        )
    assert len(db.users) == 1

    await LinkGoogleIdentityHandler(FakeUow(db), provider).handle(
        registered.user_id, "code", "nonce"
    )
    google_sign_in = await SignInWithGoogleHandler(
        FakeUow(db), provider, clock, ids
    ).handle("code", "nonce")
    assert google_sign_in.user_id == registered.user_id
