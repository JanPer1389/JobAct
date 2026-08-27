from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class FairPriceRangeUsd(BaseModel):
    min: float | None = None
    max: float | None = None


class PriceAssessment(BaseModel):
    provided_price_usd: float | None = None
    fair_price_range_usd: FairPriceRangeUsd
    price_verdict: Literal["not_provided", "reasonable", "overpriced", "significantly_overpriced", "suspiciously_low", "cannot_assess"]
    price_explanation: str


class Comparison(BaseModel):
    visible_changes: list[str]
    work_matches_description: bool
    match_explanation: str


class QualityAssessment(BaseModel):
    score: int = Field(ge=0, le=10)
    strengths: list[str]
    issues: list[str]
    unverified_items: list[str]


class EvidenceItem(BaseModel):
    observation: str
    impact: str


class VisualAuditResult(BaseModel):
    verdict: Literal["high_quality", "partially_completed", "poor_quality", "insufficient_data"]
    confidence: int = Field(ge=0, le=100)
    summary: str
    comparison: Comparison
    quality_assessment: QualityAssessment
    price_assessment: PriceAssessment
    evidence: list[EvidenceItem]
    limitations: list[str]
    recommended_next_steps: list[str]


class CreateVisualAuditRequest(BaseModel):
    before_photo_asset_ids: list[UUID] = Field(min_length=1, max_length=6)
    after_photo_asset_ids: list[UUID] = Field(min_length=1, max_length=6)


class AcknowledgeVisualAuditRequest(BaseModel):
    reason: Literal["result_reviewed", "continued_without_result"]


class VisualAuditAttemptResponse(BaseModel):
    id: UUID
    report_id: UUID
    report_revision_id: UUID
    status: str
    before_photo_asset_ids: list[UUID]
    after_photo_asset_ids: list[UUID]
    amount_cents: int | None
    currency: str
    provided_price_usd: float | None
    usd_rub_rate: float
    usd_rub_rate_date: date
    usd_rub_rate_source: str
    result: VisualAuditResult | None
    model: str | None
    failure_code: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    acknowledged_at: datetime | None
    acknowledgement_reason: str | None
