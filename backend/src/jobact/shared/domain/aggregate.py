"""Base class for aggregate roots.

Pure domain code: standard library only, no framework/infrastructure
imports allowed in this package.
"""

from jobact.shared.domain.entity import Entity
from jobact.shared.domain.events import DomainEvent


class AggregateRoot(Entity):
    """Base class for aggregate roots: entities that also emit domain events.

    An aggregate root collects `DomainEvent`s raised during its lifetime
    (via `_record_event`) and hands them off to callers via
    `pull_events()`, which returns everything collected so far and clears
    the internal queue as a side effect -- so calling `pull_events()`
    twice in a row, with nothing recorded in between, returns an empty
    list the second time.

    Subclassing pattern: call `super().__init__()` in the subclass's
    `__init__` (in addition to setting `self.id`, inherited from
    `Entity`), and raise events from business methods with
    `self._record_event(...)`:

        class Report(AggregateRoot):
            def __init__(self, id: UUID) -> None:
                super().__init__()
                self.id = id

            def sign(self, signed_by: UUID) -> None:
                ...
                self._record_event(ReportSigned(aggregate_id=self.id, signed_by=signed_by))
    """

    def __init__(self) -> None:
        self._domain_events: list[DomainEvent] = []

    def _record_event(self, event: DomainEvent) -> None:
        """Queue a domain event raised by this aggregate. For use by subclasses."""
        self._domain_events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        """Return all events collected so far and clear the internal queue.

        Draining is a side effect: a second call with nothing recorded in
        between returns an empty list.
        """
        events = self._domain_events
        self._domain_events = []
        return events
