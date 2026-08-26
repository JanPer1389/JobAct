"""operations: reports, report revisions, materials, and signatures.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-26 05:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("human_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("organization_id", "human_id", name="uq_reports_org_human_id"),
        schema="operations",
    )
    op.create_index(
        "ix_reports_organization_id", "reports", ["organization_id"], schema="operations"
    )
    op.create_table(
        "report_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operations.reports.id"),
            nullable=False,
        ),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("work_completed", sa.Text(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("ai_confidence", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confirmed_by_user_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amount_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("report_id", "revision_no", name="uq_report_revisions_report_no"),
        schema="operations",
    )
    op.create_table(
        "report_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "revision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operations.report_revisions.id"),
            nullable=False,
        ),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("qty", sa.String(), nullable=False),
        schema="operations",
    )
    op.create_table(
        "signatures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operations.reports.id"),
            nullable=False,
        ),
        sa.Column("signer_name", sa.String(), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("media_asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ip", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        schema="operations",
    )


def downgrade() -> None:
    op.drop_table("signatures", schema="operations")
    op.drop_table("report_materials", schema="operations")
    op.drop_table("report_revisions", schema="operations")
    op.drop_table("reports", schema="operations")
