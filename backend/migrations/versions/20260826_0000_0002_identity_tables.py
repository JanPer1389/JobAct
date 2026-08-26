"""identity: users, user_profiles, identities, organizations, memberships,
sessions

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-26 00:00:00

Adds the six tables backing Task 1.1's identity domain aggregates
(`User`, `Organization`, `Membership`, `Session`) to the `identity`
schema created (empty) by the Task 0.3 baseline migration (0001). This
migration does NOT recreate that schema, and does not touch
`operations`/`workflow`/`platform`/`audit`.

`identity.identities` (the `LinkedIdentity` value data nested inside the
`User` aggregate) gets its own surrogate UUID primary key rather than a
composite `(provider, provider_subject)` PK -- a plain `id` column is
simpler for a later repository to reference/update by and is consistent
with how every other table in this migration is keyed. Uniqueness of the
`(provider, provider_subject)` pair (the thing that actually matters, so
the same external account can't be linked to two different users) is
still enforced via a UNIQUE constraint.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("locale", sa.Text(), nullable=False),
        sa.Column("timezone", sa.Text(), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        schema="identity",
    )

    op.create_table(
        "user_profiles",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            primary_key=True,
        ),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("given_name", sa.Text(), nullable=False),
        sa.Column("family_name", sa.Text(), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        schema="identity",
    )

    op.create_table(
        "identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("provider_subject", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "provider", "provider_subject", name="uq_identities_provider_subject"
        ),
        schema="identity",
    )

    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="identity",
    )

    op.create_table(
        "memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity.organizations.id"),
            nullable=False,
        ),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        schema="identity",
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity.organizations.id"),
            nullable=False,
        ),
        sa.Column("device_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        schema="identity",
    )


def downgrade() -> None:
    op.drop_table("sessions", schema="identity")
    op.drop_table("memberships", schema="identity")
    op.drop_table("organizations", schema="identity")
    op.drop_table("identities", schema="identity")
    op.drop_table("user_profiles", schema="identity")
    op.drop_table("users", schema="identity")
