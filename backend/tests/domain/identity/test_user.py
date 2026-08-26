"""Tests for `User` construction and its minimal behavior:
`link_identity` (idempotent) and `touch_last_seen`.
"""

from datetime import UTC, datetime
from uuid import uuid4

from jobact.contexts.identity.domain.user import User


def _new_user() -> User:
    return User.register(
        id=uuid4(),
        email="tech@example.com",
        email_verified=True,
        display_name="Jamie Tech",
        given_name="Jamie",
        family_name="Tech",
        avatar_url=None,
        locale="en-US",
        timezone="America/New_York",
        registered_at=datetime.now(UTC),
    )


def test_register_creates_user_with_no_linked_identities() -> None:
    user = _new_user()

    assert user.email == "tech@example.com"
    assert user.linked_identities == []
    assert user.activated_at is None


def test_link_identity_adds_a_new_linked_identity() -> None:
    user = _new_user()

    user.link_identity(provider="google", provider_subject="12345")

    assert len(user.linked_identities) == 1
    assert user.linked_identities[0].provider == "google"
    assert user.linked_identities[0].provider_subject == "12345"


def test_link_identity_is_idempotent_for_the_same_provider_and_subject() -> None:
    user = _new_user()

    user.link_identity(provider="google", provider_subject="12345")
    user.link_identity(provider="google", provider_subject="12345")

    assert len(user.linked_identities) == 1


def test_touch_last_seen_updates_last_seen_at() -> None:
    user = _new_user()
    later = datetime.now(UTC)

    user.touch_last_seen(later)

    assert user.last_seen_at == later
