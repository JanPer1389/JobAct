# ADR-0002: Contract-first, versioned DTOs separate from the domain model

## Status

Accepted, implemented (Milestone 1).

## Context

PAPERCUT calls for a four-layer validation pipeline (syntactic → contract → business →
process) and a strict separation: `HTTP DTO → Application Command DTO → Domain model`,
`Domain Event → Event DTO → Workflow Activity DTO`. The alternative — letting FastAPI
serialize domain objects directly, or letting a workflow activity take a domain aggregate as
its input — is faster to write and was rejected.

## Decision

`contracts/http/v1`, `contracts/workflow/v1`, and `contracts/errors/v1` hold Pydantic v2 DTOs
that are versioned independently of the domain model and of each other. A route handler's job
is: parse the HTTP v1 DTO → call an application handler with plain arguments (or a small
command object) → the handler drives the domain aggregate → the handler builds the response
DTO from the aggregate's resulting state. No domain object crosses the HTTP boundary
directly, and no workflow activity takes a domain aggregate as its `run()` input — it takes
IDs and a `contracts/workflow/v1` DTO, then loads the aggregate itself inside its own
`UnitOfWork`.

`tests/contract/test_reports_openapi.py` pins the generated OpenAPI schema against a
committed snapshot so a contract change is a deliberate, reviewed diff, not an accidental
side effect of refactoring a response model's field order.

The event envelope (`event_id`, `event_type`, `event_version`, `occurred_at`,
`aggregate_type`, `aggregate_id`, `payload`) matches PAPERCUT's sketch with one recorded
deviation — see [`events.md`](../architecture/events.md) for the `event_type` naming gap
(class name today, not PAPERCUT's dotted `visit.started` taxonomy) and the not-yet-threaded
`correlation_id`/`causation_id` fields.

## Consequences

- A v1 contract can only gain optional fields without a version bump; removing, renaming, or
  changing the meaning of a field requires a new version. This is not yet tested by anything
  beyond code review — there's no automated "diff two OpenAPI versions and flag a breaking
  change" check in this milestone.
- Contract, domain, and workflow tests can run without a database (`tests/contract/`,
  `tests/domain/`, `tests/workflow/`-shaped tests under `tests/unit/` and `tests/application/`
  all use fakes) — only `tests/integration/` needs Postgres/Redis/MinIO, which is what makes
  the fast local test loop possible without Docker running.
