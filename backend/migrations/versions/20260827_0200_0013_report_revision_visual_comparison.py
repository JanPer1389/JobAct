"""operations: unified AI result fields on report revisions

Revision ID: 0013
Revises: 0012
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "report_revisions",
        sa.Column("visual_comparison_status", sa.String(), nullable=True),
        schema="operations",
    )
    op.add_column(
        "report_revisions",
        sa.Column("visual_comparison", postgresql.JSONB(), nullable=True),
        schema="operations",
    )


def downgrade() -> None:
    op.drop_column("report_revisions", "visual_comparison", schema="operations")
    op.drop_column("report_revisions", "visual_comparison_status", schema="operations")
