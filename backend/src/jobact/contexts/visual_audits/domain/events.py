from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from jobact.shared.domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class VisualAuditRequested(DomainEvent):
    organization_id: UUID
    report_id: UUID
    report_revision_id: UUID

