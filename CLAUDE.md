# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

JobAct is a mobile-first field-service demo: it turns a completed on-site visit (before/after photos, GPS, timestamp, voice note, work details, customer signature) into a signed customer check, drafted by AI (Qwen) and transcribed by a local Whisper model.

As of the local-demo downgrade ([ADR-0007](docs/adr/0007-local-demo-downgrade.md)), normal application state (drafts, evidence, completed checks) lives entirely in the browser (`localStorage`/IndexedDB) — the backend is two stateless AI/STT endpoints plus a PDF renderer, with no database, cache, object storage, or user accounts. See [`docs/architecture/overview.md`](docs/architecture/overview.md) for the current architecture and [`docs/roadmap.md`](docs/roadmap.md) for what a return to a production-shaped deployment would look like.

## Repository Layout

This is a monorepo with two independent projects:

- [`frontend/`](frontend/CLAUDE.md) — the Next.js UI. See `frontend/CLAUDE.md` for its architecture, screens, and local-persistence design.
- [`backend/`](backend/CLAUDE.md) — a Python (FastAPI + PydanticAI) stateless API. See `backend/CLAUDE.md` for its three endpoints and the protected STT/AI code they call, and [`docs/architecture/overview.md`](docs/architecture/overview.md) for the full design.

Run frontend commands from `frontend/` and backend commands from `backend/` — there is no root-level package manager or build tool. `docs/` holds committed architecture documentation and ADRs; `PAPERCUT.md` (gitignored, not in version control) is the private design diary that preceded and then tracked this implementation, including the downgrade.
