"""Redis Streams implementation of the `MessageBroker` port.

Uses Redis Streams' own vocabulary directly (`XADD`/`XGROUP`/`XREADGROUP`/
`XACK`) -- `stream`/`group`/`consumer` on the port aren't renamed for a
reason: this is a thin, literal wrapper, not an abstraction over Redis
Streams' actual model.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from redis.asyncio import Redis

from jobact.shared.application.ports import Message

_BLOCK_MS = 5_000
_READ_COUNT = 10


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

        while True:
            response = await self._redis.xreadgroup(
                group, consumer, {stream: ">"}, count=_READ_COUNT, block=_BLOCK_MS
            )
            if not response:
                continue
            for _stream_name, entries in response:
                for entry_id, fields in entries:
                    payload = json.loads(fields["payload"])
                    yield Message(
                        id=entry_id,
                        stream=stream,
                        payload=payload,
                        ack=_make_ack(self._redis, stream, group, entry_id),
                    )


def _make_ack(redis_client: Redis, stream: str, group: str, entry_id: str):
    async def ack() -> None:
        await redis_client.xack(stream, group, entry_id)

    return ack
