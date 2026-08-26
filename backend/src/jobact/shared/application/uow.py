"""Protocol describing the async transactional unit-of-work shape.

This is pure application-layer code: ZERO SQLAlchemy/asyncpg imports are
allowed in this module. `UnitOfWork` is a `typing.Protocol` (structural
typing), not an ABC -- application handlers (future tasks, from 1.3
onward) depend on this abstraction so they can be tested without a real
database, and so the application layer never has to know SQLAlchemy
exists. The concrete implementation, `SqlAlchemyUnitOfWork`, lives in
`jobact.shared.infrastructure.postgres.uow` and is the only place that
imports SQLAlchemy for this purpose.
"""

from types import TracebackType
from typing import Any, Protocol, Self

from jobact.shared.domain.aggregate import AggregateRoot


class UnitOfWork(Protocol):
    """Structural type for an async-context-manager-shaped unit of work.

    Usage:

        async with uow:
            aggregate = ...  # load, mutate, raise domain events
            uow.register(aggregate)
        # commits automatically on clean exit, rolls back on exception

    `register()` tells the unit of work which aggregates were touched
    during the block, so their pending domain events (`pull_events()`)
    can be drained and persisted (e.g. to a transactional outbox) as
    part of the same commit.

    `session` exposes the active session to callers that need to hand it
    to a repository (from Task 1.3 onward) -- typed `Any` here, not
    `AsyncSession`, to keep this module's zero-SQLAlchemy-imports rule;
    the concrete `SqlAlchemyUnitOfWork.session` is the real, precisely
    typed thing repositories actually receive.
    """

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    def register(self, aggregate: AggregateRoot) -> None: ...

    @property
    def session(self) -> Any: ...
