"""identity: normalized email uniqueness and local credentials

Revision ID: 0012
Revises: 0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE identity.users SET email = lower(btrim(email))")
    op.create_unique_constraint("uq_users_email", "users", ["email"], schema="identity")
    op.create_table(
        "local_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("hash_version", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_local_credentials_user_id"),
        schema="identity",
    )


def downgrade() -> None:
    op.drop_table("local_credentials", schema="identity")
    op.drop_constraint("uq_users_email", "users", schema="identity", type_="unique")
