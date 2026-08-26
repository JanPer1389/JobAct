"""operations: visits

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-26 03:00:00

Adds `operations.visits` to the existing `operations` schema.
`raw_notes` is nullable and, per this plan's own ruling, is NOT the
authoritative input to AI report drafting (POST /reports.raw_notes is) --
it only exists for a visit to carry notes if separately PATCHed.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "visits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("technician_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gps_lat", sa.Float(), nullable=True),
        sa.Column("gps_lon", sa.Float(), nullable=True),
        sa.Column("gps_accuracy_m", sa.Float(), nullable=True),
        sa.Column("before_photo_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("after_photo_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_notes", sa.String(), nullable=True),
        schema="operations",
    )
    op.create_index(
        "ix_visits_organization_id", "visits", ["organization_id"], schema="operations"
    )


def downgrade() -> None:
    op.drop_table("visits", schema="operations")
