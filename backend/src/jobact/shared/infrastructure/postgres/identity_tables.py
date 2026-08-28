"""SQLAlchemy Core table definitions for the `identity` schema.

These are lightweight Core `Table` objects (not declarative ORM models),
used by infrastructure code -- e.g. Task 1.3's identity repositories --
to build statements against the tables created by the Alembic migration
`migrations/versions/20260826_0000_0002_identity_tables.py`. The
migration is the source of truth for the actual DDL; these definitions
must stay in sync with it and are not used to generate or run the
migration itself.

Split out from `tables.py` (which holds the `platform` schema's tables)
now that there are 9 tables across 2 schemas -- keeps each file scoped to
one schema.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    MetaData,
    SmallInteger,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

users_table = Table(
    "users",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("email", Text, nullable=False),
    Column("email_verified", Boolean, nullable=False),
    Column("status", Text, nullable=False),
    Column("locale", Text, nullable=False),
    Column("timezone", Text, nullable=False),
    Column("registered_at", DateTime(timezone=True), nullable=False),
    Column("activated_at", DateTime(timezone=True), nullable=True),
    Column("last_seen_at", DateTime(timezone=True), nullable=False),
    schema="identity",
)

user_profiles_table = Table(
    "user_profiles",
    metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("identity.users.id"), primary_key=True),
    Column("display_name", Text, nullable=False),
    Column("given_name", Text, nullable=False),
    Column("family_name", Text, nullable=False),
    Column("avatar_url", Text, nullable=True),
    schema="identity",
)

identities_table = Table(
    "identities",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=False),
    Column("provider", Text, nullable=False),
    Column("provider_subject", Text, nullable=False),
    schema="identity",
)

organizations_table = Table(
    "organizations",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("name", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    schema="identity",
)

memberships_table = Table(
    "memberships",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=False),
    Column(
        "organization_id",
        UUID(as_uuid=True),
        ForeignKey("identity.organizations.id"),
        nullable=False,
    ),
    Column("role", Text, nullable=False),
    Column("joined_at", DateTime(timezone=True), nullable=False),
    Column("revoked_at", DateTime(timezone=True), nullable=True),
    schema="identity",
)

sessions_table = Table(
    "sessions",
    metadata,
    Column("id", Text, primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=False),
    Column(
        "organization_id",
        UUID(as_uuid=True),
        ForeignKey("identity.organizations.id"),
        nullable=False,
    ),
    Column("device_id", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("last_seen_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("revoked_at", DateTime(timezone=True), nullable=True),
    Column("ip", Text, nullable=True),
    Column("user_agent", Text, nullable=True),
    schema="identity",
)

local_credentials_table = Table(
    "local_credentials",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=False),
    Column("password_hash", Text, nullable=False),
    Column("hash_version", SmallInteger, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("user_id", name="uq_local_credentials_user_id"),
    schema="identity",
)
