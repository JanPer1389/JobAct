"""`Organization` aggregate: the tenancy boundary every other context
scopes its data by.

Minimal for this task -- just identity and construction. No behavior is
specified yet; later tasks add whatever organization-level operations
they need.
"""

from datetime import datetime
from uuid import UUID

from jobact.shared.domain import AggregateRoot


class Organization(AggregateRoot):
    """A tenant. Every `Membership`, and (in later contexts) every
    customer/visit/report/media record, is scoped to one `Organization`.
    """

    def __init__(self, *, id: UUID, name: str, created_at: datetime) -> None:
        super().__init__()
        self.id = id
        self.name = name
        self.created_at = created_at
