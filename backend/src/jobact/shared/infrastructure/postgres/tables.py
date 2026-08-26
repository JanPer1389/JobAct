"""SQLAlchemy Core table definitions for the `platform` schema.

These are lightweight Core `Table` objects (not declarative ORM models),
used by infrastructure code -- e.g. `SqlAlchemyUnitOfWork` writing to the
outbox -- to build statements against the tables created by the Alembic
baseline migration (`migrations/versions/`). The migration is the source
of truth for the actual DDL; these definitions must stay in sync with it
and are not used to generate or run the migration itself.
"""

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = MetaData()

outbox_table = Table(
    "outbox",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("aggregate_type", String, nullable=False),
    Column("aggregate_id", UUID(as_uuid=True), nullable=False),
    Column("event_type", String, nullable=False),
    Column("event_version", Integer, nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("published_at", DateTime(timezone=True), nullable=True),
    schema="platform",
)

inbox_table = Table(
    "inbox",
    metadata,
    Column("message_id", UUID(as_uuid=True), primary_key=True),
    Column("consumer", String, nullable=False),
    Column("processed_at", DateTime(timezone=True), nullable=False),
    schema="platform",
)

idempotency_keys_table = Table(
    "idempotency_keys",
    metadata,
    # Composite PK: uniqueness is scoped per-organization, not global --
    # two different orgs may independently send the same client-generated
    # Idempotency-Key value (migration 0003). Matches the middleware's own
    # (key, organization_id) lookup scope.
    Column("key", String, primary_key=True),
    Column("organization_id", UUID(as_uuid=True), primary_key=True),
    Column("endpoint", String, nullable=False),
    Column("request_hash", String, nullable=False),
    Column("response_status", Integer, nullable=True),
    Column("response_body", JSONB, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    schema="platform",
)
