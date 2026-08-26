"""SQLAlchemy Core table definitions for the `operations` schema.

Mirrors migration 0004; not used to generate it.
"""

from sqlalchemy import Column, DateTime, Float, Integer, MetaData, String, Table
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

visits_table = Table(
    "visits",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("organization_id", UUID(as_uuid=True), nullable=False),
    Column("customer_id", UUID(as_uuid=True), nullable=False),
    Column("technician_id", UUID(as_uuid=True), nullable=False),
    Column("status", String, nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("gps_lat", Float, nullable=True),
    Column("gps_lon", Float, nullable=True),
    Column("gps_accuracy_m", Float, nullable=True),
    Column("before_photo_count", Integer, nullable=False),
    Column("after_photo_count", Integer, nullable=False),
    Column("raw_notes", String, nullable=True),
    schema="operations",
)

media_assets_table = Table(
    "media_assets",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("organization_id", UUID(as_uuid=True), nullable=False),
    Column("storage_key", String, nullable=False),
    Column("content_type", String, nullable=False),
    Column("byte_size", Integer, nullable=False),
    Column("sha256", String, nullable=False),
    Column("kind", String, nullable=False),
    Column("phase", String, nullable=True),
    Column("status", String, nullable=False),
    Column("visit_id", UUID(as_uuid=True), nullable=True),
    Column("report_id", UUID(as_uuid=True), nullable=True),
    Column("captured_at", DateTime(timezone=True), nullable=True),
    Column("uploaded_at", DateTime(timezone=True), nullable=True),
    schema="operations",
)
