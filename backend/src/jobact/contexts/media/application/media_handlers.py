from __future__ import annotations

from uuid import UUID

from jobact.contexts.media.domain.media_asset import MediaAsset, MediaVerificationError
from jobact.contexts.media.infrastructure.media_asset_repository import (
    MediaAssetRepository,
)
from jobact.contexts.visits.infrastructure.visit_repository import VisitRepository
from jobact.shared.application.authorization import AuthorizationError
from jobact.shared.application.ports import Clock, IdGenerator, ObjectStorage
from jobact.shared.application.uow import UnitOfWork

UPLOAD_TTL_SECONDS = 15 * 60
DOWNLOAD_TTL_SECONDS = 15 * 60
MAX_AUDIO_UPLOAD_BYTES = 25 * 1024 * 1024
SUPPORTED_AUDIO_CONTENT_TYPES = frozenset({"audio/webm", "audio/mp4"})


class MediaUploadValidationError(Exception):
    pass


class RequestMediaUploadHandler:
    def __init__(
        self,
        uow: UnitOfWork,
        object_storage: ObjectStorage,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._uow = uow
        self._object_storage = object_storage
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        organization_id: UUID,
        content_type: str,
        byte_size: int,
        sha256: str,
        kind: str,
        phase: str | None,
        visit_id: UUID | None,
        report_id: UUID | None,
    ) -> tuple[MediaAsset, str]:
        if kind == "audio":
            if content_type not in SUPPORTED_AUDIO_CONTENT_TYPES:
                raise MediaUploadValidationError(
                    "Audio uploads must use audio/webm or audio/mp4."
                )
            if byte_size > MAX_AUDIO_UPLOAD_BYTES:
                raise MediaUploadValidationError(
                    "Audio uploads must not exceed 25 MiB."
                )
            if visit_id is None:
                raise MediaUploadValidationError(
                    "Audio uploads must be associated with a visit."
                )
            if phase is not None or report_id is not None:
                raise MediaUploadValidationError(
                    "Audio uploads cannot have a phase or report association."
                )
            async with self._uow:
                visit = await VisitRepository(self._uow.session).get_by_id(visit_id)
            if visit is None or visit.organization_id != organization_id:
                raise AuthorizationError(
                    f"Visit {visit_id} does not belong to organization {organization_id}."
                )

        asset_id = self._id_generator.new_id()
        storage_key = f"{organization_id}/{asset_id}"
        asset = MediaAsset(
            id=asset_id,
            organization_id=organization_id,
            storage_key=storage_key,
            content_type=content_type,
            byte_size=byte_size,
            sha256=sha256,
            kind=kind,
            phase=phase,
            status="pending_upload",
            visit_id=visit_id,
            report_id=report_id,
            captured_at=self._clock.now(),
            uploaded_at=None,
        )
        async with self._uow:
            await MediaAssetRepository(self._uow.session).add(asset)
            self._uow.register(asset)

        upload_url = await self._object_storage.presigned_put(
            storage_key,
            content_type,
            UPLOAD_TTL_SECONDS,
            metadata={"sha256": sha256},
        )
        return asset, upload_url


class AttachMediaHandler:
    def __init__(
        self, uow: UnitOfWork, object_storage: ObjectStorage, clock: Clock
    ) -> None:
        self._uow = uow
        self._object_storage = object_storage
        self._clock = clock

    async def handle(self, *, asset_id: UUID, organization_id: UUID) -> MediaAsset:
        async with self._uow:
            repo = MediaAssetRepository(self._uow.session)
            asset = await repo.get_by_id(asset_id)
            if asset is None or asset.organization_id != organization_id:
                raise AuthorizationError(
                    f"Media asset {asset_id} does not belong to organization {organization_id}."
                )

            metadata = await self._object_storage.head(asset.storage_key)
            if metadata is None:
                raise MediaVerificationError(
                    f"No object found at {asset.storage_key} -- upload may not have completed."
                )

            asset.attach(
                actual_content_type=metadata.content_type,
                actual_byte_size=metadata.byte_size,
                actual_sha256=metadata.sha256,
                now=self._clock.now(),
            )
            await repo.save(asset)
        return asset


class GetMediaDownloadUrlHandler:
    def __init__(self, uow: UnitOfWork, object_storage: ObjectStorage) -> None:
        self._uow = uow
        self._object_storage = object_storage

    async def handle(self, *, asset_id: UUID, organization_id: UUID) -> str:
        async with self._uow:
            asset = await MediaAssetRepository(self._uow.session).get_by_id(asset_id)
        if asset is None or asset.organization_id != organization_id:
            raise AuthorizationError(
                f"Media asset {asset_id} does not belong to organization {organization_id}."
            )
        return await self._object_storage.presigned_get(
            asset.storage_key, DOWNLOAD_TTL_SECONDS
        )
