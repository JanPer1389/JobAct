"""Integration tests for `SqlAlchemyUnitOfWork` against the real Postgres.

These verify the core transactional-outbox property this task exists to
prove: `async with uow:` commits domain changes AND writes any pulled
domain events into `platform.outbox` in the SAME transaction on success
-- and discards both together on an exception, never one without the
other. Deliberately not mocked, same reasoning as
`tests/integration/test_infrastructure.py`.

Requires the Alembic baseline migration to already be applied (creates
`platform.outbox`) and the real Postgres container running:
    docker compose up -d
    uv run alembic upgrade head
    uv run pytest tests/integration/test_unit_of_work.py
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.engine import RowMapping

from jobact.shared.domain.aggregate import AggregateRoot
from jobact.shared.domain.events import DomainEvent
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.tables import outbox_table
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork

# Note: `get_sessionmaker()`/`get_engine()` are process-wide cached
# (`lru_cache`), so their pooled asyncpg connections are bound to
# whichever event loop created them. This test session runs on a single
# shared event loop (see `asyncio_default_*_loop_scope = "session"` in
# pyproject.toml) so the cached engine's pool stays valid across tests.


@dataclass(frozen=True, kw_only=True)
class WidgetActivated(DomainEvent):
    """A dummy domain event for testing the outbox write path."""

    label: str


class Widget(AggregateRoot):
    """A minimal AggregateRoot subclass, following Task 0.2's documented pattern."""

    def __init__(self, id: UUID) -> None:
        super().__init__()
        self.id = id
        self.active = False

    def activate(self, label: str) -> None:
        self.active = True
        self._record_event(WidgetActivated(aggregate_id=self.id, label=label))


class BoomError(Exception):
    """A plain exception used to force a rollback mid-unit-of-work."""


@pytest.fixture
async def clean_outbox() -> AsyncIterator[None]:
    """Keep `platform.outbox` empty before and after each test."""
    session_factory = get_sessionmaker()

    async def _truncate() -> None:
        async with session_factory() as session, session.begin():
            await session.execute(delete(outbox_table))

    await _truncate()
    yield
    await _truncate()


async def _outbox_rows_for(aggregate_id: UUID) -> list[RowMapping]:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        result = await session.execute(
            select(outbox_table).where(outbox_table.c.aggregate_id == aggregate_id)
        )
        return list(result.mappings().all())


async def test_commit_writes_pulled_domain_events_to_outbox(clean_outbox: None) -> None:
    widget = Widget(id=uuid4())
    uow = SqlAlchemyUnitOfWork()

    async with uow:
        widget.activate(label="hello")
        uow.register(widget)

    rows = await _outbox_rows_for(widget.id)
    assert len(rows) == 1
    row = rows[0]
    assert row["aggregate_type"] == "Widget"
    assert row["aggregate_id"] == widget.id
    assert row["event_type"] == "WidgetActivated"
    assert row["event_version"] == 1
    assert row["payload"] == {"label": "hello"}
    assert row["published_at"] is None


async def test_pull_events_drains_the_aggregate_so_a_second_uow_writes_nothing_new(
    clean_outbox: None,
) -> None:
    widget = Widget(id=uuid4())
    uow = SqlAlchemyUnitOfWork()

    async with uow:
        widget.activate(label="only once")
        uow.register(widget)

    # Registering the same (already-drained) aggregate again in a fresh
    # unit of work must not duplicate the outbox row: pull_events() only
    # returns events recorded since the last drain.
    uow2 = SqlAlchemyUnitOfWork()
    async with uow2:
        uow2.register(widget)

    rows = await _outbox_rows_for(widget.id)
    assert len(rows) == 1


async def test_exception_rolls_back_everything_including_outbox(clean_outbox: None) -> None:
    widget = Widget(id=uuid4())
    uow = SqlAlchemyUnitOfWork()

    with pytest.raises(BoomError):
        async with uow:
            widget.activate(label="never persisted")
            uow.register(widget)
            raise BoomError("something went wrong mid-transaction")

    rows = await _outbox_rows_for(widget.id)
    assert rows == []
