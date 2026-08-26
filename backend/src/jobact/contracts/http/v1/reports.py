from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CreateReportRequest(BaseModel):
    visit_id: UUID
    raw_notes: str


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


class ReportResponse(BaseModel):
    id: UUID
    human_id: str
    status: str
    visit_id: UUID
    current_revision: ReportRevisionResponse
    signed_at: datetime | None
    completed_at: datetime | None
