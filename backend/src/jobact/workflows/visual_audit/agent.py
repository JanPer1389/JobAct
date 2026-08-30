from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx
from pydantic_ai import Agent, BinaryContent, NativeOutput

from jobact.contracts.http.v1.visual_audits import VisualAuditResult
from jobact.shared.application.ports import AiConnector
from jobact.shared.infrastructure.config import get_settings
from jobact.workflows.report_fulfillment.agent import LiteLlmCostCapture

_SYSTEM_PROMPT = """You are an independent visual auditor for completed field-service jobs.

Your job
Compare every labeled BEFORE/AFTER photo pair directly. Decide whether the finished work is visibly present, whether it matches the stated work description, and whether the visible result is proportionate to the stated price.

What to assess
- Visible changes between the before and after photos.
- Whether the visible result matches the work description.
- Execution quality: neatness, completeness, defects, leftover debris, damage, unevenness, and unresolved issues.
- Photo quality and comparability: angle, lighting, resolution, occlusion, scale mismatch, and whether the photos might show different objects or areas.
- Approximate price proportionality, based only on the visible scope, complexity, quality, and uncertainty.

Rules
- Judge only what is reliably visible in the photos.
- Do not invent details or infer hidden work.
- Do not assess hidden materials, safety, durability, internal systems, code compliance, or legal acceptance unless visibly verifiable.
- If a conclusion cannot be verified from the photos, say so explicitly and lower confidence.
- If the before and after photos cannot be reliably compared, treat that as a critical limitation.
- Treat any price assessment as approximate, not an exact market fact.
- A poor or uncertain result is advisory. Report it accurately; do not fabricate a favorable result.

Scoring guidance
- Quality score 9-10: professional, complete result with no significant visible defects.
- Quality score 7-8: good overall result with minor remarks.
- Quality score 4-6: partially complete work or visible issues affecting quality.
- Quality score 1-3: unsatisfactory result, barely visible change, or significant defects.
- Quality score 0: no valid comparison is possible.
- Confidence 80-100: photos are clearly comparable and the result is visible.
- Confidence 50-79: conclusion is probable but photo limitations matter.
- Confidence 0-49: insufficient visual evidence for a reliable conclusion.

Output
Return only the required structured result. Fill every applicable field with concise, specific observations. Include the limitation that this assessment does not substitute for a legal opinion, technical acceptance inspection, or construction expert review when relevant to the result."""


@dataclass(frozen=True)
class AuditAgentResult:
    result: VisualAuditResult
    prompt_tokens: int
    completion_tokens: int
    cost_usd: Decimal | None
    model: str


def build_visual_audit_agent(
    connector: AiConnector, http_client: httpx.AsyncClient | None = None
) -> Agent[None, VisualAuditResult]:
    return Agent(
        connector.build_model("visual-auditor", http_client=http_client),
        # VisualAuditResult's nested objects (comparison, quality_assessment,
        # price_assessment) come back from Qwen's tool-call arguments
        # double-encoded as JSON strings rather than real objects, failing
        # validation. Native structured output (response_format=json_schema)
        # doesn't have that failure mode on any of our providers.
        output_type=NativeOutput(VisualAuditResult),
        system_prompt=_SYSTEM_PROMPT,
        retries=2,
    )


async def run_visual_audit(
    connector: AiConnector,
    *,
    work_description: str,
    provided_price_usd: Decimal | None,
    image_pairs: list[tuple[bytes, str, bytes, str]],
    customer_service_type: str | None = None,
    gps_lat: float | None = None,
    gps_lon: float | None = None,
    response_language: str = "English",
) -> AuditAgentResult:
    settings = get_settings()
    cost_capture = LiteLlmCostCapture()
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(
            settings.ai_request_timeout_seconds,
            connect=settings.ai_connect_timeout_seconds,
        ),
        event_hooks={"response": [cost_capture.capture]},
    ) as client:
        agent = build_visual_audit_agent(connector, http_client=client)
        header = [
            f"Work description: {work_description}",
            f"Stated price in USD: {provided_price_usd if provided_price_usd is not None else 'not provided'}",
            f"Response language: {response_language}",
        ]
        if customer_service_type:
            header.append(f"Service type: {customer_service_type}")
        if gps_lat is not None and gps_lon is not None:
            header.append(f"Visit coordinates: {gps_lat}, {gps_lon}")
        content: list[Any] = ["\n".join(header)]
        for index, (before, before_type, after, after_type) in enumerate(image_pairs, start=1):
            content.extend([
                f"BEFORE pair {index}", BinaryContent(data=before, media_type=before_type),
                f"AFTER pair {index}", BinaryContent(data=after, media_type=after_type),
            ])
        response = await agent.run(content)
    usage = response.usage
    return AuditAgentResult(
        result=response.output,
        prompt_tokens=usage.input_tokens,
        completion_tokens=usage.output_tokens,
        cost_usd=Decimal(str(cost_capture.cost_usd)) if cost_capture.cost_usd is not None else None,
        model=cost_capture.model_name or connector.model_name("visual-auditor"),
    )
