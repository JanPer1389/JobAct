# CLAUDE.md (backend)

This file provides guidance to Claude Code when working with code in `backend/`. See the
[root CLAUDE.md](../CLAUDE.md) for the overall repo layout.

## Project

JobAct's backend is three stateless HTTP endpoints (`apps/api/routers/demo.py`): transcribe
one recording, run the unified AI analysis on one job, render one signed check PDF. There is
no database, cache, object storage, or user session — normal application state lives in the
browser (see [`../frontend/CLAUDE.md`](../frontend/CLAUDE.md)). See
[`../docs/architecture/overview.md`](../docs/architecture/overview.md) for the full design and
[ADR-0007](../docs/adr/0007-local-demo-downgrade.md) for why, and
[`../docs/architecture/ai.md`](../docs/architecture/ai.md) for the AI/STT pipeline itself.

## Commands

Run these from `backend/`. Package manager is `uv`.

```bash
uv sync --dev                                                   # install runtime + dev dependencies
uv run uvicorn jobact.apps.api.main:app --reload --port 8000   # run the API
uv run pytest                                                   # unit tests -- no external services needed
uv run ruff check .                                             # lint
uv run mypy src tests                                           # type check
```

Copy `.env.example` to `.env` first and fill in `DASHSCOPE_API_KEY` if you want `/demo/analyze`
to produce real output — everything else has working local defaults. Without a key,
`/demo/analyze` returns a 503 `ai-not-configured` error (the frontend shows a localized
message with a manual-entry fallback); `/demo/transcribe` and `/demo/check-pdf` need no key at
all. `docker compose up -d --build` (from the repo root) builds and runs the whole app
(`api` + `frontend`, no other services).

## Layering

```text
apps/api                     entrypoint only -- routing, DI wiring, process startup
  ↓
apps/api/demo_service.py     the three endpoints' orchestration
  ↓
workflows/report_fulfillment/agent.py       Qwen drafting agent            \  protected --
workflows/visual_audit/agent.py             Qwen visual-audit agent         > see below,
contexts/reports/domain/pricing.py          units -> USD cents (pure)      /  do not modify
shared/application/fx.py                    USD -> currency conversion    /
shared/infrastructure/stt/                  faster-whisper + PyAV        /
shared/infrastructure/pdf/                  ReportLab PDF renderer      /
shared/infrastructure/llm/connectors.py     the Qwen connector
```

`shared/application/ports.py` still declares `AiConnector`/`AudioInspector`/`SpeechTranscriber`
as `Protocol`s (structural typing) for type-hinting across the two AI calls and STT, but
`demo_service.py` calls the concrete STT/PDF classes directly rather than through a DI
container — there is no persistence layer left that would need to be swapped out in tests, so
the extra indirection was removed along with it.

## Contracts

`contracts/http/v1/demo.py` holds the three endpoints' request/response Pydantic models
(framework-free). Every mutating request is `multipart/form-data`, not JSON — every request
carries file bytes (audio, photos, or a signature), and the non-file fields travel as a single
`context` field containing a JSON string, parsed with `_parse_json_field()` in
`apps/api/routers/demo.py`. `contracts/http/v1/visual_audits.py` (the `VisualAuditResult`
shape) and `contracts/errors/v1/envelope.py` (the `{type, title, status, detail,
correlation_id, errors}` error shape, still returned by every endpoint) are unchanged from
Milestone 1.

## STT and AI product logic — protected

**Do not modify** `shared/infrastructure/stt/faster_whisper.py`,
`shared/infrastructure/stt/pyav_inspector.py`, `workflows/report_fulfillment/agent.py`,
`workflows/visual_audit/agent.py`, `contexts/reports/domain/pricing.py`,
`shared/application/fx.py`, or `shared/infrastructure/llm/connectors.py` without a specific,
explicit reason to change their behavior — these are the demo's actual value-producing
pipeline (already-working Whisper transcription; Qwen drafting + visual audit; deterministic
work-unit pricing), not incidental plumbing. `workflows/report_fulfillment/failures.py`
(`classify_analysis_failures`) is also load-bearing but safe to extend with new failure
categories. See [`../docs/architecture/ai.md`](../docs/architecture/ai.md) for what each piece
does and why. `contexts/reports/domain/` and `workflows/report_fulfillment/`,
`workflows/visual_audit/` only contain these protected files now — everything else that used
to live alongside them (the `Report` aggregate, the durable workflow engine, the two
background workers) was removed in [ADR-0007](../docs/adr/0007-local-demo-downgrade.md); don't
recreate that scaffolding to "properly" house a small change here.

The human-confirmation safety invariant that used to live in
`Report.mark_ready_for_signature()` (a domain-layer guard) is now a frontend precondition —
see [`../docs/architecture/ai.md`](../docs/architecture/ai.md#the-safety-invariant). If you're
touching the signature/confirmation flow, that's `frontend/components/jobact/screens/flow.tsx`,
not this codebase.

## Testing conventions

- `tests/domain/reports/test_pricing.py`, `tests/unit/test_fx.py` — pure-function tests for
  the deterministic pricing/currency conversion.
- `tests/unit/test_report_drafting_agent.py`, `tests/unit/test_visual_audit_agent.py` — the two
  agents' own structured-output/prompt-building behavior, via PydanticAI's `TestModel` (no
  network).
- `tests/unit/test_reportlab_renderer.py` — the PDF renderer.
- `tests/unit/test_demo_service.py`, `tests/unit/test_demo_router.py` — the three endpoints,
  with fakes for the transcriber/connector.
- `tests/unit/test_analysis_failures.py` — failure classification.
- `tests/unit/test_ai_connector_selection.py`, `test_ai_runtime_configuration.py` — the Qwen
  connector and `Settings` defaults.

No test in this suite calls a live model or needs Docker/Postgres/Redis running — everything
above is `uv run pytest`-able with no setup beyond `uv sync --dev`.
