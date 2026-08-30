import json

import httpx
import pytest
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError

from jobact.shared.application.ai_connectors import NoAiConnectorConfigured
from jobact.shared.infrastructure.config import Settings
from jobact.shared.infrastructure.llm.connectors import (
    QwenConnector,
    build_ai_connector,
    build_ai_connectors,
)


class _StructuredFixture(BaseModel):
    result: str


@pytest.mark.asyncio
async def test_qwen_disables_thinking_for_required_structured_output() -> None:
    captured_body: dict = {}

    def capture_and_reject(request: httpx.Request) -> httpx.Response:
        captured_body.update(json.loads(request.content))
        return httpx.Response(
            400,
            json={"error": {"message": "diagnostic rejection"}},
            request=request,
        )

    connector = QwenConnector(
        api_key="sk-qwen",
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(capture_and_reject)
    ) as client:
        model = connector.build_model("report-drafter", http_client=client)
        with pytest.raises(ModelHTTPError):
            await Agent(model, output_type=_StructuredFixture).run("Return JSON.")

    assert captured_body["tool_choice"] == "required"
    assert captured_body["enable_thinking"] is False


def test_no_key_means_no_configured_connector() -> None:
    with pytest.raises(NoAiConnectorConfigured):
        build_ai_connector(Settings(dashscope_api_key=" "))


def test_qwen_connector_uses_direct_model_studio_models() -> None:
    connector = QwenConnector(
        api_key="sk-qwen",
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1/",
    )

    drafting_model = connector.build_model("report-drafter")
    visual_model = connector.build_model("visual-auditor")

    assert connector.provider_name == "qwen"
    assert drafting_model.model_name == "qwen3.8-flash"
    assert str(drafting_model.base_url) == (
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/"
    )
    assert visual_model.model_name == "qwen3-vl-flash"


def test_build_ai_connectors_returns_only_qwen() -> None:
    """Qwen is the only supported connector -- there is no other provider to
    fail over to."""
    connectors = build_ai_connectors(Settings(dashscope_api_key="sk-qwen"))

    assert [connector.provider_name for connector in connectors] == ["qwen"]
