from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import Callable
from threading import Lock
from typing import Any

from jobact.shared.application.ports import SpeechTranscription
from jobact.workflows.report_fulfillment.activities.transcribe_audio import (
    TranscriptionUnavailableError,
)


def _default_model_factory(model_name: str, **kwargs):
    from faster_whisper import WhisperModel  # type: ignore[import-not-found]

    return WhisperModel(model_name, **kwargs)


class FasterWhisperTranscriber:
    def __init__(
        self, model_factory: Callable[..., Any] = _default_model_factory
    ) -> None:
        self._model_factory = model_factory
        self._model = None
        self._model_lock = Lock()

    async def transcribe(
        self, data: bytes, content_type: str
    ) -> SpeechTranscription:
        return await asyncio.to_thread(self._transcribe, data, content_type)

    def _get_model(self):
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    self._model = self._model_factory(
                        "small", device="cpu", compute_type="int8"
                    )
        return self._model

    def _transcribe(self, data: bytes, content_type: str) -> SpeechTranscription:
        suffix = ".webm" if content_type == "audio/webm" else ".mp4"
        path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                handle.write(data)
                path = handle.name
            segments, info = self._get_model().transcribe(
                path,
                task="transcribe",
                vad_filter=True,
                beam_size=5,
            )
            text = "".join(segment.text for segment in segments)
            return SpeechTranscription(text=text, language=info.language)
        except Exception as exc:
            raise TranscriptionUnavailableError from exc
        finally:
            if path is not None:
                try:
                    os.unlink(path)
                except FileNotFoundError:
                    pass
