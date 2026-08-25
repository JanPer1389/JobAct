"""Base class for domain events.

Pure domain code: standard library only, no framework/infrastructure
imports allowed in this package.

This is the internal, framework-free shape an aggregate emits from its
business methods -- it is deliberately minimal and is NOT the same thing
as the versioned HTTP/event contract DTOs built in later tasks, which
wrap a `DomainEvent` in an envelope for transport/persistence.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Represents something that happened in the domain.

    Carries the minimum every concrete event needs: an identifier for the
    event itself, the id of the aggregate it concerns, and when it
    occurred. Concrete event types (e.g. `VisitStarted`, `ReportSigned`,
    built in later tasks) subclass this and add their own fields:

        @dataclass(frozen=True, kw_only=True)
        class ReportSigned(DomainEvent):
            signed_by: UUID

    `kw_only=True` lets subclasses add required fields without worrying
    about dataclass field-ordering rules, since every field here has a
    default.
    """

    aggregate_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
