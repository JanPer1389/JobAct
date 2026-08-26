"""Creating a report durably starts the drafting workflow with its source notes."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete

from jobact.contexts.reports.application.report_handlers import CreateReportHandler
from jobact.contexts.reports.infrastructure.report_repository import ReportRepository
from jobact.contexts.visits.domain.visit import Visit
from jobact.contexts.visits.infrastructure.visit_repository import VisitRepository
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.operations_tables import (
    report_materials_table,
    report_number_counters_table,
    report_revisions_table,
    reports_table,
    visits_table,
)
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from jobact.shared.infrastructure.postgres.workflow_tables import (
    workflow_runs_table,
    workflow_steps_table,
)
from jobact.workflows.report_fulfillment.repository import WorkflowRunRepository
from jobact.workflows.report_fulfillment.states import WorkflowState
from tests.fakes import FakeClock, FakeIdGenerator


@pytest.fixture
async def clean_report_creation_tables():
    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        await session.execute(delete(workflow_steps_table))
        await session.execute(delete(workflow_runs_table))
        await session.execute(delete(report_materials_table))
        await session.execute(delete(report_revisions_table))
        await session.execute(delete(reports_table))
        await session.execute(delete(report_number_counters_table))
        await session.execute(delete(visits_table))
    yield
    async with session_factory() as session, session.begin():
        await session.execute(delete(workflow_steps_table))
        await session.execute(delete(workflow_runs_table))
        await session.execute(delete(report_materials_table))
        await session.execute(delete(report_revisions_table))
        await session.execute(delete(reports_table))
        await session.execute(delete(report_number_counters_table))
        await session.execute(delete(visits_table))


@pytest.mark.asyncio
async def test_create_report_starts_drafting_with_the_request_raw_notes(
    clean_report_creation_tables,
) -> None:
    org_id = uuid4()
    visit = Visit.start(
        id=uuid4(),
        organization_id=org_id,
        customer_id=uuid4(),
        technician_id=uuid4(),
        started_at=datetime(2026, 8, 26, tzinfo=UTC),
    )
    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        await VisitRepository(session).add(visit)

    report = await CreateReportHandler(
        uow=SqlAlchemyUnitOfWork(),
        clock=FakeClock(datetime(2026, 8, 26, tzinfo=UTC)),
        id_generator=FakeIdGenerator(),
    ).handle(
        organization_id=org_id,
        visit_id=visit.id,
        created_by=visit.technician_id,
        raw_notes="Replaced the leaking kitchen sink drain.",
    )

    async with session_factory() as session:
        persisted_report = await ReportRepository(session).get_by_id(report.id)
        run = await WorkflowRunRepository(session).get_by_subject(report.id)

    assert persisted_report is not None
    assert persisted_report.current_revision.source == "human"
    assert run is not None
    assert run.state == WorkflowState.DRAFTING_PENDING
    assert run.input_data == {
        "drafting": {"raw_notes": "Replaced the leaking kitchen sink drain."}
    }
