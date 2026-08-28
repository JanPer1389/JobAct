"""SQLAlchemy Core table definitions for the `operations` schema.

Mirrors migration 0004; not used to generate it.
"""

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

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
    Column(
        "visit_id",
        UUID(as_uuid=True),
        ForeignKey(
            "operations.visits.id",
            name="fk_media_assets_visit_id_visits",
            ondelete="NO ACTION",
        ),
        nullable=True,
    ),
    Column("report_id", UUID(as_uuid=True), nullable=True),
    Column("captured_at", DateTime(timezone=True), nullable=True),
    Column("uploaded_at", DateTime(timezone=True), nullable=True),
    schema="operations",
)

reports_table = Table(
    "reports",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("organization_id", UUID(as_uuid=True), nullable=False),
    Column("visit_id", UUID(as_uuid=True), nullable=False),
    Column("human_id", String, nullable=False),
    Column("status", String, nullable=False),
    Column("current_revision_id", UUID(as_uuid=True), nullable=False),
    Column("signed_at", DateTime(timezone=True), nullable=True),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    schema="operations",
)

report_revisions_table = Table(
    "report_revisions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("report_id", UUID(as_uuid=True), nullable=False),
    Column("revision_no", Integer, nullable=False),
    Column("source", String, nullable=False),
    Column("work_completed", String, nullable=False),
    Column("amount_cents", Integer, nullable=True),
    Column("currency", String, nullable=False),
    Column("ai_confidence", String, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("created_by", UUID(as_uuid=True), nullable=True),
    Column("confirmed_by_user_at", DateTime(timezone=True), nullable=True),
    Column("amount_confirmed_at", DateTime(timezone=True), nullable=True),
    Column("frozen_at", DateTime(timezone=True), nullable=True),
    Column("visual_comparison_status", String, nullable=True),
    Column("visual_comparison", JSONB, nullable=True),
    schema="operations",
)

report_materials_table = Table(
    "report_materials",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("revision_id", UUID(as_uuid=True), nullable=False),
    Column("label", String, nullable=False),
    Column("qty", String, nullable=False),
    schema="operations",
)

signatures_table = Table(
    "signatures",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("report_id", UUID(as_uuid=True), nullable=False),
    Column("signer_name", String, nullable=False),
    Column("signed_at", DateTime(timezone=True), nullable=False),
    Column("media_asset_id", UUID(as_uuid=True), nullable=False),
    Column("ip", String, nullable=True),
    Column("user_agent", String, nullable=True),
    schema="operations",
)

report_number_counters_table = Table(
    "report_number_counters",
    metadata,
    Column("organization_id", UUID(as_uuid=True), primary_key=True),
    Column("year", Integer, primary_key=True),
    Column("next_number", Integer, nullable=False),
    schema="operations",
)

visual_audit_attempts_table = Table(
    "visual_audit_attempts",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("organization_id", UUID(as_uuid=True), nullable=False),
    Column("report_id", UUID(as_uuid=True), ForeignKey("operations.reports.id"), nullable=False),
    Column("report_revision_id", UUID(as_uuid=True), ForeignKey("operations.report_revisions.id"), nullable=False),
    Column("visit_id", UUID(as_uuid=True), nullable=False),
    Column("status", String, nullable=False),
    Column("work_description", String, nullable=False),
    Column("amount_cents", Integer, nullable=True),
    Column("currency", String, nullable=False),
    Column("provided_price_usd", Numeric(12, 2), nullable=True),
    Column("usd_rub_rate", Numeric(12, 4), nullable=False),
    Column("usd_rub_rate_date", Date, nullable=False),
    Column("usd_rub_rate_source", String, nullable=False),
    Column("result", JSONB, nullable=True),
    Column("model", String, nullable=True),
    Column("prompt_tokens", Integer, nullable=True),
    Column("completion_tokens", Integer, nullable=True),
    Column("cost_usd", Numeric(16, 8), nullable=True),
    Column("latency_ms", Integer, nullable=True),
    Column("failure_code", String, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("acknowledged_at", DateTime(timezone=True), nullable=True),
    Column("acknowledged_by", UUID(as_uuid=True), nullable=True),
    Column("acknowledgement_reason", String, nullable=True),
    schema="operations",
)

visual_audit_photos_table = Table(
    "visual_audit_photos",
    metadata,
    Column("attempt_id", UUID(as_uuid=True), ForeignKey("operations.visual_audit_attempts.id"), primary_key=True),
    Column("phase", String, primary_key=True),
    Column("pair_index", Integer, primary_key=True),
    Column("media_asset_id", UUID(as_uuid=True), ForeignKey("operations.media_assets.id"), nullable=False),
    UniqueConstraint("attempt_id", "media_asset_id", name="uq_visual_audit_photo_asset"),
    schema="operations",
)
