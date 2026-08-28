"""`Report` repository -- manual Core-table mapping, same pattern as
every other context's repository.

`allocate_human_id` uses a single atomic UPSERT against
`operations.report_number_counters` rather than scanning existing
`human_id` values for max+1 -- the scan approach is not safe under
concurrent report creation within the same org/year (two concurrent
creates can read the same max before either commits, and the id would
collide against the reports table's own unique constraint). The UPSERT
executes under a Postgres row-level lock, so it's a genuine sequence.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from jobact.contexts.reports.domain.report import (
    Material,
    Report,
    ReportRevision,
    Signature,
)
from jobact.shared.infrastructure.postgres.operations_tables import (
    report_materials_table,
    report_number_counters_table,
    report_revisions_table,
    reports_table,
    signatures_table,
)


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def allocate_human_id(self, organization_id: UUID, year: int) -> str:
        statement = pg_insert(report_number_counters_table).values(
            organization_id=organization_id, year=year, next_number=1
        )
        statement = statement.on_conflict_do_update(
            index_elements=["organization_id", "year"],
            set_={"next_number": report_number_counters_table.c.next_number + 1},
        ).returning(report_number_counters_table.c.next_number)
        result = await self._session.execute(statement)
        sequence = result.scalar_one()
        return f"JA-{year}-{sequence:04d}"

    async def add(self, report: Report) -> None:
        revision = report.current_revision
        await self._session.execute(
            insert(reports_table).values(
                id=report.id,
                organization_id=report.organization_id,
                visit_id=report.visit_id,
                human_id=report.human_id,
                status=report.status,
                current_revision_id=revision.id,
                signed_at=report.signed_at,
                completed_at=report.completed_at,
            )
        )
        await self._insert_revision(report.id, revision)

    async def get_by_id(self, report_id: UUID) -> Report | None:
        result = await self._session.execute(
            select(reports_table).where(reports_table.c.id == report_id)
        )
        row = result.first()
        if row is None:
            return None
        return await self._to_domain(row)

    async def list_by_organization(self, organization_id: UUID) -> list[Report]:
        result = await self._session.execute(
            select(reports_table)
            .where(reports_table.c.organization_id == organization_id)
            .order_by(reports_table.c.human_id)
        )
        return [await self._to_domain(row) for row in result]

    async def save(self, report: Report) -> None:
        revision = report.current_revision
        await self._session.execute(
            update(reports_table)
            .where(reports_table.c.id == report.id)
            .values(
                status=report.status,
                current_revision_id=revision.id,
                signed_at=report.signed_at,
                completed_at=report.completed_at,
            )
        )
        await self._session.execute(
            update(report_revisions_table)
            .where(report_revisions_table.c.id == revision.id)
            .values(
                source=revision.source,
                work_completed=revision.work_completed,
                amount_cents=revision.amount_cents,
                currency=revision.currency,
                ai_confidence=revision.ai_confidence,
                confirmed_by_user_at=revision.confirmed_by_user_at,
                amount_confirmed_at=revision.amount_confirmed_at,
                frozen_at=revision.frozen_at,
                visual_comparison_status=revision.visual_comparison_status,
                visual_comparison=revision.visual_comparison,
            )
        )
        await self._replace_materials(revision)
        await self._insert_new_signatures(report)

    async def _replace_materials(self, revision: ReportRevision) -> None:
        await self._session.execute(
            delete(report_materials_table).where(
                report_materials_table.c.revision_id == revision.id
            )
        )
        await self._insert_materials(revision)

    async def _insert_new_signatures(self, report: Report) -> None:
        existing = await self._session.execute(
            select(signatures_table.c.id).where(
                signatures_table.c.report_id == report.id
            )
        )
        existing_ids = set(existing.scalars())
        for signature in report.signatures:
            if signature.id in existing_ids:
                continue
            await self._session.execute(
                insert(signatures_table).values(
                    id=signature.id,
                    report_id=report.id,
                    signer_name=signature.signer_name,
                    signed_at=signature.signed_at,
                    media_asset_id=signature.media_asset_id,
                    ip=signature.ip,
                    user_agent=signature.user_agent,
                )
            )

    async def _insert_revision(self, report_id: UUID, revision: ReportRevision) -> None:
        await self._session.execute(
            insert(report_revisions_table).values(
                id=revision.id,
                report_id=report_id,
                revision_no=revision.revision_no,
                source=revision.source,
                work_completed=revision.work_completed,
                amount_cents=revision.amount_cents,
                currency=revision.currency,
                ai_confidence=revision.ai_confidence,
                created_at=revision.created_at,
                created_by=revision.created_by,
                confirmed_by_user_at=revision.confirmed_by_user_at,
                amount_confirmed_at=revision.amount_confirmed_at,
                frozen_at=revision.frozen_at,
                visual_comparison_status=revision.visual_comparison_status,
                visual_comparison=revision.visual_comparison,
            )
        )
        await self._insert_materials(revision)

    async def _insert_materials(self, revision: ReportRevision) -> None:
        for material in revision.materials:
            await self._session.execute(
                insert(report_materials_table).values(
                    id=material.id,
                    revision_id=revision.id,
                    label=material.label,
                    qty=material.qty,
                )
            )

    async def _to_domain(self, row) -> Report:
        revision_result = await self._session.execute(
            select(report_revisions_table).where(
                report_revisions_table.c.id == row.current_revision_id
            )
        )
        revision_row = revision_result.one()
        material_result = await self._session.execute(
            select(report_materials_table).where(
                report_materials_table.c.revision_id == revision_row.id
            )
        )
        signature_result = await self._session.execute(
            select(signatures_table).where(signatures_table.c.report_id == row.id)
        )
        revision = ReportRevision(
            id=revision_row.id,
            revision_no=revision_row.revision_no,
            source=revision_row.source,
            work_completed=revision_row.work_completed,
            amount_cents=revision_row.amount_cents,
            currency=revision_row.currency,
            ai_confidence=revision_row.ai_confidence,
            created_at=revision_row.created_at,
            created_by=revision_row.created_by,
            confirmed_by_user_at=revision_row.confirmed_by_user_at,
            amount_confirmed_at=revision_row.amount_confirmed_at,
            frozen_at=revision_row.frozen_at,
            visual_comparison_status=revision_row.visual_comparison_status,
            visual_comparison=revision_row.visual_comparison,
            materials=[
                Material(id=item.id, label=item.label, qty=item.qty)
                for item in material_result
            ],
        )
        return Report(
            id=row.id,
            organization_id=row.organization_id,
            visit_id=row.visit_id,
            human_id=row.human_id,
            status=row.status,
            current_revision=revision,
            signed_at=row.signed_at,
            completed_at=row.completed_at,
            signatures=[
                Signature(
                    id=item.id,
                    signer_name=item.signer_name,
                    signed_at=item.signed_at,
                    media_asset_id=item.media_asset_id,
                    ip=item.ip,
                    user_agent=item.user_agent,
                )
                for item in signature_result
            ],
        )
