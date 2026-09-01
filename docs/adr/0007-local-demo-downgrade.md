# ADR-0007: Local-demo downgrade — browser-local persistence, two stateless AI/STT endpoints

## Status

Accepted, implemented.

Supersedes [ADR-0001](0001-modular-monolith.md) (modular monolith with Postgres-backed
contexts), [ADR-0003](0003-object-storage-abstraction.md) (object storage abstraction),
[ADR-0004](0004-cookie-sessions-google-oidc.md) (cookie sessions / Google OIDC), and
[ADR-0005](0005-outbox-saga-idempotency.md) (outbox/saga/idempotency) for normal demo
operation. Those ADRs remain as the historical record of Milestone 1's production-shaped
architecture; nothing in this ADR invalidates their reasoning for a future real deployment,
it just states that the demo no longer runs that architecture.

## Context

Milestone 1 built a real, production-shaped vertical slice: Google OAuth, Postgres-backed
identity/customers/visits/reports/media/visual-audit aggregates, a durable saga workflow
engine with outbox/inbox/idempotency tables, two Redis Streams workers, and MinIO object
storage — considerably more infrastructure than a demonstration needs. The task was to
downgrade to a minimal, easy-to-run local demo while preserving the two genuinely valuable,
already-working capabilities: the Whisper speech-to-text pipeline and the Qwen-based AI
report-drafting/visual-audit pipeline, without regressing either.

Inspection found both were already infrastructure-free at their core:
`FasterWhisperTranscriber`/`PyAvAudioInspector` take bytes in and structured output out with
no database/queue/storage dependency, and `draft_report()`/`run_visual_audit()`
(`workflows/report_fulfillment/agent.py`, `workflows/visual_audit/agent.py`) take a context
object and image bytes and return validated Pydantic output the same way. Every piece of
infrastructure removed by this change was orchestration *around* those two capabilities, not
inside them.

## Decision

- **Delete** the durable workflow engine, all six `contexts/` (identity, customers, visits,
  media, reports, visual_audits) except `contexts/reports/domain/pricing.py`, both background
  workers, the outbox/inbox/idempotency middleware, and the Postgres/Redis/MinIO/identity-
  provider infrastructure adapters and their Alembic migrations.
- **Keep verbatim** — zero behavioral changes — `faster_whisper.py`, `pyav_inspector.py`,
  `report_fulfillment/agent.py`, `visual_audit/agent.py`, `contexts/reports/domain/pricing.py`,
  `shared/application/fx.py`, `shared/infrastructure/llm/connectors.py`,
  `contracts/http/v1/visual_audits.py`, and `shared/infrastructure/pdf/reportlab_renderer.py`.
  `workflows/report_fulfillment/activities/transcribe_audio.py` keeps its exception types and
  size/duration constants (still imported by the two STT files above) but loses the
  Postgres-claim-and-lease orchestration class that used to share the file.
- **Replace** the API surface with three stateless endpoints
  (`apps/api/routers/demo.py`/`demo_service.py`): `POST /demo/transcribe`,
  `POST /demo/analyze`, `POST /demo/check-pdf`. Each does one unit of protected work per
  request and returns the result directly — no persistence, no polling, no idempotency key.
- **Move normal application state to the browser.** `localStorage` holds small preferences
  (locale, currency, demo user name, the active-draft pointer); IndexedDB
  (`frontend/lib/jobact/local-db.ts`/`local-store.ts`) holds structured drafts, photo/audio/
  signature/PDF blobs, and the completed-check history. The backend never stores evidence —
  it receives bytes in a request and returns a result.
- **Replace authentication** with a local-only demo identity (a name typed once, stored in
  `localStorage`) — no server session, no password, no OAuth.
- **Collapse the dashboard** (reports archive, customers CRUD, profile, sync/offline/states
  screens) into one entry screen and one home screen centered on a single primary action
  («Создать чек»), reusing the existing evidence/voice/review/signature flow components
  unchanged.
- **Default to `ru-RU`/`RUB`**, reading the existing localization layer
  (`frontend/lib/jobact/i18n.ts`) rather than rebuilding it.

## Consequences

- No durable retry, resumable workflow, or exactly-once execution guarantee survives — a lost
  connection mid-analysis loses that request; the technician retries. Draft state itself
  (notes, photos, GPS) is always safe in IndexedDB regardless.
- `Report.mark_ready_for_signature()`'s human-confirmation invariant ("AI proposes, the user
  confirms") no longer exists as a domain-layer guard — it is re-expressed as a frontend
  precondition (`draft.amountConfirmed` gates the signature step). This is a real downgrade in
  where the invariant is enforced, recorded here rather than silently accepted.
- Provider failover across multiple AI vendors is gone because there was only ever one
  provider (Qwen) left to fail over to after the earlier Anthropic/OpenRouter removal; nothing
  new was lost here.
- Local data does not survive a cleared browser profile or a different device. The signed PDF,
  once downloaded, is the durable artifact a technician actually keeps.
- Docker Compose drops from seven services (postgres, redis, minio, minio-init, api, worker,
  stt-worker) to two (api, frontend); the `faster-whisper`/`av` dependencies move from an
  optional `stt` extra built into a separate image to the single api image's normal
  dependencies, since there is only one backend process now.
