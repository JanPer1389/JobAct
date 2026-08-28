"""Attach with a wrong checksum returns a MediaVerificationError (mapped
to 422 by the route) and leaves the asset's status at pending_upload.

Uses `FakeObjectStorage` (not real MinIO) to keep this fast -- real
Postgres is what actually matters here, since it's what proves the
asset's status is left unchanged on rejection.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError

from jobact.contexts.media.application.media_handlers import (
    AttachMediaHandler,
    GetMediaDownloadUrlHandler,
    RequestMediaUploadHandler,
)
from jobact.contexts.media.domain.media_asset import MediaVerificationError
from jobact.shared.application.authorization import AuthorizationError
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.operations_tables import (
    media_assets_table,
    visits_table,
    visual_audit_attempts_table,
    visual_audit_photos_table,
)
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from tests.fakes import FakeClock, FakeIdGenerator, FakeObjectStorage


@pytest.fixture
async def clean_media_assets():
    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        await session.execute(delete(visual_audit_photos_table))
        await session.execute(delete(visual_audit_attempts_table))
        await session.execute(delete(media_assets_table))
        await session.execute(delete(visits_table))
    yield
    async with session_factory() as session, session.begin():
        await session.execute(delete(visual_audit_photos_table))
        await session.execute(delete(visual_audit_attempts_table))
        await session.execute(delete(media_assets_table))
        await session.execute(delete(visits_table))


@pytest.mark.asyncio
async def test_nonexistent_visit_id_is_rejected_by_postgres(clean_media_assets):
    with pytest.raises(IntegrityError):
        async with get_sessionmaker()() as session, session.begin():
            await session.execute(
                insert(media_assets_table).values(
                    id=uuid4(),
                    organization_id=uuid4(),
                    storage_key="test/invalid-visit",
                    content_type="image/jpeg",
                    byte_size=1,
                    sha256="a" * 64,
                    kind="photo",
                    phase="before",
                    status="pending_upload",
                    visit_id=uuid4(),
                    report_id=None,
                    captured_at=None,
                    uploaded_at=None,
                )
            )


async def _insert_visit(visit_id: UUID, organization_id: UUID) -> None:
    async with get_sessionmaker()() as session, session.begin():
        await session.execute(
            insert(visits_table).values(
                id=visit_id,
                organization_id=organization_id,
                customer_id=uuid4(),
                technician_id=uuid4(),
                status="in_progress",
                started_at=datetime.now(UTC),
                gps_lat=None,
                gps_lon=None,
                gps_accuracy_m=None,
                before_photo_count=0,
                after_photo_count=0,
                raw_notes=None,
            )
        )


@pytest.mark.asyncio
async def test_media_asset_can_be_created_and_linked_to_an_existing_visit(
    clean_media_assets,
):
    organization_id = uuid4()
    visit_id = uuid4()
    await _insert_visit(visit_id, organization_id)

    asset, _ = await RequestMediaUploadHandler(
        uow=SqlAlchemyUnitOfWork(),
        object_storage=FakeObjectStorage(),
        clock=FakeClock(),
        id_generator=FakeIdGenerator(),
    ).handle(
        organization_id=organization_id,
        content_type="image/jpeg",
        byte_size=1,
        sha256="a" * 64,
        kind="photo",
        phase="before",
        visit_id=visit_id,
        report_id=None,
    )

    async with get_sessionmaker()() as session:
        stored_visit_id = await session.scalar(
            select(media_assets_table.c.visit_id).where(
                media_assets_table.c.id == asset.id
            )
        )
    assert stored_visit_id == visit_id


@pytest.mark.asyncio
async def test_audio_upload_requires_a_visit_owned_by_the_requesting_tenant(
    clean_media_assets,
):
    owner_org_id = uuid4()
    foreign_org_id = uuid4()
    visit_id = uuid4()
    await _insert_visit(visit_id, owner_org_id)

    handler = RequestMediaUploadHandler(
        uow=SqlAlchemyUnitOfWork(),
        object_storage=FakeObjectStorage(),
        clock=FakeClock(),
        id_generator=FakeIdGenerator(),
    )

    with pytest.raises(AuthorizationError):
        await handler.handle(
            organization_id=foreign_org_id,
            content_type="audio/webm",
            byte_size=1024,
            sha256="a" * 64,
            kind="audio",
            phase=None,
            visit_id=visit_id,
            report_id=None,
        )


@pytest.mark.asyncio
async def test_deleting_a_visit_with_linked_media_is_blocked(clean_media_assets):
    organization_id = uuid4()
    visit_id = uuid4()
    await _insert_visit(visit_id, organization_id)
    async with get_sessionmaker()() as session, session.begin():
        await session.execute(
            insert(media_assets_table).values(
                id=uuid4(),
                organization_id=organization_id,
                storage_key="test/linked-visit",
                content_type="image/jpeg",
                byte_size=1,
                sha256="a" * 64,
                kind="photo",
                phase="before",
                status="pending_upload",
                visit_id=visit_id,
                report_id=None,
                captured_at=None,
                uploaded_at=None,
            )
        )

    with pytest.raises(IntegrityError):
        async with get_sessionmaker()() as session, session.begin():
            await session.execute(
                delete(visits_table).where(visits_table.c.id == visit_id)
            )


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


@pytest.mark.asyncio
async def test_get_download_url_returns_a_presigned_get_for_the_owning_org(
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

    download_handler = GetMediaDownloadUrlHandler(
        uow=SqlAlchemyUnitOfWork(), object_storage=storage
    )
    url = await download_handler.handle(asset_id=asset.id, organization_id=org_id)

    assert url == f"https://fake-storage.test/{asset.storage_key}?method=GET&ttl=900"


@pytest.mark.asyncio
async def test_get_download_url_for_another_orgs_asset_raises(clean_media_assets):
    storage = FakeObjectStorage()
    request_handler = RequestMediaUploadHandler(
        uow=SqlAlchemyUnitOfWork(),
        object_storage=storage,
        clock=FakeClock(),
        id_generator=FakeIdGenerator(),
    )
    asset, _upload_url = await request_handler.handle(
        organization_id=uuid4(),
        content_type="image/jpeg",
        byte_size=1024,
        sha256="a" * 64,
        kind="photo",
        phase="before",
        visit_id=None,
        report_id=None,
    )

    download_handler = GetMediaDownloadUrlHandler(
        uow=SqlAlchemyUnitOfWork(), object_storage=storage
    )
    with pytest.raises(AuthorizationError):
        await download_handler.handle(asset_id=asset.id, organization_id=uuid4())
