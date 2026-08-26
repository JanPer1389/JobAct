"""`WorkflowRun` -- the durable state machine tracking one report's
fulfillment (draft -> review -> signature -> finalization -> PDF).

Generic enough (`workflow_type`/`subject_id`) to describe any workflow
kind, but lives under `workflows/report_fulfillment/` per the plan's
own directory layout since this milestone only has one workflow.

Optimistic locking: `state_version` increments on every transition or
failure recorded. The REPOSITORY (not this aggregate) is responsible
for the actual compare-and-swap on save (`UPDATE ... WHERE id = ? AND
state_version = ?`) -- this class just tracks its own version in
memory so the repository knows what it started from.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from jobact.shared.domain.aggregate import AggregateRoot
from jobact.workflows.report_fulfillment.states import ALLOWED_TRANSITIONS, WorkflowState


class InvalidWorkflowTransitionError(Exception):
    pass


class WorkflowRun(AggregateRoot):
    def __init__(
        self,
        *,
        id: UUID,
        organization_id: UUID,
        workflow_type: str,
        subject_id: UUID,
        state: WorkflowState,
        attempt: int,
        next_retry_at: datetime | None,
        last_error: str | None,
        state_version: int,
        correlation_id: UUID,
    ) -> None:
        super().__init__()
        self.id = id
        self.organization_id = organization_id
        self.workflow_type = workflow_type
        self.subject_id = subject_id
        self.state = state
        self.attempt = attempt
        self.next_retry_at = next_retry_at
        self.last_error = last_error
        self.state_version = state_version
        self.correlation_id = correlation_id

    @classmethod
    def start(
        cls,
        *,
        id: UUID,
        organization_id: UUID,
        workflow_type: str,
        subject_id: UUID,
        correlation_id: UUID,
        initial_state: WorkflowState = WorkflowState.COLLECTING_EVIDENCE,
    ) -> WorkflowRun:
        return cls(
            id=id,
            organization_id=organization_id,
            workflow_type=workflow_type,
            subject_id=subject_id,
            state=initial_state,
            attempt=0,
            next_retry_at=None,
            last_error=None,
            state_version=0,
            correlation_id=correlation_id,
        )

    def transition_to(self, new_state: WorkflowState) -> None:
        allowed = ALLOWED_TRANSITIONS.get(self.state, frozenset())
        if new_state not in allowed:
            raise InvalidWorkflowTransitionError(
                f"Cannot transition from {self.state} to {new_state}."
            )
        self.state = new_state
        self.attempt = 0
        self.next_retry_at = None
        self.last_error = None
        self.state_version += 1

    def record_step_success(self) -> None:
        """Clears retry/error bookkeeping after a step succeeds, without
        changing state (the caller decides whether success also means a
        state transition, via `transition_to`).
        """
        self.attempt = 0
        self.next_retry_at = None
        self.last_error = None
        self.state_version += 1

    def record_failure(
        self,
        *,
        error: str,
        now: datetime,
        max_attempts: int = 3,
        backoff_base_seconds: float = 1.0,
    ) -> None:
        """Records a step failure. Parks the run in
        `MANUAL_INPUT_REQUIRED` once `attempt` reaches `max_attempts`;
        otherwise schedules `next_retry_at` with exponential backoff.

        `error` should already be a SAFE, non-leaking message (the
        caller's job -- e.g. an exception's type name, not its raw
        message/args, which could contain secrets or PII) before it
        reaches this method; this method does not sanitize it further.
        """
        self.attempt += 1
        self.last_error = error
        if self.attempt >= max_attempts:
            self.state = WorkflowState.MANUAL_INPUT_REQUIRED
            self.next_retry_at = None
        else:
            self.next_retry_at = now + timedelta(
                seconds=backoff_base_seconds * (2**self.attempt)
            )
        self.state_version += 1
