# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

JobAct is a mobile-first field-service prototype: it turns a completed on-site visit (before/after photos, GPS, timestamp, voice note, work details, customer signature) into a structured service report.

## Repository Layout

This is a monorepo with two independent projects:

- [`frontend/`](frontend/CLAUDE.md) — the Next.js prototype (all current functionality). See `frontend/CLAUDE.md` for its architecture, screens, and conventions.
- [`backend/`](backend/README.md) — a Python backend managed with `uv` and `pyproject.toml`. Currently an empty scaffold with no endpoints; camera, GPS, voice transcription, persistence, PDF generation, and sync are still simulated entirely in the frontend with local demo data and UI state, not real integrations.

Run frontend commands from `frontend/` and backend commands from `backend/` — there is no root-level package manager or build tool.
