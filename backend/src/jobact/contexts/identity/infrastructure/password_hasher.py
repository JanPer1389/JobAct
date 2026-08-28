"""Argon2id implementation of the application password-hashing port."""

import asyncio

from argon2 import PasswordHasher as Argon2PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from argon2.low_level import Type


class Argon2idPasswordHasher:
    def __init__(self) -> None:
        self._hasher = Argon2PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )
        self._dummy_hash = self._hasher.hash("jobact-dummy-password-value")

    async def hash(self, password: str) -> str:
        return await asyncio.to_thread(self._hasher.hash, password)

    async def verify(self, password: str, encoded_hash: str | None) -> bool:
        return await asyncio.to_thread(self._verify_sync, password, encoded_hash)

    def _verify_sync(self, password: str, encoded_hash: str | None) -> bool:
        candidate = encoded_hash or self._dummy_hash
        try:
            valid = self._hasher.verify(candidate, password)
        except (InvalidHashError, VerifyMismatchError):
            valid = False
        return valid and encoded_hash is not None
