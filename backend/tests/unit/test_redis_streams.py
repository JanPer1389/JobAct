from __future__ import annotations

import pytest
from redis.exceptions import TimeoutError

from jobact.shared.application.ports import Message
from jobact.shared.infrastructure.redis.streams import RedisStreamsBroker


class TimeoutThenMessageRedis:
    def __init__(self) -> None:
        self.calls = 0

    async def xgroup_create(self, *args, **kwargs) -> None:
        return None

    async def xreadgroup(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError("empty blocking read")
        return [["audit-stream", [("1-0", {"payload": '{"event_type":"VisualAuditRequested"}'})]]]

    async def xack(self, *args, **kwargs) -> int:
        return 1


@pytest.mark.asyncio
async def test_consume_ignores_timeout_from_an_idle_blocking_read() -> None:
    broker = RedisStreamsBroker(TimeoutThenMessageRedis())

    message: Message = await anext(broker.consume("audit-stream", "worker", "worker-1"))

    assert message.payload == {"event_type": "VisualAuditRequested"}
