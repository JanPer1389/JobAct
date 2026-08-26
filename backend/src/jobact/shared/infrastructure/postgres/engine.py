"""Async SQLAlchemy engine and session factory for Postgres.

Single place that constructs the engine/sessionmaker from
`Settings.database_url`. Other infrastructure modules (e.g.
`SqlAlchemyUnitOfWork`, and later tasks' repositories) import the
session factory from here rather than each building their own engine.
"""

from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from jobact.shared.infrastructure.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Return the process-wide cached async engine, built from `Settings`."""
    settings = get_settings()
    return create_async_engine(
        settings.database_url, connect_args={"ssl": settings.postgres_ssl}
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide cached async session factory."""
    return async_sessionmaker(get_engine(), expire_on_commit=False)
