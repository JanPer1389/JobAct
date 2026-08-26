# CLAUDE.md (frontend)

This file provides guidance to Claude Code (claude.ai/code) when working with code in `frontend/`. See the [root CLAUDE.md](../CLAUDE.md) for the overall repo layout.

## Project

JobAct is a mobile-first field-service prototype: it turns a completed on-site visit (before/after photos, GPS, timestamp, voice note, work details, customer signature) into a structured service report. As of Milestone 1, sign-in, the customer list/creation, and the entire linear visit-creation flow (`screens/flow.tsx`: GPS/photo PATCHes, notes, AI report drafting, edit/confirm, real signature capture and upload, signing, PDF) are wired to the real backend — see [`../backend`](../backend/CLAUDE.md) and [`../docs/architecture/overview.md`](../docs/architecture/overview.md). The home dashboard and reports archive (`screens/main.tsx`'s `HomeScreen`/`ReportsScreen`) still render the static demo `reports`/`CURRENT_USER` data from `lib/jobact/data.ts` — they were out of Milestone 1's scope and have not been wired to `GET /reports` yet. Camera/photo capture and GPS remain simulated by design — counts and a fixed coordinate are sent to the backend, but no real device hardware is read.

## Commands

Package manager is pnpm (`pnpm-lock.yaml` is the source of truth; a `package-lock.json` also exists but is not authoritative). Run these from `frontend/`.

```bash
pnpm install     # install dependencies
pnpm dev         # start dev server at http://localhost:3000
pnpm build       # production build
pnpm start       # run production build
```

There is no lint or test script configured. `next.config.mjs` no longer sets `typescript.ignoreBuildErrors` (dropped in Milestone 1), so `pnpm build` does fail on type errors; run `npx tsc --noEmit` for a faster standalone check. `next.config.mjs` also rewrites `/api/:path*` to `NEXT_PUBLIC_API_ORIGIN` (default `http://localhost:8000`) so the app talks to the backend same-origin in dev.

## Architecture

The entire app is a single-page client-side prototype rendered from [app/page.tsx](app/page.tsx) → [components/jobact/app.tsx](components/jobact/app.tsx). There is no Next.js file-based routing beyond the one root route — all "screens" are React components swapped by an in-memory navigation stack, not URLs.

**Navigation (`lib/jobact/store.tsx`)**: `NavProvider` holds a `Frame[]` stack (`{screen, params}`) in React state, exposing `navigate`/`replace`/`back`/`reset`. `Screen` is a string union enumerating every screen in the app — adding a new screen means adding it to this union first. The same provider also holds a single session-wide `DraftState` (customer, photos count, work description, amount, signed) used to thread state through the multi-step visit-creation flow (`visitStart → gps → beforePhotos → voice → voiceProcessing → afterPhotos → reportDraft → editReport → signature → completed`) without prop drilling.

**Routing (`components/jobact/app.tsx`)**: `Router` reads the current `frame` from `useNav()` and `ScreenView` is a big switch statement mapping `Screen` → screen component. Bottom tab nav (`home`/`reports`/`customers`/`profile`) only shows for the four tab screens, hidden during the "picking a customer for a new report" sub-state (`params.picking`).

**Screens are split by role, not 1:1 with files**:
- `screens/onboarding.tsx` — splash, sign-in
- `screens/main.tsx` — the four bottom-tab screens (home, reports, customers, profile)
- `screens/flow.tsx` — the linear visit-creation flow (GPS, photos, voice, report draft/edit, signature, completed)
- `screens/detail.tsx` — customer detail, report detail (drill-down views)
- `screens/states.tsx` — offline/syncing/hardware-permission state screens (used to demo edge-case UI, not part of the main flow)

**Presentation layer**: `components/jobact/shell.tsx` provides the phone-frame chrome (`PhoneShell`, fake status bar, `BottomNav`, `Scroll`). `components/jobact/ui.tsx` and `cards.tsx` hold shared prototype UI primitives (distinct from shadcn's `components/ui/`, which currently only has `button.tsx`, configured via `components.json` with the `base-nova` style and no Tailwind config prefix — component aliases: `@/components`, `@/lib`, `@/hooks`).

**Demo data (`lib/jobact/data.ts`)**: static `customers`/`Report`/`Material` arrays and types plus `CURRENT_USER`. Still the source for the home dashboard and reports archive (see Project section above); the customer list and visit flow instead call the real API via `lib/jobact/api.ts`. When wiring a screen to the backend, replace its demo-data usage rather than layering API calls on top of it.

**Backend API (`lib/jobact/api.ts`)**: `apiFetch<T>()` wraps `fetch` with `credentials: "include"`, an auto-generated `Idempotency-Key` header on mutating requests (preserved across retries of the same logical action), and maps the backend's v1 error envelope to a `JobActApiError`. Requests go through the `/api/*` same-origin rewrite in `next.config.mjs`, never directly to the backend origin from the browser.

## Conventions

- All interactive components are `"use client"` — there are no server components/actions in use beyond the root layout.
- Styling is Tailwind CSS 4 with CSS variables (dark theme forced via `className="dark"` on `<html>` in `app/layout.tsx`); use `cn()` from `lib/utils.ts` (clsx + tailwind-merge) for conditional classes.
- Icons come from `lucide-react`.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
