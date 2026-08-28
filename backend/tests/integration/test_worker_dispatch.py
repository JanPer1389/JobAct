"""Covers the worker's core dedup guarantee: the same event_id
delivered twice (e.g. a redelivered Redis Streams entry after a crash
before ack) runs the registered handler exactly once.
"""

import logging
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


@pytest.mark.asyncio
async def test_dispatch_logs_event_lifecycle_without_payload(
    clean_inbox, caplog
) -> None:
    async def _handler(payload: dict) -> None:
        return None

    HANDLER_REGISTRY["widget.logged"] = _handler
    event_id = str(uuid4())

    async def _ack() -> None:
        return None

    message = Message(
        id="2-0",
        stream="outbox._Widget",
        payload={
            "event_id": event_id,
            "event_type": "widget.logged",
            "secret_payload": "must-not-be-logged",
        },
        ack=_ack,
    )
    try:
        with caplog.at_level(logging.INFO, logger="jobact.apps.worker"):
            await _dispatch(message)
    finally:
        del HANDLER_REGISTRY["widget.logged"]

    text = caplog.text
    assert "worker_event_received" in text
    assert "worker_event_dispatch_started" in text
    assert "worker_event_dispatch_succeeded" in text
    assert f"event_id={event_id}" in text
    assert "must-not-be-logged" not in text
