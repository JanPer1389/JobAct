import pytest
from pydantic import ValidationError
from pydantic_ai import Agent, NativeOutput
from pydantic_ai.models.test import TestModel

from jobact.shared.infrastructure.llm.connectors import QwenConnector
from jobact.workflows.report_fulfillment import agent as agent_module
from jobact.workflows.report_fulfillment.agent import (
    DraftedReport,
    ReportAnalysisContext,
    build_drafting_agent,
    build_drafting_prompt,
    draft_report,
)


def test_drafting_agent_uses_native_structured_output() -> None:
    """`materials` is a nested list-of-objects field. Tool-call-mode
    structured output (the pydantic-ai default) makes some OpenAI-compatible
    providers -- Qwen included -- return it double-encoded as a JSON string
    instead of a real array, failing validation. Native output
    (response_format=json_schema) doesn't have that failure mode.
    """
    connector = QwenConnector(api_key="sk-fake", base_url="https://fake-llm.test")

    agent = build_drafting_agent(connector)

    assert isinstance(agent.output_type, NativeOutput)


def test_drafted_report_carries_an_estimated_work_unit_count() -> None:
    """The model reports work volume as a unit count, never a price -- the
    application (not the LLM) turns units into money.
    """
    draft = DraftedReport(
        work_completed="Replaced the damaged kitchen sink drain and tested for leaks.",
        materials=[],
        estimated_work_units=3,
        confidence="low",
    )

    assert draft.estimated_work_units == 3
    assert "amount_cents" not in DraftedReport.model_fields


@pytest.mark.parametrize("units", [0, 1001])
def test_estimated_work_units_is_bounded(units: int) -> None:
    with pytest.raises(ValidationError):
        DraftedReport(
            work_completed="Replaced the damaged kitchen sink drain and tested for leaks.",
            materials=[],
            estimated_work_units=units,
            confidence="low",
        )


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
    injected_clients = []

    def build_test_agent(llm_gateway, http_client=None):
        injected_clients.append(http_client)
        return Agent(TestModel(), output_type=DraftedReport)

    monkeypatch.setattr(agent_module, "build_drafting_agent", build_test_agent)

    result = await draft_report(
        QwenConnector(api_key="sk-fake", base_url="https://fake-llm.test"),
        ReportAnalysisContext(
            raw_notes="Replaced a leaking pipe under the sink.",
            customer_name="Ada Lovelace",
            customer_address="12 Analytical Engine Way",
            customer_service_type="Plumbing",
        ),
    )

    assert isinstance(result.prompt_tokens, int)
    assert isinstance(result.completion_tokens, int)
    assert isinstance(result.draft, DraftedReport)
    assert len(injected_clients) == 1
    assert injected_clients[0].is_closed


def test_drafting_prompt_carries_the_job_context_alongside_the_notes() -> None:
    prompt = build_drafting_prompt(
        ReportAnalysisContext(
            raw_notes="Replaced a leaking pipe under the sink.",
            customer_name="Ada Lovelace",
            customer_address="12 Analytical Engine Way",
            customer_service_type="Plumbing",
            gps_lat=55.7558,
            gps_lon=37.6173,
        )
    )

    assert "Ada Lovelace" in prompt
    assert "12 Analytical Engine Way" in prompt
    assert "55.7558" in prompt
    assert "Replaced a leaking pipe under the sink." in prompt


def test_drafting_prompt_defaults_to_english_and_can_request_russian() -> None:
    english_prompt = build_drafting_prompt(
        ReportAnalysisContext(
            raw_notes="Replaced a leaking pipe under the sink.",
            customer_name="Ada Lovelace",
            customer_address="12 Analytical Engine Way",
            customer_service_type="Plumbing",
        )
    )
    russian_prompt = build_drafting_prompt(
        ReportAnalysisContext(
            raw_notes="Replaced a leaking pipe under the sink.",
            customer_name="Ada Lovelace",
            customer_address="12 Analytical Engine Way",
            customer_service_type="Plumbing",
            response_language="Russian",
        )
    )

    assert "Response language: English" in english_prompt
    assert "Response language: Russian" in russian_prompt


@pytest.mark.asyncio
async def test_draft_report_closes_http_client_after_provider_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    injected_clients = []

    class FailingAgent:
        async def run(self, prompt: str):
            raise RuntimeError("provider unavailable")

    def build_failing_agent(connector, http_client=None):
        injected_clients.append(http_client)
        return FailingAgent()

    monkeypatch.setattr(agent_module, "build_drafting_agent", build_failing_agent)

    with pytest.raises(RuntimeError, match="provider unavailable"):
        await draft_report(
            QwenConnector(api_key="sk-fake", base_url="https://fake-llm.test"),
            ReportAnalysisContext(
                raw_notes="Non-sensitive fixture.",
                customer_name="Test Customer",
                customer_address="Test Address",
                customer_service_type="Test Service",
            ),
        )

    assert len(injected_clients) == 1
    assert injected_clients[0].is_closed
