"""operations: report_number_counters (atomic per-org/year human_id sequence)

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-26 06:00:00

Task 4.1's scaffold generated `human_id` (`JA-YYYY-NNNN`) by scanning
existing `reports.human_id` values for the org/year and taking max+1 --
not safe under concurrent report creation (two concurrent creates can
read the same max before either commits). This adds a small counter
table so allocation is a single atomic UPSERT
(`INSERT ... ON CONFLICT DO UPDATE ... RETURNING`), which Postgres
executes under a row-level lock -- the standard safe pattern for a
per-key sequence without dynamic per-org `CREATE SEQUENCE` DDL.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "report_number_counters",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("year", sa.Integer(), primary_key=True),
        sa.Column("next_number", sa.Integer(), nullable=False),
        schema="operations",
    )


def downgrade() -> None:
    op.drop_table("report_number_counters", schema="operations")
