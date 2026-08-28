"""`GenerateReportDraftActivity` -- unlike other workflow steps (which
use the generic `WorkflowRunner.run_step`), this activity has a
specific combined failure behavior the plan calls out explicitly: on
AI failure/exhaustion, it writes a deterministic template revision
(so the technician is never left with an empty draft) AND parks the
run in MANUAL_INPUT_REQUIRED, together, in one activity execution --
not "retry 3 times, then separately decide what to fall back to."

PydanticAI's own `Agent(..., retries=2)` already retries
schema-validation failures; this activity does not add a second,
outer retry loop around the whole AI call -- one call (with the
agent's own internal retries) either succeeds or this activity treats
it as exhausted and falls back immediately.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from time import monotonic
from uuid import UUID

from jobact.contexts.reports.domain.pricing import (
    SUGGESTED_AMOUNT_CURRENCY,
    suggested_amount_cents,
)
from jobact.contexts.reports.domain.report import Material, Report
from jobact.contexts.reports.infrastructure.report_repository import ReportRepository
from jobact.shared.application.ports import AiConnector, Clock, IdGenerator
from jobact.shared.application.uow import UnitOfWork
from jobact.workflows.report_fulfillment.agent import (
    DraftedReport,
    DraftingResult,
    draft_report,
)
from jobact.workflows.report_fulfillment.repository import WorkflowRunRepository
from jobact.workflows.report_fulfillment.runner import sanitize_error
from jobact.workflows.report_fulfillment.states import WorkflowState
from jobact.workflows.report_fulfillment.step_repository import WorkflowStepRepository

_TEMPLATE_WORK_COMPLETED = (
    "AI drafting was unavailable for this report. Please review the "
    "technician's raw notes and fill in the work completed, materials, "
    "and amount manually before proceeding."
)

DraftReport = Callable[[AiConnector, str], Awaitable[DraftingResult]]


class GenerateReportDraftActivity:
    def __init__(
        self,
        uow: UnitOfWork,
        llm_gateway: AiConnector,
        clock: Clock,
        id_generator: IdGenerator,
        draft_report_fn: DraftReport = draft_report,
    ) -> None:
        self._uow = uow
        self._llm_gateway = llm_gateway
        self._clock = clock
        self._id_generator = id_generator
        self._draft_report = draft_report_fn

    async def run(self, *, report_id: UUID, run_id: UUID, raw_notes: str) -> None:
        started_at = self._clock.now()
        start_time = monotonic()

        try:
            drafting_result = await self._draft_report(self._llm_gateway, raw_notes)
            drafted = drafting_result.draft
            model_used = drafting_result.model
            error_detail: str | None = None
        except Exception as exc:  # noqa: BLE001 -- any AI/network/validation
            # failure here means "fall back to the template," not "propagate."
            drafted = _template_fallback()
            drafting_result = None
            model_used = None
            error_detail = sanitize_error(exc).detail

        latency_ms = int((monotonic() - start_time) * 1000)

        async with self._uow:
            report_repo = ReportRepository(self._uow.session)
            report = await report_repo.get_by_id(report_id)
            if report is None:
                raise ValueError(f"Report {report_id} does not exist.")

            _apply_draft(report, drafted, self._id_generator)
            await report_repo.save(report)
            self._uow.register(report)

            run_repo = WorkflowRunRepository(self._uow.session)
            run = await run_repo.get_by_id(run_id)
            if run is None:
                raise ValueError(f"Workflow run {run_id} does not exist.")
            if run.subject_id != report_id:
                raise ValueError(
                    f"Workflow run {run_id} does not belong to report {report_id}."
                )
            expected_version = run.state_version

            if error_detail is None:
                assert drafting_result is not None
                run.record_step_success()
                run.transition_to(WorkflowState.REVIEW_PENDING)
                step_status = "succeeded"
                output_data = {
                    "model": model_used,
                    "prompt_tokens": drafting_result.prompt_tokens,
                    "completion_tokens": drafting_result.completion_tokens,
                    "cost_usd": drafting_result.cost_usd,
                    "latency_ms": latency_ms,
                }
            else:
                run.record_failure(
                    error=error_detail,
                    now=started_at,
                    max_attempts=1,
                )
                step_status = "failed"
                output_data = {"model": None, "latency_ms": latency_ms}

            await run_repo.save(run, expected_version=expected_version)
            await WorkflowStepRepository(self._uow.session).record(
                id=self._id_generator.new_id(),
                run_id=run.id,
                step="generate_report_draft",
                status=step_status,
                attempt=run.attempt,
                input_data=None,
                output_data=output_data,
                error=error_detail,
                started_at=started_at,
                finished_at=self._clock.now(),
            )
            self._uow.register(run)


def _apply_draft(
    report: Report, drafted: DraftedReport, id_generator: IdGenerator
) -> None:
    report.apply_ai_draft(
        work_completed=drafted.work_completed,
        materials=[
            Material(id=id_generator.new_id(), label=material.label, qty=material.qty)
            for material in drafted.materials
        ],
        amount_cents=suggested_amount_cents(drafted.estimated_work_units),
        currency=SUGGESTED_AMOUNT_CURRENCY,
        ai_confidence=drafted.confidence,
    )


def _template_fallback() -> DraftedReport:
    return DraftedReport(
        work_completed=_TEMPLATE_WORK_COMPLETED,
        materials=[],
        estimated_work_units=None,
        confidence="low",
    )
