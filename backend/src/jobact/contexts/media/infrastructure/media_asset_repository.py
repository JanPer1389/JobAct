from __future__ import annotations

from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from jobact.contexts.media.domain.media_asset import MediaAsset
from jobact.shared.infrastructure.postgres.operations_tables import media_assets_table


class MediaAssetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, asset: MediaAsset) -> None:
        await self._session.execute(
            insert(media_assets_table).values(
                id=asset.id,
                organization_id=asset.organization_id,
                storage_key=asset.storage_key,
                content_type=asset.content_type,
                byte_size=asset.byte_size,
                sha256=asset.sha256,
                kind=asset.kind,
                phase=asset.phase,
                status=asset.status,
                visit_id=asset.visit_id,
                report_id=asset.report_id,
                captured_at=asset.captured_at,
                uploaded_at=asset.uploaded_at,
            )
        )

    async def get_by_id(self, asset_id: UUID) -> MediaAsset | None:
        result = await self._session.execute(
            select(media_assets_table).where(media_assets_table.c.id == asset_id)
        )
        row = result.first()
        if row is None:
            return None
        return MediaAsset(
            id=row.id,
            organization_id=row.organization_id,
            storage_key=row.storage_key,
            content_type=row.content_type,
            byte_size=row.byte_size,
            sha256=row.sha256,
            kind=row.kind,
            phase=row.phase,
            status=row.status,
            visit_id=row.visit_id,
            report_id=row.report_id,
            captured_at=row.captured_at,
            uploaded_at=row.uploaded_at,
        )

    async def save(self, asset: MediaAsset) -> None:
        await self._session.execute(
            update(media_assets_table)
            .where(media_assets_table.c.id == asset.id)
            .values(status=asset.status, uploaded_at=asset.uploaded_at)
        )

    async def get_attached_pdf_by_report(self, report_id: UUID) -> MediaAsset | None:
        result = await self._session.execute(
            select(media_assets_table).where(
                media_assets_table.c.report_id == report_id,
                media_assets_table.c.kind == "pdf",
                media_assets_table.c.status == "attached",
            )
        )
        row = result.first()
        if row is None:
            return None
        return MediaAsset(
            id=row.id,
            organization_id=row.organization_id,
            storage_key=row.storage_key,
            content_type=row.content_type,
            byte_size=row.byte_size,
            sha256=row.sha256,
            kind=row.kind,
            phase=row.phase,
            status=row.status,
            visit_id=row.visit_id,
            report_id=row.report_id,
            captured_at=row.captured_at,
            uploaded_at=row.uploaded_at,
        )
