# Roadmap

The repository's current state is a local demo, not a production deployment — see
[`docs/architecture/overview.md`](architecture/overview.md) and
[ADR-0007](adr/0007-local-demo-downgrade.md) for what the demo pipeline is and why the
production-shaped Milestone 1 architecture (Postgres, Redis, MinIO, Google OAuth, a durable
workflow engine) was set aside. Milestone 1's own history is preserved in
[ADR-0001](adr/0001-modular-monolith.md) through [ADR-0005](adr/0005-outbox-saga-idempotency.md).

## The demo pipeline today

```text
Demo entry (local name only) → Создать чек → job info → GPS → before photos
  → voice or typed notes → real Whisper transcription → after photos
  → real Qwen drafting + visual audit → deterministic suggested price
  → review/edit → signature → real PDF → local check history
```

Everything above is real and working: real device GPS and camera capture, real browser audio
recording transcribed by an unmodified faster-whisper pipeline, real Qwen-drafted work
descriptions and visual before/after comparison, real deterministic pricing, a real signature
capture, and a real signed PDF. What's local rather than server-persisted is the draft/evidence/
history data itself — see [`frontend/CLAUDE.md`](../frontend/CLAUDE.md).

## Returning to a production-shaped deployment

Should this demo need to become a real multi-user product again, the Milestone 1 ADRs describe
a design that already solved the harder problems (durable AI/STT execution surviving a
disconnect, multi-tenant auth, permanent evidence storage, exactly-once workflow execution).
The AI/STT product logic itself never changed, so re-attaching it to that architecture is
mechanical: replace the three stateless endpoints' direct calls with the same durable-workflow
activities Milestone 1 already had (`workflows/report_fulfillment/`'s deleted
`run_report_analysis.py`/`generate_pdf.py`/`transcribe_audio.py`'s claim-and-lease orchestration
are recoverable from git history at the commit before [ADR-0007](adr/0007-local-demo-downgrade.md)
landed), and reintroduce Postgres/Redis/MinIO/auth per ADR-0001/0003/0004/0005.

## Open items, demo scope

- No opt-in live-model smoke test exists yet (`JOBACT_LIVE_LLM_TESTS=1` was planned in
  Milestone 1 and never written) — verifying a real Qwen round trip is still a manual step; see
  [`ai.md`](architecture/ai.md#testing).
- IndexedDB storage is unbounded except for a 20-check history cap and the existing photo/audio
  size limits — no explicit total-quota UI beyond the `QuotaExceededError` fallback state.
- `frontend/components/jobact/screens/detail.tsx`'s `CheckDetailScreen` is read-only; there is
  no local check editing/deletion UI beyond the automatic 20-check prune.
