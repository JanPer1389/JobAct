"""The visual-comparison result shape.

Produced inside the unified report-analysis workflow and surfaced as part
of a report revision -- there is no standalone visual-audit endpoint.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FairPriceRangeUsd(BaseModel):
    # Bounded, not just typed -- an unbounded `number` schema field triggers
    # a Qwen constrained-decoding bug where it emits a runaway, absurdly
    # long decimal literal instead of a normal value, corrupting the JSON.
    min: float | None = Field(default=None, ge=0, le=1_000_000)
    max: float | None = Field(default=None, ge=0, le=1_000_000)


class PriceAssessment(BaseModel):
    provided_price_usd: float | None = Field(default=None, ge=0, le=1_000_000)
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
