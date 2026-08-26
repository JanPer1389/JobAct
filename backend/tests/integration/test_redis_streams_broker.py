"""`RedisStreamsBroker.consume()` against real Redis -- this is the one
piece of the message broker that had zero test coverage: the worker's
own dispatch test bypasses it entirely and calls the dispatch logic
directly with a hand-built `Message`. Also serves as the regression
test for the decode_responses/bytes-vs-str bug this fix uncovered
(`fields["payload"]` would `KeyError` against a bytes-keyed dict).
"""

import asyncio
from uuid import uuid4

import pytest

from jobact.shared.infrastructure.redis.client import get_redis_client
from jobact.shared.infrastructure.redis.streams import RedisStreamsBroker


@pytest.mark.asyncio
async def test_publish_then_consume_roundtrips_payload_and_ack_clears_pending():
    stream = f"test-stream-{uuid4()}"
    group = f"test-group-{uuid4()}"
    consumer = "test-consumer-1"
    redis_client = get_redis_client()
    broker = RedisStreamsBroker(redis_client)

    payload = {"event_type": "widget.touched", "aggregate_id": str(uuid4())}
    await broker.publish(stream, payload)

    consumed = broker.consume(stream, group, consumer)
    message = await asyncio.wait_for(anext(consumed), timeout=10)

    # The payload round-trips correctly through XADD -> XREADGROUP -> our
    # own JSON decode -- this is exactly the path that used to KeyError
    # when the shared client returned bytes instead of str.
    assert message.stream == stream
    assert message.payload == payload
    assert isinstance(message.id, str)

    # Before ack: the message is pending for this consumer group.
    pending_before = await redis_client.xpending(stream, group)
    assert pending_before["pending"] == 1

    await message.ack()

    pending_after = await redis_client.xpending(stream, group)
    assert pending_after["pending"] == 0

    await redis_client.delete(stream)
