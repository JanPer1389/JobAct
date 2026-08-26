"""workflow: retain workflow-run input data

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-26 08:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column(
            "input_data",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        schema="workflow",
    )
    op.alter_column("workflow_runs", "input_data", server_default=None, schema="workflow")


def downgrade() -> None:
    op.drop_column("workflow_runs", "input_data", schema="workflow")
