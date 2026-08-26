"""Production caller for the asynchronous report-drafting activity."""

from __future__ import annotations

from uuid import UUID

from jobact.shared.infrastructure.clock import SystemClock
from jobact.shared.infrastructure.config import get_settings
from jobact.shared.infrastructure.id_generator import UuidIdGenerator
from jobact.shared.infrastructure.llm.litellm_gateway import LiteLlmGateway
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from jobact.workflows.report_fulfillment.activities.generate_report_draft import (
    GenerateReportDraftActivity,
)
from jobact.workflows.report_fulfillment.repository import WorkflowRunRepository
from jobact.workflows.report_fulfillment.states import WorkflowState


async def generate_draft_for_report(report_id: UUID) -> None:
    """Load durable drafting input and execute a newly-created report's activity.

    FastAPI schedules this after returning `POST /reports`, so report creation
    remains immediate while the workflow state/input survive process recovery.
    """
    async with SqlAlchemyUnitOfWork() as uow:
        run = await WorkflowRunRepository(uow.session).get_by_subject(report_id)

    if run is None or run.state != WorkflowState.DRAFTING_PENDING:
        return

    drafting_input = run.input_data.get("drafting")
    raw_notes = drafting_input.get("raw_notes") if isinstance(drafting_input, dict) else None
    if not isinstance(raw_notes, str):
        raise ValueError(f"Workflow run {run.id} has no drafting raw_notes.")

    activity = GenerateReportDraftActivity(
        uow=SqlAlchemyUnitOfWork(),
        llm_gateway=LiteLlmGateway(get_settings()),
        clock=SystemClock(),
        id_generator=UuidIdGenerator(),
    )
    await activity.run(report_id=report_id, run_id=run.id, raw_notes=raw_notes)
