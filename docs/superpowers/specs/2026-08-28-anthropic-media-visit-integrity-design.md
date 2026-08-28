# Anthropic Compatibility and Media Visit Integrity Design

## Scope

Fix the Anthropic provider initialization failure caused by incompatible HTTP client types, and add database-enforced referential integrity from `operations.media_assets.visit_id` to `operations.visits.id`. Preserve the report-analysis fallback that persists a usable template revision and parks the workflow in `MANUAL_INPUT_REQUIRED` after an AI-provider failure.

## Anthropic compatibility

The resolved environment uses Python 3.12.10 under `uv`, `anthropic==1.0.0`, `httpx==0.28.1`, and `httpx2==2.12.0`. `anthropic.AsyncAnthropic` now declares `http_client: httpx2.AsyncClient | None`, while PydanticAI's `AnthropicProvider` and JobAct's connector boundary still accept and inject `httpx.AsyncClient`. Constructing the provider with JobAct's client reproducibly raises `TypeError` before a request is sent.

The lowest-risk fix is to constrain Anthropic to the latest compatible pre-1.0 release through a direct `anthropic<1` project dependency and regenerate `uv.lock`. This avoids creating parallel HTTP-client implementations or introducing provider-specific lifecycle branches. JobAct retains its existing context-managed `httpx.AsyncClient`, configured connect/request timeouts, response hooks, SDK retry behavior, certificate verification, and deterministic closure.

Regression tests will instantiate the real PydanticAI Anthropic provider through `AnthropicConnector`, exercise a request boundary without external network access, verify client injection and closure, and cover provider exceptions. Existing integration coverage for template persistence and `MANUAL_INPUT_REQUIRED` will remain active and receive any narrowly necessary strengthening.

## Media asset foreign key

`operations.media_assets.visit_id` is nullable because signatures and other report-scoped assets can legitimately have no visit association. When non-null, it must reference `operations.visits.id`. The current schema has a visit/phase/status lookup index but no foreign key. The application has no visit deletion command or established child-deletion lifecycle, so neither cascading deletion nor `SET NULL` is justified. The foreign key will use PostgreSQL's restrictive/default `NO ACTION` behavior, preserving evidence and blocking direct visit deletion while linked media exists.

SQLAlchemy table metadata will declare the same nullable foreign key. Application validation remains in place; the database constraint becomes the final concurrency-safe invariant.

## Production-safe migration

A new migration after revision `0014` will:

1. Count rows whose non-null `visit_id` has no matching visit.
2. Abort with an actionable migration error if the count is non-zero, without printing record content or modifying data.
3. Create a named foreign key only when the orphan count is zero.
4. Preserve `ix_media_assets_visit_phase_status` unchanged.

Downgrade removes only the named foreign key. A separate operator SQL file will report aggregate counts and orphan identifiers needed for controlled review. It will not automatically delete, null, archive, or guess relationships. Operators must repair or deliberately dispose of each orphan under an approved data-retention policy before retrying the migration.

The migration tests will verify successful upgrade/downgrade, rejection of an orphaned preflight state, valid nullable and linked assets, rejection of nonexistent visit IDs, and blocked visit deletion with linked assets.

## Compatibility and rollout

The Anthropic constraint changes only the resolved SDK major version; the connector interface and workflow behavior remain unchanged. The database change permits all currently valid nullable and linked rows. It can block deployment only when production contains orphaned non-null references, or block future direct visit deletion while media remains linked; both are intentional safeguards.

Rollout order is dependency lock deployment, orphan preflight review, schema migration, then application deployment. If preflight finds orphans, deployment stops without data mutation until operators complete the documented review and repair process.

## Validation

Run targeted connector, workflow-fallback, media integration, and migration tests, followed by:

```text
uv run pytest
uv run ruff check .
uv run mypy src tests
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
git diff --check
```
