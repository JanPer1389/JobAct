from __future__ import annotations

from uuid import UUID

from jobact.contexts.customers.infrastructure.customer_repository import (
    CustomerRepository,
)
from jobact.contexts.visits.domain.visit import Visit
from jobact.contexts.visits.infrastructure.visit_repository import VisitRepository
from jobact.shared.application.authorization import AuthorizationError
from jobact.shared.application.ports import Clock, IdGenerator
from jobact.shared.application.uow import UnitOfWork


class StartVisitHandler:
    def __init__(self, uow: UnitOfWork, clock: Clock, id_generator: IdGenerator) -> None:
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        visit_id: UUID | None = None,
        organization_id: UUID,
        customer_id: UUID,
        technician_id: UUID,
        gps_lat: float | None = None,
        gps_lon: float | None = None,
        gps_accuracy_m: float | None = None,
    ) -> Visit:
        async with self._uow:
            customers = await CustomerRepository(self._uow.session).list_by_organization(
                organization_id
            )
            if not any(c.id == customer_id for c in customers):
                raise AuthorizationError(
                    f"Customer {customer_id} does not belong to organization {organization_id}."
                )

            visit = Visit.start(
                id=visit_id or self._id_generator.new_id(),
                organization_id=organization_id,
                customer_id=customer_id,
                technician_id=technician_id,
                started_at=self._clock.now(),
                gps_lat=gps_lat,
                gps_lon=gps_lon,
                gps_accuracy_m=gps_accuracy_m,
            )
            await VisitRepository(self._uow.session).add(visit)
            self._uow.register(visit)
        return visit


class UpdateVisitCaptureStateHandler:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def handle(
        self,
        *,
        visit_id: UUID,
        organization_id: UUID,
        gps_lat: float | None = None,
        gps_lon: float | None = None,
        gps_accuracy_m: float | None = None,
        before_photo_count: int | None = None,
        after_photo_count: int | None = None,
        raw_notes: str | None = None,
    ) -> Visit:
        async with self._uow:
            repo = VisitRepository(self._uow.session)
            visit = await repo.get_by_id(visit_id)
            if visit is None or visit.organization_id != organization_id:
                raise AuthorizationError(
                    f"Visit {visit_id} does not belong to organization {organization_id}."
                )
            visit.update_capture_state(
                gps_lat=gps_lat,
                gps_lon=gps_lon,
                gps_accuracy_m=gps_accuracy_m,
                before_photo_count=before_photo_count,
                after_photo_count=after_photo_count,
                raw_notes=raw_notes,
            )
            await repo.save(visit)
        return visit
