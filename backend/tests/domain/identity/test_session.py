"""Tests for `Session.is_active(now)`.

Task 1.1's specified test: `is_active(now)` respects `expires_at` and
`revoked_at` -- active before expiry and not revoked -> True; past
`expires_at` -> False; revoked but not yet expired -> False.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from jobact.contexts.identity.domain.session import Session


def _session(*, expires_at: datetime, revoked_at: datetime | None) -> Session:
    now = datetime.now(UTC)
    return Session(
        id="opaque-token-value",
        user_id=uuid4(),
        organization_id=uuid4(),
        device_id=None,
        created_at=now,
        last_seen_at=now,
        expires_at=expires_at,
        revoked_at=revoked_at,
        ip=None,
        user_agent=None,
    )


def test_session_is_active_before_expiry_and_not_revoked() -> None:
    now = datetime.now(UTC)
    session = _session(expires_at=now + timedelta(hours=1), revoked_at=None)

    assert session.is_active(now) is True


def test_session_is_inactive_past_expires_at() -> None:
    now = datetime.now(UTC)
    session = _session(expires_at=now - timedelta(seconds=1), revoked_at=None)

    assert session.is_active(now) is False


def test_session_is_inactive_when_revoked_even_if_not_yet_expired() -> None:
    now = datetime.now(UTC)
    session = _session(
        expires_at=now + timedelta(hours=1),
        revoked_at=now - timedelta(minutes=1),
    )

    assert session.is_active(now) is False
