# ADR-0001: Contract-first modular monolith, not microservices

## Status

Accepted, implemented (Milestone 1).

## Context

PAPERCUT's design already separates the system into bounded contexts (`identity`,
`customers`, `visits`, `reports`, `media`, plus `workflows`) with their own domain models and
repositories. The question was whether to deploy them as separate services from day one.

## Decision

One Python package (`jobact`), two entrypoints — `apps/api` (FastAPI) and `apps/worker`
(Redis Streams consumer) — sharing the same domain/application layers. Contexts are modules,
not services: `contexts/<name>/{domain,application,infrastructure}`, each with its own
aggregates and repositories, but all in one deployable unit per entrypoint.

`shared/domain/` (`Entity`, `AggregateRoot`, `DomainEvent`, `ValueObject`) is the only
cross-context import a context's domain package may take. `shared/application/ports.py`
declares every external dependency as a `Protocol`; contexts depend on ports, never on
another context's infrastructure directly.

Four Postgres schemas (`identity`, `operations`, `workflow`, `platform`), not one, so
context boundaries are visible at the database level even inside one physical database — see
[`erd.md`](../architecture/erd.md).

## Consequences

- Deploying, scaling, and operating one thing in Milestone 1 — no service mesh, no
  distributed tracing requirement, no network call between "reports" and "visits."
- Splitting a context into its own service later is a lift-and-shift of one
  `contexts/<name>/` directory plus its schema, not a rewrite — *if* the domain/
  infrastructure boundary inside that context stayed clean, which is exactly what
  `backend/CLAUDE.md`'s layering rules exist to protect.
- The cost: nothing stops a lazy import from a context's `infrastructure/` into another
  context's `domain/` except code review discipline — there is no build-time enforcement
  (e.g. a lint rule on cross-context imports) yet. Worth adding before the monolith grows
  past this milestone's five contexts.

## Deviation from PAPERCUT's literal directory sketch

PAPERCUT sketches `backend/apps/` and `backend/src/jobact/...` as siblings. This repo instead
nests `apps/` inside the package (`backend/src/jobact/apps/api`, `backend/src/jobact/apps/
worker`), because `uv_build` (via `[tool.uv.build-backend] module-name = "jobact"`) expects a
single `src/<module>` tree — fighting that build backend to preserve a directory sketch buys
nothing, and the layering intent (entrypoints as thin shells over contexts) is unchanged.

PAPERCUT also specifies seven schemas (`identity`, `attribution`, `operations`, `workflow`,
`audit`, `analytics`, `platform`); this milestone ships five (`attribution` and `analytics`
deferred — nothing in this vertical slice reads them, and the event taxonomy that would
justify them is written down in [`events.md`](../architecture/events.md) for when they're
needed, not built speculatively now). `audit` exists as an empty schema with no populated
table yet.
