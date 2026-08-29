from datetime import UTC, datetime
from uuid import uuid4

import pytest

from jobact.shared.application.ports import AudioInspection, SpeechTranscription
from jobact.workflows.report_fulfillment.activities.transcribe_audio import (
    AudioInvalidError,
    AudioTooLongError,
    ClaimedTranscription,
    TranscribeAudioActivity,
    TranscriptionUnavailableError,
)
from jobact.workflows.report_fulfillment.failures import (
    AUDIO_INVALID,
    AUDIO_TOO_LARGE,
    AUDIO_TOO_LONG,
    TRANSCRIPTION_EMPTY,
    TRANSCRIPTION_UNAVAILABLE,
)
from tests.fakes import FakeClock, FakeObjectStorage

NOW = datetime(2026, 8, 28, 12, tzinfo=UTC)


class FakeTranscriptionStore:
    def __init__(self, claim: ClaimedTranscription | None) -> None:
        self.claim = claim
        self.claim_calls = 0
        self.successes: list[dict] = []
        self.failures: list[dict] = []

    async def claim_transcription(self, *, report_id, run_id, now, lease_seconds):
        self.claim_calls += 1
        return self.claim

    async def complete_transcription(self, **kwargs) -> None:
        self.successes.append(kwargs)

    async def fail_transcription(self, **kwargs) -> None:
        self.failures.append(kwargs)

    async def heartbeat_transcription(self, **kwargs) -> None:
        return None


class FakeAudioInspector:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result or AudioInspection(
            container="webm", codec="opus", duration_seconds=4.25
        )
        self.error = error
        self.calls: list[tuple[bytes, str]] = []

    async def inspect(self, data: bytes, declared_content_type: str) -> AudioInspection:
        self.calls.append((data, declared_content_type))
        if self.error is not None:
            raise self.error
        return self.result


class FakeSpeechTranscriber:
    def __init__(
        self,
        result: SpeechTranscription | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or SpeechTranscription(text="Replaced valve.", language="en")
        self.error = error
        self.calls: list[tuple[bytes, str]] = []

    async def transcribe(
        self, data: bytes, content_type: str
    ) -> SpeechTranscription:
        self.calls.append((data, content_type))
        if self.error is not None:
            raise self.error
        return self.result


def _claim(*, byte_size: int = 10) -> ClaimedTranscription:
    return ClaimedTranscription(
        run_id=uuid4(),
        report_id=uuid4(),
        organization_id=uuid4(),
        visit_id=uuid4(),
        media_asset_id=uuid4(),
        storage_key="tenant/audio-id",
        content_type="audio/webm",
        byte_size=byte_size,
        correlation_id=uuid4(),
    )


def _activity(store, storage, inspector, transcriber) -> TranscribeAudioActivity:
    return TranscribeAudioActivity(
        store=store,
        object_storage=storage,
        audio_inspector=inspector,
        speech_transcriber=transcriber,
        clock=FakeClock(NOW),
        id_generator=type("Ids", (), {"new_id": lambda self: uuid4()})(),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("Replaced the damaged valve without leaks.", "en"),
        ("Заменил повреждённый клапан без утечек.", "ru"),
    ],
)
async def test_transcription_persists_exact_text_and_drafting_snapshot(
    text, language, caplog
) -> None:
    claim = _claim()
    store = FakeTranscriptionStore(claim)
    storage = FakeObjectStorage()
    audio = b"fake-audio"
    storage.put(claim.storage_key, audio, claim.content_type)
    inspector = FakeAudioInspector()
    transcriber = FakeSpeechTranscriber(
        SpeechTranscription(text=text, language=language)
    )

    await _activity(store, storage, inspector, transcriber).run(
        report_id=claim.report_id, run_id=claim.run_id
    )

    assert inspector.calls == [(audio, "audio/webm")]
    assert transcriber.calls == [(audio, "audio/webm")]
    assert store.failures == []
    assert len(store.successes) == 1
    success = store.successes[0]
    assert success["transcript"] == text
    assert success["detected_language"] == language
    assert success["step_metadata"] == {
        "container": "webm",
        "codec": "opus",
        "duration_seconds": 4.25,
        "transcript_chars": len(text),
        "detected_language": language,
    }
    assert audio not in repr(success).encode()
    assert text not in caplog.text
    assert repr(audio) not in caplog.text


@pytest.mark.asyncio
async def test_duplicate_delivery_does_not_download_or_transcribe() -> None:
    store = FakeTranscriptionStore(None)
    storage = FakeObjectStorage()
    inspector = FakeAudioInspector()
    transcriber = FakeSpeechTranscriber()

    await _activity(store, storage, inspector, transcriber).run(
        report_id=uuid4(), run_id=uuid4()
    )

    assert store.claim_calls == 1
    assert inspector.calls == []
    assert transcriber.calls == []
    assert store.successes == []
    assert store.failures == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("byte_size", "inspection_error", "transcription", "transcription_error", "code"),
    [
        (25 * 1024 * 1024 + 1, None, None, None, AUDIO_TOO_LARGE),
        (10, AudioInvalidError(), None, None, AUDIO_INVALID),
        (10, AudioTooLongError(), None, None, AUDIO_TOO_LONG),
        (10, None, SpeechTranscription(text="   ", language="en"), None, TRANSCRIPTION_EMPTY),
        (10, None, None, TranscriptionUnavailableError(), TRANSCRIPTION_UNAVAILABLE),
    ],
)
async def test_failures_are_persisted_as_safe_codes(
    byte_size, inspection_error, transcription, transcription_error, code
) -> None:
    claim = _claim(byte_size=byte_size)
    store = FakeTranscriptionStore(claim)
    storage = FakeObjectStorage()
    storage.put(claim.storage_key, b"fake-audio", claim.content_type)
    inspector = FakeAudioInspector(error=inspection_error)
    transcriber = FakeSpeechTranscriber(
        result=transcription, error=transcription_error
    )

    await _activity(store, storage, inspector, transcriber).run(
        report_id=claim.report_id, run_id=claim.run_id
    )

    assert store.successes == []
    assert len(store.failures) == 1
    assert store.failures[0]["error_code"] == code
    assert set(store.failures[0]) == {
        "run_id",
        "report_id",
        "error_code",
        "started_at",
        "finished_at",
        "step_id",
    }
