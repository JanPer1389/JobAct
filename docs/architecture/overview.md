# Architecture Overview

This describes what exists in `backend/`/`frontend/` today, after the local-demo downgrade
recorded in [ADR-0007](../adr/0007-local-demo-downgrade.md). The private design diary that
preceded Milestone 1 is `PAPERCUT.md` (gitignored, not in version control) — where it disagrees
with this document, this document wins, since `PAPERCUT.md` records intent at various points in
time and this records what's actually running. Milestone 1's production-shaped design (Postgres,
Redis, MinIO, Google OAuth, a durable workflow engine) is preserved as historical record in
[ADR-0001](../adr/0001-modular-monolith.md) through
[ADR-0005](../adr/0005-outbox-saga-idempotency.md); it is not what runs today.

## Shape: browser-local state, two stateless backend endpoints for protected AI/STT work

```text
Browser (all normal state)
├── localStorage — locale, currency, demo user name, active-draft pointer
└── IndexedDB "jobact-demo" (frontend/lib/jobact/local-db.ts, local-store.ts)
    ├── drafts   — the in-progress "Создать чек" flow
    ├── blobs    — photo/audio/signature/PDF bytes
    └── checks   — completed, signed checks (local history)
         │
         │  multipart/form-data — bytes in, structured result back, nothing persisted server-side
         ▼
FastAPI (apps/api, one stateless process — no DB, no Redis, no object storage, no workers)
├── POST /api/v1/demo/transcribe  → the protected STT pipeline (faster-whisper)
├── POST /api/v1/demo/analyze     → the protected AI pipeline (Qwen drafting + visual audit)
└── POST /api/v1/demo/check-pdf   → ReportLab PDF rendering
         │
         ▼
Qwen / DashScope — the only outbound network call; DASHSCOPE_API_KEY never reaches the browser
```

One Python package (`jobact`), one entrypoint (`apps/api`). See
[`backend/CLAUDE.md`](../../backend/CLAUDE.md) for layering rules and
[`frontend/CLAUDE.md`](../../frontend/CLAUDE.md) for the frontend's screen/state architecture.

## What survives from Milestone 1, unmodified

- `shared/infrastructure/stt/faster_whisper.py`, `pyav_inspector.py` — the Whisper transcription
  pipeline. Protected; see [`ai.md`](ai.md#speech-to-text).
- `workflows/report_fulfillment/agent.py`, `workflows/visual_audit/agent.py`,
  `contexts/reports/domain/pricing.py`, `shared/application/fx.py`,
  `shared/infrastructure/llm/connectors.py`, `contracts/http/v1/visual_audits.py` — the AI
  drafting + visual-audit product logic. Protected; see [`ai.md`](ai.md).
- `shared/infrastructure/pdf/reportlab_renderer.py` — the signed-check PDF renderer, including
  its Cyrillic (Noto) font registration.
- `frontend/lib/jobact/i18n.ts` — the full ru-RU/en-US localization layer (only its *default*
  locale changed, to `ru-RU`).
- `frontend/lib/jobact/audio-recorder.ts` — the browser `MediaRecorder` wrapper.
- The evidence/voice/review/signature flow screens
  (`frontend/components/jobact/screens/flow.tsx`) — same UI, rewired from backend API calls to
  local storage + the three demo endpoints.

## What moved to the browser

Normal application state — the in-progress draft, captured photos, recorded audio, the AI
result, and the completed-check history — lives in the browser via `localStorage` (small
preferences) and IndexedDB (structured records and blobs). See
[`frontend/CLAUDE.md`](../../frontend/CLAUDE.md) for the local-persistence design. The backend
never stores evidence: it receives bytes in one request and returns a result in the same
response.

## What was removed

PostgreSQL, SQLAlchemy, Alembic, Redis, MinIO/S3, Google OAuth, server sessions, the durable
saga workflow engine, the outbox/inbox/idempotency-key middleware, both background workers, and
the six `contexts/` bounded contexts (identity, customers, visits, media, reports minus
`pricing.py`, visual_audits) that existed to persist state in Postgres. See
[ADR-0007](../adr/0007-local-demo-downgrade.md) for the full KEEP/REMOVE reasoning.

## Request lifecycle

1. The browser posts evidence (audio bytes, or job context + before/after photo bytes, or a
   signature PNG + report context) as `multipart/form-data` to one of the three
   `/api/v1/demo/*` routes.
2. `apps/api/demo_service.py` runs the protected STT or AI logic directly against the request
   bytes — no queue, no database row created first.
3. The endpoint returns the result (a transcript, a structured analysis, or PDF bytes) in the
   same HTTP response. The frontend writes it into IndexedDB.

There is no idempotency layer: a duplicate request (e.g. a double-tapped retry) simply runs the
protected work twice, which costs tokens/compute but cannot corrupt state, since nothing is
shared server-side between requests.

## Default language and currency

Fresh browser state defaults to `locale = ru-RU`, `currency = RUB`
(`frontend/lib/jobact/local-prefs.ts`), read from `localStorage` once set. English/USD remain
fully supported and independent of each other, per the existing localization layer.
