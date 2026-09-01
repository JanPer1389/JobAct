# AI Drafting and Visual Audit

Post-downgrade status ([ADR-0007](../adr/0007-local-demo-downgrade.md)): this describes the
current, stateless implementation. The AI product logic itself is unchanged from Milestone 1
— only the surrounding persistence/dispatch was removed.

## Provider path

```text
apps/api/demo_service.py → Qwen / DashScope directly (QWEN_BASE_URL, DASHSCOPE_API_KEY)
                          → qwen3.8-flash    (alias: report-drafter)
                            qwen3-vl-flash   (alias: visual-auditor)
```

Qwen is the only supported AI connector (see [ADR-0006](../adr/0006-litellm-over-openrouter.md)
and `093d80a`, which removed the earlier Anthropic/OpenRouter/LiteLLM code entirely).
`QwenConnector` (`shared/infrastructure/llm/connectors.py`) builds a PydanticAI
`OpenAIChatModel` directly against DashScope's OpenAI-compatible endpoint. There is no proxy in
front of it and no other provider to fail over to — `demo_service.get_ai_connector()` (a
FastAPI dependency) returns a 503 `ai-not-configured` error if `DASHSCOPE_API_KEY` is unset,
rather than silently falling back to a different model.

## Where `raw_notes` comes from

The frontend's `NotesScreen` (`frontend/components/jobact/screens/flow.tsx`) either takes
typed notes directly, or records audio and posts it to `POST /api/v1/demo/transcribe` (see
[STT below](#speech-to-text)), setting `raw_notes` from the returned transcript. Either way,
by the time `POST /api/v1/demo/analyze` is called, `raw_notes` is a plain string — the AI
context object doesn't know or care which path produced it.

## The unified analysis call

`apps/api/demo_service.analyze()` runs two AI calls per request, back to back, and only
returns success if both succeed:

1. **Drafting** (`workflows/report_fulfillment/agent.py`, `draft_report()`) — a PydanticAI
   `Agent` with a strict Pydantic output type:

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
   materially distinct units of work volume its notes describe —
   `contexts/reports/domain/pricing.py` deterministically converts that into a suggested USD
   amount (`USD_CENTS_PER_WORK_UNIT`), and `shared/application/fx.py` converts that into the
   requested currency at a fixed, dated local rate (never a live FX call, never LLM
   arithmetic). Keeping the arithmetic out of the model means there is no price channel for a
   confused model or a prompt injection to abuse.

2. **Visual audit** (`workflows/visual_audit/agent.py`, `run_visual_audit()`) — given the
   drafted `work_completed` text, the deterministic price, and up to 6 before/after photo
   pairs (`BinaryContent`), returns a structured `VisualAuditResult`
   (`contracts/http/v1/visual_audits.py`): verdict, confidence, a visible-changes comparison, a
   quality assessment, and a price-reasonableness assessment. All numeric price fields are
   explicitly bounded (`ge=0, le=1_000_000`) — an unbounded field previously triggered a Qwen
   constrained-decoding bug that emitted a runaway, corrupt decimal literal.

Both agents use `NativeOutput(...)` (JSON-schema structured output) rather than PydanticAI's
default tool-call mode — Qwen returns nested-object fields (`materials`,
`comparison`/`quality_assessment`/`price_assessment`) double-encoded as JSON strings under
tool-call mode, which native structured output does not exhibit. Both agents disable Qwen's
"thinking" mode (`extra_body: {enable_thinking: false}` in `QwenConnector.build_model()`) for
these structured-output calls.

## The safety invariant

The domain-layer guard that used to sit on the deleted `Report` aggregate
(`mark_ready_for_signature()` requiring both `confirmed_by_user_at` and `amount_confirmed_at`)
no longer exists as domain code — there is no `Report` aggregate anymore. The same invariant
is re-expressed as a frontend precondition: `SignatureScreen`
(`frontend/components/jobact/screens/flow.tsx`) will not render its sign/finish action as
enabled until `draft.amountConfirmed` is `true`, which is only set when the technician
explicitly confirms the (editable) amount on `ReportDraftScreen`/`EditReportScreen`. This is a
real downgrade in *where* the invariant lives (frontend precondition vs. domain-layer
exception) — see [ADR-0007](../adr/0007-local-demo-downgrade.md)'s consequences section. Do
not relax it further.

## Failure handling

`demo_service.analyze()` treats any exception from either AI call — timeout, malformed JSON,
schema violation, network error — by classifying it through
`workflows/report_fulfillment/failures.classify_analysis_failures()` (unchanged from
Milestone 1) into one of: `AI_ANALYSIS_TIMEOUT` (504, retryable), `AI_PROVIDERS_UNAVAILABLE`
(502, retryable), or `AI_PROVIDER_CONFIGURATION_ERROR` (503, not retryable). There is no
template-fallback revision written anywhere (nothing to write it to) — the endpoint returns an
`ApiError`, and the frontend's `AnalysisProcessingScreen` shows a localized message with
review-photos / write-manually / retry actions, matching the durable workflow's old
user-facing outcomes without the durable workflow itself.

## Speech-to-text

`POST /api/v1/demo/transcribe` calls the same two classes the durable `stt-worker` used to
call, unmodified: `PyAvAudioInspector.inspect()` (validates the container/codec against the
declared content type, 0.5–600s duration) then `FasterWhisperTranscriber.transcribe()`
(`faster-whisper`, model `small`, `device="cpu"`, `compute_type="int8"`, `vad_filter=True`,
`beam_size=5`). See [ADR-0007](../adr/0007-local-demo-downgrade.md) for exactly what
orchestration was removed around them. This is one of the two protected subsystems —
[`backend/CLAUDE.md`](../../backend/CLAUDE.md#stt) reiterates: no changes to model, runtime,
or audio processing when working in this area.

## Cost and observability

There is no proxy in front of Qwen, so there is no server-side spend log — Qwen's
OpenAI-compatible endpoint doesn't return a per-response cost. `cost_usd` is always `None`;
token counts (from each response's own `usage`) are the only per-call cost signal, visible in
`apps/api/demo_service.py`'s structured log lines.

## Testing

`tests/unit/test_report_drafting_agent.py` and `tests/unit/test_visual_audit_agent.py` test
the agents' own structured-output/prompt-building logic directly (`TestModel`, no network).
`tests/domain/reports/test_pricing.py` and `tests/unit/test_fx.py` cover the deterministic
units→cents→currency conversion. `tests/unit/test_demo_service.py` and
`tests/unit/test_demo_router.py` cover the stateless endpoint layer with fakes for the
transcriber/connector. `tests/unit/test_analysis_failures.py` covers the failure
classification. No test in this repository calls a live model — verifying a real Qwen round
trip is still a manual (or opt-in, not-yet-written) step.
