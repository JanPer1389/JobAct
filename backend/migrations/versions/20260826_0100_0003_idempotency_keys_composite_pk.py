"""idempotency_keys: scope uniqueness to (key, organization_id)

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-26 01:00:00

The baseline migration (0001) gave `platform.idempotency_keys` a
single-column primary key on `key` alone. Task 2.1's idempotency
middleware looks up existing keys scoped by `(key, organization_id)`,
correctly preventing one organization from replaying another's cached
response -- but nothing stopped two *different* organizations from
sending the same `Idempotency-Key` header value in the first place
(client-generated, no global uniqueness guarantee across tenants).
When that happened, the second organization's INSERT hit the
single-column PK and raised an unhandled `IntegrityError` (500)
instead of being scoped correctly, which contradicts the multi-tenant
design the lookup already assumes.

Fix: drop the single-column PK and replace it with a composite PK on
`(key, organization_id)`, matching the shape the middleware's queries
already treat as the real uniqueness boundary.
"""

from __future__ import annotations

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_constraint("idempotency_keys_pkey", "idempotency_keys", schema="platform", type_="primary")
    op.create_primary_key(
        "idempotency_keys_pkey",
        "idempotency_keys",
        ["key", "organization_id"],
        schema="platform",
    )


def downgrade() -> None:
    op.drop_constraint("idempotency_keys_pkey", "idempotency_keys", schema="platform", type_="primary")
    op.create_primary_key(
        "idempotency_keys_pkey",
        "idempotency_keys",
        ["key"],
        schema="platform",
    )
