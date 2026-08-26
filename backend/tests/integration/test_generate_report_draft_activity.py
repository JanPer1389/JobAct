"""The drafting activity persists an AI draft or a usable fallback in one run."""

from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from jobact.contexts.reports.domain.report import Report
from jobact.contexts.reports.infrastructure.report_repository import ReportRepository
from jobact.shared.application.ports import LlmGateway
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.operations_tables import (
    report_materials_table,
    report_revisions_table,
    reports_table,
)
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from jobact.shared.infrastructure.postgres.workflow_tables import (
    workflow_runs_table,
    workflow_steps_table,
)
from jobact.workflows.report_fulfillment.activities.generate_report_draft import (
    GenerateReportDraftActivity,
)
from jobact.workflows.report_fulfillment.agent import DraftedReport, DraftingResult
from jobact.workflows.report_fulfillment.repository import WorkflowRunRepository
from jobact.workflows.report_fulfillment.run import WorkflowRun
from jobact.workflows.report_fulfillment.states import WorkflowState
from tests.fakes import FakeClock, FakeIdGenerator, FakeLlmGateway


@pytest.fixture
async def clean_drafting_tables():
    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        await session.execute(delete(workflow_steps_table))
        await session.execute(delete(workflow_runs_table))
        await session.execute(delete(report_materials_table))
        await session.execute(delete(report_revisions_table))
        await session.execute(delete(reports_table))
    yield
    async with session_factory() as session, session.begin():
        await session.execute(delete(workflow_steps_table))
        await session.execute(delete(workflow_runs_table))
        await session.execute(delete(report_materials_table))
        await session.execute(delete(report_revisions_table))
        await session.execute(delete(reports_table))


async def _draft_with_fake(
    gateway: LlmGateway, raw_notes: str
) -> DraftingResult:
    return await cast(FakeLlmGateway, gateway).draft(raw_notes)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "drafting_result",
        "drafting_error",
        "expected_work_completed",
        "expected_state",
        "expected_step_status",
        "expected_amount",
    ),
    [
        pytest.param(
            DraftingResult(
                draft=DraftedReport(
                    work_completed=(
                        "Replaced the damaged kitchen sink drain and tested the repair "
                        "for leaks."
                    ),
                    materials=[],
                    amount_cents=None,
                    confidence="low",
                ),
                prompt_tokens=18,
                completion_tokens=27,
                cost_usd=0.0123,
            ),
            None,
            "Replaced the damaged kitchen sink drain and tested the repair for leaks.",
            WorkflowState.REVIEW_PENDING,
            "succeeded",
            None,
            id="valid-low-confidence-draft",
        ),
        pytest.param(
            None,
            TimeoutError("LiteLLM timed out after a secret-bearing request"),
            (
                "AI drafting was unavailable for this report. Please review the "
                "technician's raw notes and fill in the work completed, materials, "
                "and amount manually before proceeding."
            ),
            WorkflowState.MANUAL_INPUT_REQUIRED,
            "failed",
            None,
            id="timeout-falls-back-and-parks",
        ),
        pytest.param(
            None,
            ValueError("PydanticAI exhausted malformed structured output retries"),
            (
                "AI drafting was unavailable for this report. Please review the "
                "technician's raw notes and fill in the work completed, materials, "
                "and amount manually before proceeding."
            ),
            WorkflowState.MANUAL_INPUT_REQUIRED,
            "failed",
            None,
            id="malformed-output-falls-back-and-parks",
        ),
    ],
)
async def test_generate_report_draft_persists_a_revision_and_records_the_run(
    clean_drafting_tables,
    drafting_result: DraftingResult | None,
    drafting_error: Exception | None,
    expected_work_completed: str,
    expected_state: WorkflowState,
    expected_step_status: str,
    expected_amount: int | None,
) -> None:
    """A broken branch would lose the report revision or fail to park the run."""
    org_id = uuid4()
    now = datetime(2026, 8, 26, tzinfo=UTC)
    report = Report.create_draft(
        id=uuid4(),
        organization_id=org_id,
        visit_id=uuid4(),
        human_id="JA-2026-0001",
        revision_id=uuid4(),
        created_at=now,
        created_by=uuid4(),
    )
    run = WorkflowRun.start(
        id=uuid4(),
        organization_id=org_id,
        workflow_type="report_fulfillment",
        subject_id=report.id,
        correlation_id=uuid4(),
        initial_state=WorkflowState.DRAFTING_PENDING,
    )
    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        await ReportRepository(session).add(report)
        await WorkflowRunRepository(session).add(run)

    fake_gateway = FakeLlmGateway(
        drafting_result=drafting_result,
        drafting_error=drafting_error,
    )
    activity = GenerateReportDraftActivity(
        uow=SqlAlchemyUnitOfWork(),
        llm_gateway=fake_gateway,
        clock=FakeClock(now),
        id_generator=FakeIdGenerator(),
        draft_report_fn=_draft_with_fake,
    )

    await activity.run(
        report_id=report.id,
        run_id=run.id,
        raw_notes="Kitchen sink drain leaked after use.",
    )

    async with session_factory() as session:
        loaded_report = await ReportRepository(session).get_by_id(report.id)
        loaded_run = await WorkflowRunRepository(session).get_by_id(run.id)
        step = (
            await session.execute(
                select(workflow_steps_table).where(workflow_steps_table.c.run_id == run.id)
            )
        ).mappings().one()

    assert fake_gateway.draft_inputs == ["Kitchen sink drain leaked after use."]
    assert loaded_report is not None
    assert loaded_report.current_revision.source == "ai"
    assert loaded_report.current_revision.work_completed == expected_work_completed
    assert loaded_report.current_revision.ai_confidence == "low"
    assert loaded_report.current_revision.amount_cents == expected_amount
    assert loaded_run is not None
    assert loaded_run.state == expected_state
    assert step["status"] == expected_step_status
    if expected_step_status == "succeeded":
        assert step["output"]["model"] == "report-drafter"
        assert step["output"]["prompt_tokens"] == 18
        assert step["output"]["completion_tokens"] == 27
        assert step["output"]["cost_usd"] == 0.0123
        assert step["output"]["latency_ms"] >= 0
    else:
        assert step["error"] == (
            f"{type(drafting_error).__name__} occurred while executing the workflow step."
        )
