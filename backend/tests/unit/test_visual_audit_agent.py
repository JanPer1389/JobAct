from pydantic_ai import NativeOutput

from jobact.contracts.http.v1.visual_audits import VisualAuditResult
from jobact.shared.infrastructure.llm.connectors import QwenConnector
from jobact.workflows.visual_audit.agent import build_visual_audit_agent


def test_price_fields_are_bounded_in_the_generated_json_schema() -> None:
    """An unbounded `number` field in the output schema triggers a Qwen
    constrained-decoding bug: it emits a runaway, hundreds-of-digits-long
    decimal literal instead of a normal value, corrupting the JSON and
    exhausting output retries. Every float field must carry explicit
    minimum/maximum bounds, not just a type.
    """
    schema = VisualAuditResult.model_json_schema()
    fair_price_range = schema["$defs"]["FairPriceRangeUsd"]["properties"]
    provided_price = schema["$defs"]["PriceAssessment"]["properties"]["provided_price_usd"]

    for field_schema in (fair_price_range["min"], fair_price_range["max"], provided_price):
        numeric_variant = next(v for v in field_schema["anyOf"] if v.get("type") == "number")
        assert "minimum" in numeric_variant
        assert "maximum" in numeric_variant


def test_visual_audit_agent_uses_native_structured_output() -> None:
    """VisualAuditResult's nested objects (comparison, quality_assessment,
    price_assessment) come back from Qwen's tool-call-mode structured output
    double-encoded as JSON strings instead of real objects, failing
    validation. Native output (response_format=json_schema) doesn't have
    that failure mode.
    """
    connector = QwenConnector(api_key="sk-fake", base_url="https://fake-llm.test")

    agent = build_visual_audit_agent(connector)

    assert isinstance(agent.output_type, NativeOutput)
