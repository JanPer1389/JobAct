"""Foundational DDD building blocks shared by every domain aggregate.

This package must stay completely framework-free: standard library only
(`dataclasses`, `uuid`, `datetime`, `abc`, `typing`). No SQLAlchemy,
Redis, FastAPI, Pydantic, or any other infrastructure/framework import
belongs here -- later layers depend on this package staying pure so the
domain remains testable in isolation.
"""

from jobact.shared.domain.aggregate import AggregateRoot
from jobact.shared.domain.entity import Entity
from jobact.shared.domain.events import DomainEvent
from jobact.shared.domain.value_object import ValueObject

__all__ = ["AggregateRoot", "DomainEvent", "Entity", "ValueObject"]
