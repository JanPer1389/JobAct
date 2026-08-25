"""Application-layer abstractions shared across bounded contexts.

Application code depends on abstractions (like `UnitOfWork`) rather than
concrete infrastructure -- dependency inversion. This package may depend
on `jobact.shared.domain`, but must never import SQLAlchemy, asyncpg,
Redis, FastAPI, or any other infrastructure/framework package.
"""

from jobact.shared.application.uow import UnitOfWork

__all__ = ["UnitOfWork"]
