"""Finalize a signed report as an attached PDF and complete its workflow."""

from __future__ import annotations

from uuid import UUID

from jobact.contexts.customers.infrastructure.customer_repository import (
    CustomerRepository,
)
from jobact.contexts.media.domain.media_asset import MediaAsset
from jobact.contexts.media.infrastructure.media_asset_repository import (
    MediaAssetRepository,
)
from jobact.contexts.reports.infrastructure.report_repository import ReportRepository
from jobact.contexts.visits.infrastructure.visit_repository import VisitRepository
from jobact.shared.application.ports import (
    Clock,
    IdGenerator,
    ObjectStorage,
    PdfRenderer,
)
from jobact.shared.application.uow import UnitOfWork
from jobact.workflows.report_fulfillment.repository import WorkflowRunRepository
from jobact.workflows.report_fulfillment.states import WorkflowState
from jobact.workflows.report_fulfillment.step_repository import WorkflowStepRepository


class GeneratePdfActivity:
    def __init__(
        self,
        uow: UnitOfWork,
        object_storage: ObjectStorage,
        pdf_renderer: PdfRenderer,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._uow = uow
        self._object_storage = object_storage
        self._pdf_renderer = pdf_renderer
        self._clock = clock
        self._id_generator = id_generator

    async def run(self, *, report_id: UUID, run_id: UUID) -> None:
        started_at = self._clock.now()
        async with self._uow:
            report_repo = ReportRepository(self._uow.session)
            report = await report_repo.get_by_id(report_id)
            if report is None:
                raise ValueError(f"Report {report_id} does not exist.")
            if report.status != "signed" or not report.signatures:
                raise ValueError("A report must be signed before its PDF is generated.")

            run_repo = WorkflowRunRepository(self._uow.session)
            run = await run_repo.get_by_id(run_id)
            if run is None:
                raise ValueError(f"Workflow run {run_id} does not exist.")
            if run.subject_id != report_id:
                raise ValueError(
                    f"Workflow run {run_id} does not belong to report {report_id}."
                )
            if run.state != WorkflowState.PDF_PENDING:
                raise ValueError(f"Workflow run {run_id} is not awaiting PDF generation.")

            visit = await VisitRepository(self._uow.session).get_by_id(report.visit_id)
            if visit is None or visit.organization_id != report.organization_id:
                raise ValueError(f"Visit {report.visit_id} does not belong to the report.")
            customer = await CustomerRepository(self._uow.session).get_by_id(
                visit.customer_id
            )
            if customer is None or customer.organization_id != report.organization_id:
                raise ValueError(f"Customer {visit.customer_id} does not belong to the report.")

            signature = report.signatures[-1]
            media_repo = MediaAssetRepository(self._uow.session)
            signature_asset = await media_repo.get_by_id(signature.media_asset_id)
            if (
                signature_asset is None
                or signature_asset.organization_id != report.organization_id
                or signature_asset.kind != "signature"
                or signature_asset.status != "attached"
                or signature_asset.content_type != "image/png"
            ):
                raise ValueError("A signed report requires an attached PNG signature asset.")

            signature_png = await self._object_storage.download(signature_asset.storage_key)
            pdf_bytes = await self._pdf_renderer.render(
                _pdf_context(report, visit, customer, signature.signer_name, signature_png)
            )
            asset_id = self._id_generator.new_id()
            storage_key = f"{report.organization_id}/{asset_id}.pdf"
            metadata = await self._object_storage.upload(
                storage_key, pdf_bytes, "application/pdf"
            )
            now = self._clock.now()
            pdf_asset = MediaAsset(
                id=asset_id,
                organization_id=report.organization_id,
                storage_key=storage_key,
                content_type="application/pdf",
                byte_size=metadata.byte_size,
                sha256=metadata.sha256,
                kind="pdf",
                phase=None,
                status="pending_upload",
                visit_id=report.visit_id,
                report_id=report.id,
                captured_at=now,
                uploaded_at=None,
            )
            pdf_asset.attach(
                actual_content_type=metadata.content_type,
                actual_byte_size=metadata.byte_size,
                actual_sha256=metadata.sha256,
                now=now,
            )
            await media_repo.add(pdf_asset)

            report.complete(now=now)
            await report_repo.save(report)
            expected_version = run.state_version
            run.record_step_success()
            run.transition_to(WorkflowState.COMPLETED)
            await run_repo.save(run, expected_version=expected_version)
            await WorkflowStepRepository(self._uow.session).record(
                id=self._id_generator.new_id(),
                run_id=run.id,
                step="generate_pdf",
                status="succeeded",
                attempt=run.attempt,
                input_data=None,
                output_data={
                    "media_asset_id": str(pdf_asset.id),
                    "byte_size": pdf_asset.byte_size,
                    "signature_media_asset_id": str(signature_asset.id),
                },
                error=None,
                started_at=started_at,
                finished_at=now,
            )
            self._uow.register(report)
            self._uow.register(pdf_asset)
            self._uow.register(run)


def _pdf_context(report, visit, customer, signer_name: str, signature_png: bytes) -> dict:
    revision = report.current_revision
    amount = (
        f"{revision.amount_cents / 100:.2f} {revision.currency}"
        if revision.amount_cents is not None
        else f"Not specified ({revision.currency})"
    )
    return {
        "header": "JobAct Service Report",
        "report_number": report.human_id,
        "customer": {
            "name": customer.name,
            "address": customer.address,
            "phone": customer.phone,
            "service_type": customer.service_type,
        },
        "timestamp": report.signed_at,
        "gps": {"latitude": visit.gps_lat, "longitude": visit.gps_lon},
        "work_completed": revision.work_completed,
        "materials": [
            {"label": material.label, "qty": material.qty}
            for material in revision.materials
        ],
        "amount": amount,
        "signature_png": signature_png,
        "signer_name": signer_name,
    }
