"""Covers the worker's core dedup guarantee: the same event_id
delivered twice (e.g. a redelivered Redis Streams entry after a crash
before ack) runs the registered handler exactly once.
"""

from uuid import uuid4

import pytest
from sqlalchemy import delete

from jobact.apps.worker.__main__ import HANDLER_REGISTRY, _dispatch
from jobact.shared.application.ports import Message
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.tables import inbox_table


@pytest.fixture
async def clean_inbox():
    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        await session.execute(delete(inbox_table))
    yield
    async with session_factory() as session, session.begin():
        await session.execute(delete(inbox_table))


@pytest.mark.asyncio
async def test_duplicate_delivery_runs_handler_once(clean_inbox):
    calls: list[dict] = []

    async def _handler(payload: dict) -> None:
        calls.append(payload)

    HANDLER_REGISTRY["widget.touched"] = _handler
    try:
        event_id = str(uuid4())
        acked: list[bool] = []

        async def _ack() -> None:
            acked.append(True)

        def _message() -> Message:
            return Message(
                id="1-0",
                stream="outbox._Widget",
                payload={"event_id": event_id, "event_type": "widget.touched"},
                ack=_ack,
            )

        await _dispatch(_message())
        await _dispatch(_message())

        assert len(calls) == 1
        assert len(acked) == 2  # both deliveries ack; only the first runs the handler
    finally:
        del HANDLER_REGISTRY["widget.touched"]
