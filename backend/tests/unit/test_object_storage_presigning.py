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
