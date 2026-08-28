from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from jobact.apps.api.routers.reports import transcription_from_workflow
from jobact.contracts.http.v1.media import RequestMediaUploadRequest
from jobact.contracts.http.v1.reports import CreateReportRequest
from jobact.workflows.report_fulfillment.run import WorkflowRun
from jobact.workflows.report_fulfillment.states import WorkflowState


def test_create_report_requires_exactly_one_typed_input() -> None:
    visit_id = uuid4()
    audio_media_asset_id = uuid4()

    typed = CreateReportRequest(
        visit_id=visit_id,
        raw_notes="Replaced a kitchen faucet and verified water flow.",
    )
    audio = CreateReportRequest(
        visit_id=visit_id, audio_media_asset_id=audio_media_asset_id
    )

    assert typed.raw_notes == "Replaced a kitchen faucet and verified water flow."
    assert typed.audio_media_asset_id is None
    assert audio.raw_notes is None
    assert audio.audio_media_asset_id == audio_media_asset_id
    with pytest.raises(ValidationError):
        CreateReportRequest(
            visit_id=visit_id,
            raw_notes="Replaced a kitchen faucet and verified water flow.",
            audio_media_asset_id=audio_media_asset_id,
        )
    with pytest.raises(ValidationError):
        CreateReportRequest(visit_id=visit_id)


def test_create_report_rejects_notes_that_are_only_whitespace() -> None:
    with pytest.raises(ValidationError):
        CreateReportRequest(visit_id=uuid4(), raw_notes=" " * 20)


def test_audio_upload_contract_accepts_only_visit_bound_supported_audio() -> None:
    visit_id = uuid4()
    request = RequestMediaUploadRequest(
        content_type="audio/webm",
        byte_size=25 * 1024 * 1024,
        sha256="a" * 64,
        kind="audio",
        visit_id=visit_id,
    )

    assert request.visit_id == visit_id
    for invalid in (
        {"content_type": "audio/wav"},
        {"byte_size": 25 * 1024 * 1024 + 1},
        {"visit_id": None},
        {"phase": "before"},
        {"report_id": uuid4()},
    ):
        payload = request.model_dump()
        payload.update(invalid)
        with pytest.raises(ValidationError):
            RequestMediaUploadRequest(**payload)


@pytest.mark.parametrize(
    ("state", "claimed_at", "input_data", "expected_status"),
    [
        (
            WorkflowState.TRANSCRIPTION_PENDING,
            None,
            {"transcription": {"media_asset_id": str(uuid4())}},
            "queued",
        ),
        (
            WorkflowState.TRANSCRIPTION_PENDING,
            datetime(2026, 8, 28, tzinfo=UTC),
            {"transcription": {"media_asset_id": str(uuid4())}},
            "running",
        ),
        (
            WorkflowState.DRAFTING_PENDING,
            None,
            {
                "transcription": {
                    "media_asset_id": str(uuid4()),
                    "transcript": "Replaced the damaged valve.",
                    "detected_language": "en",
                }
            },
            "completed",
        ),
        (
            WorkflowState.MANUAL_INPUT_REQUIRED,
            None,
            {"transcription": {"media_asset_id": str(uuid4())}},
            "failed",
        ),
    ],
)
def test_transcription_response_is_derived_from_workflow_data(
    state, claimed_at, input_data, expected_status
) -> None:
    run = WorkflowRun(
        id=uuid4(),
        organization_id=uuid4(),
        workflow_type="report_fulfillment",
        subject_id=uuid4(),
        state=state,
        attempt=0,
        next_retry_at=None,
        last_error=None,
        state_version=0,
        correlation_id=uuid4(),
        input_data=input_data,
        claimed_at=claimed_at,
    )

    response = transcription_from_workflow(run)

    assert response is not None
    assert response.status == expected_status
    assert response.media_asset_id == UUID(
        input_data["transcription"]["media_asset_id"]
    )
    assert response.transcript == input_data["transcription"].get("transcript")
    assert response.detected_language == input_data["transcription"].get(
        "detected_language"
    )
