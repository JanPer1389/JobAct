"""The PydanticAI drafting agent -- turns a technician's rough notes
into a structured report draft.

Bound to LiteLLM via its OpenAI-compatible endpoint (`LlmGateway.
base_url`/`api_key`) -- the agent owns the actual HTTP call lifecycle
and structured-output validation directly; `LlmGateway` only supplies
credentials (see its own docstring in `shared/application/ports.py`).

The agent's output is validated before it reaches the report aggregate.
In particular, a low-confidence draft cannot carry a proposed amount.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from jobact.shared.application.ports import LlmGateway


class DraftedMaterial(BaseModel):
    label: str
    qty: str


class DraftedReport(BaseModel):
    work_completed: str = Field(min_length=20, max_length=2000)
    materials: list[DraftedMaterial] = Field(default_factory=list, max_length=20)
    amount_cents: int | None = Field(default=None, ge=0, le=10_000_000)
    confidence: Literal["high", "medium", "low"]

    @model_validator(mode="after")
    def low_confidence_cannot_propose_an_amount(self) -> DraftedReport:
        if self.confidence == "low" and self.amount_cents is not None:
            raise ValueError("Low-confidence drafts must leave amount_cents unset.")
        return self


@dataclass(frozen=True)
class DraftingResult:
    draft: DraftedReport
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float | None


_SYSTEM_PROMPT = (
    "You are drafting a field-service work report from a technician's rough "
    "notes. Extract: (1) a clear, customer-readable summary of the work "
    "completed, (2) any materials/parts used with quantities, (3) the amount "
    "to charge in cents, if the notes clearly state or strongly imply one -- "
    "otherwise leave amount_cents unset. Set confidence to 'low' whenever "
    "you are not confident about the amount specifically; never guess an "
    "amount you are not confident about."
)


def build_drafting_agent(llm_gateway: LlmGateway) -> Agent[None, DraftedReport]:
    model = OpenAIChatModel(
        llm_gateway.model_name("report-drafter"),
        provider=OpenAIProvider(
            base_url=_openai_compatible_base_url(llm_gateway.base_url),
            api_key=llm_gateway.api_key,
        ),
    )
    return Agent(
        model,
        output_type=DraftedReport,
        system_prompt=_SYSTEM_PROMPT,
        retries=2,
    )


async def draft_report(llm_gateway: LlmGateway, raw_notes: str) -> DraftingResult:
    agent = build_drafting_agent(llm_gateway)
    result = await agent.run(raw_notes)
    usage = result.usage()
    return DraftingResult(
        draft=result.output,
        prompt_tokens=usage.input_tokens,
        completion_tokens=usage.output_tokens,
        cost_usd=float(usage.cost) if usage.cost is not None else None,
    )


def _openai_compatible_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    return normalized if normalized.endswith("/v1") else f"{normalized}/v1"
