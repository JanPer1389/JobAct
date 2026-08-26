# AI Drafting

## Provider path

```text
jobact API/worker → LiteLLM proxy (http://litellm:4000, internal LITELLM_MASTER_KEY)
                  → OpenRouter (OPENROUTER_API_KEY, container-only)
                  → openrouter/anthropic/claude-sonnet-4.5  (alias: report-drafter)
                    openrouter/openai/gpt-4.1-mini           (alias: report-drafter-fallback)
```

The application code never sees an OpenRouter key — `LlmGateway` (`shared/application/
ports.py`, implemented by `shared/infrastructure/llm/litellm_gateway.py`) only carries
LiteLLM's base URL and master key, both read from `Settings`
(`shared/infrastructure/config.py`). The only place `OPENROUTER_API_KEY` is consumed is the
`litellm` service in `docker-compose.yml`, via `backend/litellm_config.yaml`. Rotating or
swapping the provider is an edit to `.env` and `litellm_config.yaml`, not a code change — see
[ADR-0006](../adr/0006-litellm-over-openrouter.md).

The `report-drafter-fallback` alias is registered in `litellm_config.yaml` but nothing in
`workflows/report_fulfillment/agent.py` currently selects it on failure — the only fallback
this milestone implements is the deterministic template below, not an automatic
model-to-model fallback. Wiring LiteLLM's own fallback behavior (or picking the fallback
alias explicitly on a `report-drafter` failure) is open work, not a bug — it just wasn't
needed to prove the vertical slice.

## Where `raw_notes` comes from

There is no speech-to-text in this milestone. `POST /reports` takes a `raw_notes` string
directly. The frontend (`VoiceScreen`, see `frontend/components/jobact/screens/flow.tsx`)
feeds this field from either path a technician takes:

- "Type it instead" — real typed notes.
- The simulated recorder — a canned demo transcript constant.

Both converge on the same field, so a future `TranscribeAudioActivity` only needs to populate
`raw_notes` before `DRAFTING_PENDING` runs; nothing downstream changes.

## The agent

`workflows/report_fulfillment/agent.py` builds a PydanticAI `Agent` bound to LiteLLM's
OpenAI-compatible endpoint (`OpenAIChatModel` + `OpenAIProvider`, base URL normalized to end
in `/v1`), with a strict Pydantic output type:

```python
class DraftedMaterial(BaseModel):
    label: str
    qty: str

class DraftedReport(BaseModel):
    work_completed: str = Field(min_length=20, max_length=2000)
    materials: list[DraftedMaterial] = Field(default_factory=list, max_length=20)
    amount_cents: int | None = Field(default=None, ge=0, le=10_000_000)
    confidence: Literal["high", "medium", "low"]
```

A `model_validator` rejects any output where `confidence == "low"` and `amount_cents` is set
— the model is not allowed to claim low confidence while still proposing a number. The agent
itself has `retries=2` for schema-validation failures; `GenerateReportDraftActivity` does not
add a second, outer retry loop — one call (with the agent's own internal retries) either
succeeds or is treated as exhausted.

## The safety invariant (enforced in the domain, not the prompt)

**`Report.mark_ready_for_signature()` raises unless the current revision has both
`confirmed_by_user_at` and `amount_confirmed_at` set** (`contexts/reports/domain/report.py`).
This is PAPERCUT's first domain principle — "AI only proposes; the user confirms" — expressed
as a code invariant the AI response can never bypass, regardless of what confidence value or
amount it returns. `apply_ai_draft()` additionally drops `amount_cents` to `None` whenever
`ai_confidence == "low"`, so a low-confidence draft never even displays a plausible-looking
guess to confirm past. Do not relax either check for convenience or a demo — this is the
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

LiteLLM keeps its own spend log server-side. In addition, `LiteLlmCostCapture` reads the
`x-litellm-model-name` / `x-litellm-response-cost` response headers on every drafting call and
`GenerateReportDraftActivity` writes `{model, prompt_tokens, completion_tokens, cost_usd,
latency_ms}` into that step's `workflow.workflow_steps.output` JSONB column — no separate
cost-tracking table exists or is needed for "what does a report cost."

## Testing

`tests/integration/test_generate_report_draft_activity.py` uses a fake `draft_report_fn`
(never a live model) to cover: a valid draft producing an `ai` revision; a malformed/timeout
case falling back to the template and parking the run; and a `confidence: "low"` draft
leaving `amount_cents` unset. `tests/unit/test_report_drafting_agent.py` covers the agent's
own output-validation rules directly.

The plan called for a real, opt-in smoke test against the live model
(`tests/integration/test_live_llm.py`, gated on `JOBACT_LIVE_LLM_TESTS=1`) — **this file does
not exist yet.** No test in this milestone calls a live model; CI safety therefore isn't at
risk, but "does the real OpenRouter round trip actually work" has only been verified manually
(see `docs/roadmap.md`), not by an automated, opt-in test. Adding it is open work.
