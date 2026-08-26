from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from jobact.shared.domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class VisitStarted(DomainEvent):
    organization_id: UUID
    customer_id: UUID
