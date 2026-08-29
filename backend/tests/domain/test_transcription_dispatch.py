from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from jobact.shared.infrastructure.postgres.outbox_publisher import stream_for_event
from jobact.workflows.report_fulfillment.events import (
    TranscriptionDispatchRequested,
    WorkflowStepDispatchRequested,
)
from jobact.workflows.report_fulfillment.run import WorkflowRun
from jobact.workflows.report_fulfillment.states import WorkflowState


def _run() -> WorkflowRun:
    return WorkflowRun.start(
        id=uuid4(),
        organization_id=uuid4(),
        workflow_type="report_fulfillment",
        subject_id=uuid4(),
        correlation_id=uuid4(),
        initial_state=WorkflowState.TRANSCRIPTION_PENDING,
        input_data={"transcription": {"media_asset_id": str(uuid4())}},
    )


def test_transcription_dispatch_uses_dedicated_event_and_stream_without_binary() -> None:
    run = _run()

    run.request_dispatch()

    events = run.pull_events()
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, TranscriptionDispatchRequested)
    assert not isinstance(event, WorkflowStepDispatchRequested)
    assert event.subject_id == run.subject_id
    assert event.media_asset_id == UUID(run.input_data["transcription"]["media_asset_id"])
    assert not hasattr(event, "audio")
    assert stream_for_event(type(event).__name__, "WorkflowRun") == "outbox.Transcription"
    assert stream_for_event("WorkflowStepDispatchRequested", "WorkflowRun") == (
        "outbox.WorkflowRun"
    )

def test_claim_lease_blocks_duplicates_but_expired_claim_can_be_recovered() -> None:
    now = datetime(2026, 8, 28, 12, tzinfo=UTC)
    run = _run()
    run.claim_attempt(now=now)

    assert run.can_claim(now=now + timedelta(minutes=14), lease_seconds=900) is False
    assert run.can_claim(now=now + timedelta(minutes=15), lease_seconds=900) is True


def test_retry_failure_releases_claim_and_parks_on_third_attempt() -> None:
    now = datetime(2026, 8, 28, 12, tzinfo=UTC)
    run = _run()

    for attempt in range(1, 4):
        run.claim_attempt(now=now)
        run.record_failure(error="TRANSCRIPTION_UNAVAILABLE", now=now)
        assert run.claimed_at is None
        assert run.attempt == attempt

    assert run.state is WorkflowState.MANUAL_INPUT_REQUIRED
    assert run.next_retry_at is None


def test_only_stt_worker_registers_transcription_handler() -> None:
    from jobact.apps.stt_worker.__main__ import HANDLER_REGISTRY as STT_HANDLERS
    from jobact.apps.worker.__main__ import HANDLER_REGISTRY as GENERAL_HANDLERS

    assert set(STT_HANDLERS) == {"TranscriptionDispatchRequested"}
    assert "TranscriptionDispatchRequested" not in GENERAL_HANDLERS
