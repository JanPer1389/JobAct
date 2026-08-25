"""Base class for domain objects defined entirely by their attributes.

Pure domain code: standard library only, no framework/infrastructure
imports allowed in this package.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject:
    """Base class for things defined entirely by their attributes.

    Unlike `Entity`, a `ValueObject` has no identity: two instances are
    equal when all of their attributes are equal, regardless of whether
    they are the "same" object.

    Subclassing pattern: decorate the subclass with
    `@dataclass(frozen=True)` and declare its fields as dataclass fields,
    e.g.:

        @dataclass(frozen=True)
        class Coordinates(ValueObject):
            latitude: float
            longitude: float

    `frozen=True` makes instances immutable and hashable, and gives you
    `__eq__`/`__hash__` generated from every declared field for free --
    do not override them by hand. All field values should themselves be
    immutable (other `ValueObject`s, primitives, tuples, etc.) so the
    whole value object stays hashable and safe to share.
    """
