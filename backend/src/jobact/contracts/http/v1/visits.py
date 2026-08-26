from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StartVisitRequest(BaseModel):
    id: UUID
    customer_id: UUID
    gps_lat: float | None = None
    gps_lon: float | None = None
    gps_accuracy_m: float | None = None


class UpdateVisitRequest(BaseModel):
    gps_lat: float | None = None
    gps_lon: float | None = None
    gps_accuracy_m: float | None = None
    before_photo_count: int | None = None
    after_photo_count: int | None = None
    raw_notes: str | None = None


class VisitResponse(BaseModel):
    id: UUID
    customer_id: UUID
    technician_id: UUID
    status: str
    started_at: datetime
    gps_lat: float | None
    gps_lon: float | None
    gps_accuracy_m: float | None
    before_photo_count: int
    after_photo_count: int
