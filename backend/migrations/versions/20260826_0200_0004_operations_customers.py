"""operations: customers

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-26 02:00:00

Adds `operations.customers` to the `operations` schema created (empty)
by the Task 0.3 baseline migration. Does not touch any other schema.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column("service_type", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="operations",
    )
    op.create_index(
        "ix_customers_organization_id",
        "customers",
        ["organization_id"],
        schema="operations",
    )


def downgrade() -> None:
    op.drop_table("customers", schema="operations")
