"""SQLAlchemy Core table definitions for the `operations` schema.

Mirrors migration 0004; not used to generate it.
"""

from sqlalchemy import Column, DateTime, MetaData, String, Table
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

customers_table = Table(
    "customers",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("organization_id", UUID(as_uuid=True), nullable=False),
    Column("name", String, nullable=False),
    Column("address", String, nullable=False),
    Column("phone", String, nullable=False),
    Column("service_type", String, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    schema="operations",
)
