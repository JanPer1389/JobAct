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
from typing import Any
from uuid import UUID

from jobact.shared.domain.aggregate import AggregateRoot
from jobact.workflows.report_fulfillment.events import (
    TranscriptionDispatchRequested,
    WorkflowStepDispatchRequested,
)
from jobact.workflows.report_fulfillment.states import (
    ALLOWED_TRANSITIONS,
    WorkflowState,
)


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
        input_data: dict[str, Any],
        claimed_at: datetime | None = None,
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
        self.input_data = input_data
        self.claimed_at = claimed_at

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
        input_data: dict[str, Any] | None = None,
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
            input_data=input_data or {},
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
        self.claimed_at = None
        self.state_version += 1

    def claim_attempt(self, *, now: datetime) -> None:
        """Claim exclusive execution of the current pending step.

        Sets `claimed_at` and bumps `state_version`, without changing
        `state`/`attempt`/`last_error`. `state` alone can't mark "already
        being worked on" because the run only leaves its pending state once
        the external call (e.g. an AI provider request) finishes -- exactly
        the window this claim protects. Callers must check `claimed_at is
        not None` themselves before claiming (this method does not
        re-check it) and must treat a `WorkflowConcurrencyError` from the
        repository's compare-and-swap save() as "someone else already
        claimed this," not as an error to propagate -- a concurrent or
        duplicate dispatch of the same pending step (at-least-once
        delivery) must not re-run the external call.
        """
        self.claimed_at = now
        self.state_version += 1

    def can_claim(self, *, now: datetime, lease_seconds: int) -> bool:
        if self.claimed_at is None:
            return True
        return self.claimed_at + timedelta(seconds=lease_seconds) <= now

    def request_dispatch(self) -> None:
        """Ask for the current state's step to be executed asynchronously.

        Call once, right after `start()` or a `transition_to()` that
        moves the run into a pending state a worker must act on.
        """
        event_type = (
            TranscriptionDispatchRequested
            if self.state == WorkflowState.TRANSCRIPTION_PENDING
            else WorkflowStepDispatchRequested
        )
        event_kwargs: dict[str, Any] = {}
        if event_type is TranscriptionDispatchRequested:
            transcription = self.input_data.get("transcription")
            media_asset_id = (
                transcription.get("media_asset_id")
                if isinstance(transcription, dict)
                else None
            )
            if not isinstance(media_asset_id, str):
                raise ValueError("Transcription dispatch requires an audio media asset.")
            event_kwargs = {
                "media_asset_id": UUID(media_asset_id),
                "not_before": self.next_retry_at,
            }
        self._record_event(
            event_type(
                aggregate_id=self.id,
                organization_id=self.organization_id,
                workflow_type=self.workflow_type,
                subject_id=self.subject_id,
                state=self.state.value,
                **event_kwargs,
            )
        )

    def resume_to(self, target_state: WorkflowState) -> None:
        """Resume a parked or explicitly failed run into `target_state`.

        Resuming is deliberately outside `ALLOWED_TRANSITIONS`:
        `MANUAL_INPUT_REQUIRED` is terminal for the workflow itself, and
        leaving it is an explicit human-initiated act (a manual edit, or
        a retry), not a normal forward transition.
        """
        if self.state not in {
            WorkflowState.MANUAL_INPUT_REQUIRED,
            WorkflowState.FAILED,
        }:
            raise InvalidWorkflowTransitionError(f"Cannot resume from {self.state}.")
        self.state = target_state
        self.attempt = 0
        self.next_retry_at = None
        self.last_error = None
        self.claimed_at = None
        self.state_version += 1

    def fail(self, *, code: str, now: datetime) -> None:
        """Finish an asynchronous step with a safe, client-visible error code."""
        del now  # Kept in the command signature for consistent domain audit semantics.
        self.state = WorkflowState.FAILED
        self.attempt += 1
        self.next_retry_at = None
        self.last_error = code
        self.state_version += 1

    def resume_manual_review(self) -> None:
        """Resume a drafting failure after a human supplies the report revision."""
        self.resume_to(WorkflowState.REVIEW_PENDING)

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
        self.claimed_at = None
        if self.attempt >= max_attempts:
            self.state = WorkflowState.MANUAL_INPUT_REQUIRED
            self.next_retry_at = None
        else:
            self.next_retry_at = now + timedelta(
                seconds=backoff_base_seconds * (2**self.attempt)
            )
        self.state_version += 1
