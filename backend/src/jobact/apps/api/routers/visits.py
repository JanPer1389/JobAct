from uuid import UUID

from fastapi import APIRouter, Depends

from jobact.apps.api.deps import CurrentPrincipal, get_current_principal
from jobact.contexts.visits.application.visit_handlers import (
    StartVisitHandler,
    UpdateVisitCaptureStateHandler,
)
from jobact.contracts.http.v1.visits import (
    StartVisitRequest,
    UpdateVisitRequest,
    VisitResponse,
)
from jobact.shared.infrastructure.clock import SystemClock
from jobact.shared.infrastructure.id_generator import UuidIdGenerator
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/visits", tags=["visits"])


def _to_response(visit) -> VisitResponse:
    return VisitResponse(
        id=visit.id,
        customer_id=visit.customer_id,
        technician_id=visit.technician_id,
        status=visit.status,
        started_at=visit.started_at,
        gps_lat=visit.gps_lat,
        gps_lon=visit.gps_lon,
        gps_accuracy_m=visit.gps_accuracy_m,
        before_photo_count=visit.before_photo_count,
        after_photo_count=visit.after_photo_count,
    )


@router.post("", response_model=VisitResponse, status_code=201)
async def start_visit(
    body: StartVisitRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> VisitResponse:
    handler = StartVisitHandler(
        uow=SqlAlchemyUnitOfWork(), clock=SystemClock(), id_generator=UuidIdGenerator()
    )
    visit = await handler.handle(
        visit_id=body.id,
        organization_id=principal.organization_id,
        customer_id=body.customer_id,
        technician_id=principal.user_id,
        gps_lat=body.gps_lat,
        gps_lon=body.gps_lon,
        gps_accuracy_m=body.gps_accuracy_m,
    )
    return _to_response(visit)


@router.patch("/{visit_id}", response_model=VisitResponse)
async def update_visit(
    visit_id: UUID,
    body: UpdateVisitRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> VisitResponse:
    handler = UpdateVisitCaptureStateHandler(uow=SqlAlchemyUnitOfWork())
    visit = await handler.handle(
        visit_id=visit_id,
        organization_id=principal.organization_id,
        gps_lat=body.gps_lat,
        gps_lon=body.gps_lon,
        gps_accuracy_m=body.gps_accuracy_m,
        before_photo_count=body.before_photo_count,
        after_photo_count=body.after_photo_count,
        raw_notes=body.raw_notes,
    )
    return _to_response(visit)
