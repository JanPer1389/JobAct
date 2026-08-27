from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from jobact.apps.api.deps import CurrentPrincipal, get_current_principal
from jobact.contexts.visual_audits.application.visual_audit_handlers import (
    AcknowledgeVisualAuditHandler,
    CreateVisualAuditHandler,
    GetVisualAuditHandler,
    ListVisualAuditsHandler,
    LocalFxSnapshot,
)
from jobact.contexts.visual_audits.domain.visual_audit import VisualAuditAttempt
from jobact.contracts.http.v1.visual_audits import (
    AcknowledgeVisualAuditRequest,
    CreateVisualAuditRequest,
    VisualAuditAttemptResponse,
    VisualAuditResult,
)
from jobact.shared.infrastructure.clock import SystemClock
from jobact.shared.infrastructure.config import get_settings
from jobact.shared.infrastructure.id_generator import UuidIdGenerator
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/reports/{report_id}/audits", tags=["visual-audits"])


def _response(attempt: VisualAuditAttempt) -> VisualAuditAttemptResponse:
    return VisualAuditAttemptResponse(
        id=attempt.id, report_id=attempt.report_id, report_revision_id=attempt.report_revision_id,
        status=attempt.status,
        before_photo_asset_ids=[pair.before_asset_id for pair in attempt.photo_pairs],
        after_photo_asset_ids=[pair.after_asset_id for pair in attempt.photo_pairs],
        amount_cents=attempt.amount_cents, currency=attempt.currency,
        provided_price_usd=float(attempt.provided_price_usd) if attempt.provided_price_usd is not None else None,
        usd_rub_rate=float(attempt.usd_rub_rate), usd_rub_rate_date=attempt.usd_rub_rate_date,
        usd_rub_rate_source=attempt.usd_rub_rate_source,
        result=VisualAuditResult.model_validate(attempt.result) if attempt.result is not None else None,
        model=attempt.model, failure_code=attempt.failure_code, created_at=attempt.created_at,
        started_at=attempt.started_at, completed_at=attempt.completed_at,
        acknowledged_at=attempt.acknowledged_at, acknowledgement_reason=attempt.acknowledgement_reason,
    )


@router.post("", response_model=VisualAuditAttemptResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_audit(report_id: UUID, body: CreateVisualAuditRequest, principal: CurrentPrincipal = Depends(get_current_principal)) -> VisualAuditAttemptResponse:
    settings = get_settings()
    attempt = await CreateVisualAuditHandler(
        SqlAlchemyUnitOfWork(), SystemClock(), UuidIdGenerator(),
        LocalFxSnapshot(settings.usd_rub_rate, settings.usd_rub_rate_date, settings.usd_rub_rate_source),
    ).handle(
        organization_id=principal.organization_id, report_id=report_id,
        before_photo_asset_ids=body.before_photo_asset_ids, after_photo_asset_ids=body.after_photo_asset_ids,
    )
    return _response(attempt)


@router.get("", response_model=list[VisualAuditAttemptResponse])
async def list_audits(report_id: UUID, principal: CurrentPrincipal = Depends(get_current_principal)) -> list[VisualAuditAttemptResponse]:
    attempts = await ListVisualAuditsHandler(SqlAlchemyUnitOfWork()).handle(organization_id=principal.organization_id, report_id=report_id)
    return [_response(item) for item in attempts]


@router.get("/{attempt_id}", response_model=VisualAuditAttemptResponse)
async def get_audit(report_id: UUID, attempt_id: UUID, principal: CurrentPrincipal = Depends(get_current_principal)) -> VisualAuditAttemptResponse:
    return _response(await GetVisualAuditHandler(SqlAlchemyUnitOfWork()).handle(organization_id=principal.organization_id, report_id=report_id, attempt_id=attempt_id))


@router.post("/{attempt_id}/acknowledge", response_model=VisualAuditAttemptResponse)
async def acknowledge_audit(report_id: UUID, attempt_id: UUID, body: AcknowledgeVisualAuditRequest, principal: CurrentPrincipal = Depends(get_current_principal)) -> VisualAuditAttemptResponse:
    attempt = await AcknowledgeVisualAuditHandler(SqlAlchemyUnitOfWork(), SystemClock()).handle(
        organization_id=principal.organization_id, report_id=report_id, attempt_id=attempt_id,
        user_id=principal.user_id, reason=body.reason,
    )
    return _response(attempt)
