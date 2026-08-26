"""Integration tests for the local Docker Compose infrastructure stack.

These tests exercise the *real* Postgres, Redis, MinIO, and LiteLLM
services started via `docker compose up -d` (run from `backend/`) -- they
are deliberately not mocked. This is an infrastructure-existence test: it
verifies the stack is reachable and configured correctly, using the same
`Settings` the application itself will use, rather than a second set of
hardcoded credentials.

Run with:
    docker compose up -d
    uv run pytest tests/integration/test_infrastructure.py
"""

import aioboto3
import asyncpg
import httpx
import pytest
import redis.asyncio as redis

from jobact.shared.infrastructure.config import get_settings


@pytest.mark.asyncio
async def test_postgres_accepts_connection() -> None:
    settings = get_settings()
    conn = await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database=settings.postgres_db,
        ssl=False,
    )
    try:
        result = await conn.fetchval("SELECT 1")
        assert result == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_redis_round_trips_set_get() -> None:
    settings = get_settings()
    client = redis.from_url(settings.redis_url)
    try:
        await client.set("jobact:test:infrastructure", "ok")
        value = await client.get("jobact:test:infrastructure")
        assert value == b"ok"
    finally:
        await client.delete("jobact:test:infrastructure")
        await client.aclose()


@pytest.mark.asyncio
async def test_minio_bucket_exists() -> None:
    settings = get_settings()
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.minio_endpoint_url,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
    ) as s3:
        # head_bucket raises a ClientError if the bucket does not exist.
        await s3.head_bucket(Bucket=settings.minio_bucket_name)


@pytest.mark.asyncio
async def test_litellm_liveliness() -> None:
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.litellm_base_url}/health/liveliness")
    assert response.status_code == 200
