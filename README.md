# JobAct

> Turn a finished job into a signed customer check, from the job site.

JobAct is a mobile-first field-service demo for independent technicians and small service teams. It turns a completed visit into a customer-facing check with before-and-after photos, location, timestamp, an AI-drafted work summary from a voice note, materials, a deterministic suggested price, and a customer signature.

The product is designed for businesses such as air-conditioning maintenance, pool cleaning, cleaning services, repairs, and other on-site work where a customer may later dispute whether the visit happened or what was completed.

## What's real here

This is a **local demo**: everything in the core pipeline is real, working code — real device GPS and camera, a real browser audio recording transcribed by a real local Whisper model, a real Qwen-drafted work summary and visual before/after comparison, a real deterministic price, a real signature capture, and a real signed PDF. What's *not* real is server-side persistence: normal application state (drafts, evidence, completed checks) lives in the browser (`localStorage` + IndexedDB), not a database, and there is no user account system. See [`docs/architecture/overview.md`](docs/architecture/overview.md) and [ADR-0007](docs/adr/0007-local-demo-downgrade.md) for the full design and why.

## Core Workflow

1. Open the app, type a name once (no account).
2. Tap **Создать чек** (Create a check).
3. Enter the customer/job info and confirm the visit's location and time.
4. Take before photos.
5. Describe the work — type it, or record a voice note that's transcribed locally.
6. Take after photos.
7. Get an AI-drafted work summary, materials list, and suggested price, plus a visual before/after comparison — review and edit any of it.
8. Collect the customer's signature.
9. Get a signed PDF check, kept in a local history.

## Tech Stack

- Frontend: [Next.js](https://nextjs.org/) 16, React 19, TypeScript, Tailwind CSS 4, Lucide React, pnpm.
- Backend: Python, FastAPI, PydanticAI, `uv`, `faster-whisper`, ReportLab.
- AI: Qwen / DashScope (drafting + visual audit). No other provider.

## Repository Layout

This is a monorepo with the frontend and backend kept as separate projects:

```text
frontend/   Next.js UI — see frontend/CLAUDE.md
backend/    Python (FastAPI/PydanticAI) API, managed with uv — see backend/CLAUDE.md
docs/       Committed architecture docs and ADRs — see docs/architecture/overview.md
```

## Getting Started

### One-command local stack (Docker)

Prerequisites: Docker Desktop, `backend/.env` (copy from `backend/.env.example`, fill in
`DASHSCOPE_API_KEY` for real AI drafting).

```bash
docker compose up -d --build
```

This builds and starts everything the demo needs — the FastAPI `api` service and the Next.js
`frontend` — from the root [`docker-compose.yml`](docker-compose.yml). No database, cache, or
object storage to configure.

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

Use `docker compose logs -f <service>` to tail logs and `docker compose down` to stop
everything. Rerun with `--build` after changing a dependency (`pyproject.toml`, `package.json`)
or the Dockerfiles.

For iterating on code with hot reload and faster feedback, see the frontend/backend-only setup
below instead.

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
frontend/app/                       Next.js root route and global styles
frontend/components/jobact/         Product shell, shared UI, cards, and screens
frontend/components/jobact/screens/ Individual screens and the create-check flow
frontend/lib/jobact/local-db.ts     IndexedDB wrapper (drafts, blobs, completed checks)
frontend/lib/jobact/local-store.ts  Typed local persistence operations
frontend/lib/jobact/store.tsx       Navigation stack and session-wide draft state
frontend/public/                    Icons and static assets
```

### Backend

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/). No other services to run.

```bash
cd backend
cp .env.example .env   # fill in DASHSCOPE_API_KEY for real AI drafting
uv sync --dev
uv run uvicorn jobact.apps.api.main:app --reload --port 8000
```

See [`backend/CLAUDE.md`](backend/CLAUDE.md) for the full command list and which modules are
protected (the Whisper and Qwen pipelines), and
[`docs/architecture/overview.md`](docs/architecture/overview.md) for the design this implements.

## Design Principles

- Mobile-first interaction for technicians working on site;
- One obvious primary action, not a dashboard;
- Minimal data entry during a visit;
- Evidence captured close to the moment of work;
- Local-first: the demo works with no account and no server-side database;
- Clear separation between draft, review, signature, and completed states.

## Project Status

The core pipeline described above runs end-to-end: real GPS/camera capture, real Whisper
transcription, real Qwen drafting and visual audit, real deterministic pricing, real signature
capture, and a real signed PDF, all backed by browser-local storage instead of a server
database. See [`docs/roadmap.md`](docs/roadmap.md) for what a return to a production-shaped,
multi-user deployment would look like, and [ADR-0007](docs/adr/0007-local-demo-downgrade.md)
for the downgrade's full reasoning and consequences.
