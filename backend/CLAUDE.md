# CLAUDE.md (backend)

This file provides guidance to Claude Code when working with code in `backend/`. See the
[root CLAUDE.md](../CLAUDE.md) for the overall repo layout.

## Project

JobAct's backend is a contract-first modular monolith serving one vertical slice:
visit → AI-drafted report → real customer signature → signed PDF. See
[`docs/architecture/overview.md`](../docs/architecture/overview.md) for the full design and
[`docs/roadmap.md`](../docs/roadmap.md) for what is deliberately still simulated in the
frontend (photos, GPS, voice transcription).

## Commands

Run these from `backend/`. Package manager is `uv`.

```bash
uv sync --dev                                        # install runtime + dev dependencies
uv run uvicorn jobact.apps.api.main:app --reload --port 8000   # run the API
uv run python -m jobact.apps.worker                  # run the Redis Streams worker
uv run alembic upgrade head                          # apply migrations
uv run alembic revision -m "..." --autogenerate       # draft a new migration (review it by hand)
uv run pytest                                        # domain/contract/workflow tests + integration tests
uv run ruff check .                                  # lint
uv run mypy src tests                                # type check
```

`docker compose up -d` (from `backend/`) starts Postgres 17, Redis 8, MinIO (+ a one-shot
bucket-init container), and a LiteLLM proxy in front of OpenRouter. Copy `.env.example` to
`.env` first and fill in `OPENROUTER_API_KEY` if you want AI drafting to produce real output
— everything else has working local defaults. Integration tests that touch Postgres/Redis/
MinIO need this stack running; domain, contract, and workflow tests do not.

## Layering rules

```text
apps/api, apps/worker        entrypoints only — routing, DI wiring, process startup
  ↓
contexts/<name>/application   command handlers; own the UnitOfWork/transaction boundary
  ↓
contexts/<name>/domain        aggregates, value objects, domain events — pure Python
  ↓ (implemented by, never imported by domain)
contexts/<name>/infrastructure  SQLAlchemy repositories, adapters
```

**Domain imports nothing from infrastructure, FastAPI, SQLAlchemy, Redis, or httpx.**
`shared/domain/` (`Entity`, `AggregateRoot`, `DomainEvent`, `ValueObject`) is the only thing a
context's domain package may import beyond the standard library. If a domain file needs to
import a driver or framework, the logic belongs in `application/` or `infrastructure/`
instead.

`shared/application/ports.py` defines every external dependency (`ObjectStorage`,
`MessageBroker`, `IdentityProvider`, `PdfRenderer`, `LlmGateway`, `Clock`, `IdGenerator`) as a
`Protocol`. Application handlers depend on these ports, never on a concrete adapter — see
`tests/fakes.py` for the in-memory fakes used everywhere in domain/application/workflow
tests. Only integration tests exercise the real adapters in `shared/infrastructure/`.

`UnitOfWork` (`shared/application/uow.py`) is the only place a transaction commits. A command
handler pulls domain events off the aggregate (`aggregate.pull_events()`) and the UoW writes
them to `platform.outbox` in the *same* transaction as the aggregate's own row changes —
never commit an aggregate change and publish its event as two separate operations.

Repositories are one per aggregate root (`VisitRepository`, `ReportRepository`,
`CustomerRepository`, `MediaAssetRepository`, ...), not one per query. Every repository
method that reads or writes an `organization_id`-scoped row filters by the caller's
organization itself — this is enforced at the repository, not trusted to the router.

## Contracts

`contracts/http/v1`, `contracts/workflow/v1`, `contracts/errors/v1` hold framework-free
Pydantic DTOs versioned independently of the domain model. A route handler converts
HTTP DTO → application command → domain call, and converts the result back — it never
passes a domain object straight to a Pydantic response model. Within a version, only
optional fields may be added; anything else is a new version.

`tests/contract/test_reports_openapi.py` asserts the generated OpenAPI schema against a
committed snapshot — regenerate the snapshot deliberately when the contract changes, don't
let a diff silently drift.

## Workflow engine

`workflows/report_fulfillment/` is a durable saga, not a hidden chain of Redis jobs. Its
states live in `states.py`; `ALLOWED_TRANSITIONS` is the single source of truth for legal
moves, and `MANUAL_INPUT_REQUIRED` is reachable from every non-terminal state but is never a
transition's *source* — resuming a parked run is a manual, out-of-band operation. Run/step
persistence uses optimistic locking on `state_version`; a stale write raises rather than
silently overwriting a concurrent transition. Activities take and return strict DTOs from
`contracts/workflow/v1` and must be safe to retry (id-driven idempotency, not "run twice by
accident" tolerance).

## AI drafting

See [`docs/architecture/ai.md`](../docs/architecture/ai.md) for the full design. The load-bearing
invariant is in the domain, not the prompt: `Report.mark_ready_for_signature()` raises unless
the current revision has both `confirmed_by_user_at` and `amount_confirmed_at` set, so an
AI-proposed amount can never reach a signed document without an explicit human confirmation.
Do not relax this for convenience — see ADR-0006 and the AI design doc for why.

## Testing conventions

- `tests/domain/`, `tests/application/`, `tests/workflow/` — no real Postgres/Redis/MinIO;
  use the fakes in `tests/fakes.py`.
- `tests/contract/` — OpenAPI snapshot and schema shape assertions.
- `tests/integration/` — real Postgres/Redis/MinIO via `docker compose up -d`; a fake drafting
  function still stands in for the live model everywhere in this suite.
- An opt-in live-model smoke test (`JOBACT_LIVE_LLM_TESTS=1`) is called for by the plan but
  not yet written — see [`docs/architecture/ai.md`](../docs/architecture/ai.md). Never add
  one that runs by default in CI.
