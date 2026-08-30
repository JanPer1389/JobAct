from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from jobact.shared.infrastructure.config import Settings
from jobact.shared.infrastructure.object_storage.s3_compatible import (
    S3CompatibleObjectStorage,
)


async def test_browser_presigned_urls_use_public_endpoint() -> None:
    storage = S3CompatibleObjectStorage(
        Settings(
            _env_file=None,
            minio_endpoint_url="http://minio:9000",
            minio_public_endpoint_url="http://localhost:9000",
            minio_access_key="test-access",
            minio_secret_key="test-secret",
        )
    )

    put_url = await storage.presigned_put(
        "visits/before.jpg",
        "image/jpeg",
        60,
        {"sha256": "0" * 64},
    )
    get_url = await storage.presigned_get("visits/before.jpg", 60)

    assert urlsplit(put_url).netloc == "localhost:9000"
    assert urlsplit(get_url).netloc == "localhost:9000"


async def test_head_accepts_minio_capitalized_sha256_metadata() -> None:
    storage = S3CompatibleObjectStorage(
        Settings(
            _env_file=None,
            minio_endpoint_url="http://minio:9000",
            minio_public_endpoint_url="http://localhost:9000",
            minio_access_key="test-access",
            minio_secret_key="test-secret",
        )
    )

    class FakeS3Client:
        async def head_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
            return {
                "ContentType": "image/jpeg",
                "ContentLength": 29,
                "Metadata": {"Sha256": "a" * 64},
            }

    @asynccontextmanager
    async def client_ctx(*, endpoint_url: str | None = None):
        yield FakeS3Client()

    storage._client_ctx = client_ctx  # type: ignore[method-assign]

    metadata = await storage.head("visits/before.jpg")

    assert metadata is not None
    assert metadata.sha256 == "a" * 64
