"""Tests for `ValueObject` attribute-based equality."""

from dataclasses import FrozenInstanceError, dataclass

import pytest

from jobact.shared.domain import ValueObject


@dataclass(frozen=True)
class Coordinates(ValueObject):
    """A minimal ValueObject subclass for testing attribute-based semantics."""

    latitude: float
    longitude: float


def test_value_objects_with_same_attributes_are_equal() -> None:
    first = Coordinates(latitude=51.5, longitude=-0.12)
    second = Coordinates(latitude=51.5, longitude=-0.12)

    assert first == second


def test_value_objects_with_different_attributes_are_not_equal() -> None:
    first = Coordinates(latitude=51.5, longitude=-0.12)
    second = Coordinates(latitude=40.7, longitude=-74.0)

    assert first != second


def test_value_objects_with_same_attributes_have_same_hash() -> None:
    first = Coordinates(latitude=51.5, longitude=-0.12)
    second = Coordinates(latitude=51.5, longitude=-0.12)

    assert hash(first) == hash(second)
    assert len({first, second}) == 1


def test_value_object_is_immutable() -> None:
    coordinates = Coordinates(latitude=51.5, longitude=-0.12)

    with pytest.raises(FrozenInstanceError):
        coordinates.latitude = 0.0  # type: ignore[misc]
