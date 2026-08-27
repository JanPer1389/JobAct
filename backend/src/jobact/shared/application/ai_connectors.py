from __future__ import annotations

from enum import StrEnum


class AiConnectorKind(StrEnum):
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"


class NoAiConnectorConfigured(RuntimeError):
    pass


def select_ai_connector(*, anthropic_api_key: str, openrouter_api_key: str) -> AiConnectorKind:
    """Pure provider policy. Presence in environment is the only truth signal."""
    if anthropic_api_key.strip():
        return AiConnectorKind.ANTHROPIC
    if openrouter_api_key.strip():
        return AiConnectorKind.OPENROUTER
    raise NoAiConnectorConfigured("Set ANTHROPIC_API_KEY or OPENROUTER_API_KEY in .env.")
