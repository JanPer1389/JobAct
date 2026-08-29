"""An activity that raises three times lands the run in
MANUAL_INPUT_REQUIRED with a safe (non-leaking) last_error, and the
report itself is not blocked -- its own row/status is untouched by
workflow failures.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete

from jobact.contexts.reports.domain.report import Report
from jobact.contexts.reports.infrastructure.report_repository import ReportRepository
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.operations_tables import (
    report_materials_table,
    report_number_counters_table,
    report_revisions_table,
    reports_table,
    visual_audit_attempts_table,
    visual_audit_photos_table,
)
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from jobact.shared.infrastructure.postgres.workflow_tables import (
    workflow_runs_table,
    workflow_steps_table,
)
from jobact.workflows.report_fulfillment.repository import WorkflowRunRepository
from jobact.workflows.report_fulfillment.run import WorkflowRun
from jobact.workflows.report_fulfillment.runner import WorkflowRunner
from jobact.workflows.report_fulfillment.states import WorkflowState
from tests.fakes import FakeClock, FakeIdGenerator


@pytest.fixture
async def clean_tables():
    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        await session.execute(delete(workflow_steps_table))
        await session.execute(delete(workflow_runs_table))
        await session.execute(delete(visual_audit_photos_table))
        await session.execute(delete(visual_audit_attempts_table))
        await session.execute(delete(report_materials_table))
        await session.execute(delete(report_revisions_table))
        await session.execute(delete(reports_table))
        await session.execute(delete(report_number_counters_table))
    yield
    async with session_factory() as session, session.begin():
        await session.execute(delete(workflow_steps_table))
        await session.execute(delete(workflow_runs_table))
        await session.execute(delete(visual_audit_photos_table))
        await session.execute(delete(visual_audit_attempts_table))
        await session.execute(delete(report_materials_table))
        await session.execute(delete(report_revisions_table))
        await session.execute(delete(reports_table))
        await session.execute(delete(report_number_counters_table))


@pytest.mark.asyncio
async def test_three_failures_parks_run_without_blocking_the_report(clean_tables):
    org_id = uuid4()
    session_factory = get_sessionmaker()

    report = Report.create_draft(
        id=uuid4(),
        organization_id=org_id,
        visit_id=uuid4(),
        human_id="JA-2026-0001",
        revision_id=uuid4(),
        created_at=datetime.now(UTC),
        created_by=uuid4(),
        currency="RUB",
    )
    async with session_factory() as session, session.begin():
        await ReportRepository(session).add(report)

    run = WorkflowRun.start(
        id=uuid4(),
        organization_id=org_id,
        workflow_type="report_fulfillment",
        subject_id=report.id,
        correlation_id=uuid4(),
    )
    async with session_factory() as session, session.begin():
        await WorkflowRunRepository(session).add(run)

    async def always_fails() -> dict:
        raise RuntimeError("sensitive internal detail that must not leak")

    runner = WorkflowRunner(
        uow=SqlAlchemyUnitOfWork(),
        clock=FakeClock(),
        id_generator=FakeIdGenerator(),
        max_attempts=3,
    )
    for _ in range(3):
        result = await runner.run_step(run.id, "draft_report", always_fails)
        assert result is None

    async with session_factory() as session:
        loaded_run = await WorkflowRunRepository(session).get_by_id(run.id)
    assert loaded_run is not None
    assert loaded_run.state == WorkflowState.MANUAL_INPUT_REQUIRED
    assert loaded_run.last_error is not None
    assert "sensitive internal detail" not in loaded_run.last_error

    # The report itself is completely unaffected by the workflow's failure.
    async with session_factory() as session:
        loaded_report = await ReportRepository(session).get_by_id(report.id)
    assert loaded_report is not None
    assert loaded_report.status == "draft"
