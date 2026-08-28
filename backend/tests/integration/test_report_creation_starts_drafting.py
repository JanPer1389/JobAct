"""Report creation gates on evidence and durably enqueues the analysis.

The gate is the first half of the guarantee: a report is only created
once the visit actually carries the evidence AI analysis needs. The
outbox row is the second half: creation returns without running any AI
work, and the job survives an API restart because it lives in the
database rather than in an in-process task.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from jobact.contexts.media.domain.media_asset import MediaAsset
from jobact.contexts.media.infrastructure.media_asset_repository import (
    MediaAssetRepository,
)
from jobact.contexts.reports.application.report_handlers import (
    CreateReportHandler,
    GetReportManualRecoveryHandler,
    ReportEvidenceIncompleteError,
)
from jobact.contexts.reports.infrastructure.report_repository import ReportRepository
from jobact.contexts.visits.domain.visit import Visit
from jobact.contexts.visits.infrastructure.visit_repository import VisitRepository
from jobact.shared.application.authorization import AuthorizationError
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.operations_tables import (
    media_assets_table,
    report_materials_table,
    report_number_counters_table,
    report_revisions_table,
    reports_table,
    visits_table,
    visual_audit_attempts_table,
    visual_audit_photos_table,
)
from jobact.shared.infrastructure.postgres.tables import outbox_table
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from jobact.shared.infrastructure.postgres.workflow_tables import (
    workflow_runs_table,
    workflow_steps_table,
)
from jobact.workflows.report_fulfillment.repository import WorkflowRunRepository
from jobact.workflows.report_fulfillment.states import WorkflowState
from tests.fakes import FakeClock, FakeIdGenerator

NOW = datetime(2026, 8, 26, tzinfo=UTC)
RAW_NOTES = "Replaced the leaking kitchen sink drain and tested for leaks."

# Ordered so FK-referencing rows (visual-audit photos/attempts, workflow
# steps/runs) are deleted before the report_revisions/media_assets rows
# they point to -- otherwise a row left behind by another integration
# test module trips a foreign-key violation here.
_TABLES = (
    workflow_steps_table,
    workflow_runs_table,
    visual_audit_photos_table,
    visual_audit_attempts_table,
    report_materials_table,
    report_revisions_table,
    reports_table,
    report_number_counters_table,
    media_assets_table,
    visits_table,
    outbox_table,
)


async def _truncate() -> None:
    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        for table in _TABLES:
            await session.execute(delete(table))


@pytest.fixture
async def clean_report_creation_tables():
    await _truncate()
    yield
    await _truncate()


def _photo(org_id, visit_id, phase: str, index: int) -> MediaAsset:
    return MediaAsset(
        id=uuid4(),
        organization_id=org_id,
        storage_key=f"{org_id}/{phase}-{index}.jpg",
        content_type="image/jpeg",
        byte_size=1024,
        sha256="0" * 64,
        kind="photo",
        phase=phase,
        status="attached",
        visit_id=visit_id,
        report_id=None,
        captured_at=NOW + timedelta(minutes=index),
        uploaded_at=NOW + timedelta(minutes=index),
    )


async def _seed_visit(*, org_id, before: int, after: int, with_gps: bool = True) -> Visit:
    visit = Visit.start(
        id=uuid4(),
        organization_id=org_id,
        customer_id=uuid4(),
        technician_id=uuid4(),
        started_at=NOW,
        gps_lat=55.7558 if with_gps else None,
        gps_lon=37.6173 if with_gps else None,
        gps_accuracy_m=4.0 if with_gps else None,
    )
    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        await VisitRepository(session).add(visit)
        media_repo = MediaAssetRepository(session)
        for index in range(before):
            await media_repo.add(_photo(org_id, visit.id, "before", index))
        for index in range(after):
            await media_repo.add(_photo(org_id, visit.id, "after", index))
    return visit


def _handler() -> CreateReportHandler:
    return CreateReportHandler(
        uow=SqlAlchemyUnitOfWork(),
        clock=FakeClock(NOW),
        id_generator=FakeIdGenerator(),
    )


@pytest.mark.asyncio
async def test_create_report_enqueues_analysis_without_running_it(
    clean_report_creation_tables,
) -> None:
    org_id = uuid4()
    visit = await _seed_visit(org_id=org_id, before=2, after=2)

    created = await _handler().handle(
        organization_id=org_id,
        visit_id=visit.id,
        created_by=visit.technician_id,
        raw_notes=RAW_NOTES,
    )

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        persisted_report = await ReportRepository(session).get_by_id(created.report.id)
        run = await WorkflowRunRepository(session).get_by_subject(created.report.id)
        dispatch_rows = (
            (
                await session.execute(
                    select(outbox_table).where(
                        outbox_table.c.event_type == "WorkflowStepDispatchRequested"
                    )
                )
            )
            .mappings()
            .all()
        )

    # No AI ran: the revision is still the empty human draft.
    assert persisted_report is not None
    assert persisted_report.current_revision.source == "human"
    assert persisted_report.current_revision.work_completed == ""
    assert persisted_report.current_revision.visual_comparison is None

    assert run is not None
    assert run.id == created.workflow_run_id
    assert run.state == WorkflowState.DRAFTING_PENDING
    assert run.input_data == {"drafting": {"raw_notes": RAW_NOTES}}

    # The job is durable: it is a committed outbox row, not an in-process task.
    assert len(dispatch_rows) == 1
    assert dispatch_rows[0]["aggregate_type"] == "WorkflowRun"
    assert dispatch_rows[0]["published_at"] is None
    assert dispatch_rows[0]["payload"]["state"] == WorkflowState.DRAFTING_PENDING.value
    assert dispatch_rows[0]["payload"]["subject_id"] == str(created.report.id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("before", "after", "with_gps", "expected"),
    [
        (1, 0, True, "after_photos_matching_before"),
        (2, 1, True, "after_photos_matching_before"),
        (0, 0, True, "before_photos"),
        (1, 1, False, "geolocation"),
    ],
)
async def test_create_report_rejects_incomplete_evidence(
    clean_report_creation_tables, before, after, with_gps, expected
) -> None:
    org_id = uuid4()
    visit = await _seed_visit(
        org_id=org_id, before=before, after=after, with_gps=with_gps
    )

    with pytest.raises(ReportEvidenceIncompleteError) as excinfo:
        await _handler().handle(
            organization_id=org_id,
            visit_id=visit.id,
            created_by=visit.technician_id,
            raw_notes=RAW_NOTES,
        )

    assert expected in excinfo.value.missing

    # Nothing was created, so nothing can be left half-started.
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        reports = (await session.execute(select(reports_table))).all()
        runs = (await session.execute(select(workflow_runs_table))).all()
        outbox_rows = (await session.execute(select(outbox_table))).all()

    assert reports == []
    assert runs == []
    assert outbox_rows == []


@pytest.mark.asyncio
async def test_manual_recovery_returns_persisted_notes_only_to_owning_org(
    clean_report_creation_tables,
) -> None:
    org_id = uuid4()
    visit = await _seed_visit(org_id=org_id, before=1, after=1)

    created = await _handler().handle(
        organization_id=org_id,
        visit_id=visit.id,
        created_by=visit.technician_id,
        raw_notes=RAW_NOTES,
    )
    report_id = created.report.id

    handler = GetReportManualRecoveryHandler(uow=SqlAlchemyUnitOfWork())
    with pytest.raises(AuthorizationError):
        await handler.handle(report_id=report_id, organization_id=org_id)

    async with SqlAlchemyUnitOfWork() as uow:
        run_repo = WorkflowRunRepository(uow.session)
        run = await run_repo.get_by_subject(report_id)
        assert run is not None
        expected_version = run.state_version
        run.record_failure(
            error="TimeoutError occurred while executing the workflow step.",
            now=NOW,
            max_attempts=1,
        )
        await run_repo.save(run, expected_version=expected_version)

    recovery_input = await handler.handle(report_id=report_id, organization_id=org_id)

    assert recovery_input.raw_notes == RAW_NOTES
    assert recovery_input.stage == "analysis"
    with pytest.raises(AuthorizationError):
        await handler.handle(report_id=report_id, organization_id=uuid4())
