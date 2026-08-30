from pydantic_ai import NativeOutput

from jobact.shared.infrastructure.llm.connectors import QwenConnector
from jobact.workflows.visual_audit.agent import build_visual_audit_agent


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
