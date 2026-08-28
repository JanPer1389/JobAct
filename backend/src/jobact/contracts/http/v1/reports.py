from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, model_validator

from jobact.contracts.http.v1.visual_audits import VisualAuditResult


class CreateReportRequest(BaseModel):
    visit_id: UUID
    raw_notes: str | None = None
    audio_media_asset_id: UUID | None = None

    @model_validator(mode="after")
    def validate_input_source(self) -> CreateReportRequest:
        if (self.raw_notes is None) == (self.audio_media_asset_id is None):
            raise ValueError(
                "Exactly one of raw_notes or audio_media_asset_id is required."
            )
        if self.raw_notes is not None:
            self.raw_notes = self.raw_notes.strip()
            if len(self.raw_notes) < 20:
                raise ValueError(
                    "raw_notes must contain at least 20 non-whitespace characters."
                )
        return self


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


class TranscriptionResponse(BaseModel):
    status: Literal["queued", "running", "completed", "failed"]
    media_asset_id: UUID
    transcript: str | None = None
    detected_language: str | None = None


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
    transcription: TranscriptionResponse | None = None


class ManualRecoveryResponse(BaseModel):
    """The durable drafting input a technician needs after AI fallback.

    `stage` says which part of the workflow parked, so the client can
    offer the right recovery actions.
    """

    raw_notes: str | None = None
    stage: Literal["analysis", "transcription", "pdf"] = "analysis"
