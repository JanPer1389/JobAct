from __future__ import annotations

from typing import Any

from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider

from jobact.shared.application.ai_connectors import AiConnectorKind, select_ai_connector
from jobact.shared.application.ports import AiConnector
from jobact.shared.infrastructure.config import Settings

_ANTHROPIC_MODELS = {
    "report-drafter": "claude-sonnet-4-5",
    "visual-auditor": "claude-sonnet-4-5",
}
_OPENROUTER_MODELS = {
    "report-drafter": "report-drafter",
    "visual-auditor": "visual-auditor",
}


class AnthropicConnector:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def model_name(self, alias: str) -> str:
        return _model_name(_ANTHROPIC_MODELS, alias)

    def build_model(self, alias: str, http_client: Any | None = None) -> AnthropicModel:
        return AnthropicModel(
            self.model_name(alias),
            provider=AnthropicProvider(api_key=self._api_key, http_client=http_client),
        )


class OpenRouterConnector:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def provider_name(self) -> str:
        return "openrouter"

    def model_name(self, alias: str) -> str:
        return _model_name(_OPENROUTER_MODELS, alias)

    def build_model(self, alias: str, http_client: Any | None = None) -> OpenAIChatModel:
        base_url = self._settings.litellm_base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        return OpenAIChatModel(
            self.model_name(alias),
            provider=OpenAIProvider(
                base_url=base_url,
                api_key=self._settings.litellm_master_key,
                http_client=http_client,
            ),
        )


def build_ai_connector(settings: Settings) -> AiConnector:
    selected = select_ai_connector(
        anthropic_api_key=settings.anthropic_api_key,
        openrouter_api_key=settings.openrouter_api_key,
    )
    if selected == AiConnectorKind.ANTHROPIC:
        return AnthropicConnector(settings.anthropic_api_key)
    return OpenRouterConnector(settings)


def _model_name(models: dict[str, str], alias: str) -> str:
    try:
        return models[alias]
    except KeyError as exc:
        raise ValueError(f"Unknown AI model alias: {alias!r}.") from exc
