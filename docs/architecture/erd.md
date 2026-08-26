# Data Model (Milestone 1)

Five Postgres schemas: `identity`, `operations`, `workflow`, `platform`, `audit`. This is
fewer than PAPERCUT's original seven — `attribution` and `analytics` are deferred; see
[ADR-0001](../adr/0001-modular-monolith.md) and the roadmap for why. `audit` exists as an
empty schema (created by the baseline migration) with no populated table yet in this
milestone — a placeholder for the audit trail PAPERCUT specifies, not yet wired to any
handler.

Source of truth: `backend/migrations/versions/`. The `Table` objects in
`backend/src/jobact/shared/infrastructure/postgres/*.py` are hand-kept mirrors used by
application code to build statements — if they and a migration ever disagree, the migration
wins and the mirror has a bug.

## identity

```text
identity.users              id, email, email_verified, status, locale, timezone,
                             registered_at, activated_at, last_seen_at
identity.user_profiles      user_id (FK users), display_name, given_name, family_name, avatar_url
identity.identities         id, user_id (FK users), provider, provider_subject
identity.organizations      id, name, created_at
identity.memberships        id, user_id (FK users), organization_id (FK organizations),
                             role, joined_at, revoked_at
identity.sessions           id (opaque cookie value, text PK), user_id (FK users),
                             organization_id (FK organizations), device_id, created_at,
                             last_seen_at, expires_at, revoked_at, ip, user_agent
```

A first Google sign-in creates one `User`, one personal `Organization`, and an `owner`
`Membership` in the same transaction (`SignInWithGoogleHandler`). `Session` rows are also
cached in Redis; Postgres is the source of truth, Redis is the fast path
(`CurrentPrincipal` checks Redis first, falls back to Postgres).

## operations

```text
operations.customers               id, organization_id, name, address, phone, service_type, created_at
operations.visits                  id, organization_id, customer_id, technician_id, status,
                                    started_at, gps_lat, gps_lon, gps_accuracy_m,
                                    before_photo_count, after_photo_count, raw_notes
operations.media_assets            id, organization_id, storage_key, content_type, byte_size,
                                    sha256, kind ('photo'|'signature'|'pdf'), phase ('before'|'after'|null),
                                    status ('pending_upload'|'uploaded'|'attached'),
                                    visit_id, report_id, captured_at, uploaded_at
operations.reports                 id, organization_id, visit_id, human_id ('JA-2026-0001'),
                                    status ('draft'|'pending_signature'|'signed'|'completed'),
                                    current_revision_id, signed_at, completed_at
operations.report_revisions        id, report_id, revision_no, source ('ai'|'human'),
                                    work_completed, amount_cents, currency, ai_confidence,
                                    created_at, created_by,
                                    confirmed_by_user_at, amount_confirmed_at, frozen_at
operations.report_materials        id, revision_id, label, qty
operations.signatures              id, report_id, signer_name, signed_at, media_asset_id, ip, user_agent
operations.report_number_counters  organization_id, year (composite PK), next_number
```

`report_number_counters` exists because a scan-for-`max+1` `human_id` allocation is unsafe
under concurrent report creation. Allocation is one atomic
`INSERT ... ON CONFLICT DO UPDATE ... RETURNING` per `(organization_id, year)`, executed
under a row-level lock — see the `report_handlers.py` allocation function.

`media_assets.kind` in this milestone is only ever `'signature'` (real upload/attach path) or
`'pdf'` (server-generated); `'photo'`/`'audio'` are declared in the design but nothing writes
them yet, since photo/voice capture stay simulated (counts on `visits`, no file).

## workflow

```text
workflow.workflow_runs    id, organization_id, workflow_type, subject_id, state, attempt,
                           next_retry_at, last_error, state_version, correlation_id, input_data
workflow.workflow_steps   id, run_id (FK workflow_runs), step, status, attempt,
                           input, output, error, started_at, finished_at
```

`state_version` is the optimistic-locking column: every transition does
`UPDATE ... WHERE id = :id AND state_version = :expected`, and a zero-row result means a
concurrent writer won and this caller must reload and retry rather than clobber it.
`workflow_steps.output` is where the drafting step records `{model, prompt_tokens,
completion_tokens, cost_usd, latency_ms}` (see [`ai.md`](ai.md)) — there is no separate cost
table in this milestone.

## platform

```text
platform.outbox             id, aggregate_type, aggregate_id, event_type, event_version,
                             payload, occurred_at, published_at
platform.inbox              message_id (PK), consumer, processed_at
platform.idempotency_keys   key, organization_id (composite PK), endpoint, request_hash,
                             response_status, response_body, created_at, expires_at
```

`idempotency_keys` has a **composite** primary key `(key, organization_id)`, not a global
unique `key` — two different organizations may independently generate the same client-side
UUID for an idempotency key, and that must not collide (migration 0003 fixed this after the
baseline shipped with a global PK).

## Invariants enforced in the domain, not just by column constraints

- `Report.status` moves only `draft → pending_signature → signed → completed`
  (`ReportStateError` on any other transition attempt) — see `report.py`.
- A revision is editable only while its report is `draft` and the revision itself is not
  frozen; freezing (`freeze_revision`) is one-way.
- `mark_ready_for_signature()` requires `confirmed_by_user_at` **and** `amount_confirmed_at`
  on the current revision — the amount-confirmation invariant from
  [ADR-0006](../adr/0006-litellm-over-openrouter.md)'s AI-safety discussion.
- `sign()` requires status `pending_signature`, a frozen revision, and a non-null
  `signature_media_asset_id`.
- `WorkflowRun` transitions are checked against `ALLOWED_TRANSITIONS`
  (`workflows/report_fulfillment/states.py`); an illegal transition raises before it ever
  reaches Postgres.
