"""A customer created in org A is invisible to org B -- proven at the
repository level, not via HTTP routes.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete

from jobact.contexts.customers.domain.customer import Customer
from jobact.contexts.customers.infrastructure.customer_repository import (
    CustomerRepository,
)
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.operations_tables import customers_table


@pytest.fixture
async def clean_customers():
    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        await session.execute(delete(customers_table))
    yield
    async with session_factory() as session, session.begin():
        await session.execute(delete(customers_table))


@pytest.mark.asyncio
async def test_customer_is_scoped_to_its_organization(clean_customers):
    org_a = uuid4()
    org_b = uuid4()
    session_factory = get_sessionmaker()

    async with session_factory() as session, session.begin():
        repo = CustomerRepository(session)
        await repo.add(
            Customer(
                id=uuid4(),
                organization_id=org_a,
                name="Aurora Dental",
                address="1 Main St",
                phone="+1-555-0100",
                service_type="AC maintenance",
                created_at=datetime.now(UTC),
            )
        )

    async with session_factory() as session:
        repo = CustomerRepository(session)
        assert len(await repo.list_by_organization(org_a)) == 1
        assert len(await repo.list_by_organization(org_b)) == 0
