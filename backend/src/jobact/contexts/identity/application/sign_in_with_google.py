"""`SignInWithGoogleHandler`: the first application-layer command
handler in this codebase.

Orchestrates `IdentityProvider.exchange()` + the identity context's
repositories + `UnitOfWork` to turn a completed Google OAuth code
exchange into a persisted `User`/`Organization`/`Membership`/`Session`
(new user) or an updated `User`/`Session` (returning user).

Pure application-layer code: no SQLAlchemy import here, only the
`UnitOfWork`/port Protocols and this context's own repositories (which
own all the SQLAlchemy Core statements).
"""

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from jobact.contexts.identity.domain.membership import Membership
from jobact.contexts.identity.domain.organization import Organization
from jobact.contexts.identity.domain.session import Session
from jobact.contexts.identity.domain.user import User
from jobact.contexts.identity.infrastructure.membership_repository import (
    MembershipRepository,
)
from jobact.contexts.identity.infrastructure.organization_repository import (
    OrganizationRepository,
)
from jobact.contexts.identity.infrastructure.session_repository import SessionRepository
from jobact.contexts.identity.infrastructure.user_repository import UserRepository
from jobact.shared.application.ports import (
    Clock,
    ExternalIdentity,
    IdentityProvider,
    IdGenerator,
)
from jobact.shared.application.uow import UnitOfWork

_SESSION_LIFETIME = timedelta(days=30)


class InvalidNonceError(Exception):
    """Raised when the ID token's `nonce` claim doesn't match the value
    the caller expected -- a possible replay/CSRF attack, so sign-in must
    never silently proceed.
    """


@dataclass(frozen=True)
class SignInResult:
    session_id: str
    user_id: UUID
    organization_id: UUID
    role: str


class SignInWithGoogleHandler:
    """Handles a completed Google OAuth authorization-code exchange,
    creating a new user (plus a personal organization and owner
    membership) on first sign-in, or updating the existing user on a
    later sign-in.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        identity_provider: IdentityProvider,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._uow = uow
        self._identity_provider = identity_provider
        self._clock = clock
        self._id_generator = id_generator

    async def handle(self, code: str, expected_nonce: str) -> SignInResult:
        external_identity = await self._identity_provider.exchange(code)

        if external_identity.nonce != expected_nonce:
            raise InvalidNonceError(
                "ID token nonce does not match the expected nonce for this sign-in attempt"
            )

        async with self._uow:
            user_repo = UserRepository(self._uow.session)
            user = await user_repo.get_by_linked_identity(
                "google", external_identity.subject
            )

            if user is None:
                user, organization_id, role = await self._register_new_user(
                    external_identity, user_repo
                )
            else:
                organization_id, role = await self._update_existing_user(
                    user, external_identity, user_repo
                )

            session = Session(
                id=str(self._id_generator.new_id()),
                user_id=user.id,
                organization_id=organization_id,
                device_id=None,
                created_at=self._clock.now(),
                last_seen_at=self._clock.now(),
                expires_at=self._clock.now() + _SESSION_LIFETIME,
                revoked_at=None,
                ip=None,
                user_agent=None,
            )
            session_repo = SessionRepository(self._uow.session)
            await session_repo.add(session)

            self._uow.register(user)

            return SignInResult(
                session_id=session.id,
                user_id=user.id,
                organization_id=organization_id,
                role=role,
            )

    async def _register_new_user(
        self, external_identity: ExternalIdentity, user_repo: UserRepository
    ) -> tuple[User, UUID, str]:
        now = self._clock.now()
        user = User.register(
            id=self._id_generator.new_id(),
            email=external_identity.email,
            email_verified=external_identity.email_verified,
            display_name=external_identity.name,
            given_name=external_identity.name,
            family_name="",
            avatar_url=external_identity.picture,
            locale="en-US",
            timezone="UTC",
            registered_at=now,
        )
        user.link_identity("google", external_identity.subject)
        await user_repo.add(user)

        organization = Organization(
            id=self._id_generator.new_id(),
            name=f"{external_identity.name}'s workspace",
            created_at=now,
        )
        org_repo = OrganizationRepository(self._uow.session)
        await org_repo.add(organization)

        membership = Membership(
            id=self._id_generator.new_id(),
            user_id=user.id,
            organization_id=organization.id,
            role="owner",
            joined_at=now,
            revoked_at=None,
        )
        membership_repo = MembershipRepository(self._uow.session)
        await membership_repo.add(membership)

        return user, organization.id, "owner"

    async def _update_existing_user(
        self, user: User, external_identity: ExternalIdentity, user_repo: UserRepository
    ) -> tuple[UUID, str]:
        if user.email != external_identity.email:
            user.change_email(external_identity.email, external_identity.email_verified)
        user.touch_last_seen(self._clock.now())
        await user_repo.save(user)

        membership_repo = MembershipRepository(self._uow.session)
        membership = await membership_repo.get_by_user_id(user.id)
        assert membership is not None, f"user {user.id} has no membership"

        return membership.organization_id, membership.role
