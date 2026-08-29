from __future__ import annotations

import asyncio
import io
from collections.abc import Callable
from typing import Any

from jobact.shared.application.ports import AudioInspection
from jobact.workflows.report_fulfillment.activities.transcribe_audio import (
    AudioInvalidError,
    AudioTooLongError,
)

_MIN_DURATION_SECONDS = 0.5
_MAX_DURATION_SECONDS = 600.0
_FORMAT_RULES = {
    "audio/webm": ("webm", "opus"),
    "audio/mp4": ("mp4", "aac"),
}


def _open_with_pyav(data: bytes):
    import av  # type: ignore[import-not-found]

    return av.open(io.BytesIO(data))


class PyAvAudioInspector:
    def __init__(
        self, open_container: Callable[[bytes], Any] = _open_with_pyav
    ) -> None:
        self._open_container = open_container

    async def inspect(
        self, data: bytes, declared_content_type: str
    ) -> AudioInspection:
        return await asyncio.to_thread(self._inspect, data, declared_content_type)

    def _inspect(self, data: bytes, declared_content_type: str) -> AudioInspection:
        if not data or declared_content_type not in _FORMAT_RULES:
            raise AudioInvalidError
        container = None
        try:
            container = self._open_container(data)
            audio_streams = list(container.streams.audio)
            if len(audio_streams) != 1 or list(container.streams.video):
                raise AudioInvalidError
            stream = audio_streams[0]
            format_name = str(container.format.name).lower().split(",")
            expected_container, expected_codec = _FORMAT_RULES[declared_content_type]
            codec = str(stream.codec_context.name).lower()
            if expected_container not in format_name or codec != expected_codec:
                raise AudioInvalidError
            duration_seconds = self._duration_seconds(container, stream)
            if duration_seconds > _MAX_DURATION_SECONDS:
                raise AudioTooLongError
            if duration_seconds < _MIN_DURATION_SECONDS:
                raise AudioInvalidError
            return AudioInspection(
                container=expected_container,
                codec=expected_codec,
                duration_seconds=duration_seconds,
            )
        except (AudioInvalidError, AudioTooLongError):
            raise
        except Exception as exc:
            raise AudioInvalidError from exc
        finally:
            if container is not None:
                container.close()

    @staticmethod
    def _duration_seconds(container, stream) -> float:
        if stream.duration is not None and stream.time_base is not None:
            return float(stream.duration * stream.time_base)
        if container.duration is not None:
            return float(container.duration) / 1_000_000
        raise AudioInvalidError
