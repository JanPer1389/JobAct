"""Tests for `AggregateRoot` event recording and draining.

The core behavior under test: an aggregate records domain events raised
during its lifetime, and `pull_events()` drains the queue exactly once --
a second call with nothing new recorded in between returns an empty list.
"""

from dataclasses import dataclass
from uuid import UUID, uuid4

from jobact.shared.domain import AggregateRoot, DomainEvent


@dataclass(frozen=True, kw_only=True)
class WidgetActivated(DomainEvent):
    """A dummy domain event for testing."""


class Widget(AggregateRoot):
    """A minimal AggregateRoot subclass for testing event recording."""

    def __init__(self, id: UUID) -> None:
        super().__init__()
        self.id = id
        self.active = False

    def activate(self) -> None:
        self.active = True
        self._record_event(WidgetActivated(aggregate_id=self.id))


def test_aggregate_starts_with_no_pending_events() -> None:
    widget = Widget(id=uuid4())

    assert widget.pull_events() == []


def test_recorded_events_are_returned_by_pull_events() -> None:
    widget = Widget(id=uuid4())

    widget.activate()

    events = widget.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], WidgetActivated)
    assert events[0].aggregate_id == widget.id


def test_pull_events_drains_the_queue_exactly_once() -> None:
    widget = Widget(id=uuid4())
    widget.activate()

    first_pull = widget.pull_events()
    second_pull = widget.pull_events()

    assert len(first_pull) == 1
    assert second_pull == []


def test_events_recorded_after_a_drain_are_returned_on_the_next_pull() -> None:
    widget = Widget(id=uuid4())
    widget.activate()
    widget.pull_events()

    widget.activate()
    events = widget.pull_events()

    assert len(events) == 1
