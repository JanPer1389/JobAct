"""Register a local-password account and its personal tenancy."""

from jobact.contexts.identity.application.authentication import (
    AuthenticationResult,
    provision_personal_account,
)
from jobact.contexts.identity.domain.local_credential import (
    PASSWORD_HASH_VERSION,
    LocalCredential,
    normalize_email,
    validate_password,
)
from jobact.contexts.identity.domain.user import User
from jobact.contexts.identity.infrastructure.local_credential_repository import (
    LocalCredentialRepository,
)
from jobact.contexts.identity.infrastructure.user_repository import UserRepository
from jobact.shared.application.ports import Clock, IdGenerator, PasswordHasher
from jobact.shared.application.uow import UnitOfWork


class AccountAlreadyExistsError(Exception):
    pass


class RegisterWithPasswordHandler:
    def __init__(
        self,
        uow: UnitOfWork,
        password_hasher: PasswordHasher,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._uow = uow
        self._password_hasher = password_hasher
        self._clock = clock
        self._id_generator = id_generator

    async def handle(self, email: str, password: str) -> AuthenticationResult:
        normalized_email = normalize_email(email)
        validate_password(password)
        password_hash = await self._password_hasher.hash(password)
        now = self._clock.now()
        async with self._uow:
            if await UserRepository(self._uow.session).get_by_email(normalized_email):
                raise AccountAlreadyExistsError
            display_name = normalized_email.split("@", 1)[0]
            user = User.register(
                id=self._id_generator.new_id(),
                email=normalized_email,
                email_verified=False,
                display_name=display_name,
                given_name=display_name,
                family_name="",
                avatar_url=None,
                locale="en-US",
                currency="RUB",
                timezone="UTC",
                registered_at=now,
            )
            result = await provision_personal_account(
                self._uow.session,
                user=user,
                workspace_name=f"{display_name}'s workspace",
                now=now,
                id_generator=self._id_generator,
            )
            credential = LocalCredential(
                id=self._id_generator.new_id(),
                user_id=user.id,
                password_hash=password_hash,
                hash_version=PASSWORD_HASH_VERSION,
                created_at=now,
                updated_at=now,
            )
            await LocalCredentialRepository(self._uow.session).add(credential)
            self._uow.register(user)
            return result
