# AI Drafting

## Provider path

```text
jobact API/worker → Qwen / DashScope directly (QWEN_BASE_URL, DASHSCOPE_API_KEY)
                  → qwen3.8-flash    (alias: report-drafter)
                    qwen3-vl-flash   (alias: visual-auditor)
```

Qwen is the only supported AI connector (see [ADR-0006](../adr/0006-litellm-over-openrouter.md),
now superseded). `QwenConnector` (`shared/infrastructure/llm/connectors.py`) builds a
PydanticAI `OpenAIChatModel` directly against DashScope's OpenAI-compatible endpoint, using
`Settings.dashscope_api_key`/`qwen_base_url`. There is no proxy in front of it and no other
provider to fail over to — `build_ai_connector()` raises `NoAiConnectorConfigured` if
`DASHSCOPE_API_KEY` is unset, rather than silently falling back to a different model.

## Where `raw_notes` comes from

There is no speech-to-text in this milestone. `POST /reports` takes a `raw_notes` string
directly. The frontend (`VoiceScreen`, see `frontend/components/jobact/screens/flow.tsx`)
feeds this field from either path a technician takes:

- "Type it instead" — real typed notes.
- The simulated recorder — a canned demo transcript constant.

Both converge on the same field, so a future `TranscribeAudioActivity` only needs to populate
`raw_notes` before `DRAFTING_PENDING` runs; nothing downstream changes.

## The agent

`workflows/report_fulfillment/agent.py` builds a PydanticAI `Agent` bound directly to Qwen's
OpenAI-compatible endpoint (`OpenAIChatModel` + `OpenAIProvider`), with a strict Pydantic
output type:

```python
class DraftedMaterial(BaseModel):
    label: str
    qty: str

class DraftedReport(BaseModel):
    work_completed: str = Field(min_length=20, max_length=2000)
    materials: list[DraftedMaterial] = Field(default_factory=list, max_length=20)
    estimated_work_units: int | None = Field(default=None, ge=1, le=1000)
    confidence: Literal["high", "medium", "low"]
```

The model never emits a price. It returns `estimated_work_units` — an integer count of the
materially distinct units of work volume its notes describe — and
`contexts/reports/domain/pricing.py` deterministically converts that into a suggested amount
at a fixed `USD_CENTS_PER_WORK_UNIT` rate before `GenerateReportDraftActivity` applies the
draft. Keeping the arithmetic out of the model (rather than asking it to compute or state a
price and validating the result) means there is no price channel for a prompt-injection or a
confused model to abuse in the first place. The agent itself has `retries=2` for
schema-validation failures; `GenerateReportDraftActivity` does not add a second, outer retry
loop — one call (with the agent's own internal retries) either succeeds or is treated as
exhausted.

## The safety invariant (enforced in the domain, not the prompt)

**`Report.mark_ready_for_signature()` raises unless the current revision has both
`confirmed_by_user_at` and `amount_confirmed_at` set** (`contexts/reports/domain/report.py`).
This is PAPERCUT's first domain principle — "AI only proposes; the user confirms" — expressed
as a code invariant the AI response can never bypass, regardless of what confidence value or
suggested amount it returns. The suggested amount pre-fills the revision's `amount_cents`
regardless of `ai_confidence` (confidence is display-only metadata, not a gate on whether a
price appears) — `apply_ai_draft()` never sets `confirmed_by_user_at` or
`amount_confirmed_at`, so a suggested price can never itself count as a human confirmation.
Do not relax the `mark_ready_for_signature()` check for convenience or a demo — this is the
highest-consequence failure mode in the product, called out explicitly in the plan's Risks
section.

## Failure handling

`GenerateReportDraftActivity.run()` (`workflows/report_fulfillment/activities/
generate_report_draft.py`) treats *any* exception from the drafting call — timeout, malformed
JSON, schema violation, network error — identically: it writes a deterministic template
revision (`work_completed` tells the technician AI drafting was unavailable and to fill the
report in manually, `confidence="low"`, no amount, no materials) **and** parks the workflow
run in `MANUAL_INPUT_REQUIRED`, in the same activity execution and the same transaction as
the report write. A model outage therefore never blocks a report — `GET /reports/{id}`
still returns a report, in `MANUAL_INPUT_REQUIRED`, ready for a human to finish by hand
(`PATCH /reports/{id}/revision` then `POST /reports/{id}/confirm`, same as touching up an AI
draft).

## Cost and observability

There is no proxy in front of Qwen, so there is no server-side spend log to read from — Qwen's
OpenAI-compatible endpoint doesn't return a per-response cost. `cost_usd` is always `None` in
the `{model, prompt_tokens, completion_tokens, cost_usd, latency_ms}` written into that step's
`workflow.workflow_steps.output` JSONB column; token counts (from the response's own `usage`)
are the only real per-call cost signal available today.

## Testing

`tests/integration/test_generate_report_draft_activity.py` uses a fake `draft_report_fn`
(never a live model) to cover: a valid draft producing an `ai` revision with its suggested
amount pre-filled (even at `confidence: "low"`); and a malformed/timeout case falling back to
the template, which proposes no amount at all since no unit count exists to price.
`tests/unit/test_report_drafting_agent.py` covers the agent's own output-validation rules
directly, and `tests/domain/reports/test_pricing.py` covers the units→cents conversion.

The plan called for a real, opt-in smoke test against the live model
(`tests/integration/test_live_llm.py`, gated on `JOBACT_LIVE_LLM_TESTS=1`) — **this file does
not exist yet.** No test in this milestone calls a live model; CI safety therefore isn't at
risk, but "does the real Qwen round trip actually work" has only been verified manually, not
by an automated, opt-in test. Adding it is open work.
