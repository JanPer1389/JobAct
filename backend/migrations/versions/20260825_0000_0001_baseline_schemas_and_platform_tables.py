"""baseline: five schemas + platform outbox/inbox/idempotency_keys tables

Revision ID: 0001
Revises:
Create Date: 2026-08-25 00:00:00

Creates the five schema namespaces this milestone's plan uses
(`identity`, `operations`, `workflow`, `platform`, `audit`) and the
`platform.outbox` / `platform.inbox` / `platform.idempotency_keys`
tables that the transactional-outbox / idempotency-key mechanisms
(this task and Tasks 2.1/2.2/2.3) depend on.

Deliberately out of scope for this migration (later tasks own these):
- Any tables inside `identity`, `operations`, `workflow`, or `audit` --
  those schemas are created here as empty namespaces only.
- `audit.audit_log` specifically -- nothing in this milestone's plan
  writes to an audit trail yet, so building that table now would be
  speculative, unused scope.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMAS = ("identity", "operations", "workflow", "platform", "audit")


def upgrade() -> None:
    for schema in SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    op.create_table(
        "outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("aggregate_type", sa.String(), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        schema="platform",
    )

    op.create_table(
        "inbox",
        sa.Column("message_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("consumer", sa.String(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        schema="platform",
    )

    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("request_hash", sa.String(), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        schema="platform",
    )


def downgrade() -> None:
    op.drop_table("idempotency_keys", schema="platform")
    op.drop_table("inbox", schema="platform")
    op.drop_table("outbox", schema="platform")

    for schema in SCHEMAS:
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
