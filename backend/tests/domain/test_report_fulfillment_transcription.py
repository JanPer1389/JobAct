from datetime import UTC, datetime
from uuid import uuid4

import pytest

from jobact.workflows.report_fulfillment.run import (
    InvalidWorkflowTransitionError,
    WorkflowRun,
)
from jobact.workflows.report_fulfillment.states import WorkflowState


def _run(*, state: WorkflowState) -> WorkflowRun:
    return WorkflowRun.start(
        id=uuid4(),
        organization_id=uuid4(),
        workflow_type="report_fulfillment",
        subject_id=uuid4(),
        correlation_id=uuid4(),
        initial_state=state,
    )


def test_transcription_pending_can_progress_to_drafting_or_manual_recovery() -> None:
    run = _run(state=WorkflowState.TRANSCRIPTION_PENDING)

    run.transition_to(WorkflowState.DRAFTING_PENDING)

    assert run.state is WorkflowState.DRAFTING_PENDING

    parked = _run(state=WorkflowState.TRANSCRIPTION_PENDING)
    parked.transition_to(WorkflowState.MANUAL_INPUT_REQUIRED)

    assert parked.state is WorkflowState.MANUAL_INPUT_REQUIRED
    with pytest.raises(InvalidWorkflowTransitionError):
        parked.transition_to(WorkflowState.DRAFTING_PENDING)


def test_transition_clears_an_in_flight_claim() -> None:
    run = _run(state=WorkflowState.DRAFTING_PENDING)
    run.claim_attempt(now=datetime(2026, 8, 28, tzinfo=UTC))

    run.transition_to(WorkflowState.REVIEW_PENDING)

    assert run.claimed_at is None
