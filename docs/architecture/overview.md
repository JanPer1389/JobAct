# Architecture Overview

Milestone 1 status: **implemented and running**, not a design document ahead of code. This
page describes what exists in `backend/` today. The private design diary that preceded it is
`PAPERCUT.md` (gitignored, not in version control) — this document and its siblings in
`docs/architecture/` are the committed, kept-current record; where they conflict with
`PAPERCUT.md`, these win, since `PAPERCUT.md` records intent and this records what shipped.

## Shape: contract-first modular monolith

One Python package (`jobact`), two entrypoints:

- `apps/api` — FastAPI HTTP app.
- `apps/worker` — a Redis Streams consumer that drains the outbox and drives the report
  fulfillment workflow's activities.

Both entrypoints sit on the same application/domain/infrastructure layers — there is no
network boundary between "the API" and "the worker" beyond the broker. See
[`backend/CLAUDE.md`](../../backend/CLAUDE.md) for the layering rules enforced in code.

```text
apps/api, apps/worker
    │
    ▼
contexts/<name>/application    command handlers, UnitOfWork boundary
    │
    ▼
contexts/<name>/domain         aggregates, invariants, domain events (pure Python)
    │
    ▼ (implements ports declared in shared/application/ports.py)
shared/infrastructure/         Postgres, Redis, MinIO/S3, Google OIDC, ReportLab, Qwen
```

## Bounded contexts

| Context | Aggregate(s) | Responsibility |
|---|---|---|
| `identity` | `User`, `Organization`, `Membership`, `Session` | Google sign-in, multi-tenant membership, cookie sessions |
| `customers` | `Customer` | Org-scoped customer records |
| `visits` | `Visit` | Visit lifecycle; simulated GPS/photo counts/notes as plain fields |
| `media` | `MediaAsset` | Upload lifecycle (`pending_upload → uploaded → attached`) for photos/signatures/PDFs |
| `reports` | `Report` (+ `ReportRevision`, `Material`, `Signature`) | Draft → confirm → sign → complete state machine |
| `workflows/report_fulfillment` | `WorkflowRun` | The durable saga tying visit → AI draft → signature → PDF together |

`shared/` holds only what every context needs and nothing domain-specific: primitives
(`Entity`, `AggregateRoot`, `DomainEvent`, `ValueObject`), the `UnitOfWork` protocol, the
external-system ports, and their infrastructure implementations.

## Request lifecycle

1. A route in `apps/api/routers/*` parses an HTTP v1 DTO (`contracts/http/v1`), resolves the
   current principal and organization from the session cookie, and calls one application
   handler.
2. The handler opens a `UnitOfWork`, loads the aggregate(s) through their repository, calls a
   domain method, and lets the UoW commit the aggregate's row changes and its pulled domain
   events (written to `platform.outbox`) in one transaction.
3. A separate outbox publisher loop moves committed, unpublished outbox rows onto a Redis
   Stream in `occurred_at` order.
4. `apps/worker` consumes the stream (deduping via `platform.inbox`), and dispatches to the
   report fulfillment workflow's activities, which persist their own progress in
   `workflow.workflow_runs` / `workflow.workflow_steps` with optimistic locking on
   `state_version`.

Every mutating HTTP request also carries a client-generated `Idempotency-Key`; a replay with
the same key and body returns the stored response instead of re-executing the handler
(`platform.idempotency_keys`, scoped per organization).

## What is real vs. simulated in this milestone

Real: Google OIDC sign-in and cookie sessions, customers, visit records, the full report
state machine, AI drafting via Qwen, the durable workflow, signature capture
and upload, PDF generation and storage, idempotency, the outbox/broker/worker path.

Deliberately still simulated (frontend-only, no backend integration): camera/photo capture
(counts only), GPS (a fixed value from a client-side timer), and voice-to-text (a canned
transcript or a typed-notes fallback feeding the same `raw_notes` field STT will eventually
populate). See [`docs/roadmap.md`](../roadmap.md) for when these graduate.

## Further reading

- [`erd.md`](erd.md) — schemas and tables.
- [`events.md`](events.md) — the domain event envelope and taxonomy.
- [`ai.md`](ai.md) — the drafting agent, its safety invariant, and cost tracking.
- `docs/adr/` — the specific trade-offs this milestone locked in and why.
