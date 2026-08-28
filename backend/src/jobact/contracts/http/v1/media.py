from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, model_validator

MAX_AUDIO_UPLOAD_BYTES = 25 * 1024 * 1024
SUPPORTED_AUDIO_CONTENT_TYPES = frozenset({"audio/webm", "audio/mp4"})


class RequestMediaUploadRequest(BaseModel):
    content_type: str
    byte_size: int
    sha256: str
    kind: str
    phase: str | None = None
    visit_id: UUID | None = None
    report_id: UUID | None = None

    @model_validator(mode="after")
    def validate_audio_upload(self) -> RequestMediaUploadRequest:
        if self.kind != "audio":
            return self
        if self.content_type not in SUPPORTED_AUDIO_CONTENT_TYPES:
            raise ValueError("Audio uploads must use audio/webm or audio/mp4.")
        if self.byte_size > MAX_AUDIO_UPLOAD_BYTES:
            raise ValueError("Audio uploads must not exceed 25 MiB.")
        if self.visit_id is None:
            raise ValueError("Audio uploads must be associated with a visit.")
        if self.phase is not None or self.report_id is not None:
            raise ValueError("Audio uploads cannot have a phase or report association.")
        return self


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
