"""Durable entry point for report-fulfillment work.

`apps/worker` consumes `WorkflowStepDispatchRequested` off
`outbox.WorkflowRun` and calls into here. Each branch reloads the run and
no-ops unless it is still in the state that branch handles, so duplicate
or out-of-order delivery is harmless.
"""

from __future__ import annotations

import logging
from uuid import UUID

from jobact.contexts.visual_audits.application.fx import LocalFxSnapshot
from jobact.shared.infrastructure.clock import SystemClock
from jobact.shared.infrastructure.config import get_settings
from jobact.shared.infrastructure.id_generator import UuidIdGenerator
from jobact.shared.infrastructure.llm.connectors import build_ai_connectors
from jobact.shared.infrastructure.object_storage.s3_compatible import (
    S3CompatibleObjectStorage,
)
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from jobact.workflows.report_fulfillment.activities.run_report_analysis import (
    RunReportAnalysisActivity,
)
from jobact.workflows.report_fulfillment.pdf_dispatcher import generate_pdf_for_report
from jobact.workflows.report_fulfillment.repository import WorkflowRunRepository
from jobact.workflows.report_fulfillment.states import WorkflowState

logger = logging.getLogger(__name__)

WORKFLOW_TYPE = "report_fulfillment"


async def process_report_fulfillment_event(payload: dict) -> None:
    inner = payload.get("payload") or {}
    if inner.get("workflow_type") != WORKFLOW_TYPE:
        return

    subject_id = UUID(inner["subject_id"])
    state = inner.get("state")
    if state == WorkflowState.DRAFTING_PENDING.value:
        await run_report_analysis(subject_id)
    elif state == WorkflowState.PDF_PENDING.value:
        await generate_pdf_for_report(subject_id)


async def run_report_analysis(report_id: UUID) -> None:
    """Run the unified AI analysis while the run is still awaiting it."""
    async with SqlAlchemyUnitOfWork() as uow:
        run = await WorkflowRunRepository(uow.session).get_by_subject(report_id)

    if run is None or run.state != WorkflowState.DRAFTING_PENDING:
        logger.info("report_analysis_skipped report_id=%s", report_id)
        return

    settings = get_settings()
    connectors = build_ai_connectors(settings)
    activity = RunReportAnalysisActivity(
        uow=SqlAlchemyUnitOfWork(),
        connector=None,
        connectors=connectors,
        object_storage=S3CompatibleObjectStorage(settings),
        clock=SystemClock(),
        id_generator=UuidIdGenerator(),
        fx=LocalFxSnapshot(
            settings.usd_rub_rate,
            settings.usd_rub_rate_date,
            settings.usd_rub_rate_source,
        ),
    )
    await activity.run(report_id=report_id, run_id=run.id)
