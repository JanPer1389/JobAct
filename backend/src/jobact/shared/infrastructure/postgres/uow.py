"""SQLAlchemy-backed implementation of the `UnitOfWork` protocol.

`SqlAlchemyUnitOfWork` wraps a single `AsyncSession` transaction per
`async with` block: clean exit commits, an exception rolls back (and
re-raises). Before committing, it drains pending domain events from
every aggregate registered during the block (via `register()`) and
inserts each one as a row in `platform.outbox`, in the SAME
transaction as the aggregate's own changes -- the transactional
outbox pattern. A future task (2.2) adds the separate process that
drains `platform.outbox` and actually publishes those events.
"""

from dataclasses import fields
from datetime import datetime
from types import TracebackType
from typing import Any, Self
from uuid import UUID

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobact.shared.domain.aggregate import AggregateRoot
from jobact.shared.domain.events import DomainEvent
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.tables import outbox_table

# Fields already captured by dedicated outbox columns; everything else on
# a concrete `DomainEvent` subclass is considered event-specific data and
# goes into the `payload` JSONB column.
_RESERVED_EVENT_FIELDS = {"aggregate_id", "event_id", "occurred_at"}


class SqlAlchemyUnitOfWork:
    """Concrete `UnitOfWork`: one SQLAlchemy async transaction per block."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._session_factory = session_factory or get_sessionmaker()
        self._session: AsyncSession | None = None
        self._registered_aggregates: list[AggregateRoot] = []

    @property
    def session(self) -> AsyncSession:
        """The active session. Only valid inside an `async with` block."""
        if self._session is None:
            raise RuntimeError("SqlAlchemyUnitOfWork used outside of an `async with` block")
        return self._session

    def register(self, aggregate: AggregateRoot) -> None:
        """Register an aggregate touched during this unit of work.

        Registered aggregates have their pending domain events drained
        and written to `platform.outbox` at commit time.
        """
        self._registered_aggregates.append(aggregate)

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self._registered_aggregates = []
        await self._session.begin()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None:
                await self.commit()
            else:
                await self.rollback()
        finally:
            await self.session.close()
            self._session = None

    async def commit(self) -> None:
        """Write outbox rows for pending domain events, then commit.

        The outbox insert happens on the same session/transaction as
        everything else the caller did in this unit of work, so a
        rollback discards both together.
        """
        await self._write_outbox()
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def _write_outbox(self) -> None:
        for aggregate in self._registered_aggregates:
            aggregate_type = type(aggregate).__name__
            for event in aggregate.pull_events():
                await self.session.execute(
                    insert(outbox_table).values(**_outbox_row(aggregate_type, event))
                )


def _outbox_row(aggregate_type: str, event: DomainEvent) -> dict[str, Any]:
    return {
        "id": event.event_id,
        "aggregate_type": aggregate_type,
        "aggregate_id": event.aggregate_id,
        "event_type": type(event).__name__,
        "event_version": 1,
        "payload": _event_payload(event),
        "occurred_at": event.occurred_at,
        "published_at": None,
    }


def _event_payload(event: DomainEvent) -> dict[str, Any]:
    """Serialize the event's non-reserved fields into a JSON-safe dict."""
    return {
        f.name: _json_safe(getattr(event, f.name))
        for f in fields(event)
        if f.name not in _RESERVED_EVENT_FIELDS
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value
