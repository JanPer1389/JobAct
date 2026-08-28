"""SQLAlchemy Core table definitions for the `workflow` schema.

Mirrors migration 0009; not used to generate it.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, String, Table
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = MetaData()

workflow_runs_table = Table(
    "workflow_runs",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("organization_id", UUID(as_uuid=True), nullable=False),
    Column("workflow_type", String, nullable=False),
    Column("subject_id", UUID(as_uuid=True), nullable=False),
    Column("state", String, nullable=False),
    Column("attempt", Integer, nullable=False),
    Column("next_retry_at", DateTime(timezone=True), nullable=True),
    Column("last_error", String, nullable=True),
    Column("state_version", Integer, nullable=False),
    Column("correlation_id", UUID(as_uuid=True), nullable=False),
    Column("input_data", JSONB, nullable=False),
    # Set while a pending step's external work (e.g. an AI provider call) is
    # in flight, cleared whenever the run re-enters a pending state via
    # resume_to(). Lets a duplicate/concurrent dispatch of the same pending
    # step recognize that another execution already claimed it, even though
    # claiming alone does not change `state` -- see WorkflowRun.claim_attempt().
    Column("claimed_at", DateTime(timezone=True), nullable=True),
    schema="workflow",
)

workflow_steps_table = Table(
    "workflow_steps",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "run_id",
        UUID(as_uuid=True),
        ForeignKey("workflow.workflow_runs.id"),
        nullable=False,
    ),
    Column("step", String, nullable=False),
    Column("status", String, nullable=False),
    Column("attempt", Integer, nullable=False),
    Column("input", JSONB, nullable=True),
    Column("output", JSONB, nullable=True),
    Column("error", String, nullable=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    schema="workflow",
)
