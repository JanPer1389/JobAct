"""The `MediaAsset` aggregate -- metadata for one photo/audio/signature/
PDF file. The bytes themselves live in object storage; Postgres only
tracks metadata and lifecycle.

Lifecycle: pending_upload (client requested a presigned URL) ->
attached (the object's real content_type/byte_size/sha256, read back
via ObjectStorage.head(), matched what the client claimed at upload-
request time). `attach()` raises MediaVerificationError on any
mismatch and leaves status unchanged (pending_upload) -- the caller's
handler maps that to a 422, per the plan's own test description.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from jobact.shared.domain.aggregate import AggregateRoot


class MediaVerificationError(Exception):
    pass


class MediaAsset(AggregateRoot):
    def __init__(
        self,
        *,
        id: UUID,
        organization_id: UUID,
        storage_key: str,
        content_type: str,
        byte_size: int,
        sha256: str,
        kind: str,
        phase: str | None,
        status: str,
        visit_id: UUID | None,
        report_id: UUID | None,
        captured_at: datetime | None,
        uploaded_at: datetime | None,
    ) -> None:
        super().__init__()
        self.id = id
        self.organization_id = organization_id
        self.storage_key = storage_key
        self.content_type = content_type
        self.byte_size = byte_size
        self.sha256 = sha256
        self.kind = kind
        self.phase = phase
        self.status = status
        self.visit_id = visit_id
        self.report_id = report_id
        self.captured_at = captured_at
        self.uploaded_at = uploaded_at

    def attach(self, *, actual_content_type: str, actual_byte_size: int, actual_sha256: str, now: datetime) -> None:
        if (
            actual_content_type != self.content_type
            or actual_byte_size != self.byte_size
            or actual_sha256 != self.sha256
        ):
            raise MediaVerificationError(
                "Uploaded object does not match the claimed content_type/byte_size/sha256."
            )
        self.status = "attached"
        self.uploaded_at = now
