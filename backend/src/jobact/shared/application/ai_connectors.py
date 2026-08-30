from __future__ import annotations

from enum import StrEnum


class AiConnectorKind(StrEnum):
    QWEN = "qwen"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"


class NoAiConnectorConfigured(RuntimeError):
    pass


def select_ai_connector(
    *, qwen_api_key: str, anthropic_api_key: str, openrouter_api_key: str
) -> AiConnectorKind:
    """Pure provider policy. Presence in environment is the only truth signal."""
    if qwen_api_key.strip():
        return AiConnectorKind.QWEN
    if anthropic_api_key.strip():
        return AiConnectorKind.ANTHROPIC
    if openrouter_api_key.strip():
        return AiConnectorKind.OPENROUTER
    raise NoAiConnectorConfigured(
        "Set DASHSCOPE_API_KEY, ANTHROPIC_API_KEY, or OPENROUTER_API_KEY in .env."
    )
