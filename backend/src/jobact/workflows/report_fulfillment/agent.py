"""The PydanticAI drafting agent -- turns a technician's rough notes
into a structured report draft.

Bound to LiteLLM via its OpenAI-compatible endpoint (`LlmGateway.
base_url`/`api_key`) -- the agent owns the actual HTTP call lifecycle
and structured-output validation directly; `LlmGateway` only supplies
credentials (see its own docstring in `shared/application/ports.py`).

The agent's output is validated before it reaches the report aggregate. In
particular, the model never emits a price: it returns a count of materially
distinct work units, and turning that into a suggested amount is deterministic
application logic (`contexts/reports/domain/pricing.py`), not something the
LLM can compute or bypass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx
from pydantic import BaseModel, Field
from pydantic_ai import Agent, NativeOutput

from jobact.shared.application.ports import AiConnector
from jobact.shared.infrastructure.config import get_settings


class DraftedMaterial(BaseModel):
    label: str
    qty: str


class DraftedReport(BaseModel):
    work_completed: str = Field(min_length=20, max_length=2000)
    materials: list[DraftedMaterial] = Field(default_factory=list, max_length=20)
    estimated_work_units: int | None = Field(default=None, ge=1, le=1000)
    confidence: Literal["high", "medium", "low"]


@dataclass(frozen=True)
class DraftingResult:
    draft: DraftedReport
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float | None
    model: str


class LiteLlmCostCapture:
    """Accumulates LiteLLM's authoritative per-response cost headers."""

    def __init__(self) -> None:
        self._cost_usd = Decimal(0)
        self._has_cost = False
        self._model_name: str | None = None

    async def capture(self, response: httpx.Response) -> None:
        model_name = response.headers.get("x-litellm-model-name")
        if model_name:
            self._model_name = model_name
        raw_cost = response.headers.get("x-litellm-response-cost")
        if raw_cost is None:
            return
        try:
            self._cost_usd += Decimal(raw_cost)
        except InvalidOperation:
            return
        self._has_cost = True

    @property
    def cost_usd(self) -> float | None:
        return float(self._cost_usd) if self._has_cost else None

    @property
    def model_name(self) -> str | None:
        return self._model_name


_SYSTEM_PROMPT = (
    "You are drafting a field-service work report from a technician's rough "
    "notes and the job's context. Extract: (1) a clear, customer-readable "
    "summary of the work completed, (2) any materials/parts used with "
    "quantities, (3) estimated_work_units -- an integer count of the "
    "materially distinct units of work volume the notes actually describe. "
    "One unit is one discrete, materially distinct piece of work (e.g. one "
    "fixture replaced, one leak sealed, one section serviced). Never count "
    "the same work twice because it is mentioned more than once, and never "
    "count work the notes do not describe. Never output a price, a "
    "currency, or any monetary amount -- the application computes the "
    "price from your unit count. Never perform currency conversion and "
    "never decide or state which currency applies -- that is the "
    "application's job. Write every natural-language field (the work "
    "summary and material labels) in the response language given in the "
    "job context -- never default to English if a different response "
    "language is specified. Set confidence to reflect how well the notes "
    "support the summary and the unit count."
)


@dataclass(frozen=True)
class ReportAnalysisContext:
    """Structured job context handed to both AI steps of one analysis run."""

    raw_notes: str
    customer_name: str
    customer_address: str
    customer_service_type: str
    gps_lat: float | None = None
    gps_lon: float | None = None
    current_work_completed: str | None = None
    current_materials: list[DraftedMaterial] = field(default_factory=list)
    current_amount_cents: int | None = None
    currency: str = "USD"
    response_language: str = "English"


def build_drafting_prompt(context: ReportAnalysisContext) -> str:
    lines = [
        "Job context:",
        f"- Customer: {context.customer_name}",
        f"- Address: {context.customer_address}",
        f"- Service type: {context.customer_service_type}",
        (
            "- Currency (context only -- do not convert or restate an "
            f"amount in this currency; the application handles all money): "
            f"{context.currency}"
        ),
        f"- Response language: {context.response_language}",
    ]
    if context.gps_lat is not None and context.gps_lon is not None:
        lines.append(f"- Visit coordinates: {context.gps_lat}, {context.gps_lon}")
    if context.current_work_completed:
        lines += [
            "",
            (
                "An earlier version of this report already exists. Verify and "
                "improve it rather than starting over:"
            ),
            f"- Current work completed: {context.current_work_completed}",
        ]
        if context.current_materials:
            materials = ", ".join(
                f"{m.label} x{m.qty}" for m in context.current_materials
            )
            lines.append(f"- Current materials: {materials}")
        if context.current_amount_cents is not None:
            lines.append(f"- Current amount (cents): {context.current_amount_cents}")
    lines += ["", "Technician's raw notes:", context.raw_notes]
    return "\n".join(lines)


def build_drafting_agent(
    connector: AiConnector, http_client: httpx.AsyncClient | None = None
) -> Agent[None, DraftedReport]:
    model = connector.build_model("report-drafter", http_client=http_client)
    return Agent(
        model,
        # Tool-call arguments containing a nested list-of-objects field
        # (materials) come back from Qwen double-encoded as a JSON string
        # instead of a real array, failing validation. Native structured
        # output (response_format=json_schema) doesn't have that failure
        # mode on any of our providers.
        output_type=NativeOutput(DraftedReport),
        system_prompt=_SYSTEM_PROMPT,
        retries=2,
    )


async def draft_report(
    connector: AiConnector, context: ReportAnalysisContext
) -> DraftingResult:
    settings = get_settings()
    cost_capture = LiteLlmCostCapture()
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(
            settings.ai_request_timeout_seconds,
            connect=settings.ai_connect_timeout_seconds,
        ),
        event_hooks={"response": [cost_capture.capture]},
    ) as http_client:
        agent = build_drafting_agent(connector, http_client=http_client)
        result = await agent.run(build_drafting_prompt(context))
    usage = result.usage
    return DraftingResult(
        draft=result.output,
        prompt_tokens=usage.input_tokens,
        completion_tokens=usage.output_tokens,
        cost_usd=cost_capture.cost_usd,
        model=cost_capture.model_name
        or connector.model_name("report-drafter"),
    )
