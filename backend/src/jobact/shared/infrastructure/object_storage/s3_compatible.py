"""S3-compatible `ObjectStorage` -- works against MinIO in dev and
Yandex Object Storage in prod, since both speak the S3 API.
"""

from __future__ import annotations

import hashlib

import aioboto3
from botocore.config import Config

from jobact.shared.application.ports import ObjectMetadata
from jobact.shared.infrastructure.config import Settings


class S3CompatibleObjectStorage:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._session = aioboto3.Session()

    def _client_ctx(self, *, endpoint_url: str | None = None):
        return self._session.client(
            "s3",
            endpoint_url=endpoint_url or self._settings.minio_endpoint_url,
            aws_access_key_id=self._settings.minio_access_key,
            aws_secret_access_key=self._settings.minio_secret_key,
            config=Config(
                signature_version="s3v4",
                connect_timeout=self._settings.object_storage_connect_timeout_seconds,
                read_timeout=self._settings.object_storage_read_timeout_seconds,
            ),
        )

    async def presigned_put(
        self,
        key: str,
        content_type: str,
        ttl_seconds: int,
        metadata: dict[str, str] | None = None,
    ) -> str:
        async with self._client_ctx(
            endpoint_url=self._settings.minio_public_endpoint_url
        ) as client:
            return await client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self._settings.minio_bucket_name,
                    "Key": key,
                    "ContentType": content_type,
                    "Metadata": metadata or {},
                },
                ExpiresIn=ttl_seconds,
            )

    async def presigned_get(self, key: str, ttl_seconds: int) -> str:
        async with self._client_ctx(
            endpoint_url=self._settings.minio_public_endpoint_url
        ) as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._settings.minio_bucket_name, "Key": key},
                ExpiresIn=ttl_seconds,
            )

    async def head(self, key: str) -> ObjectMetadata | None:
        async with self._client_ctx() as client:
            try:
                response = await client.head_object(
                    Bucket=self._settings.minio_bucket_name, Key=key
                )
            except client.exceptions.ClientError:
                return None
            metadata = {
                key.lower(): value
                for key, value in response.get("Metadata", {}).items()
            }
            return ObjectMetadata(
                content_type=response.get("ContentType", ""),
                byte_size=response["ContentLength"],
                sha256=metadata.get("sha256", ""),
            )

    async def download(self, key: str) -> bytes:
        async with self._client_ctx() as client:
            response = await client.get_object(
                Bucket=self._settings.minio_bucket_name, Key=key
            )
            async with response["Body"] as body:
                return await body.read()

    async def upload(self, key: str, data: bytes, content_type: str) -> ObjectMetadata:
        sha256 = compute_sha256(data)
        async with self._client_ctx() as client:
            await client.put_object(
                Bucket=self._settings.minio_bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
                Metadata={"sha256": sha256},
            )
        return ObjectMetadata(
            content_type=content_type,
            byte_size=len(data),
            sha256=sha256,
        )


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
