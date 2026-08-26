"""Real `Clock` implementation: the system's own UTC wall clock."""

from datetime import UTC, datetime


class SystemClock:
    """`Clock` backed by `datetime.now(UTC)`."""

    def now(self) -> datetime:
        return datetime.now(UTC)
