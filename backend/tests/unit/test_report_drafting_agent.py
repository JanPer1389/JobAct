import pytest
from httpx import Response
from pydantic import ValidationError

from jobact.workflows.report_fulfillment.agent import DraftedReport, LiteLlmCostCapture


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
