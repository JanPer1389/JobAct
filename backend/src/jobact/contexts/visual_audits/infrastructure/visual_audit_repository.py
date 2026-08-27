from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from jobact.contexts.visual_audits.domain.visual_audit import (
    PhotoPair,
    VisualAuditAttempt,
)
from jobact.shared.infrastructure.postgres.operations_tables import (
    visual_audit_attempts_table,
    visual_audit_photos_table,
)


class VisualAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, attempt: VisualAuditAttempt) -> None:
        await self._session.execute(insert(visual_audit_attempts_table).values(**_values(attempt)))
        for index, pair in enumerate(attempt.photo_pairs, start=1):
            await self._session.execute(
                insert(visual_audit_photos_table),
                [
                    {"attempt_id": attempt.id, "phase": "before", "pair_index": index, "media_asset_id": pair.before_asset_id},
                    {"attempt_id": attempt.id, "phase": "after", "pair_index": index, "media_asset_id": pair.after_asset_id},
                ],
            )

    async def get_by_id(self, attempt_id: UUID, organization_id: UUID | None = None) -> VisualAuditAttempt | None:
        statement = select(visual_audit_attempts_table).where(visual_audit_attempts_table.c.id == attempt_id)
        if organization_id is not None:
            statement = statement.where(visual_audit_attempts_table.c.organization_id == organization_id)
        row = (await self._session.execute(statement)).first()
        return None if row is None else await self._to_domain(row)

    async def list_by_report(self, report_id: UUID, organization_id: UUID) -> list[VisualAuditAttempt]:
        rows = await self._session.execute(
            select(visual_audit_attempts_table)
            .where(
                visual_audit_attempts_table.c.report_id == report_id,
                visual_audit_attempts_table.c.organization_id == organization_id,
            )
            .order_by(visual_audit_attempts_table.c.created_at.desc())
        )
        return [await self._to_domain(row) for row in rows]

    async def latest_by_report(self, report_id: UUID, organization_id: UUID) -> VisualAuditAttempt | None:
        attempts = await self.list_by_report(report_id, organization_id)
        return attempts[0] if attempts else None

    async def save(self, attempt: VisualAuditAttempt) -> None:
        await self._session.execute(
            update(visual_audit_attempts_table)
            .where(
                visual_audit_attempts_table.c.id == attempt.id,
                visual_audit_attempts_table.c.organization_id == attempt.organization_id,
            )
            .values(**_values(attempt))
        )

    async def _to_domain(self, row) -> VisualAuditAttempt:
        photo_rows = (
            await self._session.execute(
                select(visual_audit_photos_table)
                .where(visual_audit_photos_table.c.attempt_id == row.id)
                .order_by(visual_audit_photos_table.c.pair_index, visual_audit_photos_table.c.phase.desc())
            )
        ).all()
        pairs: dict[int, dict[str, UUID]] = {}
        for photo in photo_rows:
            pairs.setdefault(photo.pair_index, {})[photo.phase] = photo.media_asset_id
        return VisualAuditAttempt(
            id=row.id,
            organization_id=row.organization_id,
            report_id=row.report_id,
            report_revision_id=row.report_revision_id,
            visit_id=row.visit_id,
            photo_pairs=[PhotoPair(before_asset_id=pair["before"], after_asset_id=pair["after"]) for _, pair in sorted(pairs.items())],
            work_description=row.work_description,
            amount_cents=row.amount_cents,
            currency=row.currency,
            provided_price_usd=Decimal(row.provided_price_usd) if row.provided_price_usd is not None else None,
            usd_rub_rate=Decimal(row.usd_rub_rate),
            usd_rub_rate_date=row.usd_rub_rate_date,
            usd_rub_rate_source=row.usd_rub_rate_source,
            status=row.status,
            result=row.result,
            model=row.model,
            prompt_tokens=row.prompt_tokens,
            completion_tokens=row.completion_tokens,
            cost_usd=Decimal(row.cost_usd) if row.cost_usd is not None else None,
            latency_ms=row.latency_ms,
            failure_code=row.failure_code,
            created_at=row.created_at,
            started_at=row.started_at,
            completed_at=row.completed_at,
            acknowledged_at=row.acknowledged_at,
            acknowledged_by=row.acknowledged_by,
            acknowledgement_reason=row.acknowledgement_reason,
        )


def _values(attempt: VisualAuditAttempt) -> dict:
    return {
        "id": attempt.id,
        "organization_id": attempt.organization_id,
        "report_id": attempt.report_id,
        "report_revision_id": attempt.report_revision_id,
        "visit_id": attempt.visit_id,
        "status": attempt.status,
        "work_description": attempt.work_description,
        "amount_cents": attempt.amount_cents,
        "currency": attempt.currency,
        "provided_price_usd": attempt.provided_price_usd,
        "usd_rub_rate": attempt.usd_rub_rate,
        "usd_rub_rate_date": attempt.usd_rub_rate_date,
        "usd_rub_rate_source": attempt.usd_rub_rate_source,
        "result": attempt.result,
        "model": attempt.model,
        "prompt_tokens": attempt.prompt_tokens,
        "completion_tokens": attempt.completion_tokens,
        "cost_usd": attempt.cost_usd,
        "latency_ms": attempt.latency_ms,
        "failure_code": attempt.failure_code,
        "created_at": attempt.created_at,
        "started_at": attempt.started_at,
        "completed_at": attempt.completed_at,
        "acknowledged_at": attempt.acknowledged_at,
        "acknowledged_by": attempt.acknowledged_by,
        "acknowledgement_reason": attempt.acknowledgement_reason,
    }
