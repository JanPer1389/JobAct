"""Report fulfillment workflow states and allowed transitions.

The live path is `COLLECTING_EVIDENCE -> DRAFTING_PENDING -> REVIEW_PENDING ->
SIGNATURE_PENDING -> FINALIZATION_PENDING -> PDF_PENDING -> COMPLETED`,
with `MANUAL_INPUT_REQUIRED` for generic retry exhaustion and `FAILED` for a
terminal, client-visible AI failure.
"""

from __future__ import annotations

from enum import StrEnum


class WorkflowState(StrEnum):
    COLLECTING_EVIDENCE = "COLLECTING_EVIDENCE"
    TRANSCRIPTION_PENDING = "TRANSCRIPTION_PENDING"
    DRAFTING_PENDING = "DRAFTING_PENDING"
    REVIEW_PENDING = "REVIEW_PENDING"
    SIGNATURE_PENDING = "SIGNATURE_PENDING"
    FINALIZATION_PENDING = "FINALIZATION_PENDING"
    PDF_PENDING = "PDF_PENDING"
    COMPLETED = "COMPLETED"
    MANUAL_INPUT_REQUIRED = "MANUAL_INPUT_REQUIRED"
    FAILED = "FAILED"


TERMINAL_STATES = frozenset(
    {WorkflowState.COMPLETED, WorkflowState.MANUAL_INPUT_REQUIRED, WorkflowState.FAILED}
)

# Explicit forward-only transition map -- any transition not listed here
# is rejected by WorkflowRun.transition_to(). MANUAL_INPUT_REQUIRED is
# reachable from every non-terminal state (retry exhaustion can happen
# at any step), never a *source* state -- resuming a parked run is a
# manual, out-of-band operation not modeled as a normal transition.
ALLOWED_TRANSITIONS: dict[WorkflowState, frozenset[WorkflowState]] = {
    WorkflowState.COLLECTING_EVIDENCE: frozenset(
        {WorkflowState.DRAFTING_PENDING, WorkflowState.MANUAL_INPUT_REQUIRED}
    ),
    WorkflowState.TRANSCRIPTION_PENDING: frozenset(
        {WorkflowState.DRAFTING_PENDING, WorkflowState.MANUAL_INPUT_REQUIRED}
    ),
    WorkflowState.DRAFTING_PENDING: frozenset(
        {
            WorkflowState.REVIEW_PENDING,
            WorkflowState.MANUAL_INPUT_REQUIRED,
            WorkflowState.FAILED,
        }
    ),
    WorkflowState.REVIEW_PENDING: frozenset(
        {WorkflowState.SIGNATURE_PENDING, WorkflowState.MANUAL_INPUT_REQUIRED}
    ),
    WorkflowState.SIGNATURE_PENDING: frozenset(
        {WorkflowState.FINALIZATION_PENDING, WorkflowState.MANUAL_INPUT_REQUIRED}
    ),
    WorkflowState.FINALIZATION_PENDING: frozenset(
        {WorkflowState.PDF_PENDING, WorkflowState.MANUAL_INPUT_REQUIRED}
    ),
    WorkflowState.PDF_PENDING: frozenset(
        {WorkflowState.COMPLETED, WorkflowState.MANUAL_INPUT_REQUIRED}
    ),
    WorkflowState.COMPLETED: frozenset(),
    WorkflowState.MANUAL_INPUT_REQUIRED: frozenset(),
    WorkflowState.FAILED: frozenset(),
}
