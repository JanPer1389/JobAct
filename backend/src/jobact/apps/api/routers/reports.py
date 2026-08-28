"""`/api/v1/reports` routes -- the 7 endpoints from the plan's HTTP
contract. Routes stay thin: parse the request DTO, call a handler,
map the aggregate back to a response DTO.
"""

import logging
from collections.abc import Mapping, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from jobact.apps.api.deps import CurrentPrincipal, get_current_principal
from jobact.apps.api.middleware.correlation import get_correlation_id
from jobact.contexts.media.infrastructure.media_asset_repository import (
    MediaAssetRepository,
)
from jobact.contexts.reports.application.report_handlers import (
    ConfirmReportHandler,
    CreateReportHandler,
    GetReportHandler,
    GetReportManualRecoveryHandler,
    ListReportsHandler,
    ReadyForSignatureHandler,
    RetryReportWorkflowHandler,
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
    TranscriptionResponse,
    UpdateReportRevisionRequest,
    WorkflowErrorResponse,
)
from jobact.contracts.http.v1.visual_audits import VisualAuditResult
from jobact.shared.infrastructure.clock import SystemClock
from jobact.shared.infrastructure.id_generator import UuidIdGenerator
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from jobact.workflows.report_fulfillment.failures import failure_from_code
from jobact.workflows.report_fulfillment.repository import WorkflowRunRepository
from jobact.workflows.report_fulfillment.run import WorkflowRun
from jobact.workflows.report_fulfillment.states import WorkflowState

router = APIRouter(prefix="/reports", tags=["reports"])
logger = logging.getLogger(__name__)


def _to_response(
    report: Report,
    *,
    workflow_state: WorkflowState | None = None,
    pdf_media_asset_id: UUID | None = None,
    workflow_error: WorkflowErrorResponse | None = None,
    transcription: TranscriptionResponse | None = None,
) -> ReportResponse:
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
            visual_comparison_status=revision.visual_comparison_status,
            visual_comparison=(
                VisualAuditResult.model_validate(revision.visual_comparison)
                if revision.visual_comparison is not None
                else None
            ),
        ),
        signed_at=report.signed_at,
        completed_at=report.completed_at,
        workflow_state=workflow_state,
        workflow_error=workflow_error,
        pdf_media_asset_id=pdf_media_asset_id,
        transcription=transcription,
    )


def transcription_from_workflow(
    run: WorkflowRun | None,
) -> TranscriptionResponse | None:
    if run is None:
        return None
    transcription = run.input_data.get("transcription")
    if not isinstance(transcription, dict):
        return None
    media_asset_id = transcription.get("media_asset_id")
    if not isinstance(media_asset_id, str):
        return None
    try:
        parsed_media_asset_id = UUID(media_asset_id)
    except ValueError:
        return None

    transcript = transcription.get("transcript")
    detected_language = transcription.get("detected_language")
    if run.state in {WorkflowState.MANUAL_INPUT_REQUIRED, WorkflowState.FAILED}:
        status = "failed"
    elif run.state == WorkflowState.TRANSCRIPTION_PENDING:
        status = "running" if run.claimed_at is not None else "queued"
    elif isinstance(transcript, str):
        status = "completed"
    else:
        status = "failed"

    return TranscriptionResponse(
        status=status,
        media_asset_id=parsed_media_asset_id,
        transcript=transcript if isinstance(transcript, str) else None,
        detected_language=(
            detected_language if isinstance(detected_language, str) else None
        ),
    )


def list_report_responses(
    reports: Sequence[Report], runs_by_report_id: Mapping[UUID, WorkflowRun]
) -> list[ReportResponse]:
    return [
        _to_response(
            report,
            workflow_state=(
                runs_by_report_id[report.id].state
                if report.id in runs_by_report_id
                else None
            ),
            transcription=transcription_from_workflow(runs_by_report_id.get(report.id)),
        )
        for report in reports
    ]


async def _to_enriched_response(report: Report) -> ReportResponse:
    async with SqlAlchemyUnitOfWork() as uow:
        run = await WorkflowRunRepository(uow.session).get_by_subject(report.id)
        pdf_asset = await MediaAssetRepository(uow.session).get_attached_pdf_by_report(
            report.id
        )
    failure = failure_from_code(run.last_error if run is not None else None)
    return _to_response(
        report,
        workflow_state=run.state if run is not None else None,
        workflow_error=(
            WorkflowErrorResponse(
                code=failure.code,
                http_status=failure.http_status,
                message=failure.message,
                retryable=failure.retryable,
            )
            if failure is not None
            else None
        ),
        pdf_media_asset_id=pdf_asset.id if pdf_asset is not None else None,
        transcription=transcription_from_workflow(run),
    )


