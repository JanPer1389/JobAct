import httpx
import pytest
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError

from jobact.shared.application.ai_connectors import (
    AiConnectorKind,
    NoAiConnectorConfigured,
    select_ai_connector,
)
from jobact.shared.infrastructure.config import Settings
from jobact.shared.infrastructure.llm.connectors import (
    AnthropicConnector,
    build_ai_connectors,
)


@pytest.mark.asyncio
async def test_anthropic_connector_accepts_the_managed_httpx_client() -> None:
    """A dependency update must not make provider construction reject our client."""
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(503, request=request))) as client:
        model = AnthropicConnector("test-key").build_model(
            "report-drafter", http_client=client
        )

    assert model.model_name == "claude-sonnet-4-5"


@pytest.mark.asyncio
async def test_anthropic_request_uses_injected_client_and_surfaces_provider_failure() -> None:
    request_count = 0

    def reject(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(401, json={"error": {"message": "rejected"}}, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(reject)) as client:
        model = AnthropicConnector("test-key").build_model(
            "report-drafter", http_client=client
        )
        with pytest.raises(ModelHTTPError) as raised:
            await Agent(model).run("Use this non-sensitive test fixture.")

    assert raised.value.status_code == 401
    assert request_count == 1


def test_anthropic_wins_when_both_keys_are_present() -> None:
    assert select_ai_connector(anthropic_api_key="sk-ant", openrouter_api_key="sk-or") == AiConnectorKind.ANTHROPIC


def test_openrouter_is_used_when_it_is_the_only_key() -> None:
    assert select_ai_connector(anthropic_api_key="", openrouter_api_key="sk-or") == AiConnectorKind.OPENROUTER


def test_no_key_means_no_configured_connector() -> None:
    with pytest.raises(NoAiConnectorConfigured):
        select_ai_connector(anthropic_api_key=" ", openrouter_api_key="")


def test_all_configured_connectors_are_returned_in_failover_order() -> None:
    connectors = build_ai_connectors(
        Settings(
            anthropic_api_key="sk-ant",
            openrouter_api_key="sk-or",
            litellm_master_key="sk-or",
        )
    )

    assert [connector.provider_name for connector in connectors] == [
        "anthropic",
        "openrouter",
    ]
