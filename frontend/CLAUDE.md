# CLAUDE.md (frontend)

This file provides guidance to Claude Code (claude.ai/code) when working with code in `frontend/`. See the [root CLAUDE.md](../CLAUDE.md) for the overall repo layout.

## Project

JobAct is a mobile-first field-service demo: it turns a completed on-site visit (before/after photos, GPS, timestamp, voice note, work details, customer signature) into a signed customer check. As of the local-demo downgrade ([ADR-0007](../docs/adr/0007-local-demo-downgrade.md)), the entire product journey is `demoEntry → home → Создать чек → job info → GPS → before photos → notes (typed or real Whisper-transcribed voice) → after photos → real Qwen AI analysis → review/edit → signature → signed PDF → local history`, with **no sign-in and no server-side persistence** — draft/evidence/history state lives in the browser (`localStorage` + IndexedDB), and the backend is three stateless endpoints under `/api/v1/demo/*` (see [`../backend/CLAUDE.md`](../backend/CLAUDE.md)). Photo capture, GPS, and voice recording are all real device APIs, not simulated.

## Commands

Package manager is pnpm (`pnpm-lock.yaml` is the source of truth). Run these from `frontend/`.

```bash
pnpm install     # install dependencies
pnpm dev         # start dev server at http://localhost:3000
pnpm build       # production build
pnpm start       # run production build
pnpm test        # Node's built-in test runner against lib/jobact/*.test.ts
```

`pnpm build` fails on type errors (`next.config.mjs` does not set `typescript.ignoreBuildErrors`); run `npx tsc --noEmit` for a faster standalone check. `next.config.mjs` rewrites `/api/:path*` to `NEXT_PUBLIC_API_ORIGIN` (default `http://localhost:8000`) so the app talks to the backend same-origin in dev.

## Architecture

The entire app is a single-page client-side app rendered from [app/page.tsx](app/page.tsx) → [components/jobact/app.tsx](components/jobact/app.tsx). There is no Next.js file-based routing beyond the one root route — all "screens" are React components swapped by an in-memory navigation stack, not URLs.

**Navigation (`lib/jobact/store.tsx`)**: `NavProvider` holds a `Frame[]` stack (`{screen, params}`) in React state, exposing `navigate`/`replace`/`back`/`reset`. `Screen` is a string union enumerating every screen in the app (14 screens total: `demoEntry`, `home`, `addCustomer`, `visitStart`, `gps`, `beforePhotos`, `notes`, `afterPhotos`, `analysisProcessing`, `reportDraft`, `editReport`, `signature`, `completed`, `checkDetail`) — adding a new screen means adding it to this union first. The same provider holds a session-wide `DraftState` (customer/job info, GPS, before/after photo blob ids, notes, the AI result, amount/confirmation, signature/PDF blob ids) threaded through the create-check flow without prop drilling. A `useEffect` inside `NavProvider` write-throughs every `draft` change to IndexedDB (keyed by the current screen, so a reload resumes exactly where the technician left off) — screens just call `setDraft(patch)` like normal React state; they never call the persistence layer directly for the draft itself.

**Local persistence (`lib/jobact/local-db.ts`, `local-store.ts`, `local-prefs.ts`)**: `local-db.ts` is a minimal hand-rolled IndexedDB wrapper (database `jobact-demo`, stores `drafts`/`blobs`/`checks`) — no ORM, no new dependency. `local-store.ts` layers typed domain operations on top: `saveDraft`/`loadDraft`/`deleteDraft` (abandons a draft, cascades to its blobs) vs. `finalizeDraft` (a completed check retires its draft record *without* cascading — the check now references the same blob ids under a different owner; conflating these two deletes a just-completed check's PDF, a real bug caught during manual testing, see the regression test in `local-store.test.ts`). `putBlob`/`getBlob` store/read photo, audio, signature, and PDF bytes as real `Blob`s, never base64. `saveCheck`/`listRecentChecks` manage the completed-check history, pruned to the newest 20 on every save. `local-prefs.ts` wraps `localStorage` for the small scalar preferences (locale, currency, demo user name, the active-draft-id resume pointer). See [`../docs/architecture/overview.md`](../docs/architecture/overview.md) for the full persistence design and its risk tradeoffs.

**Backend API client (`lib/jobact/api.ts`)**: `transcribeRecording()`, `analyzeReport()`, `renderCheckPdf()` — one function per `/api/v1/demo/*` endpoint, each posting `multipart/form-data` (never JSON alone, since every request carries file bytes) and mapping non-2xx responses to `JobActApiError`. Requests go through the `/api/*` same-origin rewrite in `next.config.mjs`, never directly to the backend origin from the browser. There is no session cookie and no `Idempotency-Key` header — nothing server-side to deduplicate against.

**AI analysis** runs once per attempt, from `analysisProcessing`, requiring job notes and at least one equal-count before/after photo pair (validated client-side; the backend also rejects with `evidence-incomplete` if photos are missing). The result — work summary, materials, suggested price, visual comparison — is written straight into `draft` and IndexedDB; there is no polling, since the endpoint returns the finished result in one response.

**Routing (`components/jobact/app.tsx`)**: `Router` reads the current `frame` from `useNav()` and `ScreenView` is a switch statement mapping `Screen` → screen component. There is no sidebar or bottom tab bar — the app is a single linear flow, not a multi-section dashboard.

**Screens are split by role, not 1:1 with files**:
- `screens/demo-entry.tsx` — the one-field local entry screen (a name, stored locally; no auth).
- `screens/main.tsx` — `HomeScreen`: the single "Создать чек" CTA, a resumable-draft row, and the recent-checks list.
- `screens/flow.tsx` — the linear check-creation flow (job info, GPS, photos, notes, AI analysis, report draft/edit, signature, completed).
- `screens/detail.tsx` — `CheckDetailScreen`, the read-only local-history detail view.

**Presentation layer**: `components/jobact/shell.tsx` provides `AppShell` (a plain scrollable container, no persistent chrome), `Page`/`ActionBar`/`PageHeader`. `components/jobact/ui.tsx` and `cards.tsx` hold shared UI primitives (distinct from shadcn's `components/ui/`, which currently only has `button.tsx`). `ui.tsx`'s `ReportStatus`/`SyncState` types now live in `local-store.ts` rather than a removed `lib/jobact/data.ts`.

## Conventions

- All interactive components are `"use client"` — there are no server components/actions in use beyond the root layout.
- Styling is Tailwind CSS 4 with CSS variables (dark theme forced via `className="dark"` on `<html>` in `app/layout.tsx`); use `cn()` from `lib/utils.ts` (clsx + tailwind-merge) for conditional classes.
- Icons come from `lucide-react`.
- A same-directory sibling import within `lib/jobact/` (e.g. `local-store.ts` importing `local-db.ts`) uses a relative specifier with an explicit `.ts` extension (`tsconfig.json` sets `allowImportingTsExtensions`) rather than the `@/lib/jobact/...` alias, so the module also resolves under plain `node --experimental-strip-types` for `pnpm test` — the alias only resolves through Next's own bundler.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
