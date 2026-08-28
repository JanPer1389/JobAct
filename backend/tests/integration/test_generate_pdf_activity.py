"""The finalization activity embeds the recorded signature in a stored PDF."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from jobact.contexts.customers.domain.customer import Customer
from jobact.contexts.customers.infrastructure.customer_repository import (
    CustomerRepository,
)
from jobact.contexts.media.domain.media_asset import MediaAsset
from jobact.contexts.media.infrastructure.media_asset_repository import (
    MediaAssetRepository,
)
from jobact.contexts.reports.application.report_handlers import (
    ReadyForSignatureHandler,
    SignReportHandler,
)
from jobact.contexts.reports.domain.report import Material, Report
from jobact.contexts.reports.infrastructure.report_repository import ReportRepository
from jobact.contexts.visits.domain.visit import Visit
from jobact.contexts.visits.infrastructure.visit_repository import VisitRepository
from jobact.shared.infrastructure.pdf.reportlab_renderer import ReportLabPdfRenderer
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.operations_tables import (
    customers_table,
    media_assets_table,
    report_materials_table,
    report_revisions_table,
    reports_table,
    signatures_table,
    visits_table,
    visual_audit_attempts_table,
    visual_audit_photos_table,
)
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from jobact.shared.infrastructure.postgres.workflow_tables import (
    workflow_runs_table,
    workflow_steps_table,
)
from jobact.workflows.report_fulfillment.activities.generate_pdf import (
    GeneratePdfActivity,
)
from jobact.workflows.report_fulfillment.repository import WorkflowRunRepository
from jobact.workflows.report_fulfillment.run import WorkflowRun
from jobact.workflows.report_fulfillment.states import WorkflowState
from tests.fakes import FakeClock, FakeIdGenerator, FakeObjectStorage


@pytest.fixture
async def clean_pdf_tables():
    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        await session.execute(delete(workflow_steps_table))
        await session.execute(delete(workflow_runs_table))
        await session.execute(delete(signatures_table))
        await session.execute(delete(visual_audit_photos_table))
        await session.execute(delete(visual_audit_attempts_table))
        await session.execute(delete(report_materials_table))
        await session.execute(delete(report_revisions_table))
        await session.execute(delete(reports_table))
        await session.execute(delete(media_assets_table))
        await session.execute(delete(visits_table))
        await session.execute(delete(customers_table))
    yield
    async with session_factory() as session, session.begin():
        await session.execute(delete(workflow_steps_table))
        await session.execute(delete(workflow_runs_table))
        await session.execute(delete(signatures_table))
        await session.execute(delete(visual_audit_photos_table))
        await session.execute(delete(visual_audit_attempts_table))
        await session.execute(delete(report_materials_table))
        await session.execute(delete(report_revisions_table))
        await session.execute(delete(reports_table))
        await session.execute(delete(media_assets_table))
        await session.execute(delete(visits_table))
        await session.execute(delete(customers_table))


@pytest.mark.asyncio
async def test_generate_pdf_completes_signed_workflow_with_embedded_signature(
    clean_pdf_tables,
) -> None:
    """Removing the signature image from the renderer makes the PDF no larger than text-only."""
    org_id = uuid4()
    now = datetime(2026, 8, 26, 10, 30, tzinfo=UTC)
    customer = Customer(
        id=uuid4(),
        organization_id=org_id,
        name="Ada Lovelace",
        address="12 Analytical Engine Way",
        phone="+7 900 123-45-67",
        service_type="Plumbing",
        created_at=now,
    )
    visit = Visit.start(
        id=uuid4(),
        organization_id=org_id,
        customer_id=customer.id,
        technician_id=uuid4(),
        started_at=now,
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
        created_at=now,
        created_by=uuid4(),
    )
    report.update_revision(
        work_completed="Replaced the damaged sink trap and verified there are no leaks.",
        amount_cents=12500,
        materials=[Material(id=uuid4(), label="Sink trap", qty="1")],
    )
    report.confirm(now=now)

    signature_asset = MediaAsset(
        id=uuid4(),
        organization_id=org_id,
        storage_key=f"{org_id}/signature.png",
        content_type="image/png",
        byte_size=0,
        sha256="",
        kind="signature",
        phase=None,
        status="attached",
        visit_id=None,
        report_id=report.id,
        captured_at=now,
        uploaded_at=now,
    )
    run = WorkflowRun.start(
        id=uuid4(),
        organization_id=org_id,
        workflow_type="report_fulfillment",
        subject_id=report.id,
        correlation_id=uuid4(),
        initial_state=WorkflowState.REVIEW_PENDING,
    )

    storage = FakeObjectStorage()
    signature_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    storage.put(signature_asset.storage_key, signature_png, "image/png")
    signature_metadata = await storage.head(signature_asset.storage_key)
    assert signature_metadata is not None
    signature_asset.byte_size = signature_metadata.byte_size
    signature_asset.sha256 = signature_metadata.sha256

    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        await CustomerRepository(session).add(customer)
        await VisitRepository(session).add(visit)
        report_repo = ReportRepository(session)
        await report_repo.add(report)
        await report_repo.save(report)
        await MediaAssetRepository(session).add(signature_asset)
        await WorkflowRunRepository(session).add(run)

    ready_report = await ReadyForSignatureHandler(
        uow=SqlAlchemyUnitOfWork(), clock=FakeClock(now)
    ).handle(report_id=report.id, organization_id=org_id)

    async with session_factory() as session:
        run_before_signing = await WorkflowRunRepository(session).get_by_id(run.id)

    assert ready_report.status == "pending_signature"
    assert run_before_signing is not None
    assert run_before_signing.state == WorkflowState.SIGNATURE_PENDING

    signed_report = await SignReportHandler(
        uow=SqlAlchemyUnitOfWork(),
        clock=FakeClock(now),
        id_generator=FakeIdGenerator(),
    ).handle(
        report_id=report.id,
        organization_id=org_id,
        signer_name="Ada Lovelace",
        signature_media_asset_id=signature_asset.id,
        ip=None,
        user_agent=None,
    )

    async with session_factory() as session:
        run_before_pdf = await WorkflowRunRepository(session).get_by_id(run.id)

    assert signed_report.status == "signed"
    assert run_before_pdf is not None
    assert run_before_pdf.state == WorkflowState.PDF_PENDING

    renderer = ReportLabPdfRenderer()
    activity = GeneratePdfActivity(
        uow=SqlAlchemyUnitOfWork(),
        object_storage=storage,
        pdf_renderer=renderer,
        clock=FakeClock(now),
        id_generator=FakeIdGenerator(),
    )

    await activity.run(report_id=report.id, run_id=run.id)

    async with session_factory() as session:
        loaded_report = await ReportRepository(session).get_by_id(report.id)
        loaded_run = await WorkflowRunRepository(session).get_by_id(run.id)
        pdf_asset = (
            await session.execute(
                select(media_assets_table).where(
                    media_assets_table.c.kind == "pdf",
                    media_assets_table.c.report_id == report.id,
                )
            )
        ).mappings().one()
        step = (
            await session.execute(
                select(workflow_steps_table).where(
                    workflow_steps_table.c.run_id == run.id
                )
            )
        ).mappings().one()

    pdf_bytes = await storage.download(pdf_asset["storage_key"])
    text_only_pdf = await renderer.render(
        {
            "header": "JobAct Service Report",
            "report_number": report.human_id,
            "customer": {
                "name": customer.name,
                "address": customer.address,
                "phone": customer.phone,
                "service_type": customer.service_type,
            },
            "timestamp": now,
            "gps": {"latitude": visit.gps_lat, "longitude": visit.gps_lon},
            "work_completed": report.current_revision.work_completed,
            "materials": [{"label": "Sink trap", "qty": "1"}],
            "amount": "125.00 RUB",
            "signature_png": None,
            "signer_name": "Ada Lovelace",
        }
    )

    assert loaded_report is not None
    assert loaded_report.status == "completed"
    assert loaded_run is not None
    assert loaded_run.state == WorkflowState.COMPLETED
    assert pdf_asset["status"] == "attached"
    assert pdf_asset["content_type"] == "application/pdf"
    assert pdf_bytes.startswith(b"%PDF-")
    assert pdf_bytes.rstrip().endswith(b"%%EOF")
    assert len(pdf_bytes) > len(text_only_pdf)
    assert step["status"] == "succeeded"
    assert step["output"]["media_asset_id"] == str(pdf_asset["id"])
