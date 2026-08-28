"""workflow: add workflow_runs.claimed_at for atomic step claiming

Revision ID: 0016
Revises: 0015
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        schema="workflow",
    )


def downgrade() -> None:
    op.drop_column("workflow_runs", "claimed_at", schema="workflow")
