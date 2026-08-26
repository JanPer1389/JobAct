"""Executes one workflow step against a `WorkflowRun`, with retry/
backoff/park-on-exhaustion -- the actual engine `Report.mark_ready_
for_signature()` etc. don't provide; the report aggregate only guards
its OWN invariants, this decides what happens when an external
activity (AI drafting, PDF rendering) fails.

Deliberately generic over the activity's own input/output shape (a
plain `dict` in, `dict` out) -- concrete activities (Task 4.4/4.5) are
async callables the caller constructs; this runner only cares whether
the callable raised or returned.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from jobact.contracts.workflow.v1.activity import ActivityError
from jobact.shared.application.ports import Clock, IdGenerator
from jobact.shared.application.uow import UnitOfWork
from jobact.workflows.report_fulfillment.repository import WorkflowRunRepository
from jobact.workflows.report_fulfillment.states import WorkflowState
from jobact.workflows.report_fulfillment.step_repository import WorkflowStepRepository

_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 1.0


def sanitize_error(exc: Exception) -> ActivityError:
    """Turns a raised exception into a safe-to-store `ActivityError`.

    Only the exception's TYPE NAME is kept -- never `str(exc)` or
    `exc.args`, which could contain API keys, raw request/response
    bodies, or other data that shouldn't end up in `workflow_runs.
    last_error` (a column later tasks may surface to end users).
    """
    return ActivityError(
        error_type=type(exc).__name__,
        detail=f"{type(exc).__name__} occurred while executing the workflow step.",
    )


class WorkflowRunner:
    def __init__(
        self,
        uow: UnitOfWork,
        clock: Clock,
        id_generator: IdGenerator,
        max_attempts: int = _MAX_ATTEMPTS,
        backoff_base_seconds: float = _BACKOFF_BASE_SECONDS,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator
        self._max_attempts = max_attempts
        self._backoff_base_seconds = backoff_base_seconds

    async def run_step(
        self,
        run_id: UUID,
        step_name: str,
        activity: Callable[[], Awaitable[dict]],
        *,
        on_success_transition_to: WorkflowState | None = None,
    ) -> dict | None:
        """Executes `activity()` once. On success, records the step,
        clears retry bookkeeping, and (if given) transitions the run's
        state. On failure, records the step, and either schedules a
        retry (`next_retry_at`) or parks the run in
        `MANUAL_INPUT_REQUIRED` if `max_attempts` is reached.

        Returns the activity's result dict on success, `None` on
        failure (the caller decides what "the report itself is not
        blocked" means for its own HTTP-facing state -- this runner
        only owns the workflow run's own bookkeeping).
        """
        started_at = self._clock.now()

        async with self._uow:
            run_repo = WorkflowRunRepository(self._uow.session)
            run = await run_repo.get_by_id(run_id)
            if run is None:
                raise ValueError(f"WorkflowRun {run_id} does not exist.")
            expected_version = run.state_version

            try:
                result = await activity()
            except Exception as exc:  # noqa: BLE001 -- intentionally broad: any
                # activity failure (AI/PDF/network/etc.) must be caught here,
                # sanitized, and turned into retry/park bookkeeping rather
                # than propagating and crashing the worker loop.
                activity_error = sanitize_error(exc)
                run.record_failure(
                    error=activity_error.detail,
                    now=started_at,
                    max_attempts=self._max_attempts,
                    backoff_base_seconds=self._backoff_base_seconds,
                )
                await run_repo.save(run, expected_version=expected_version)
                await WorkflowStepRepository(self._uow.session).record(
                    id=self._id_generator.new_id(),
                    run_id=run.id,
                    step=step_name,
                    status="failed",
                    attempt=run.attempt,
                    input_data=None,
                    output_data=None,
                    error=activity_error.detail,
                    started_at=started_at,
                    finished_at=self._clock.now(),
                )
                self._uow.register(run)
                return None

            run.record_step_success()
            if on_success_transition_to is not None:
                run.transition_to(on_success_transition_to)
            await run_repo.save(run, expected_version=expected_version)
            await WorkflowStepRepository(self._uow.session).record(
                id=self._id_generator.new_id(),
                run_id=run.id,
                step=step_name,
                status="succeeded",
                attempt=run.attempt,
                input_data=None,
                output_data=result,
                error=None,
                started_at=started_at,
                finished_at=self._clock.now(),
            )
            self._uow.register(run)
            return result
