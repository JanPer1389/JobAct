# CLAUDE.md (frontend)

This file provides guidance to Claude Code (claude.ai/code) when working with code in `frontend/`. See the [root CLAUDE.md](../CLAUDE.md) for the overall repo layout.

## Project

JobAct is a mobile-first field-service prototype: it turns a completed on-site visit (before/after photos, GPS, timestamp, voice note, work details, customer signature) into a structured service report. This directory is a frontend prototype only — camera, GPS, voice transcription, persistence, PDF generation, and sync are all simulated with local demo data and UI state, not real integrations. The [`../backend`](../backend) project is a placeholder scaffold with no endpoints yet.

## Commands

Package manager is pnpm (`pnpm-lock.yaml` is the source of truth; a `package-lock.json` also exists but is not authoritative). Run these from `frontend/`.

```bash
pnpm install     # install dependencies
pnpm dev         # start dev server at http://localhost:3000
pnpm build       # production build
pnpm start       # run production build
```

There is no lint, typecheck, or test script configured. `next.config.mjs` sets `typescript.ignoreBuildErrors: true`, so `pnpm build` does not fail on type errors — run `npx tsc --noEmit` manually if you need type verification.

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

**Demo data (`lib/jobact/data.ts`)**: static `customers`/`Report`/`Material` arrays and types plus `CURRENT_USER`. There is no backend, database, or API layer wired up yet — any "save" or "sync" action should update local state/draft only, matching the prototype's stated scope.

## Conventions

- All interactive components are `"use client"` — there are no server components/actions in use beyond the root layout.
- Styling is Tailwind CSS 4 with CSS variables (dark theme forced via `className="dark"` on `<html>` in `app/layout.tsx`); use `cn()` from `lib/utils.ts` (clsx + tailwind-merge) for conditional classes.
- Icons come from `lucide-react`.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
