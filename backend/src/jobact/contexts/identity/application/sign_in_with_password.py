"""Authenticate a local credential without revealing account existence."""

from jobact.contexts.identity.application.authentication import (
    AuthenticationResult,
    create_session_for_user,
)
from jobact.contexts.identity.domain.local_credential import normalize_email
from jobact.contexts.identity.infrastructure.local_credential_repository import (
    LocalCredentialRepository,
)
from jobact.contexts.identity.infrastructure.user_repository import UserRepository
from jobact.shared.application.ports import Clock, IdGenerator, PasswordHasher
from jobact.shared.application.uow import UnitOfWork


class InvalidCredentialsError(Exception):
    pass


class SignInWithPasswordHandler:
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
        async with self._uow:
            user = await UserRepository(self._uow.session).get_by_email(
                normalize_email(email)
            )
            credential = (
                None
                if user is None
                else await LocalCredentialRepository(
                    self._uow.session
                ).get_by_user_id(user.id)
            )
            encoded_hash = None if credential is None else credential.password_hash

        if not await self._password_hasher.verify(password, encoded_hash):
            raise InvalidCredentialsError
        assert user is not None
        async with self._uow:
            result = await create_session_for_user(
                self._uow.session,
                user_id=user.id,
                now=self._clock.now(),
                id_generator=self._id_generator,
            )
            user.touch_last_seen(self._clock.now())
            await UserRepository(self._uow.session).save(user)
            self._uow.register(user)
            return result
