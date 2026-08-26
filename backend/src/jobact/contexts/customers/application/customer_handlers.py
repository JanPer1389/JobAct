"""Customer command/query handlers -- thin orchestration over
`UnitOfWork` + `CustomerRepository`, no business logic of its own
(there isn't any yet -- `Customer` has no behavior beyond construction).
"""

from __future__ import annotations

from uuid import UUID

from jobact.contexts.customers.domain.customer import Customer
from jobact.contexts.customers.infrastructure.customer_repository import (
    CustomerRepository,
)
from jobact.shared.application.ports import Clock, IdGenerator
from jobact.shared.application.uow import UnitOfWork


class CreateCustomerHandler:
    def __init__(self, uow: UnitOfWork, clock: Clock, id_generator: IdGenerator) -> None:
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        organization_id: UUID,
        name: str,
        address: str,
        phone: str,
        service_type: str,
    ) -> Customer:
        customer = Customer(
            id=self._id_generator.new_id(),
            organization_id=organization_id,
            name=name,
            address=address,
            phone=phone,
            service_type=service_type,
            created_at=self._clock.now(),
        )
        async with self._uow:
            await CustomerRepository(self._uow.session).add(customer)
            self._uow.register(customer)
        return customer


class ListCustomersHandler:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def handle(self, *, organization_id: UUID) -> list[Customer]:
        async with self._uow:
            return await CustomerRepository(self._uow.session).list_by_organization(
                organization_id
            )
