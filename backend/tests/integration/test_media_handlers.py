"""Attach with a wrong checksum returns a MediaVerificationError (mapped
to 422 by the route) and leaves the asset's status at pending_upload.

Uses `FakeObjectStorage` (not real MinIO) to keep this fast -- real
Postgres is what actually matters here, since it's what proves the
asset's status is left unchanged on rejection.
"""

from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from jobact.contexts.media.application.media_handlers import (
    AttachMediaHandler,
    RequestMediaUploadHandler,
)
from jobact.contexts.media.domain.media_asset import MediaVerificationError
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.operations_tables import media_assets_table
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from tests.fakes import FakeClock, FakeIdGenerator, FakeObjectStorage


@pytest.fixture
async def clean_media_assets():
    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        await session.execute(delete(media_assets_table))
    yield
    async with session_factory() as session, session.begin():
        await session.execute(delete(media_assets_table))


@pytest.mark.asyncio
async def test_attach_with_wrong_checksum_rejects_and_leaves_pending(
    clean_media_assets,
):
    org_id = uuid4()
    storage = FakeObjectStorage()

    request_handler = RequestMediaUploadHandler(
        uow=SqlAlchemyUnitOfWork(),
        object_storage=storage,
        clock=FakeClock(),
        id_generator=FakeIdGenerator(),
    )
    asset, _upload_url = await request_handler.handle(
        organization_id=org_id,
        content_type="image/jpeg",
        byte_size=1024,
        sha256="a" * 64,
        kind="photo",
        phase="before",
        visit_id=None,
        report_id=None,
    )

    # Simulate a client uploading bytes that DON'T match the claimed
    # sha256 -- FakeObjectStorage.put() computes the real sha256 of
    # whatever bytes it's given.
    storage.put(asset.storage_key, b"actually different bytes", "image/jpeg")

    attach_handler = AttachMediaHandler(
        uow=SqlAlchemyUnitOfWork(), object_storage=storage, clock=FakeClock()
    )
    with pytest.raises(MediaVerificationError):
        await attach_handler.handle(asset_id=asset.id, organization_id=org_id)

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        result = await session.execute(
            select(media_assets_table).where(media_assets_table.c.id == asset.id)
        )
        row = result.first()
    assert row.status == "pending_upload"
