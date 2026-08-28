"""A failed analysis terminates explicitly instead of leaving it running.

Both AI steps and PDF rendering share one guarantee: whatever goes wrong,
the run reaches FAILED and the technician is left with a
usable draft to edit or retry -- never a job stuck in a pending state
with nothing left to move it.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import ClassVar
from uuid import uuid4

import pytest
from sqlalchemy import delete

from jobact.contexts.customers.domain.customer import Customer
from jobact.contexts.customers.infrastructure.customer_repository import (
    CustomerRepository,
)
from jobact.contexts.media.domain.media_asset import MediaAsset
from jobact.contexts.media.infrastructure.media_asset_repository import (
    MediaAssetRepository,
)
from jobact.contexts.reports.application.report_handlers import (
    RetryReportWorkflowHandler,
)
from jobact.contexts.reports.domain.report import Report
from jobact.contexts.reports.infrastructure.report_repository import ReportRepository
from jobact.contexts.visits.domain.visit import Visit
from jobact.contexts.visits.infrastructure.visit_repository import VisitRepository
from jobact.contexts.visual_audits.application.fx import LocalFxSnapshot
from jobact.shared.infrastructure.config import get_settings
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.operations_tables import (
    customers_table,
    media_assets_table,
    report_materials_table,
    report_number_counters_table,
    report_revisions_table,
    reports_table,
    signatures_table,
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
from jobact.workflows.report_fulfillment.activities.run_report_analysis import (
    RunReportAnalysisActivity,
)
from jobact.workflows.report_fulfillment.repository import WorkflowRunRepository
from jobact.workflows.report_fulfillment.run import WorkflowRun
from jobact.workflows.report_fulfillment.states import WorkflowState
from tests.fakes import FakeClock, FakeIdGenerator, FakeObjectStorage

NOW = datetime(2026, 8, 26, tzinfo=UTC)
RAW_NOTES = "Replaced the leaking kitchen sink drain and tested for leaks."

_TABLES = (
    workflow_steps_table,
    workflow_runs_table,
    visual_audit_photos_table,
    visual_audit_attempts_table,
    signatures_table,
    report_materials_table,
    report_revisions_table,
    reports_table,
    report_number_counters_table,
    media_assets_table,
    visits_table,
    customers_table,
    outbox_table,
)


async def _truncate() -> None:
    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        for table in _TABLES:
            await session.execute(delete(table))


@pytest.fixture
async def clean_analysis_tables():
    await _truncate()
    yield
    await _truncate()


class FakeConnector:
    provider_name = "fake"

    def model_name(self, alias: str) -> str:
        return alias

    def build_model(self, alias: str, http_client=None):
        raise AssertionError("The fake connector never builds a real model.")


async def _seed(org_id, storage: FakeObjectStorage):
    customer = Customer(
        id=uuid4(),
        organization_id=org_id,
        name="Ada Lovelace",
        address="12 Analytical Engine Way",
        phone="+7 900 123-45-67",
        service_type="Plumbing",
        created_at=NOW,
    )
    visit = Visit.start(
        id=uuid4(),
        organization_id=org_id,
        customer_id=customer.id,
        technician_id=uuid4(),
        started_at=NOW,
        gps_lat=55.7558,
        gps_lon=37.6173,
        gps_accuracy_m=4.0,
    )
    report = Report.create_draft(
        id=uuid4(),
        organization_id=org_id,
        visit_id=visit.id,
        human_id="JA-2026-0001",
        revision_id=uuid4(),
        created_at=NOW,
        created_by=visit.technician_id,
    )
    run = WorkflowRun.start(
        id=uuid4(),
        organization_id=org_id,
        workflow_type="report_fulfillment",
        subject_id=report.id,
        correlation_id=uuid4(),
        initial_state=WorkflowState.DRAFTING_PENDING,
        input_data={"drafting": {"raw_notes": RAW_NOTES}},
    )

    photos = []
    for phase in ("before", "after"):
        key = f"{org_id}/{phase}.jpg"
        storage.put(key, b"fake-image-bytes", "image/jpeg")
        photos.append(
            MediaAsset(
                id=uuid4(),
                organization_id=org_id,
                storage_key=key,
                content_type="image/jpeg",
                byte_size=16,
                sha256="0" * 64,
                kind="photo",
                phase=phase,
                status="attached",
                visit_id=visit.id,
                report_id=None,
                captured_at=NOW + timedelta(minutes=1),
                uploaded_at=NOW + timedelta(minutes=1),
            )
        )

    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        await CustomerRepository(session).add(customer)
        await VisitRepository(session).add(visit)
        await ReportRepository(session).add(report)
        media_repo = MediaAssetRepository(session)
        for photo in photos:
            await media_repo.add(photo)
        await WorkflowRunRepository(session).add(run)
    return report, run


def _activity(storage: FakeObjectStorage, *, draft_fn, audit_fn):
    settings = get_settings()
    return RunReportAnalysisActivity(
        uow=SqlAlchemyUnitOfWork(),
        connector=FakeConnector(),
        object_storage=storage,
        clock=FakeClock(NOW),
        id_generator=FakeIdGenerator(),
        fx=LocalFxSnapshot(
            settings.usd_rub_rate,
            settings.usd_rub_rate_date,
            settings.usd_rub_rate_source,
        ),
        draft_report_fn=draft_fn,
        run_visual_audit_fn=audit_fn,
    )


@pytest.mark.asyncio
async def test_ai_timeout_fails_the_run_with_a_usable_draft(
    clean_analysis_tables, caplog,
) -> None:
    org_id = uuid4()
    storage = FakeObjectStorage()
    report, run = await _seed(org_id, storage)

    async def timing_out_draft(connector, context):
        raise TimeoutError("the provider did not respond")

    async def never_called_audit(*args, **kwargs):
        raise AssertionError("Visual comparison must not run after drafting failed.")

    with caplog.at_level(
        logging.INFO,
        logger="jobact.workflows.report_fulfillment.activities.run_report_analysis",
    ):
        await _activity(
            storage, draft_fn=timing_out_draft, audit_fn=never_called_audit
        ).run(report_id=report.id, run_id=run.id)

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        loaded_run = await WorkflowRunRepository(session).get_by_id(run.id)
        loaded_report = await ReportRepository(session).get_by_id(report.id)

    assert loaded_run is not None
    assert loaded_run.state == WorkflowState.FAILED
    assert loaded_run.last_error is not None
    assert loaded_run.last_error == "AI_ANALYSIS_TIMEOUT"
    # Sanitized: never the provider's own message.
    assert "did not respond" not in loaded_run.last_error

    assert loaded_report is not None
    revision = loaded_report.current_revision
    assert revision.work_completed  # a usable template draft, not an empty report
    assert revision.ai_confidence == "low"
    assert revision.amount_cents is None
    assert revision.visual_comparison is None
    assert "notes_chars=61" in caplog.text
    assert "photo_pair_count=1" in caplog.text
    assert RAW_NOTES not in caplog.text


@pytest.mark.asyncio
async def test_concurrent_dispatch_of_the_same_run_calls_the_ai_provider_once(
    clean_analysis_tables,
) -> None:
    """Simulates duplicate at-least-once delivery of the same dispatch
    event (e.g. a worker crash before the inbox record commits, or two
    worker replicas racing on the same pending stream entry): two
    activity runs for the SAME workflow run must not both pay for the
    AI provider call. The atomic claim in `_load_analysis_inputs`
    (optimistic-locking compare-and-swap on `state_version`) must let
    exactly one of them proceed.
    """
    org_id = uuid4()
    storage = FakeObjectStorage()
    report, run = await _seed(org_id, storage)

    calls = 0
    entered = asyncio.Event()
    release = asyncio.Event()

    async def slow_failing_draft(connector, context):
        nonlocal calls
        calls += 1
        entered.set()
        await release.wait()
        raise TimeoutError("the provider did not respond")

    async def never_called_audit(*args, **kwargs):
        raise AssertionError("Visual comparison must not run after drafting failed.")

    first_task = asyncio.create_task(
        _activity(storage, draft_fn=slow_failing_draft, audit_fn=never_called_audit).run(
            report_id=report.id, run_id=run.id
        )
    )
    await entered.wait()
    second_task = asyncio.create_task(
        _activity(storage, draft_fn=slow_failing_draft, audit_fn=never_called_audit).run(
            report_id=report.id, run_id=run.id
        )
    )
    await asyncio.sleep(0.05)
    release.set()
    await asyncio.gather(first_task, second_task)

    assert calls == 1

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        loaded_run = await WorkflowRunRepository(session).get_by_id(run.id)

    assert loaded_run is not None
    assert loaded_run.state == WorkflowState.FAILED


@pytest.mark.asyncio
async def test_visual_comparison_failure_also_fails_the_run(
    clean_analysis_tables,
) -> None:
    org_id = uuid4()
    storage = FakeObjectStorage()
    report, run = await _seed(org_id, storage)

    class _Draft:
        work_completed = "Replaced the damaged sink trap and verified no leaks remain."
        materials: ClassVar[list] = []
        estimated_work_units = 3
        confidence = "high"

    class _Result:
        draft = _Draft()
        model = "fake-model"
        prompt_tokens = 1
        completion_tokens = 1
        cost_usd = None

    async def ok_draft(connector, context):
        return _Result()

    async def failing_audit(*args, **kwargs):
        raise TimeoutError("the vision provider did not respond")

    await _activity(storage, draft_fn=ok_draft, audit_fn=failing_audit).run(
        report_id=report.id, run_id=run.id
    )

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        loaded_run = await WorkflowRunRepository(session).get_by_id(run.id)
        loaded_report = await ReportRepository(session).get_by_id(report.id)

    assert loaded_run is not None
    assert loaded_run.state == WorkflowState.FAILED
    assert loaded_report is not None
    assert loaded_report.current_revision.visual_comparison is None


@pytest.mark.asyncio
async def test_retry_resumes_a_parked_analysis_and_re_enqueues_it(
    clean_analysis_tables,
) -> None:
    org_id = uuid4()
    storage = FakeObjectStorage()
    report, run = await _seed(org_id, storage)

    async def timing_out_draft(connector, context):
        raise TimeoutError("the provider did not respond")

    await _activity(storage, draft_fn=timing_out_draft, audit_fn=None).run(
        report_id=report.id, run_id=run.id
    )

    await RetryReportWorkflowHandler(uow=SqlAlchemyUnitOfWork()).handle(
        report_id=report.id, organization_id=org_id
    )

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        loaded_run = await WorkflowRunRepository(session).get_by_id(run.id)
        dispatch_rows = (
            (
                await session.execute(
                    outbox_table.select().where(
                        outbox_table.c.event_type == "WorkflowStepDispatchRequested"
                    )
                )
            )
            .mappings()
            .all()
        )

    assert loaded_run is not None
    assert loaded_run.state == WorkflowState.DRAFTING_PENDING
    assert loaded_run.attempt == 0
    assert loaded_run.last_error is None
    assert len(dispatch_rows) == 1
