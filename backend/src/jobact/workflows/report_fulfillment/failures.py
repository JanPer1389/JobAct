from __future__ import annotations

from dataclasses import dataclass

import httpx

AI_ANALYSIS_TIMEOUT = "AI_ANALYSIS_TIMEOUT"
AI_PROVIDERS_UNAVAILABLE = "AI_PROVIDERS_UNAVAILABLE"


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
    return None


def _is_timeout(error: Exception) -> bool:
    return isinstance(error, (TimeoutError, httpx.TimeoutException))
