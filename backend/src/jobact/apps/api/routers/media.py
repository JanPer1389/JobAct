from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends

from jobact.apps.api.deps import CurrentPrincipal, get_current_principal
from jobact.contexts.media.application.media_handlers import (
    UPLOAD_TTL_SECONDS,
    AttachMediaHandler,
    GetMediaDownloadUrlHandler,
    RequestMediaUploadHandler,
)
from jobact.contracts.http.v1.media import (
    MediaAssetResponse,
    MediaDownloadUrlResponse,
    RequestMediaUploadRequest,
    RequestMediaUploadResponse,
)
from jobact.shared.infrastructure.clock import SystemClock
from jobact.shared.infrastructure.config import get_settings
from jobact.shared.infrastructure.id_generator import UuidIdGenerator
from jobact.shared.infrastructure.object_storage.s3_compatible import (
    S3CompatibleObjectStorage,
)
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/media", tags=["media"])


@router.post("/uploads", response_model=RequestMediaUploadResponse, status_code=201)
async def request_upload(
    body: RequestMediaUploadRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> RequestMediaUploadResponse:
    handler = RequestMediaUploadHandler(
        uow=SqlAlchemyUnitOfWork(),
        object_storage=S3CompatibleObjectStorage(get_settings()),
        clock=SystemClock(),
        id_generator=UuidIdGenerator(),
    )
    asset, upload_url = await handler.handle(
        organization_id=principal.organization_id,
        content_type=body.content_type,
        byte_size=body.byte_size,
        sha256=body.sha256,
        kind=body.kind,
        phase=body.phase,
        visit_id=body.visit_id,
        report_id=body.report_id,
    )
    return RequestMediaUploadResponse(
        media_asset_id=asset.id,
        upload_url=upload_url,
        expires_at=datetime.now(UTC) + timedelta(seconds=UPLOAD_TTL_SECONDS),
    )


@router.post("/{asset_id}/attach", response_model=MediaAssetResponse)
async def attach(
    asset_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> MediaAssetResponse:
    handler = AttachMediaHandler(
        uow=SqlAlchemyUnitOfWork(),
        object_storage=S3CompatibleObjectStorage(get_settings()),
        clock=SystemClock(),
    )
    asset = await handler.handle(
        asset_id=asset_id, organization_id=principal.organization_id
    )
    return MediaAssetResponse(id=asset.id, status=asset.status, kind=asset.kind)


@router.get("/{asset_id}/url", response_model=MediaDownloadUrlResponse)
async def get_download_url(
    asset_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> MediaDownloadUrlResponse:
    handler = GetMediaDownloadUrlHandler(
        uow=SqlAlchemyUnitOfWork(),
        object_storage=S3CompatibleObjectStorage(get_settings()),
    )
    url = await handler.handle(
        asset_id=asset_id, organization_id=principal.organization_id
    )
    return MediaDownloadUrlResponse(url=url)
