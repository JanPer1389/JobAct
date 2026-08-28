"""Minimal `redis.asyncio` client factory plus two small, focused
helpers built on top of it: OAuth state/nonce storage and a session
cache.

Deliberately NOT the future `MessageBroker` (Task 2.2's Redis Streams
implementation of `shared.application.ports.MessageBroker`) -- this
module only does plain key/value GET/SET/DELETE with TTLs. No streams,
consumer groups, or generic cache abstraction here.
"""

import json
from dataclasses import asdict, dataclass
from functools import lru_cache

import redis.asyncio as redis

from jobact.shared.infrastructure.config import get_settings

_STATE_KEY_PREFIX = "jobact:oauth-state:"
_SESSION_KEY_PREFIX = "jobact:session:"
_AUTH_RATE_KEY_PREFIX = "jobact:auth-rate:"

# OAuth `state` -> `nonce` round trip is short-lived: the user is expected
# to complete the Google redirect within a few minutes.
STATE_TTL_SECONDS = 5 * 60


@lru_cache
def get_redis_client() -> redis.Redis:
    """Return the process-wide cached Redis client, built from `Settings`.

    Same `lru_cache` pattern as
    `shared.infrastructure.postgres.engine.get_engine()`.

    `decode_responses=True` -- without it, redis-py returns raw `bytes`
    for keys/values/stream fields, which silently breaks any string-keyed
    dict lookup downstream (e.g. `RedisStreamsBroker.consume()`'s
    `fields["payload"]` would `KeyError` against a `bytes`-keyed dict).
    `OAuthStateStore`/`SessionCache`'s existing `json.loads(raw)` calls
    already tolerate either `str` or `bytes`, so this is a safe,
    backward-compatible change for every existing caller of this client.
    """
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


@dataclass(frozen=True)
class OAuthAttempt:
    nonce: str
    operation: str = "sign_in"
    user_id: str | None = None
    session_id: str | None = None


class OAuthStateStore:
    """Stores the `nonce` expected for a given OAuth `state`, keyed by
    `state`, for the short window between `/auth/google/start` and
    `/auth/google/callback`. One-time use: callers should `pop` (not just
    `get`) so a `state` can't be replayed.
    """

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    async def put(
        self,
        state: str,
        nonce: str,
        ttl_seconds: int = STATE_TTL_SECONDS,
        *,
        operation: str = "sign_in",
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        attempt = OAuthAttempt(
            nonce=nonce,
            operation=operation,
            user_id=user_id,
            session_id=session_id,
        )
        await self._client.set(
            f"{_STATE_KEY_PREFIX}{state}", json.dumps(asdict(attempt)), ex=ttl_seconds
        )

    async def pop(self, state: str) -> OAuthAttempt | None:
        """Return the `nonce` stored for `state`, deleting the entry so it
        cannot be consumed twice. Returns `None` if `state` is unknown
        (never stored, already consumed, or expired).
        """
        key = f"{_STATE_KEY_PREFIX}{state}"
        raw = await self._client.getdel(key)
        if raw is None:
            return None
        data = json.loads(raw)
        return OAuthAttempt(**data)


class AuthRateLimiter:
    """Small Redis fixed-window limiter used only at the auth boundary."""

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    async def check(
        self, key: str, *, limit: int, window_seconds: int
    ) -> int | None:
        redis_key = f"{_AUTH_RATE_KEY_PREFIX}{key}"
        count = await self._client.incr(redis_key)
        if count == 1:
            await self._client.expire(redis_key, window_seconds)
        if count <= limit:
            return None
        ttl = await self._client.ttl(redis_key)
        return max(int(ttl), 1)


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
