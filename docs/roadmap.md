# Roadmap

Milestone 1 (this repository's current state) proves one vertical slice end-to-end: visit →
AI-drafted report → real customer signature → signed PDF, with cookie-based Google sign-in.
See [`docs/architecture/overview.md`](architecture/overview.md) for what's real vs. simulated
today.

## Milestone 2 — Photos, GPS, offline queue

- Real camera capture and upload, reusing the existing `MediaAsset` pending_upload → uploaded
  → attached pipeline and presigned-URL flow (already proven end-to-end by the signature
  upload) — this is endpoint reuse, not new plumbing.
- Real device GPS instead of the fixed simulated coordinate PATCHed today.
- The offline queue PAPERCUT's design assumes: client-side command queuing while offline,
  replayed on reconnect. Milestone 1 deliberately only laid the groundwork this needs
  (client-generated entity UUIDs, `Idempotency-Key` on every mutation) without building the
  queue itself.
- A lint or CI check enforcing the no-cross-context-infrastructure-import rule from
  [ADR-0001](adr/0001-modular-monolith.md), before more contexts make a violation likely.

## Milestone 3 — Speech-to-text

- `TranscribeAudioActivity`, populating the same `raw_notes` field the AI drafting agent
  already reads (see [`ai.md`](architecture/ai.md)) — no change needed downstream of it.
- Registering `TRANSCRIPTION_PENDING` in the workflow's `ALLOWED_TRANSITIONS`
  (`workflows/report_fulfillment/states.py`); it's already defined in the design, just
  unregistered because nothing produces it yet.
- The opt-in live-model smoke test (`JOBACT_LIVE_LLM_TESTS=1`, gated off in CI) that Milestone
  1's plan called for but that was not written this session — see [`ai.md`](architecture/ai.md).

## Milestone 4 — Delivery, analytics, attribution

- `DELIVERY_PENDING` (defined, unregistered, same as `TRANSCRIPTION_PENDING`) and a
  `DeliverReportActivity` — sending the completed PDF to the customer.
- The `attribution` and `analytics` Postgres schemas PAPERCUT specifies but Milestone 1
  deliberately deferred (see [ADR-0001](adr/0001-modular-monolith.md) and
  [`erd.md`](architecture/erd.md)) — `analytics.user_milestones`, `analytics.product_events`,
  `attribution.touchpoints`, `attribution.user_attribution`.
- Adopting PAPERCUT's dotted event-name taxonomy (`report.signed`, `media.upload_completed`,
  ...) for `platform.outbox.event_type`, replacing or supplementing today's Python-class-name
  values — see the naming deviation recorded in [`events.md`](architecture/events.md) — and
  emitting the domain events that today are notably *not* emitted (customer creation, media
  attach, report confirm/sign, workflow transitions) now that something outside the workflow
  itself needs to react to them.
- Populating the `audit` schema (created but empty since the Milestone 1 baseline migration)
  with an actual `audit.audit_log` table and the handlers that write to it.
- A legal/compliance review of data residency, consent, and retention for the Russian launch
  PAPERCUT's design targets — flagged in [ADR-0004](adr/0004-cookie-sessions-google-oidc.md)
  regarding Google OIDC specifically, and more broadly wherever personal data, location, or
  device identifiers are collected.

## Open items not tied to a specific milestone

- `correlation_id`/`causation_id` are in PAPERCUT's original event envelope sketch but not yet
  threaded through `DomainEvent` or the outbox row (see [`events.md`](architecture/events.md))
  — needed once tracing a chain of triggered events becomes necessary.
- Amending a signed report (PAPERCUT: "corrections create a new revision chain") is refused by
  the domain state machine today rather than supported — the state machine already protects
  the invariant, but the amendment endpoint itself doesn't exist yet.
