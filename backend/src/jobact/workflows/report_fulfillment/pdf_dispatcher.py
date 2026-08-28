"""Production caller for asynchronous signed-report PDF generation."""

from uuid import UUID

from jobact.shared.infrastructure.clock import SystemClock
from jobact.shared.infrastructure.config import get_settings
from jobact.shared.infrastructure.id_generator import UuidIdGenerator
from jobact.shared.infrastructure.object_storage.s3_compatible import (
    S3CompatibleObjectStorage,
)
from jobact.shared.infrastructure.pdf.reportlab_renderer import ReportLabPdfRenderer
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from jobact.workflows.report_fulfillment.activities.generate_pdf import (
    GeneratePdfActivity,
)
from jobact.workflows.report_fulfillment.repository import WorkflowRunRepository
from jobact.workflows.report_fulfillment.states import WorkflowState


async def generate_pdf_for_report(report_id: UUID) -> None:
    """Generate a PDF only while the durable workflow is awaiting it."""
    async with SqlAlchemyUnitOfWork() as uow:
        run = await WorkflowRunRepository(uow.session).get_by_subject(report_id)

    if run is None or run.state != WorkflowState.PDF_PENDING:
        return

    settings = get_settings()
    activity = GeneratePdfActivity(
        uow=SqlAlchemyUnitOfWork(),
        object_storage=S3CompatibleObjectStorage(settings),
        pdf_renderer=ReportLabPdfRenderer(),
        clock=SystemClock(),
        id_generator=UuidIdGenerator(),
        render_timeout_seconds=settings.pdf_render_timeout_seconds,
    )
    await activity.run(report_id=report_id, run_id=run.id)
