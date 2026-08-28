from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from jobact.contracts.http.v1.visual_audits import VisualAuditResult


class CreateReportRequest(BaseModel):
    visit_id: UUID
    raw_notes: str = Field(min_length=20)


class MaterialDto(BaseModel):
    label: str
    qty: str


class UpdateReportRevisionRequest(BaseModel):
    work_completed: str
    amount_cents: int | None = None
    currency: str = "RUB"
    materials: list[MaterialDto] = []


class SignReportRequest(BaseModel):
    signer_name: str
    signature_media_asset_id: UUID


class ReportRevisionResponse(BaseModel):
    id: UUID
    revision_no: int
    source: str
    work_completed: str
    amount_cents: int | None
    currency: str
    ai_confidence: str | None
    confirmed_by_user_at: datetime | None
    amount_confirmed_at: datetime | None
    frozen_at: datetime | None
    materials: list[MaterialDto]
    visual_comparison_status: str | None = None
    visual_comparison: VisualAuditResult | None = None


class WorkflowErrorResponse(BaseModel):
    code: str
    http_status: int
    message: str
    retryable: bool


class ReportResponse(BaseModel):
    id: UUID
    human_id: str
    status: str
    visit_id: UUID
    current_revision: ReportRevisionResponse
    signed_at: datetime | None
    completed_at: datetime | None
    workflow_state: str | None = None
    workflow_error: WorkflowErrorResponse | None = None
    pdf_media_asset_id: UUID | None = None


class ManualRecoveryResponse(BaseModel):
    """The durable drafting input a technician needs after AI fallback.

    `stage` says which part of the workflow parked, so the client can
    offer the right recovery actions.
    """

    raw_notes: str
    stage: Literal["analysis", "pdf"] = "analysis"
