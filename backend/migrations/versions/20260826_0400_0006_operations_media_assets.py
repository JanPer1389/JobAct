"""operations: media_assets

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-26 04:00:00

Adds `operations.media_assets` to the existing `operations` schema.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("phase", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        schema="operations",
    )
    op.create_index(
        "ix_media_assets_organization_id",
        "media_assets",
        ["organization_id"],
        schema="operations",
    )


def downgrade() -> None:
    op.drop_table("media_assets", schema="operations")
