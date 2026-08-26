import pytest
from httpx import Response
from pydantic import ValidationError
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from jobact.workflows.report_fulfillment import agent as agent_module
from jobact.workflows.report_fulfillment.agent import (
    DraftedReport,
    LiteLlmCostCapture,
    draft_report,
)
from tests.fakes import FakeLlmGateway


def test_low_confidence_structured_output_rejects_a_proposed_amount() -> None:
    """Removing the safety validation would let an uncertain price reach a report."""
    with pytest.raises(ValidationError):
        DraftedReport(
            work_completed="Replaced the damaged kitchen sink drain and tested for leaks.",
            materials=[],
            amount_cents=12_500,
            confidence="low",
        )


@pytest.mark.asyncio
async def test_litellm_cost_capture_sums_proxy_response_cost_headers() -> None:
    capture = LiteLlmCostCapture()

    await capture.capture(
        Response(
            200,
            headers={
                "x-litellm-response-cost": "0.0012",
                "x-litellm-model-name": "openrouter/anthropic/claude-sonnet-4.5",
            },
        )
    )
    await capture.capture(Response(200, headers={"x-litellm-response-cost": "0.0008"}))

    assert capture.cost_usd == 0.002
    assert capture.model_name == "openrouter/anthropic/claude-sonnet-4.5"


@pytest.mark.asyncio
async def test_draft_report_reads_token_usage_from_the_real_agent_run_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`AgentRunResult.usage` is a property, not a method, in the installed
    pydantic-ai version -- `result.usage()` raises `TypeError: 'RunUsage'
    object is not callable`. This runs `draft_report()` against a real
    `Agent`/`AgentRunResult` (via `TestModel`, no network) so a regression
    back to calling `.usage()` fails here instead of only on a live model call.
    """
    monkeypatch.setattr(
        agent_module,
        "build_drafting_agent",
        lambda llm_gateway, http_client=None: Agent(
            TestModel(), output_type=DraftedReport
        ),
    )

    result = await draft_report(FakeLlmGateway(), "Replaced a leaking pipe under the sink.")

    assert isinstance(result.prompt_tokens, int)
    assert isinstance(result.completion_tokens, int)
    assert isinstance(result.draft, DraftedReport)
