"""Local email/password identity rules and credential aggregate."""

from datetime import datetime
from uuid import UUID

from jobact.shared.domain import AggregateRoot

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128
PASSWORD_HASH_VERSION = 1


class PasswordPolicyError(ValueError):
    """Raised when a password does not meet the public password policy."""


def normalize_email(email: str) -> str:
    """Return the canonical form used for identity lookup and uniqueness."""
    return email.strip().lower()


def validate_password(password: str) -> None:
    """Enforce a length-only policy without obscure composition rules."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise PasswordPolicyError(
            f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
        )


class LocalCredential(AggregateRoot):
    """A versioned, one-per-user password credential.

    Raw passwords and confirmation values never enter this aggregate. The
    infrastructure password adapter supplies an encoded Argon2id hash.
    """

    def __init__(
        self,
        *,
        id: UUID,
        user_id: UUID,
        password_hash: str,
        hash_version: int,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        super().__init__()
        if not password_hash.startswith("$argon2id$"):
            raise ValueError("Local credentials require an encoded Argon2id hash.")
        if hash_version < 1:
            raise ValueError("Credential hash version must be positive.")
        self.id = id
        self.user_id = user_id
        self.password_hash = password_hash
        self.hash_version = hash_version
        self.created_at = created_at
        self.updated_at = updated_at

    def replace_hash(self, password_hash: str, now: datetime) -> None:
        if not password_hash.startswith("$argon2id$"):
            raise ValueError("Local credentials require an encoded Argon2id hash.")
        self.password_hash = password_hash
        self.hash_version = PASSWORD_HASH_VERSION
        self.updated_at = now
