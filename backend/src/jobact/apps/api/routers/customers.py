"""`/api/v1/customers` routes -- org-scoped list and create."""

from fastapi import APIRouter, Depends

from jobact.apps.api.deps import CurrentPrincipal, get_current_principal
from jobact.contexts.customers.application.customer_handlers import (
    CreateCustomerHandler,
    ListCustomersHandler,
)
from jobact.contracts.http.v1.customers import CreateCustomerRequest, CustomerResponse
from jobact.shared.infrastructure.clock import SystemClock
from jobact.shared.infrastructure.id_generator import UuidIdGenerator
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/customers", tags=["customers"])


def _to_response(customer) -> CustomerResponse:
    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        address=customer.address,
        phone=customer.phone,
        service_type=customer.service_type,
        created_at=customer.created_at,
    )


@router.get("", response_model=list[CustomerResponse])
async def list_customers(
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> list[CustomerResponse]:
    handler = ListCustomersHandler(uow=SqlAlchemyUnitOfWork())
    customers = await handler.handle(organization_id=principal.organization_id)
    return [_to_response(c) for c in customers]


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(
    body: CreateCustomerRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> CustomerResponse:
    handler = CreateCustomerHandler(
        uow=SqlAlchemyUnitOfWork(),
        clock=SystemClock(),
        id_generator=UuidIdGenerator(),
    )
    customer = await handler.handle(
        organization_id=principal.organization_id,
        name=body.name,
        address=body.address,
        phone=body.phone,
        service_type=body.service_type,
    )
    return _to_response(customer)
