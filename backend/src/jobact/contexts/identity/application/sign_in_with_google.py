"""Google OIDC sign-in using stable provider subjects and explicit collisions."""

from jobact.contexts.identity.application.authentication import (
    AuthenticationResult,
    create_session_for_user,
    provision_personal_account,
)
from jobact.contexts.identity.domain.local_credential import normalize_email
from jobact.contexts.identity.domain.user import User
from jobact.contexts.identity.infrastructure.user_repository import UserRepository
from jobact.shared.application.ports import (
    Clock,
    ExternalIdentity,
    IdentityProvider,
    IdGenerator,
)
from jobact.shared.application.uow import UnitOfWork

SignInResult = AuthenticationResult


class InvalidNonceError(Exception):
    """The verified ID token nonce did not match the issued nonce."""


class GoogleAccountLinkRequiredError(Exception):
    """The Google email belongs to an existing, unlinked account."""


class SignInWithGoogleHandler:
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
            repo = UserRepository(self._uow.session)
            user = await repo.get_by_linked_identity(
                "google", external_identity.subject
            )
            if user is None:
                result, user = await self._register_new_user(external_identity, repo)
            else:
                result = await self._update_existing_user(
                    user, external_identity, repo
                )
            self._uow.register(user)
            return result

    async def _register_new_user(
        self, external_identity: ExternalIdentity, repo: UserRepository
    ) -> tuple[SignInResult, User]:
        normalized_email = normalize_email(external_identity.email)
        if await repo.get_by_email(normalized_email) is not None:
            raise GoogleAccountLinkRequiredError
        now = self._clock.now()
        user = User.register(
            id=self._id_generator.new_id(),
            email=normalized_email,
            email_verified=external_identity.email_verified,
            display_name=external_identity.name,
            given_name=external_identity.name,
            family_name="",
            avatar_url=external_identity.picture,
            locale="en-US",
            currency="RUB",
            timezone="UTC",
            registered_at=now,
        )
        user.link_identity("google", external_identity.subject)
        result = await provision_personal_account(
            self._uow.session,
            user=user,
            workspace_name=f"{external_identity.name}'s workspace",
            now=now,
            id_generator=self._id_generator,
        )
        return result, user

    async def _update_existing_user(
        self, user: User, external_identity: ExternalIdentity, repo: UserRepository
    ) -> SignInResult:
        normalized_email = normalize_email(external_identity.email)
        if user.email != normalized_email:
            email_owner = await repo.get_by_email(normalized_email)
            if email_owner is None or email_owner.id == user.id:
                user.change_email(normalized_email, external_identity.email_verified)
        user.touch_last_seen(self._clock.now())
        await repo.save(user)
        return await create_session_for_user(
            self._uow.session,
            user_id=user.id,
            now=self._clock.now(),
            id_generator=self._id_generator,
        )
