"""The `Visit` aggregate -- one on-site job for a customer.

`raw_notes` set here is NOT the authoritative input to AI report
drafting; `POST /reports.raw_notes` is (avoiding two sources of truth)
-- this field only exists so a visit can carry notes if a caller
separately PATCHes them.

`before_photo_count`/`after_photo_count` are legacy client-supplied
counters, kept for contract compatibility but NOT authoritative:
readiness is evaluated against real attached `MediaAsset` rows, via
`evidence_readiness()`.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from jobact.contexts.visits.domain.events import VisitStarted
from jobact.contexts.visits.domain.visit_readiness import VisitReadiness
from jobact.shared.domain.aggregate import AggregateRoot


class Visit(AggregateRoot):
    def __init__(
        self,
        *,
        id: UUID,
        organization_id: UUID,
        customer_id: UUID,
        technician_id: UUID,
        status: str,
        started_at: datetime,
        gps_lat: float | None = None,
        gps_lon: float | None = None,
        gps_accuracy_m: float | None = None,
        before_photo_count: int = 0,
        after_photo_count: int = 0,
        raw_notes: str | None = None,
    ) -> None:
        super().__init__()
        self.id = id
        self.organization_id = organization_id
        self.customer_id = customer_id
        self.technician_id = technician_id
        self.status = status
        self.started_at = started_at
        self.gps_lat = gps_lat
        self.gps_lon = gps_lon
        self.gps_accuracy_m = gps_accuracy_m
        self.before_photo_count = before_photo_count
        self.after_photo_count = after_photo_count
        self.raw_notes = raw_notes

    @classmethod
    def start(
        cls,
        *,
        id: UUID,
        organization_id: UUID,
        customer_id: UUID,
        technician_id: UUID,
        started_at: datetime,
        gps_lat: float | None = None,
        gps_lon: float | None = None,
        gps_accuracy_m: float | None = None,
    ) -> Visit:
        visit = cls(
            id=id,
            organization_id=organization_id,
            customer_id=customer_id,
            technician_id=technician_id,
            status="in_progress",
            started_at=started_at,
            gps_lat=gps_lat,
            gps_lon=gps_lon,
            gps_accuracy_m=gps_accuracy_m,
        )
        visit._record_event(
            VisitStarted(
                aggregate_id=visit.id,
                organization_id=organization_id,
                customer_id=customer_id,
            )
        )
        return visit

    def update_capture_state(
        self,
        *,
        gps_lat: float | None = None,
        gps_lon: float | None = None,
        gps_accuracy_m: float | None = None,
        before_photo_count: int | None = None,
        after_photo_count: int | None = None,
        raw_notes: str | None = None,
    ) -> None:
        if gps_lat is not None:
            self.gps_lat = gps_lat
        if gps_lon is not None:
            self.gps_lon = gps_lon
        if gps_accuracy_m is not None:
            self.gps_accuracy_m = gps_accuracy_m
        if before_photo_count is not None:
            self.before_photo_count = before_photo_count
        if after_photo_count is not None:
            self.after_photo_count = after_photo_count
        if raw_notes is not None:
            self.raw_notes = raw_notes

    def evidence_readiness(
        self, *, attached_before_count: int, attached_after_count: int
    ) -> VisitReadiness:
        return VisitReadiness(
            has_customer=self.customer_id is not None,
            has_geolocation=self.gps_lat is not None and self.gps_lon is not None,
            has_before_photos=attached_before_count >= 1,
            has_matching_after_photos=(
                attached_after_count >= 1
                and attached_after_count == attached_before_count
            ),
        )
