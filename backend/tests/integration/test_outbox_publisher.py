"""Covers the outbox publisher's core guarantee: a committed event is
published exactly once; a rolled-back one is never published at all.

The rollback half is largely already proven by Task 0.3's UnitOfWork
tests (a rolled-back transaction discards the outbox insert entirely --
there's nothing for the publisher to find). This test focuses on what's
new here: draining, publishing via the broker, and stamping
`published_at` so a second drain doesn't republish.
"""

from uuid import uuid4

import pytest
from sqlalchemy import delete

from jobact.shared.domain.aggregate import AggregateRoot
from jobact.shared.domain.events import DomainEvent
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.outbox_publisher import (
    publish_pending_outbox_events,
)
from jobact.shared.infrastructure.postgres.tables import outbox_table
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from tests.fakes import FakeMessageBroker


class _WidgetEvent(DomainEvent):
    pass


class _Widget(AggregateRoot):
    def __init__(self, id):
        super().__init__()
        self.id = id

    def touch(self):
        self._record_event(_WidgetEvent(aggregate_id=self.id))


@pytest.fixture
async def clean_outbox():
    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        await session.execute(delete(outbox_table))
    yield
    async with session_factory() as session, session.begin():
        await session.execute(delete(outbox_table))


@pytest.mark.asyncio
async def test_committed_event_is_published_exactly_once(clean_outbox):
    widget = _Widget(id=uuid4())
    widget.touch()

    async with SqlAlchemyUnitOfWork() as uow:
        uow.register(widget)

    broker = FakeMessageBroker()

    first_batch = await publish_pending_outbox_events(broker)
    second_batch = await publish_pending_outbox_events(broker)

    assert first_batch == 1
    assert second_batch == 0
    assert len(broker.published) == 1
    stream, payload = broker.published[0]
    assert stream == "outbox._Widget"
    assert payload["aggregate_id"] == str(widget.id)
