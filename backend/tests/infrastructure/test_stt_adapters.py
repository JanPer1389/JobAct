from pathlib import Path
from types import SimpleNamespace

import pytest

from jobact.shared.infrastructure.stt.faster_whisper import FasterWhisperTranscriber
from jobact.shared.infrastructure.stt.pyav_inspector import PyAvAudioInspector
from jobact.workflows.report_fulfillment.activities.transcribe_audio import (
    AudioInvalidError,
    AudioTooLongError,
)


class _Container:
    def __init__(self, *, format_name, audio, video=(), duration=2_000_000) -> None:
        self.format = SimpleNamespace(name=format_name)
        self.streams = SimpleNamespace(audio=list(audio), video=list(video))
        self.duration = duration
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _stream(codec: str, *, duration=2000, time_base=0.001):
    return SimpleNamespace(
        codec_context=SimpleNamespace(name=codec),
        duration=duration,
        time_base=time_base,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content_type", "format_name", "codec", "expected_container"),
    [
        ("audio/webm", "matroska,webm", "opus", "webm"),
        ("audio/mp4", "mov,mp4,m4a,3gp,3g2,mj2", "aac", "mp4"),
    ],
)
async def test_pyav_inspector_accepts_only_matching_supported_audio(
    content_type, format_name, codec, expected_container
) -> None:
    container = _Container(format_name=format_name, audio=[_stream(codec)])
    inspector = PyAvAudioInspector(open_container=lambda _: container)

    result = await inspector.inspect(b"audio", content_type)

    assert result.container == expected_container
    assert result.codec == codec
    assert result.duration_seconds == 2.0
    assert container.closed is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "container",
    [
        _Container(format_name="matroska,webm", audio=[]),
        _Container(
            format_name="matroska,webm",
            audio=[_stream("opus"), _stream("opus")],
        ),
        _Container(
            format_name="matroska,webm", audio=[_stream("opus")], video=[object()]
        ),
        _Container(format_name="mov,mp4", audio=[_stream("opus")]),
        _Container(format_name="matroska,webm", audio=[_stream("aac")]),
        _Container(
            format_name="matroska,webm", audio=[_stream("opus", duration=100)]
        ),
    ],
)
async def test_pyav_inspector_rejects_malformed_or_mismatched_audio(container) -> None:
    inspector = PyAvAudioInspector(open_container=lambda _: container)

    with pytest.raises(AudioInvalidError):
        await inspector.inspect(b"audio", "audio/webm")


@pytest.mark.asyncio
async def test_pyav_inspector_rejects_audio_longer_than_ten_minutes() -> None:
    container = _Container(
        format_name="matroska,webm", audio=[_stream("opus", duration=600_001)]
    )

    with pytest.raises(AudioTooLongError):
        await PyAvAudioInspector(open_container=lambda _: container).inspect(
            b"audio", "audio/webm"
        )


@pytest.mark.asyncio
async def test_faster_whisper_loads_once_consumes_segments_and_removes_temp_file() -> None:
    factory_calls: list[tuple[str, dict]] = []
    transcribe_calls: list[tuple[str, dict]] = []

    class Model:
        def transcribe(self, path: str, **kwargs):
            transcribe_calls.append((path, kwargs))
            assert Path(path).read_bytes() == b"voice"
            return iter(
                [SimpleNamespace(text="Привет, "), SimpleNamespace(text="world!")]
            ), SimpleNamespace(language="ru")

    def factory(model_name: str, **kwargs):
        factory_calls.append((model_name, kwargs))
        return Model()

    adapter = FasterWhisperTranscriber(model_factory=factory)
    first = await adapter.transcribe(b"voice", "audio/webm")
    second = await adapter.transcribe(b"voice", "audio/webm")

    assert first.text == "Привет, world!"
    assert first.language == "ru"
    assert second == first
    assert factory_calls == [("small", {"device": "cpu", "compute_type": "int8"})]
    assert [call[1] for call in transcribe_calls] == [
        {"task": "transcribe", "vad_filter": True, "beam_size": 5},
        {"task": "transcribe", "vad_filter": True, "beam_size": 5},
    ]
    assert all(not Path(path).exists() for path, _ in transcribe_calls)
