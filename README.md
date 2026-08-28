# JobAct

> Create a customer-ready service report from the job site in two minutes.

JobAct is a mobile-first field service app concept for independent technicians and small service teams. It turns a completed visit into a structured proof-of-work report with before-and-after photos, location, timestamp, voice notes, work details, customer approval, and an archive of past reports.

The product is designed for businesses such as air-conditioning maintenance, pool cleaning, cleaning services, repairs, and other on-site work where a customer may later dispute whether the visit happened or what was completed.

## Why JobAct

Small field-service businesses often rely on informal WhatsApp messages, scattered photos, or paper forms. That makes it difficult to prove:

- that a technician arrived at the customer location;
- what the site looked like before and after the work;
- what was done and which materials were used;
- when the visit happened;
- that the customer reviewed and accepted the result.

JobAct brings those pieces into one fast, repeatable workflow.

## Core Workflow

1. Start a new visit.
2. Capture the visit location and timestamp.
3. Take before photos.
4. Describe the work with a voice note.
5. Capture after photos.
6. Generate a structured report draft.
7. Review and edit the work, materials, and total.
8. Collect the customer's signature.
9. Complete the report and keep it in the archive.

## Prototype Scope

This repository contains a polished interactive product prototype built around the core mobile workflow. It currently includes:

- splash and sign-in screens;
- home dashboard with visit and report summaries;
- reports archive and report details;
- customer list, customer details, and customer creation;
- visit flow with GPS, before/after photo capture, and voice input states;
- report draft and editing screens;
- customer signature and completed-report confirmation;
- offline, syncing, and hardware-access state screens;
- mobile phone shell with bottom navigation.

As of Milestone 1, sign-in, customers, and the full visit flow (evidence entry → AI-drafted report → real signature → signed PDF) run against a real backend — see [`docs/architecture/overview.md`](docs/architecture/overview.md). Camera and GPS are still represented by UI states and counts rather than real device hardware; the home dashboard and reports archive still render local demo data. See [`docs/roadmap.md`](docs/roadmap.md) for what's next.

## Product Direction

### Target users

- Independent service technicians;
- Owners of small field-service businesses with one to five employees;
- Teams that need lightweight visit documentation and employee visit visibility.

### Value proposition

**A completed service report from the job site in two minutes.**

### Planned MVP capabilities

- Before-and-after photos;
- GPS location and visit timestamp;
- Voice description converted into a structured report;
- Work performed, materials, and amount;
- On-screen customer signature or shareable confirmation;
- Offline-first capture with later synchronization;
- Customer and report archive;
- Owner visibility into employee visits.

## Tech Stack

- [Next.js](https://nextjs.org/) 16
- React 19
- TypeScript
- Tailwind CSS 4
- Lucide React
- pnpm

## Repository Layout

This is a monorepo with the frontend and backend kept as separate projects:

```text
frontend/   Next.js prototype UI — see frontend/CLAUDE.md
backend/    Python (FastAPI/PydanticAI/LiteLLM) backend, managed with uv — see backend/CLAUDE.md
docs/       Committed architecture docs and ADRs — see docs/architecture/overview.md
```

## Getting Started

### One-command local stack (Docker)

Prerequisites: Docker Desktop, `backend/.env` (copy from `backend/.env.example`).

```bash
docker compose up -d --build
```

This builds and starts everything — Postgres, Redis, MinIO, LiteLLM, the FastAPI `api`
service (migrations run automatically on boot), the Redis Streams `worker`, and the Next.js
`frontend` — from the root [`docker-compose.yml`](docker-compose.yml). No other terminals or
commands needed.

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001
- LiteLLM: http://localhost:4000

Use `docker compose logs -f <service>` to tail logs and `docker compose down` to stop
everything. Rerun with `--build` after changing a dependency (`pyproject.toml`,
`package.json`) or the Dockerfiles.

For iterating on code with hot reload and faster feedback, see the frontend/backend-only
setup below instead.

### Frontend

Prerequisites: Node.js 20 or newer, pnpm.

```bash
cd frontend
pnpm install
pnpm dev     # http://localhost:3000
pnpm build   # production build
pnpm start   # run production build
```

```text
frontend/app/                       Next.js routes and global styles
frontend/components/jobact/         Product shell, shared UI, cards, and screens
frontend/components/jobact/screens/ Individual prototype screens and flows
frontend/lib/jobact/data.ts         Demo customers, reports, and product data
frontend/lib/jobact/store.tsx       Local navigation and prototype state
frontend/public/                    Icons and static assets
```

### Backend

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), Docker (for Postgres/Redis/MinIO/LiteLLM).

```bash
cd backend
cp .env.example .env   # fill in OPENROUTER_API_KEY for real AI drafting
docker compose up -d
uv sync --dev
uv run alembic upgrade head
uv run uvicorn jobact.apps.api.main:app --reload --port 8000
```

See [`backend/CLAUDE.md`](backend/CLAUDE.md) for the full command list, layering rules, and
test suite, and [`docs/architecture/overview.md`](docs/architecture/overview.md) for the
design this implements.

## Design Principles

- Mobile-first interaction for technicians working on site;
- Minimal data entry during a visit;
- Evidence captured close to the moment of work;
- Clear separation between draft, review, signature, and completed states;
- Offline-aware workflows for locations with unreliable connectivity;
- A focused interface for repeated operational use rather than a marketing dashboard.

## Roadmap

AI-drafted reports, real signature capture, and signed PDF generation are implemented as of
Milestone 1 (see [`docs/architecture/overview.md`](docs/architecture/overview.md)). See
[`docs/roadmap.md`](docs/roadmap.md) for the detailed, milestone-by-milestone plan; in short:

- Milestone 2 — real camera/geolocation and an offline command queue;
- Milestone 3 — speech-to-text feeding the existing AI drafting pipeline;
- Milestone 4 — report delivery (e.g. WhatsApp), analytics, and attribution.

Also still ahead: role-based access beyond owner/technician, service templates, recurring
visits, and materials tracking; validating signature and report requirements for target
markets.

## Project Status

**Milestone 1 complete.** One vertical slice — visit → AI-drafted report → real signature →
signed PDF — runs end-to-end against a real backend, proven by domain, contract, workflow,
and integration tests. The rest of the product surface (home dashboard, reports archive,
camera/GPS hardware, offline sync) remains prototype/UI-state as described above.
