"""identity: add users.currency for the AI-suggested-price currency preference

Revision ID: 0017
Revises: 0016
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("currency", sa.Text(), nullable=False, server_default="RUB"),
        schema="identity",
    )
    op.alter_column("users", "currency", server_default=None, schema="identity")


def downgrade() -> None:
    op.drop_column("users", "currency", schema="identity")
