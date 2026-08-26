"""`WorkflowRun` repository -- the `save()` compare-and-swap is the
actual optimistic-locking mechanism (Postgres has no built-in
primitive for this): `UPDATE ... WHERE id = ? AND state_version = ?`
using the version the run had when it was LOADED, not its new value.
Zero rows affected means someone else updated the run concurrently --
raised as `WorkflowConcurrencyError` rather than silently overwritten.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from jobact.shared.infrastructure.postgres.workflow_tables import workflow_runs_table
from jobact.workflows.report_fulfillment.run import WorkflowRun
from jobact.workflows.report_fulfillment.states import WorkflowState


class WorkflowConcurrencyError(Exception):
    pass


class WorkflowRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, run: WorkflowRun) -> None:
        await self._session.execute(
            insert(workflow_runs_table).values(
                id=run.id,
                organization_id=run.organization_id,
                workflow_type=run.workflow_type,
                subject_id=run.subject_id,
                state=run.state.value,
                attempt=run.attempt,
                next_retry_at=run.next_retry_at,
                last_error=run.last_error,
                state_version=run.state_version,
                correlation_id=run.correlation_id,
                input_data=run.input_data,
            )
        )

    async def get_by_id(self, run_id: UUID) -> WorkflowRun | None:
        result = await self._session.execute(
            select(workflow_runs_table).where(workflow_runs_table.c.id == run_id)
        )
        row = result.first()
        if row is None:
            return None
        return _to_domain(row)

    async def get_by_subject(self, subject_id: UUID) -> WorkflowRun | None:
        result = await self._session.execute(
            select(workflow_runs_table).where(
                workflow_runs_table.c.subject_id == subject_id
            )
        )
        row = result.first()
        if row is None:
            return None
        return _to_domain(row)

    async def save(self, run: WorkflowRun, *, expected_version: int) -> None:
        result = await self._session.execute(
            update(workflow_runs_table)
            .where(
                workflow_runs_table.c.id == run.id,
                workflow_runs_table.c.state_version == expected_version,
            )
            .values(
                state=run.state.value,
                attempt=run.attempt,
                next_retry_at=run.next_retry_at,
                last_error=run.last_error,
                state_version=run.state_version,
            )
        )
        if result.rowcount == 0:
            raise WorkflowConcurrencyError(
                f"WorkflowRun {run.id} was modified concurrently "
                f"(expected state_version={expected_version})."
            )


def _to_domain(row) -> WorkflowRun:
    return WorkflowRun(
        id=row.id,
        organization_id=row.organization_id,
        workflow_type=row.workflow_type,
        subject_id=row.subject_id,
        state=WorkflowState(row.state),
        attempt=row.attempt,
        next_retry_at=row.next_retry_at,
        last_error=row.last_error,
        state_version=row.state_version,
        correlation_id=row.correlation_id,
        input_data=row.input_data,
    )
