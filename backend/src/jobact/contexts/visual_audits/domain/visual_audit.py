from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from jobact.contexts.visual_audits.domain.events import VisualAuditRequested
from jobact.shared.domain.aggregate import AggregateRoot

AuditStatus = Literal["pending", "running", "succeeded", "failed"]
AcknowledgementReason = Literal["result_reviewed", "continued_without_result"]


class VisualAuditValidationError(ValueError):
    pass


class VisualAuditStateError(RuntimeError):
    pass


@dataclass(frozen=True)
class PhotoPair:
    before_asset_id: UUID
    after_asset_id: UUID


class VisualAuditAttempt(AggregateRoot):
    def __init__(
        self,
        *,
        id: UUID,
        organization_id: UUID,
        report_id: UUID,
        report_revision_id: UUID,
        visit_id: UUID,
        photo_pairs: list[PhotoPair],
        work_description: str,
        amount_cents: int | None,
        currency: str,
        provided_price_usd: Decimal | None,
        usd_rub_rate: Decimal,
        usd_rub_rate_date: date,
        usd_rub_rate_source: str,
        status: AuditStatus,
        result: dict[str, Any] | None,
        model: str | None,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        cost_usd: Decimal | None,
        latency_ms: int | None,
        failure_code: str | None,
        created_at: datetime,
        started_at: datetime | None,
        completed_at: datetime | None,
        acknowledged_at: datetime | None,
        acknowledged_by: UUID | None,
        acknowledgement_reason: AcknowledgementReason | None,
    ) -> None:
        super().__init__()
        self.id = id
        self.organization_id = organization_id
        self.report_id = report_id
        self.report_revision_id = report_revision_id
        self.visit_id = visit_id
        self.photo_pairs = tuple(photo_pairs)
        self.work_description = work_description
        self.amount_cents = amount_cents
        self.currency = currency
        self.provided_price_usd = provided_price_usd
        self.usd_rub_rate = usd_rub_rate
        self.usd_rub_rate_date = usd_rub_rate_date
        self.usd_rub_rate_source = usd_rub_rate_source
        self.status = status
        self.result = result
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.cost_usd = cost_usd
        self.latency_ms = latency_ms
        self.failure_code = failure_code
        self.created_at = created_at
        self.started_at = started_at
        self.completed_at = completed_at
        self.acknowledged_at = acknowledged_at
        self.acknowledged_by = acknowledged_by
        self.acknowledgement_reason = acknowledgement_reason

    @classmethod
    def request(
        cls,
        *,
        id: UUID,
        organization_id: UUID,
        report_id: UUID,
        report_revision_id: UUID,
        visit_id: UUID,
        photo_pairs: list[PhotoPair],
        work_description: str,
        amount_cents: int | None,
        currency: str,
        provided_price_usd: Decimal | None,
        usd_rub_rate: Decimal,
        usd_rub_rate_date: date,
        usd_rub_rate_source: str,
        created_at: datetime,
    ) -> VisualAuditAttempt:
        if not 1 <= len(photo_pairs) <= 6:
            raise VisualAuditValidationError("A visual audit requires 1 to 6 photo pairs.")
        before_ids = [pair.before_asset_id for pair in photo_pairs]
        after_ids = [pair.after_asset_id for pair in photo_pairs]
        if len(set(before_ids)) != len(before_ids) or len(set(after_ids)) != len(after_ids):
            raise VisualAuditValidationError("Photo assets cannot be repeated within a phase.")
        if not work_description.strip():
            raise VisualAuditValidationError("Work description is required.")

        attempt = cls(
            id=id,
            organization_id=organization_id,
            report_id=report_id,
            report_revision_id=report_revision_id,
            visit_id=visit_id,
            photo_pairs=photo_pairs,
            work_description=work_description,
            amount_cents=amount_cents,
            currency=currency,
            provided_price_usd=provided_price_usd,
            usd_rub_rate=usd_rub_rate,
            usd_rub_rate_date=usd_rub_rate_date,
            usd_rub_rate_source=usd_rub_rate_source,
            status="pending",
            result=None,
            model=None,
            prompt_tokens=None,
            completion_tokens=None,
            cost_usd=None,
            latency_ms=None,
            failure_code=None,
            created_at=created_at,
            started_at=None,
            completed_at=None,
            acknowledged_at=None,
            acknowledged_by=None,
            acknowledgement_reason=None,
        )
        attempt._record_event(
            VisualAuditRequested(
                aggregate_id=id,
                organization_id=organization_id,
                report_id=report_id,
                report_revision_id=report_revision_id,
            )
        )
        return attempt

    def start(self, *, now: datetime) -> None:
        if self.status != "pending":
            raise VisualAuditStateError(f"Cannot start audit from {self.status}.")
        self.status = "running"
        self.started_at = now

    def succeed(
        self,
        *,
        result: dict[str, Any],
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: Decimal | None,
        latency_ms: int,
        now: datetime,
    ) -> None:
        if self.status != "running":
            raise VisualAuditStateError(f"Cannot complete audit from {self.status}.")
        self.status = "succeeded"
        self.result = result
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.cost_usd = cost_usd
        self.latency_ms = latency_ms
        self.completed_at = now
        self.failure_code = None

    def fail(self, *, failure_code: str, latency_ms: int, now: datetime) -> None:
        if self.status != "running":
            raise VisualAuditStateError(f"Cannot fail audit from {self.status}.")
        self.status = "failed"
        self.failure_code = failure_code
        self.latency_ms = latency_ms
        self.completed_at = now

    def acknowledge(
        self,
        *,
        reason: AcknowledgementReason,
        user_id: UUID,
        current_revision_id: UUID,
        now: datetime,
    ) -> None:
        if current_revision_id != self.report_revision_id:
            raise VisualAuditStateError("Audit does not belong to the current report revision.")
        if self.acknowledged_at is not None:
            raise VisualAuditStateError("Audit acknowledgement cannot be replaced.")
        if reason == "result_reviewed" and self.status != "succeeded":
            raise VisualAuditStateError("Only a succeeded audit result can be reviewed.")
        if reason == "continued_without_result" and self.status != "failed":
            raise VisualAuditStateError("Only a failed audit can be continued without a result.")
        self.acknowledgement_reason = reason
        self.acknowledged_by = user_id
        self.acknowledged_at = now

    def is_acknowledged_for(self, revision_id: UUID) -> bool:
        return self.report_revision_id == revision_id and self.acknowledged_at is not None
