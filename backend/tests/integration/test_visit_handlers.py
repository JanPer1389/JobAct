"""Starting a visit for another org's customer raises AuthorizationError."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete

from jobact.contexts.customers.domain.customer import Customer
from jobact.contexts.customers.infrastructure.customer_repository import (
    CustomerRepository,
)
from jobact.contexts.visits.application.visit_handlers import StartVisitHandler
from jobact.shared.application.authorization import AuthorizationError
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.operations_tables import (
    customers_table,
    visits_table,
)
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from tests.fakes import FakeClock, FakeIdGenerator


@pytest.fixture
async def clean_tables():
    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        await session.execute(delete(visits_table))
        await session.execute(delete(customers_table))
    yield
    async with session_factory() as session, session.begin():
        await session.execute(delete(visits_table))
        await session.execute(delete(customers_table))


@pytest.mark.asyncio
async def test_starting_a_visit_for_another_orgs_customer_raises(clean_tables):
    org_a = uuid4()
    org_b = uuid4()
    session_factory = get_sessionmaker()

    async with session_factory() as session, session.begin():
        await CustomerRepository(session).add(
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
        customer_a = (await CustomerRepository(session).list_by_organization(org_a))[0]

    handler = StartVisitHandler(
        uow=SqlAlchemyUnitOfWork(),
        clock=FakeClock(),
        id_generator=FakeIdGenerator(),
    )

    with pytest.raises(AuthorizationError):
        await handler.handle(
            organization_id=org_b,
            customer_id=customer_a.id,
            technician_id=uuid4(),
        )
