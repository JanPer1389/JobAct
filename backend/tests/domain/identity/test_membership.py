"""Tests for `Membership` revocation.

Task 1.1's specified test: `Membership.revoke()` blocks access -- an
active membership's `is_active` flips to `False` once revoked.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from jobact.contexts.identity.domain.membership import Membership


def _active_membership(joined_at: datetime) -> Membership:
    return Membership(
        id=uuid4(),
        user_id=uuid4(),
        organization_id=uuid4(),
        role="technician",
        joined_at=joined_at,
        revoked_at=None,
    )


def test_new_membership_is_active() -> None:
    membership = _active_membership(joined_at=datetime.now(UTC))

    assert membership.is_active is True


def test_revoke_blocks_access() -> None:
    membership = _active_membership(joined_at=datetime.now(UTC))
    revoked_at = datetime.now(UTC)

    membership.revoke(revoked_at)

    assert membership.is_active is False
    assert membership.revoked_at == revoked_at


def test_revoking_an_already_revoked_membership_raises() -> None:
    membership = _active_membership(joined_at=datetime.now(UTC))
    membership.revoke(datetime.now(UTC))

    with pytest.raises(ValueError):
        membership.revoke(datetime.now(UTC))
