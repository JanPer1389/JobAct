"""operations: immutable visual audit attempts

Revision ID: 0011
Revises: 0010
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "visual_audit_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operations.reports.id"), nullable=False),
        sa.Column("report_revision_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operations.report_revisions.id"), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("work_description", sa.String(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("provided_price_usd", sa.Numeric(12, 2), nullable=True),
        sa.Column("usd_rub_rate", sa.Numeric(12, 4), nullable=False),
        sa.Column("usd_rub_rate_date", sa.Date(), nullable=False),
        sa.Column("usd_rub_rate_source", sa.String(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(16, 8), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("failure_code", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("acknowledgement_reason", sa.String(), nullable=True),
        schema="operations",
    )
    op.create_index("ix_visual_audit_report", "visual_audit_attempts", ["organization_id", "report_id", "created_at"], schema="operations")
    op.create_table(
        "visual_audit_photos",
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operations.visual_audit_attempts.id"), primary_key=True),
        sa.Column("phase", sa.String(), primary_key=True),
        sa.Column("pair_index", sa.Integer(), primary_key=True),
        sa.Column("media_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operations.media_assets.id"), nullable=False),
        sa.UniqueConstraint("attempt_id", "media_asset_id", name="uq_visual_audit_photo_asset"),
        schema="operations",
    )


def downgrade() -> None:
    op.drop_table("visual_audit_photos", schema="operations")
    op.drop_index("ix_visual_audit_report", table_name="visual_audit_attempts", schema="operations")
    op.drop_table("visual_audit_attempts", schema="operations")
