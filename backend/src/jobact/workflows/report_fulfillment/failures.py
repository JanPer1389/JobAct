from __future__ import annotations

from dataclasses import dataclass

import httpx

AI_ANALYSIS_TIMEOUT = "AI_ANALYSIS_TIMEOUT"
AI_PROVIDERS_UNAVAILABLE = "AI_PROVIDERS_UNAVAILABLE"
AUDIO_INVALID = "AUDIO_INVALID"
AUDIO_TOO_LARGE = "AUDIO_TOO_LARGE"
AUDIO_TOO_LONG = "AUDIO_TOO_LONG"
TRANSCRIPTION_EMPTY = "TRANSCRIPTION_EMPTY"
TRANSCRIPTION_UNAVAILABLE = "TRANSCRIPTION_UNAVAILABLE"


@dataclass(frozen=True)
class WorkflowFailure:
    code: str
    http_status: int
    message: str
    retryable: bool


def classify_analysis_failures(errors: list[Exception]) -> WorkflowFailure:
    if errors and all(_is_timeout(error) for error in errors):
        return WorkflowFailure(
            code=AI_ANALYSIS_TIMEOUT,
            http_status=504,
            message="The AI analysis timed out. Please try again.",
            retryable=True,
        )
    return WorkflowFailure(
        code=AI_PROVIDERS_UNAVAILABLE,
        http_status=502,
        message="The AI analysis could not be completed. Please try again.",
        retryable=True,
    )


def failure_from_code(code: str | None) -> WorkflowFailure | None:
    if code == AI_ANALYSIS_TIMEOUT:
        return classify_analysis_failures([TimeoutError()])
    if code == AI_PROVIDERS_UNAVAILABLE:
        return classify_analysis_failures([RuntimeError()])
    transcription_failures = {
        AUDIO_INVALID: WorkflowFailure(
            code=AUDIO_INVALID,
            http_status=422,
            message="The recording is not valid WebM/Opus or MP4/AAC audio.",
            retryable=False,
        ),
        AUDIO_TOO_LARGE: WorkflowFailure(
            code=AUDIO_TOO_LARGE,
            http_status=413,
            message="The recording exceeds the 25 MiB limit.",
            retryable=False,
        ),
        AUDIO_TOO_LONG: WorkflowFailure(
            code=AUDIO_TOO_LONG,
            http_status=422,
            message="The recording exceeds the 10 minute limit.",
            retryable=False,
        ),
        TRANSCRIPTION_EMPTY: WorkflowFailure(
            code=TRANSCRIPTION_EMPTY,
            http_status=422,
            message="No speech could be transcribed from the recording.",
            retryable=True,
        ),
        TRANSCRIPTION_UNAVAILABLE: WorkflowFailure(
            code=TRANSCRIPTION_UNAVAILABLE,
            http_status=503,
            message="Transcription is temporarily unavailable. Please try again.",
            retryable=True,
        ),
    }
    if code in transcription_failures:
        return transcription_failures[code]
    return None


def _is_timeout(error: Exception) -> bool:
    return isinstance(error, (TimeoutError, httpx.TimeoutException))
