# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

JobAct is a mobile-first field-service prototype: it turns a completed on-site visit (before/after photos, GPS, timestamp, voice note, work details, customer signature) into a structured service report.

## Repository Layout

This is a monorepo with two independent projects:

- [`frontend/`](frontend/CLAUDE.md) — the Next.js prototype UI. See `frontend/CLAUDE.md` for its architecture, screens, and conventions.
- [`backend/`](backend/CLAUDE.md) — a Python (FastAPI + SQLAlchemy async + PydanticAI) contract-first modular monolith. See `backend/CLAUDE.md` for layering rules and commands, and [`docs/architecture/overview.md`](docs/architecture/overview.md) for the full design.

Milestone 1 wires a real vertical slice end-to-end: Google sign-in, customers, visits, AI-drafted reports (Qwen/DashScope), a real signature capture, and signed PDFs, all backed by Postgres/Redis/MinIO. Camera/photo capture and GPS stay simulated by design (counts and a fixed coordinate only); voice notes go through a real `raw_notes` field but with no speech-to-text yet (a canned transcript or typed notes fill it). See [`docs/roadmap.md`](docs/roadmap.md) for what's next.

Run frontend commands from `frontend/` and backend commands from `backend/` — there is no root-level package manager or build tool. `docs/` holds committed architecture documentation and ADRs; `PAPERCUT.md` (gitignored, not in version control) is the private design diary that preceded this implementation.
