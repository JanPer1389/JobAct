# Anthropic Compatibility and Media Visit Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore Anthropic drafting with the existing managed HTTP client and enforce valid non-null media-to-visit references through a production-safe PostgreSQL migration.

**Architecture:** Constrain the transitive Anthropic SDK to its legacy-`httpx` compatible major line, retaining the connector and client lifecycle. Add a nullable, restrictive foreign key in SQLAlchemy metadata and Alembic, guarded by a non-destructive orphan preflight and supported by an operator diagnostic query.

**Tech Stack:** Python 3.12+, uv, anthropic, httpx, PydanticAI, SQLAlchemy Core, Alembic, PostgreSQL, pytest.

**Spec:** `docs/superpowers/specs/2026-08-28-anthropic-media-visit-integrity-design.md`

## Global Constraints

- Preserve template-draft persistence and `MANUAL_INPUT_REQUIRED` on every AI-provider failure.
- Preserve configured request/connect timeouts, SDK retries, TLS verification, response hooks, and deterministic HTTP client closure.
- Keep `media_assets.visit_id` nullable and retain `ix_media_assets_visit_phase_status`.
- Do not automatically modify or delete orphaned production records.
- Never log API keys, notes, prompts, or AI output.

---

### Task 1: Anthropic HTTP compatibility regression

**Files:**
- Modify: `backend/tests/unit/test_ai_connector_selection.py`
- Modify: `backend/tests/unit/test_report_drafting_agent.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock`

**Interfaces:**
- Consumes: `AnthropicConnector.build_model(alias, http_client)` and `draft_report(connector, context)`.
- Produces: a resolved pre-1.0 Anthropic SDK accepting `httpx.AsyncClient` without changing application interfaces.

- [ ] Add a test that constructs `AnthropicConnector("test-key").build_model("report-drafter", http_client=httpx.AsyncClient(...))`; the current environment must fail with the reproduced `TypeError`.
- [ ] Add a request-boundary test using `httpx.MockTransport` that proves the injected client reaches Anthropic request handling without a client-type error and provider HTTP failures propagate without exposing payloads.
- [ ] Add a lifecycle test around `draft_report`'s managed client that proves closure after both success and provider failure.
- [ ] Run the focused tests and record the expected failure against `anthropic==1.0.0`.
- [ ] Add `anthropic<1` to runtime dependencies and run `uv lock` so manifest and lock agree.
- [ ] Re-run focused tests and verify they pass with the resolved SDK version.

### Task 2: Preserve durable AI fallback

**Files:**
- Modify only if coverage is incomplete: `backend/tests/integration/test_report_analysis_failure.py`

**Interfaces:**
- Consumes: report-analysis activity and workflow run persistence.
- Produces: regression proof that a provider exception persists a usable template revision and parks the run in `MANUAL_INPUT_REQUIRED`.

- [ ] Inspect existing failure tests and name any missing observable invariant.
- [ ] If needed, add a failing assertion/test for persisted template content, workflow state, and non-stuck terminal activity behavior.
- [ ] Run the focused integration test before and after any test-only strengthening; do not change fallback production behavior unless the regression exposes a defect.

### Task 3: Database referential-integrity regression

**Files:**
- Modify: `backend/tests/integration/test_media_handlers.py`
- Create: `backend/tests/integration/test_media_asset_visit_fk_migration.py`

**Interfaces:**
- Consumes: `operations.media_assets`, `operations.visits`, Alembic revisions `0014` and new `0015`.
- Produces: behavioral coverage for nullable assets, valid links, invalid links, restricted visit deletion, preflight failure, upgrade, and downgrade.

- [ ] Add integration fixtures that create the minimum valid customer/visit/media rows and clean children before parents.
- [ ] Add tests proving a valid visit link and a null visit link persist.
- [ ] Add a test proving an unknown non-null `visit_id` raises `IntegrityError`; verify it fails before the FK exists.
- [ ] Add a test proving deleting a linked visit raises `IntegrityError` after migration.
- [ ] Add migration tests that downgrade to `0014`, insert an orphan, verify upgrade to `0015` aborts without modifying it, repair it explicitly in test setup, then verify upgrade/downgrade/upgrade behavior.

### Task 4: Safe foreign-key migration and metadata

**Files:**
- Modify: `backend/src/jobact/shared/infrastructure/postgres/operations_tables.py`
- Create: `backend/migrations/versions/20260828_0000_0015_media_assets_visit_fk.py`
- Create: `backend/docs/operations/media_assets_visit_fk_preflight.sql`

**Interfaces:**
- Produces: named constraint `fk_media_assets_visit_id_visits`, nullable `visit_id`, default PostgreSQL `NO ACTION`, and a read-only operator report.

- [ ] Add `ForeignKey("operations.visits.id", name="fk_media_assets_visit_id_visits")` to metadata.
- [ ] In migration `upgrade`, execute a parameter-free orphan count query and raise `RuntimeError` containing only the count and remediation-file path when nonzero.
- [ ] Create the named foreign key only after a zero count; leave the existing index unchanged.
- [ ] In `downgrade`, drop only `fk_media_assets_visit_id_visits`.
- [ ] Add read-only SQL returning total/null/orphan counts and orphan identifiers, with no automatic remediation statements.
- [ ] Run the focused database and migration tests until green.

### Task 5: Full verification and report

**Files:**
- Inspect all changed files; do not modify unrelated user work.

**Interfaces:**
- Produces: fresh validation evidence and the requested diagnosis/fix report.

- [ ] Run targeted connector tests and `tests/integration/test_report_analysis_failure.py`.
- [ ] Run targeted media and migration integration tests.
- [ ] Run `uv run pytest`.
- [ ] Run `uv run ruff check .`.
- [ ] Run `uv run mypy src tests`.
- [ ] Run `uv run alembic upgrade head`.
- [ ] Run `uv run alembic downgrade -1`.
- [ ] Run `uv run alembic upgrade head`.
- [ ] Run `git diff --check` from the repository root.
- [ ] Inspect the final diff and report exact versions, changed files, schema behavior, rollout steps, and any failures or remaining risks without claiming unverified success.
