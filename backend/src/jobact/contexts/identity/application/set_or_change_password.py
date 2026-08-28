"""Authenticated password setup and replacement."""

from uuid import UUID

from jobact.contexts.identity.domain.local_credential import (
    PASSWORD_HASH_VERSION,
    LocalCredential,
    validate_password,
)
from jobact.contexts.identity.infrastructure.local_credential_repository import (
    LocalCredentialRepository,
)
from jobact.shared.application.ports import Clock, IdGenerator, PasswordHasher
from jobact.shared.application.uow import UnitOfWork


class CurrentPasswordRequiredError(Exception):
    pass


class SetOrChangePasswordHandler:
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

    async def handle(
        self, user_id: UUID, current_password: str | None, new_password: str
    ) -> None:
        validate_password(new_password)
        async with self._uow:
            credential = await LocalCredentialRepository(
                self._uow.session
            ).get_by_user_id(user_id)
            encoded_hash = None if credential is None else credential.password_hash

        if credential is not None and not await self._password_hasher.verify(
            current_password or "", encoded_hash
        ):
            raise CurrentPasswordRequiredError
        new_hash = await self._password_hasher.hash(new_password)
        now = self._clock.now()
        async with self._uow:
            repo = LocalCredentialRepository(self._uow.session)
            credential = await repo.get_by_user_id(user_id)
            if credential is None:
                await repo.add(
                    LocalCredential(
                        id=self._id_generator.new_id(),
                        user_id=user_id,
                        password_hash=new_hash,
                        hash_version=PASSWORD_HASH_VERSION,
                        created_at=now,
                        updated_at=now,
                    )
                )
            else:
                credential.replace_hash(new_hash, now)
                await repo.save(credential)
