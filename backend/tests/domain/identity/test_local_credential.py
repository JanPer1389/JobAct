from datetime import UTC, datetime
from uuid import uuid4

import pytest

from jobact.contexts.identity.domain.local_credential import (
    LocalCredential,
    PasswordPolicyError,
    normalize_email,
    validate_password,
)


def test_normalize_email_trims_and_lowercases() -> None:
    assert normalize_email("  Tech@Example.COM ") == "tech@example.com"


def test_password_policy_is_length_only() -> None:
    validate_password("correct horse battery staple")
    with pytest.raises(PasswordPolicyError):
        validate_password("too-short")


def test_local_credential_rejects_non_argon2id_hash() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValueError):
        LocalCredential(
            id=uuid4(),
            user_id=uuid4(),
            password_hash="plaintext",
            hash_version=1,
            created_at=now,
            updated_at=now,
        )
