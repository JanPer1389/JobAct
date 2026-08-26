"""Real `IdGenerator` implementation: random UUIDv4s."""

from uuid import UUID, uuid4


class UuidIdGenerator:
    """`IdGenerator` backed by `uuid.uuid4()`."""

    def new_id(self) -> UUID:
        return uuid4()
