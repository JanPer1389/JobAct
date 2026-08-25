"""Tests for `Entity` identity-based equality."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from jobact.shared.domain import Entity


@dataclass(eq=False)
class DummyEntity(Entity):
    """A minimal Entity subclass for testing identity semantics."""

    id: UUID
    name: str


def test_entities_with_same_id_are_equal_even_if_other_fields_differ() -> None:
    shared_id = uuid4()
    first = DummyEntity(id=shared_id, name="Alice")
    second = DummyEntity(id=shared_id, name="Bob")

    assert first == second


def test_entities_with_different_ids_are_never_equal_even_if_other_fields_match() -> None:
    first = DummyEntity(id=uuid4(), name="Alice")
    second = DummyEntity(id=uuid4(), name="Alice")

    assert first != second


def test_entities_of_different_types_with_same_id_are_not_equal() -> None:
    @dataclass(eq=False)
    class OtherEntity(Entity):
        id: UUID

    shared_id = uuid4()
    first = DummyEntity(id=shared_id, name="Alice")
    second = OtherEntity(id=shared_id)

    assert first != second


def test_entity_hash_is_based_on_id() -> None:
    shared_id = uuid4()
    first = DummyEntity(id=shared_id, name="Alice")
    second = DummyEntity(id=shared_id, name="Bob")

    assert hash(first) == hash(second)
    assert len({first, second}) == 1
