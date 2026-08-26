"""Minimal `redis.asyncio` client factory plus two small, focused
helpers built on top of it: OAuth state/nonce storage and a session
cache.

Deliberately NOT the future `MessageBroker` (Task 2.2's Redis Streams
implementation of `shared.application.ports.MessageBroker`) -- this
module only does plain key/value GET/SET/DELETE with TTLs. No streams,
consumer groups, or generic cache abstraction here.
"""

import json
from functools import lru_cache

import redis.asyncio as redis

from jobact.shared.infrastructure.config import get_settings

_STATE_KEY_PREFIX = "jobact:oauth-state:"
_SESSION_KEY_PREFIX = "jobact:session:"

# OAuth `state` -> `nonce` round trip is short-lived: the user is expected
# to complete the Google redirect within a few minutes.
STATE_TTL_SECONDS = 5 * 60


@lru_cache
def get_redis_client() -> redis.Redis:
    """Return the process-wide cached Redis client, built from `Settings`.

    Same `lru_cache` pattern as
    `shared.infrastructure.postgres.engine.get_engine()`.
    """
    settings = get_settings()
    return redis.from_url(settings.redis_url)


class OAuthStateStore:
    """Stores the `nonce` expected for a given OAuth `state`, keyed by
    `state`, for the short window between `/auth/google/start` and
    `/auth/google/callback`. One-time use: callers should `pop` (not just
    `get`) so a `state` can't be replayed.
    """

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    async def put(
        self, state: str, nonce: str, ttl_seconds: int = STATE_TTL_SECONDS
    ) -> None:
        await self._client.set(
            f"{_STATE_KEY_PREFIX}{state}", json.dumps({"nonce": nonce}), ex=ttl_seconds
        )

    async def pop(self, state: str) -> str | None:
        """Return the `nonce` stored for `state`, deleting the entry so it
        cannot be consumed twice. Returns `None` if `state` is unknown
        (never stored, already consumed, or expired).
        """
        key = f"{_STATE_KEY_PREFIX}{state}"
        raw = await self._client.get(key)
        if raw is None:
            return None
        await self._client.delete(key)
        data = json.loads(raw)
        nonce: str = data["nonce"]
        return nonce


class SessionCache:
    """Fast-path cache of session data, keyed by session id.

    NOT the source of truth -- Postgres (`SessionRepository`) is.
    Entries here just avoid a Postgres round trip on every request; a
    cache miss (expired TTL, never written, or explicitly deleted on
    logout) must fall back to Postgres, never be treated as "session
    doesn't exist".
    """

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    async def put(
        self,
        session_id: str,
        *,
        user_id: str,
        organization_id: str,
        role: str,
        ttl_seconds: int,
    ) -> None:
        if ttl_seconds <= 0:
            return
        await self._client.set(
            f"{_SESSION_KEY_PREFIX}{session_id}",
            json.dumps(
                {"user_id": user_id, "organization_id": organization_id, "role": role}
            ),
            ex=ttl_seconds,
        )

    async def get(self, session_id: str) -> dict[str, str] | None:
        raw = await self._client.get(f"{_SESSION_KEY_PREFIX}{session_id}")
        if raw is None:
            return None
        data: dict[str, str] = json.loads(raw)
        return data

    async def delete(self, session_id: str) -> None:
        await self._client.delete(f"{_SESSION_KEY_PREFIX}{session_id}")
