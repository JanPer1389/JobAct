"""workflow: workflow_runs, workflow_steps

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-26 07:00:00

Adds `workflow.workflow_runs` and `workflow.workflow_steps` to the
existing (empty) `workflow` schema created by the Task 0.3 baseline
migration. `state_version` backs optimistic locking on `workflow_runs`
(compare-and-swap at the repository layer, not enforced by a DB
constraint here -- Postgres has no built-in optimistic-lock primitive,
the UPDATE ... WHERE state_version = ? pattern is the whole mechanism).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_type", sa.String(), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        schema="workflow",
    )
    op.create_index(
        "ix_workflow_runs_subject_id", "workflow_runs", ["subject_id"], schema="workflow"
    )
    op.create_table(
        "workflow_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow.workflow_runs.id"),
            nullable=False,
        ),
        sa.Column("step", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("input", postgresql.JSONB(), nullable=True),
        sa.Column("output", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        schema="workflow",
    )
    op.create_index(
        "ix_workflow_steps_run_id", "workflow_steps", ["run_id"], schema="workflow"
    )


def downgrade() -> None:
    op.drop_table("workflow_steps", schema="workflow")
    op.drop_table("workflow_runs", schema="workflow")
