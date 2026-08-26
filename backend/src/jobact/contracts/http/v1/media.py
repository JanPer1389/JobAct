from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RequestMediaUploadRequest(BaseModel):
    content_type: str
    byte_size: int
    sha256: str
    kind: str
    phase: str | None = None
    visit_id: UUID | None = None
    report_id: UUID | None = None


class RequestMediaUploadResponse(BaseModel):
    media_asset_id: UUID
    upload_url: str
    expires_at: datetime


class MediaAssetResponse(BaseModel):
    id: UUID
    status: str
    kind: str


class MediaDownloadUrlResponse(BaseModel):
    url: str
