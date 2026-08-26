"""`/api/v1/reports` routes -- the 7 endpoints from the plan's HTTP
contract. Routes stay thin: parse the request DTO, call a handler,
map the aggregate back to a response DTO.
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from jobact.apps.api.deps import CurrentPrincipal, get_current_principal
from jobact.contexts.reports.application.report_handlers import (
    ConfirmReportHandler,
    CreateReportHandler,
    GetReportManualRecoveryHandler,
    GetReportHandler,
    ListReportsHandler,
    ReadyForSignatureHandler,
    SignReportHandler,
    UpdateReportRevisionHandler,
)
from jobact.contexts.reports.domain.report import Material, Report
from jobact.contracts.http.v1.reports import (
    CreateReportRequest,
    ManualRecoveryResponse,
    MaterialDto,
    ReportResponse,
    ReportRevisionResponse,
    SignReportRequest,
    UpdateReportRevisionRequest,
)
from jobact.shared.infrastructure.clock import SystemClock
from jobact.shared.infrastructure.id_generator import UuidIdGenerator
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from jobact.workflows.report_fulfillment.drafting_dispatcher import (
    generate_draft_for_report,
)
from jobact.workflows.report_fulfillment.pdf_dispatcher import generate_pdf_for_report

router = APIRouter(prefix="/reports", tags=["reports"])


def _to_response(report: Report) -> ReportResponse:
    revision = report.current_revision
    return ReportResponse(
        id=report.id,
        human_id=report.human_id,
        status=report.status,
        visit_id=report.visit_id,
        current_revision=ReportRevisionResponse(
            id=revision.id,
            revision_no=revision.revision_no,
            source=revision.source,
            work_completed=revision.work_completed,
            amount_cents=revision.amount_cents,
            currency=revision.currency,
            ai_confidence=revision.ai_confidence,
            confirmed_by_user_at=revision.confirmed_by_user_at,
            amount_confirmed_at=revision.amount_confirmed_at,
            frozen_at=revision.frozen_at,
            materials=[
                MaterialDto(label=m.label, qty=m.qty) for m in revision.materials
            ],
        ),
        signed_at=report.signed_at,
        completed_at=report.completed_at,
    )


@router.post("", response_model=ReportResponse, status_code=201)
async def create_report(
    body: CreateReportRequest,
    background_tasks: BackgroundTasks,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> ReportResponse:
    handler = CreateReportHandler(
        uow=SqlAlchemyUnitOfWork(), clock=SystemClock(), id_generator=UuidIdGenerator()
    )
    report = await handler.handle(
        organization_id=principal.organization_id,
        visit_id=body.visit_id,
        created_by=principal.user_id,
        raw_notes=body.raw_notes,
    )
    background_tasks.add_task(generate_draft_for_report, report.id)
    return _to_response(report)


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> list[ReportResponse]:
    handler = ListReportsHandler(uow=SqlAlchemyUnitOfWork())
    reports = await handler.handle(organization_id=principal.organization_id)
    return [_to_response(r) for r in reports]


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> ReportResponse:
    handler = GetReportHandler(uow=SqlAlchemyUnitOfWork())
    report = await handler.handle(
        report_id=report_id, organization_id=principal.organization_id
    )
    return _to_response(report)


@router.get("/{report_id}/manual-recovery", response_model=ManualRecoveryResponse)
async def get_report_manual_recovery(
    report_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> ManualRecoveryResponse:
    handler = GetReportManualRecoveryHandler(uow=SqlAlchemyUnitOfWork())
    recovery_input = await handler.handle(
        report_id=report_id, organization_id=principal.organization_id
    )
    return ManualRecoveryResponse(raw_notes=recovery_input.raw_notes)


@router.patch("/{report_id}/revision", response_model=ReportResponse)
async def update_revision(
    report_id: UUID,
    body: UpdateReportRevisionRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> ReportResponse:
    handler = UpdateReportRevisionHandler(uow=SqlAlchemyUnitOfWork())
    id_generator = UuidIdGenerator()
    report = await handler.handle(
        report_id=report_id,
        organization_id=principal.organization_id,
        work_completed=body.work_completed,
        amount_cents=body.amount_cents,
        currency=body.currency,
        materials=[
            Material(id=id_generator.new_id(), label=m.label, qty=m.qty)
            for m in body.materials
        ],
    )
    return _to_response(report)


@router.post("/{report_id}/confirm", response_model=ReportResponse)
async def confirm_report(
    report_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> ReportResponse:
    handler = ConfirmReportHandler(uow=SqlAlchemyUnitOfWork(), clock=SystemClock())
    report = await handler.handle(
        report_id=report_id, organization_id=principal.organization_id
    )
    return _to_response(report)


@router.post("/{report_id}/ready-for-signature", response_model=ReportResponse)
async def ready_for_signature(
    report_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> ReportResponse:
    handler = ReadyForSignatureHandler(uow=SqlAlchemyUnitOfWork(), clock=SystemClock())
    report = await handler.handle(
        report_id=report_id, organization_id=principal.organization_id
    )
    return _to_response(report)


@router.post("/{report_id}/sign", response_model=ReportResponse)
async def sign_report(
    report_id: UUID,
    body: SignReportRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> ReportResponse:
    handler = SignReportHandler(
        uow=SqlAlchemyUnitOfWork(), clock=SystemClock(), id_generator=UuidIdGenerator()
    )
    report = await handler.handle(
        report_id=report_id,
        organization_id=principal.organization_id,
        signer_name=body.signer_name,
        signature_media_asset_id=body.signature_media_asset_id,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    background_tasks.add_task(generate_pdf_for_report, report.id)
    return _to_response(report)
