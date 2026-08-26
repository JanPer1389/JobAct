"""Append-only audit trail for individual step attempts within a
`WorkflowRun` -- separate from the run's own retry/state bookkeeping,
purely for observability (what happened, when, with what input/output).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from jobact.shared.infrastructure.postgres.workflow_tables import workflow_steps_table


class WorkflowStepRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        id: UUID,
        run_id: UUID,
        step: str,
        status: str,
        attempt: int,
        input_data: dict[str, Any] | None,
        output_data: dict[str, Any] | None,
        error: str | None,
        started_at: datetime,
        finished_at: datetime | None,
    ) -> None:
        await self._session.execute(
            insert(workflow_steps_table).values(
                id=id,
                run_id=run_id,
                step=step,
                status=status,
                attempt=attempt,
                input=input_data,
                output=output_data,
                error=error,
                started_at=started_at,
                finished_at=finished_at,
            )
        )
