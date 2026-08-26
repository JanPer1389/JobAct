from __future__ import annotations

from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from jobact.contexts.visits.domain.visit import Visit
from jobact.shared.infrastructure.postgres.operations_tables import visits_table


class VisitRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, visit: Visit) -> None:
        await self._session.execute(
            insert(visits_table).values(
                id=visit.id,
                organization_id=visit.organization_id,
                customer_id=visit.customer_id,
                technician_id=visit.technician_id,
                status=visit.status,
                started_at=visit.started_at,
                gps_lat=visit.gps_lat,
                gps_lon=visit.gps_lon,
                gps_accuracy_m=visit.gps_accuracy_m,
                before_photo_count=visit.before_photo_count,
                after_photo_count=visit.after_photo_count,
                raw_notes=visit.raw_notes,
            )
        )

    async def get_by_id(self, visit_id: UUID) -> Visit | None:
        result = await self._session.execute(
            select(visits_table).where(visits_table.c.id == visit_id)
        )
        row = result.first()
        if row is None:
            return None
        return _to_domain(row)

    async def save(self, visit: Visit) -> None:
        await self._session.execute(
            update(visits_table)
            .where(visits_table.c.id == visit.id)
            .values(
                gps_lat=visit.gps_lat,
                gps_lon=visit.gps_lon,
                gps_accuracy_m=visit.gps_accuracy_m,
                before_photo_count=visit.before_photo_count,
                after_photo_count=visit.after_photo_count,
                raw_notes=visit.raw_notes,
            )
        )


def _to_domain(row) -> Visit:
    return Visit(
        id=row.id,
        organization_id=row.organization_id,
        customer_id=row.customer_id,
        technician_id=row.technician_id,
        status=row.status,
        started_at=row.started_at,
        gps_lat=row.gps_lat,
        gps_lon=row.gps_lon,
        gps_accuracy_m=row.gps_accuracy_m,
        before_photo_count=row.before_photo_count,
        after_photo_count=row.after_photo_count,
        raw_notes=row.raw_notes,
    )
