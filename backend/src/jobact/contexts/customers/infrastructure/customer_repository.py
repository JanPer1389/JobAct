"""`Customer` repository -- manual Core-table mapping, same pattern as
`contexts/identity/infrastructure/*_repository.py`.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from jobact.contexts.customers.domain.customer import Customer
from jobact.shared.infrastructure.postgres.operations_tables import customers_table


class CustomerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, customer: Customer) -> None:
        await self._session.execute(
            insert(customers_table).values(
                id=customer.id,
                organization_id=customer.organization_id,
                name=customer.name,
                address=customer.address,
                phone=customer.phone,
                service_type=customer.service_type,
                created_at=customer.created_at,
            )
        )

    async def list_by_organization(self, organization_id: UUID) -> list[Customer]:
        result = await self._session.execute(
            select(customers_table).where(
                customers_table.c.organization_id == organization_id
            )
        )
        return [
            Customer(
                id=row.id,
                organization_id=row.organization_id,
                name=row.name,
                address=row.address,
                phone=row.phone,
                service_type=row.service_type,
                created_at=row.created_at,
            )
            for row in result
        ]
