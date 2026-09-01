# ADR-0005: Transactional outbox + durable saga + idempotency, not `arq` job queues

## Status

Accepted, implemented (Milestone 1). **Superseded for normal demo operation by
[ADR-0007](0007-local-demo-downgrade.md)** — the demo's AI/STT calls run synchronously in the
request with no durable retry; kept here as the historical record and reference design for a
future real deployment.

## Context

The report fulfillment path (AI drafting, PDF generation) is long-running and must survive a
crash mid-flight without losing or duplicating work, and the frontend is designed offline-
first, meaning the same client mutation may be retried after a network gap. PAPERCUT's design
calls for a transactional outbox, Redis Streams as the broker, a durable saga for the
multi-step workflow, and client-generated idempotency keys — as one coherent reliability
story, not four independent mechanisms.

## Decision

- **Outbox**: `UnitOfWork.commit()` writes an aggregate's row changes and its pulled domain
  events to `platform.outbox` in one transaction (`shared/infrastructure/postgres/uow.py`).
  An event from a rolled-back transaction is never persisted.
- **Broker**: Redis Streams behind a `MessageBroker` port
  (`shared/infrastructure/redis/streams.py`), with consumer groups — not `arq`. Durability
  already comes from the outbox; layering `arq`'s own job-state model on top would compete
  with it rather than add anything, and the consumer loop is small (~150 lines) built
  directly on Streams.
- **Publisher**: a loop drains unpublished outbox rows in `occurred_at` order and stamps
  `published_at`, so publishing is at-least-once and resumable after a crash
  (`shared/infrastructure/postgres/outbox_publisher.py`).
- **Worker/inbox**: `apps/worker` dedupes redelivered messages via `platform.inbox`
  (`message_id` primary key) before dispatching to a handler registry, with exponential
  backoff and a park-on-exhaustion path.
- **Saga**: `workflows/report_fulfillment/` is a `WorkflowRun` aggregate with its own state
  (`workflow.workflow_runs`/`workflow.workflow_steps`), explicit `ALLOWED_TRANSITIONS`
  (`states.py`), and optimistic locking on `state_version` — a stale-version write raises
  rather than clobbering a concurrent transition. No single long transaction spans the whole
  drafting/signing/PDF flow; each activity commits its own step.
- **Idempotency**: every mutating HTTP request carries a client-generated `Idempotency-Key`;
  `platform.idempotency_keys` (composite PK `(key, organization_id)`) stores the request hash
  and response so a replay with the same key and body returns the stored response without
  re-executing the handler, and a reused key with a different body is rejected (409).

## Consequences

- Retrying an offline-queued mutation, or a redelivered broker message, or a workflow step
  after a crash, are all the same solved problem — dedupe at the boundary, don't rely on the
  caller (client or broker) to only ever send something once.
- `MANUAL_INPUT_REQUIRED` (reachable from every non-terminal workflow state, never a
  transition's source) means retry exhaustion in *any* step degrades to "a human finishes
  this by hand," never a stuck or silently-failed report — verified directly by
  `tests/integration/test_workflow_runner.py`'s three-failures-parks-the-run case.
- The idempotency-key uniqueness scope had to be corrected from a global `key` primary key to
  composite `(key, organization_id)` (migration 0003) after the baseline shipped — two
  different organizations can legitimately generate the same client-side UUID, and a global
  PK would have made the second organization's request fail outright instead of behaving like
  a normal, unrelated mutation.
