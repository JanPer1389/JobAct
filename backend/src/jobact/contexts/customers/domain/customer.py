"""The `Customer` aggregate -- a service business's client, scoped to
one organization.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from jobact.shared.domain.aggregate import AggregateRoot


class Customer(AggregateRoot):
    def __init__(
        self,
        *,
        id: UUID,
        organization_id: UUID,
        name: str,
        address: str,
        phone: str,
        service_type: str,
        created_at: datetime,
    ) -> None:
        super().__init__()
        self.id = id
        self.organization_id = organization_id
        self.name = name
        self.address = address
        self.phone = phone
        self.service_type = service_type
        self.created_at = created_at