@router.post("", response_model=ReportResponse, status_code=201)
async def create_report(
    body: CreateReportRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> ReportResponse:
    correlation_id = get_correlation_id(request)
    handler = CreateReportHandler(
        uow=SqlAlchemyUnitOfWork(), clock=SystemClock(), id_generator=UuidIdGenerator()
    )
    created = await handler.handle(
        organization_id=principal.organization_id,
        visit_id=body.visit_id,
        created_by=principal.user_id,
        raw_notes=body.raw_notes,
        audio_media_asset_id=body.audio_media_asset_id,
        correlation_id=correlation_id,
    )
    logger.info(
        "report_workflow_created report_id=%s workflow_run_id=%s organization_id=%s "
        "state=%s correlation_id=%s",
        created.report.id,
        created.workflow_run_id,
        principal.organization_id,
        created.workflow_run.state.value,
        correlation_id,
    )
    # The dispatch request committed to the outbox in the same transaction
    # as the run, so the worker picks it up even if this process restarts.
    logger.info(
        "report_workflow_enqueued report_id=%s workflow_run_id=%s correlation_id=%s",
        created.report.id,
        created.workflow_run_id,
        correlation_id,
    )
    return _to_response(
        created.report,
        workflow_state=created.workflow_run.state,
        transcription=transcription_from_workflow(created.workflow_run),
    )


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> list[ReportResponse]:
    handler = ListReportsHandler(uow=SqlAlchemyUnitOfWork())
    reports = await handler.handle(organization_id=principal.organization_id)
    async with SqlAlchemyUnitOfWork() as uow:
        runs_by_report_id = await WorkflowRunRepository(
            uow.session
        ).list_by_subject_ids(
            [report.id for report in reports], principal.organization_id
        )
    return list_report_responses(reports, runs_by_report_id)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> ReportResponse:
    handler = GetReportHandler(uow=SqlAlchemyUnitOfWork())
    report = await handler.handle(
        report_id=report_id, organization_id=principal.organization_id
    )
    return await _to_enriched_response(report)


@router.get("/{report_id}/manual-recovery", response_model=ManualRecoveryResponse)
async def get_report_manual_recovery(
    report_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> ManualRecoveryResponse:
    handler = GetReportManualRecoveryHandler(uow=SqlAlchemyUnitOfWork())
    recovery_input = await handler.handle(
        report_id=report_id, organization_id=principal.organization_id
    )
    return ManualRecoveryResponse(
        raw_notes=recovery_input.raw_notes, stage=recovery_input.stage
    )


@router.post("/{report_id}/retry", response_model=ReportResponse)
async def retry_report_workflow(
    report_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> ReportResponse:
    handler = RetryReportWorkflowHandler(uow=SqlAlchemyUnitOfWork())
    report = await handler.handle(
        report_id=report_id, organization_id=principal.organization_id
    )
    return await _to_enriched_response(report)


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
    return _to_response(report, workflow_state=WorkflowState.REVIEW_PENDING)


@router.post("/{report_id}/confirm", response_model=ReportResponse)
async def confirm_report(
    report_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> ReportResponse:
    handler = ConfirmReportHandler(uow=SqlAlchemyUnitOfWork(), clock=SystemClock())
    report = await handler.handle(
        report_id=report_id, organization_id=principal.organization_id
    )
    return _to_response(report, workflow_state=WorkflowState.REVIEW_PENDING)


@router.post("/{report_id}/ready-for-signature", response_model=ReportResponse)
async def ready_for_signature(
    report_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> ReportResponse:
    handler = ReadyForSignatureHandler(uow=SqlAlchemyUnitOfWork(), clock=SystemClock())
    report = await handler.handle(
        report_id=report_id, organization_id=principal.organization_id
    )
    return _to_response(report, workflow_state=WorkflowState.SIGNATURE_PENDING)


@router.post("/{report_id}/sign", response_model=ReportResponse)
async def sign_report(
    report_id: UUID,
    body: SignReportRequest,
    request: Request,
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
    return _to_response(report, workflow_state=WorkflowState.PDF_PENDING)
