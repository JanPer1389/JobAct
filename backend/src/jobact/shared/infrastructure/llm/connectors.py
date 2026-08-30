from __future__ import annotations

from typing import Any

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from jobact.shared.application.ai_connectors import NoAiConnectorConfigured
from jobact.shared.application.ports import AiConnector
from jobact.shared.infrastructure.config import Settings

_QWEN_MODELS = {
    "report-drafter": "qwen3.8-flash",
    "visual-auditor": "qwen3-vl-flash",
}


class QwenConnector:
    def __init__(self, api_key: str, base_url: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "qwen"

    def model_name(self, alias: str) -> str:
        return _model_name(_QWEN_MODELS, alias)

    def build_model(self, alias: str, http_client: Any | None = None) -> OpenAIChatModel:
        return OpenAIChatModel(
            self.model_name(alias),
            provider=OpenAIProvider(
                base_url=self._base_url,
                api_key=self._api_key,
                http_client=http_client,
            ),
            settings={"extra_body": {"enable_thinking": False}},
        )


def build_ai_connector(settings: Settings) -> AiConnector:
    if not settings.dashscope_api_key.strip():
        raise NoAiConnectorConfigured("Set DASHSCOPE_API_KEY in .env.")
    return QwenConnector(settings.dashscope_api_key, settings.qwen_base_url)


def build_ai_connectors(settings: Settings) -> list[AiConnector]:
    """Qwen is the only supported connector -- a single-item list purely to
    keep `RunReportAnalysisActivity`'s connector-iteration shape."""
    return [build_ai_connector(settings)]


def _model_name(models: dict[str, str], alias: str) -> str:
    try:
        return models[alias]
    except KeyError as exc:
        raise ValueError(f"Unknown AI model alias: {alias!r}.") from exc
