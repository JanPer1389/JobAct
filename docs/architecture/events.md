# Domain Events

## Envelope

Every event travels from aggregate → outbox → Redis Stream in the shape below
(`platform.outbox` columns / `contracts/events/v1` envelope, matching PAPERCUT):

```json
{
  "event_id": "uuid",
  "event_type": "VisitStarted",
  "event_version": 1,
  "occurred_at": "2026-08-26T12:00:00Z",
  "aggregate_type": "Visit",
  "aggregate_id": "uuid",
  "payload": { "...": "event-specific fields" }
}
```

**Naming deviation from PAPERCUT, recorded here deliberately:** PAPERCUT's design examples
use a dotted, past-tense taxonomy (`visit.started`, `report.signed`,
`media.upload_completed`) for analytics-style event names. What ships in this milestone
stamps `event_type` as the Python class name of the concrete `DomainEvent` subclass (e.g.
`"VisitStarted"`, from `type(event).__name__` in `SqlAlchemyUnitOfWork`) — see
`shared/infrastructure/postgres/uow.py`. This is simpler and was sufficient for the one event
this milestone emits, but it is not the dotted taxonomy PAPERCUT specifies for the
`analytics.product_events` table that doesn't exist yet (see [`erd.md`](erd.md) and the
roadmap). Adopting the dotted naming — and deciding whether it lives alongside or replaces
the class-name `event_type` — is open work for the milestone that builds `analytics`.

`correlation_id`/`causation_id` from PAPERCUT's original envelope sketch are not yet threaded
through `DomainEvent` or the outbox row; every event today is its own correlation root. Worth
revisiting once a workflow run needs to trace which HTTP request or upstream event triggered
which downstream one across a chain longer than "one command produced one event."

## What's actually emitted in this milestone

| Event | Aggregate | Emitted by | Payload |
|---|---|---|---|
| `VisitStarted` | `Visit` | `Visit.start()` (`contexts/visits/domain/visit.py`) | `organization_id`, `customer_id` |

That's the only domain event wired end-to-end (aggregate → `pull_events()` →
`UnitOfWork.commit()` → `platform.outbox` row) today. Every other lifecycle transition this
milestone implements — customer creation, media upload/attach, report drafting/confirmation/
signing, workflow state transitions, PDF completion — is fully real as a *state change*, but
none of it currently also emits a `DomainEvent`. They are correct today because the report
fulfillment workflow drives its own state machine directly (via `WorkflowRunRepository`, not
via consuming its own domain events), so nothing downstream is missing data. The gap matters
the moment something *outside* the workflow (analytics, a notification, a future delivery
channel) needs to react to "a report was signed" — that requires adding a `ReportSigned`
(and friends) `DomainEvent`, which is straightforward given the pattern `VisitStarted`
already establishes.

## Outbox → broker → worker

1. A command handler's `UnitOfWork.commit()` writes the aggregate's row changes and its
   pulled domain events (as outbox rows) in one transaction. An event written inside a
   transaction that later rolls back is never persisted, let alone published.
2. `shared/infrastructure/postgres/outbox_publisher.py` polls `platform.outbox` for rows
   with `published_at IS NULL`, publishes each to a Redis Stream via the `MessageBroker` port
   (`shared/infrastructure/redis/streams.py`), and stamps `published_at` — so a publish that
   crashes mid-way is retried, not silently dropped, and a crash *after* the Redis write but
   before the stamp can double-publish (the stream is at-least-once; consumers must dedupe).
3. `apps/worker` consumes via a Redis Streams consumer group, checks `platform.inbox` for the
   message id before dispatching (dedup on redelivery), runs the registered handler, then
   acks and records the id in `platform.inbox`.

## Event vs. workflow-activity DTOs

Domain events (`shared/domain/events.py`, e.g. `VisitStarted`) and workflow activity DTOs
(`contracts/workflow/v1/activity.py`) are deliberately different types serving different
layers — a domain event is "something that happened," framework-free, emitted from inside an
aggregate method; an activity DTO is "what a workflow step needs as input/output," and is
never emitted from domain code. Don't conflate them when adding a new one.
