"""Base class for domain objects with identity.

Pure domain code: standard library only, no framework/infrastructure
imports allowed in this package.
"""

from typing import Any


class Entity:
    """Base class for anything with identity.

    Equality and hash are based solely on `id` (and the concrete type),
    not on any other attribute. Two `Entity` instances of the same type
    with the same `id` are equal even if their other fields differ;
    instances with different `id`s are never equal, even if every other
    field happens to match. Instances of different `Entity` subclasses
    are never equal to each other, even if they share an `id` value.

    Subclassing pattern: set `self.id` in `__init__` (or declare it as a
    dataclass field), e.g.:

        class Report(Entity):
            def __init__(self, id: UUID, title: str) -> None:
                self.id = id
                self.title = title

    `id` must be set before the entity is compared, hashed, or put in a
    set/dict.

    If a subclass is written as a `@dataclass`, pass `eq=False` so the
    dataclass does not generate its own `__eq__`/`__hash__` and override
    the identity-based ones defined here, e.g.
    `@dataclass(eq=False)`.
    """

    id: Any

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity) or type(self) is not type(other):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash((type(self), self.id))
