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

The current implementation is a frontend prototype. Camera, GPS, voice transcription, persistence, PDF generation, messaging, authentication, and server synchronization are represented by UI states and local demo data rather than connected production services.

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

This is a monorepo with the frontend prototype and the (not yet implemented) backend kept as separate projects:

```text
frontend/   Next.js prototype — see frontend/README below and CLAUDE.md
backend/    Python backend, managed with uv — see backend/README.md
```

## Getting Started

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

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync
uv run jobact-backend
```

The backend is currently an empty scaffold (`pyproject.toml` + `uv.lock`). All server-side behavior described below is still simulated in the frontend.

## Design Principles

- Mobile-first interaction for technicians working on site;
- Minimal data entry during a visit;
- Evidence captured close to the moment of work;
- Clear separation between draft, review, signature, and completed states;
- Offline-aware workflows for locations with unreliable connectivity;
- A focused interface for repeated operational use rather than a marketing dashboard.

## Roadmap

- Connect real camera and geolocation permissions;
- Add offline local storage and background synchronization;
- Add speech-to-text and report generation;
- Generate signed PDF reports;
- Share reports through WhatsApp and other channels;
- Add role-based access for owners and employees;
- Add service templates, recurring visits, and materials tracking;
- Validate signature and report requirements for the target markets.

## Project Status

**Prototype / MVP exploration.** The repository is intended to validate the product flow and user experience before production mobile infrastructure and integrations are added.
