import pytest

from jobact.shared.application.ai_connectors import (
    AiConnectorKind,
    NoAiConnectorConfigured,
    select_ai_connector,
)


def test_anthropic_wins_when_both_keys_are_present() -> None:
    assert select_ai_connector(anthropic_api_key="sk-ant", openrouter_api_key="sk-or") == AiConnectorKind.ANTHROPIC


def test_openrouter_is_used_when_it_is_the_only_key() -> None:
    assert select_ai_connector(anthropic_api_key="", openrouter_api_key="sk-or") == AiConnectorKind.OPENROUTER


def test_no_key_means_no_configured_connector() -> None:
    with pytest.raises(NoAiConnectorConfigured):
        select_ai_connector(anthropic_api_key=" ", openrouter_api_key="")
