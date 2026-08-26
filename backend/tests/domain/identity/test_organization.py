"""Minimal construction test for `Organization`."""

from datetime import UTC, datetime
from uuid import uuid4

from jobact.contexts.identity.domain.organization import Organization


def test_organization_construction_sets_fields() -> None:
    org_id = uuid4()
    created_at = datetime.now(UTC)

    org = Organization(id=org_id, name="Acme Field Services", created_at=created_at)

    assert org.id == org_id
    assert org.name == "Acme Field Services"
    assert org.created_at == created_at
