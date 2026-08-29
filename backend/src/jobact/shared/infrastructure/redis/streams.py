"""Redis Streams implementation of the `MessageBroker` port.

Uses Redis Streams' own vocabulary directly (`XADD`/`XGROUP`/`XREADGROUP`/
`XACK`) -- `stream`/`group`/`consumer` on the port aren't renamed for a
reason: this is a thin, literal wrapper, not an abstraction over Redis
Streams' actual model.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import TimeoutError as RedisTimeoutError

from jobact.shared.application.ports import Message

_BLOCK_MS = 5_000
_READ_COUNT = 10
_STALE_PENDING_MS = 120_000


class RedisStreamsBroker:
    """Concrete `MessageBroker` over Redis Streams."""

    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    async def publish(self, stream: str, payload: dict[str, Any]) -> None:
        await self._redis.xadd(stream, {"payload": json.dumps(payload)})

    async def consume(
        self, stream: str, group: str, consumer: str
    ) -> AsyncIterator[Message]:
        try:
            await self._redis.xgroup_create(stream, group, id="0", mkstream=True)
        except Exception as exc:
            # BUSYGROUP: the group already exists -- expected on every
            # consumer after the first, not an error.
            if "BUSYGROUP" not in str(exc):
                raise

        claim_cursor = "0-0"
        while True:
            # Recover messages left pending by a worker that died after
            # claiming them.  New deliveries still use ">" below, so an
            # active worker's pending message is never redelivered early.
            claimed = await self._redis.xautoclaim(
                stream,
                group,
                consumer,
                min_idle_time=_STALE_PENDING_MS,
                start_id=claim_cursor,
                count=_READ_COUNT,
            )
            claim_cursor, claimed_entries, _deleted = claimed
            for entry_id, fields in claimed_entries:
                payload = json.loads(fields["payload"])
                yield Message(
                    id=entry_id,
                    stream=stream,
                    payload=payload,
                    ack=_make_ack(self._redis, stream, group, entry_id),
                )
            try:
                response = await self._redis.xreadgroup(
                    group, consumer, {stream: ">"}, count=_READ_COUNT, block=_BLOCK_MS
                )
            except RedisTimeoutError:
                # redis-py can surface the normal end of a blocking stream
                # read as a socket timeout instead of an empty response.
                continue
            if not response:
                continue
            # `xreadgroup`'s declared return type is a union that also
            # covers RESP3's dict-shaped stream responses; this client
            # never enables RESP3, so the actual shape here is always the
            # classic `[[stream_name, [(id, fields), ...]], ...]` list --
            # asserting it narrows the type (iterating a dict would yield
            # just its keys, which is a real bug this assert also guards
            # against, not just a type-checker satisfaction).
            assert isinstance(response, list)
            for _stream_name, entries in response:
                for entry_id, fields in entries:
                    payload = json.loads(fields["payload"])
                    yield Message(
                        id=entry_id,
                        stream=stream,
                        payload=payload,
                        ack=_make_ack(self._redis, stream, group, entry_id),
                    )


def _make_ack(
    redis_client: Redis, stream: str, group: str, entry_id: str
) -> Callable[[], Awaitable[None]]:
    async def ack() -> None:
        await redis_client.xack(stream, group, entry_id)

    return ack
