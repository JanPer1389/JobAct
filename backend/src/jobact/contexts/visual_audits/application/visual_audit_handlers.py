from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from jobact.contexts.media.infrastructure.media_asset_repository import (
    MediaAssetRepository,
)
from jobact.contexts.reports.infrastructure.report_repository import ReportRepository
from jobact.contexts.visual_audits.domain.visual_audit import (
    AcknowledgementReason,
    PhotoPair,
    VisualAuditAttempt,
    VisualAuditStateError,
    VisualAuditValidationError,
)
from jobact.contexts.visual_audits.infrastructure.visual_audit_repository import (
    VisualAuditRepository,
)
from jobact.shared.application.authorization import AuthorizationError
from jobact.shared.application.ports import Clock, IdGenerator
from jobact.shared.application.uow import UnitOfWork
from jobact.workflows.report_fulfillment.repository import WorkflowRunRepository
from jobact.workflows.report_fulfillment.states import WorkflowState

_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


@dataclass(frozen=True)
class LocalFxSnapshot:
    usd_rub_rate: Decimal
    effective_date: date
    source: str


class CreateVisualAuditHandler:
    def __init__(self, uow: UnitOfWork, clock: Clock, id_generator: IdGenerator, fx: LocalFxSnapshot) -> None:
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator
        self._fx = fx

    async def handle(self, *, organization_id: UUID, report_id: UUID, before_photo_asset_ids: list[UUID], after_photo_asset_ids: list[UUID]) -> VisualAuditAttempt:
        if len(before_photo_asset_ids) != len(after_photo_asset_ids):
            raise VisualAuditValidationError("Before and after photo counts must match.")
        async with self._uow:
            report = await ReportRepository(self._uow.session).get_by_id(report_id)
            if report is None or report.organization_id != organization_id:
                raise AuthorizationError(f"Report {report_id} does not belong to organization {organization_id}.")
            revision = report.current_revision
            if report.status != "draft" or revision.confirmed_by_user_at is None or revision.amount_confirmed_at is None:
                raise VisualAuditStateError("The current report revision must be confirmed before auditing.")
            run = await WorkflowRunRepository(self._uow.session).get_by_subject(report_id)
            if run is None or run.organization_id != organization_id or run.state != WorkflowState.REVIEW_PENDING:
                raise VisualAuditStateError("The report is not awaiting pre-signature review.")

            media_repo = MediaAssetRepository(self._uow.session)
            for asset_id, phase in [*[(item, "before") for item in before_photo_asset_ids], *[(item, "after") for item in after_photo_asset_ids]]:
                asset = await media_repo.get_by_id(asset_id)
                if asset is None or asset.organization_id != organization_id:
                    raise AuthorizationError(f"Media asset {asset_id} does not belong to this organization.")
                if asset.status != "attached" or asset.kind != "photo" or asset.phase != phase or asset.visit_id != report.visit_id or asset.content_type not in _IMAGE_TYPES:
                    raise VisualAuditValidationError(f"Media asset {asset_id} is not an attached {phase} photo for this visit.")

            attempt = VisualAuditAttempt.request(
                id=self._id_generator.new_id(), organization_id=organization_id, report_id=report.id,
                report_revision_id=revision.id, visit_id=report.visit_id,
                photo_pairs=[PhotoPair(before, after) for before, after in zip(before_photo_asset_ids, after_photo_asset_ids, strict=True)],
                work_description=revision.work_completed, amount_cents=revision.amount_cents, currency=revision.currency,
                provided_price_usd=_provided_price_usd(revision.amount_cents, revision.currency, self._fx.usd_rub_rate),
                usd_rub_rate=self._fx.usd_rub_rate, usd_rub_rate_date=self._fx.effective_date,
                usd_rub_rate_source=self._fx.source, created_at=self._clock.now(),
            )
            await VisualAuditRepository(self._uow.session).add(attempt)
            self._uow.register(attempt)
        return attempt


class ListVisualAuditsHandler:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def handle(self, *, organization_id: UUID, report_id: UUID) -> list[VisualAuditAttempt]:
        async with self._uow:
            report = await ReportRepository(self._uow.session).get_by_id(report_id)
            if report is None or report.organization_id != organization_id:
                raise AuthorizationError(f"Report {report_id} does not belong to this organization.")
            return await VisualAuditRepository(self._uow.session).list_by_report(report_id, organization_id)


class GetVisualAuditHandler:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def handle(self, *, organization_id: UUID, report_id: UUID, attempt_id: UUID) -> VisualAuditAttempt:
        async with self._uow:
            attempt = await VisualAuditRepository(self._uow.session).get_by_id(attempt_id, organization_id)
        if attempt is None or attempt.report_id != report_id:
            raise AuthorizationError(f"Visual audit {attempt_id} does not belong to this report.")
        return attempt


class AcknowledgeVisualAuditHandler:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def handle(self, *, organization_id: UUID, report_id: UUID, attempt_id: UUID, user_id: UUID, reason: AcknowledgementReason) -> VisualAuditAttempt:
        async with self._uow:
            report = await ReportRepository(self._uow.session).get_by_id(report_id)
            repo = VisualAuditRepository(self._uow.session)
            attempt = await repo.get_by_id(attempt_id, organization_id)
            if report is None or report.organization_id != organization_id or attempt is None or attempt.report_id != report_id:
                raise AuthorizationError("Report or visual audit does not belong to this organization.")
            revision = report.current_revision
            if (
                attempt.work_description != revision.work_completed
                or attempt.amount_cents != revision.amount_cents
                or attempt.currency != revision.currency
            ):
                raise VisualAuditStateError("Audit does not match the current report content.")
            attempt.acknowledge(reason=reason, user_id=user_id, current_revision_id=report.current_revision.id, now=self._clock.now())
            await repo.save(attempt)
            self._uow.register(attempt)
        return attempt


def _provided_price_usd(amount_cents: int | None, currency: str, usd_rub_rate: Decimal) -> Decimal | None:
    if amount_cents is None:
        return None
    amount = Decimal(amount_cents) / Decimal(100)
    if currency.upper() == "USD":
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if currency.upper() == "RUB":
        return (amount / usd_rub_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return None
