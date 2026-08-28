"""Explicitly attach a verified Google subject to an authenticated user."""

from uuid import UUID

from jobact.contexts.identity.application.sign_in_with_google import InvalidNonceError
from jobact.contexts.identity.infrastructure.user_repository import UserRepository
from jobact.shared.application.ports import IdentityProvider
from jobact.shared.application.uow import UnitOfWork


class GoogleIdentityAlreadyLinkedError(Exception):
    pass


class LinkGoogleIdentityHandler:
    def __init__(self, uow: UnitOfWork, identity_provider: IdentityProvider) -> None:
        self._uow = uow
        self._identity_provider = identity_provider

    async def handle(self, user_id: UUID, code: str, expected_nonce: str) -> None:
        external_identity = await self._identity_provider.exchange(code)
        if external_identity.nonce != expected_nonce:
            raise InvalidNonceError
        async with self._uow:
            repo = UserRepository(self._uow.session)
            owner = await repo.get_by_linked_identity("google", external_identity.subject)
            if owner is not None and owner.id != user_id:
                raise GoogleIdentityAlreadyLinkedError
            user = await repo.get_by_id(user_id)
            if user is None:
                raise ValueError("Authenticated user no longer exists.")
            user.link_identity("google", external_identity.subject)
            await repo.save(user)
            self._uow.register(user)
