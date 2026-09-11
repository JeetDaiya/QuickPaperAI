# Architecture

Living reference — edit in place when the thing it describes changes. Don't append dated
entries here; that's `CHANGELOG.md`'s job.

## Stack

React 19 + TanStack Router (file-based routing) + TanStack Query + Tailwind v4 + KaTeX, built
with Vite. Plain client-side SPA — no server-side rendering, no TanStack Start/Nitro. The old
`QuickPaperAI/client` app (Lovable-generated) used TanStack Start; this one deliberately doesn't,
since there's nothing here that needs a server (no SSR, no API routes of its own) — see
`docs/DEPLOYMENT.md` for what that means for hosting it.

## Layers (one-way dependency)

```
src/routes/*.tsx    — thin containers: TanStack Query hooks + navigation, no JSX layout logic
        ↓ props
src/pages/*.tsx      — presentational: props in, JSX out, zero knowledge of HTTP or routing
        ↑ used by
src/hooks/*.ts        — TanStack Query wrappers (useQuery/useMutation) around src/lib/api/*
        ↑ used by
src/lib/api/*.ts       — the ONLY code that knows about HTTP. One function per backend endpoint.
```

A page component never imports from `lib/api` directly — if you're adding a new screen, the
route file owns the data-fetching hook and passes plain props/callbacks down.

### `src/lib/api/` — the typed client
- `types.ts` — request/response types matching `docs/api-contract.md` exactly.
- `http.ts` — the only `fetch()` wrapper (`jsonFetch`, `formFetch`), token storage
  (`getToken`/`setToken`/`clearToken`), 401 → auto-redirect-to-login, and `resolveFileUrl()` /
  `withToken()` for turning a backend-relative path into an authenticated URL (used for
  downloads and the SSE stream, which can't send an `Authorization` header — see GOTCHAS).
- `auth.ts`, `paper.ts`, `db.ts` — one function per endpoint, named after the route.

### `src/hooks/`
- `useAuth.ts`, `usePaper.ts` — TanStack Query `useQuery`/`useMutation` wrappers, one per
  `lib/api` function that a route actually needs.
- `useGenerationStatus.ts` — the SSE hook for `/api/status/{threadId}/stream`. Not a generic
  fetch wrapper; see GOTCHAS before touching it, its reconnect behavior is load-bearing.
- `useDocumentTitle.ts` — sets `document.title`, restores the previous one on unmount.

### `src/routes/` (TanStack Router, file-based)
File name → URL path (dots = nesting, `$param` = dynamic segment):
- `login.tsx`, `signup.tsx`, `forgot-password.tsx`, `verify-otp.tsx`, `reset-password.tsx` —
  auth flow. `verify-otp` and `reset-password` carry state via search params (`email`,
  `purpose`, `token`), validated with `validateSearch`.
- `dashboard.tsx` — Cloud Vault (saved papers, from `GET /api/db/history`) + Recent Drafts
  (client-only, see below) + notification settings.
- `generate.setup.tsx` — the paper configuration form.
- `generate.$threadId.tsx` — the single container that renders Progress → Review → Downloads
  depending on live SSE status. This is the most stateful file in the app; read it and
  `useGenerationStatus.ts` together before changing either.
- `__root.tsx` — root layout (just an `<Outlet />`, no shared chrome — each page pulls in its
  own `AppShell`/`AuthShell`).
- `routeTree.gen.ts` — **generated** by `@tanstack/router-plugin` on every dev/build run from
  the files in `routes/`. Never hand-edit it.

### `src/pages/`
One component per screen, ported from the Stitch wireframes in `design/` (see that directory
for the original exports if you need to re-check fidelity against the design). Each takes plain
props (data + callbacks + loading/error booleans) and renders JSX — no `fetch`, no
`useQuery`/`useMutation` inside a page component.

### `src/components/`
- `layout/AppShell.tsx` — sidebar nav + mobile bottom nav, wraps every authenticated page
  (Dashboard, Setup, Progress, Review, Downloads).
- `layout/AuthShell.tsx` — header + centered card + footer, wraps every auth page.
- `Latex.tsx` — renders `$...$` / `$$...$$` math via KaTeX, matching the backend PDF's own
  rendering convention exactly (see GOTCHAS for why it must always return a single wrapping
  element, never a bare Fragment).

### `src/lib/` (non-API)
- `auth.ts` — `isAuthenticated()` / `useAuthGuard()` (redirects to `/login` if no token).
- `drafts.ts` — client-side (localStorage) tracking of in-progress paper sessions. There is no
  backend endpoint that lists a user's non-saved sessions (`GET /api/db/history` only returns
  `status="saved"` rows), so "Recent Drafts" on the dashboard is sourced entirely from here,
  keyed per-user by decoding the JWT's `sub` claim. Lifecycle: `upsertDraft()` on successful
  `POST /api/generate`, `updateDraftStatus()` on every SSE status change, `removeDraft()` on
  cancel. Ported from `QuickPaperAI/client/src/lib/drafts.ts` (logic only, not its design).
- `paper-config.ts` — static config for the Setup form: difficulty presets, the four "Paper
  Type Mode" presets (Standard/MCQ-only/Objective-only/Custom) and which `allowed_types` each
  one locks in, question-type label lists.
- `utils.ts` — `cn()` (clsx + tailwind-merge), `sortNatural()` (numeric-aware string sort, since
  chapter names from the backend can be bare numbers like "1", "2", "10").

## Design system — "Examiner's Desk"

Defined once in `src/styles.css` as Tailwind v4 `@theme` tokens, transcribed **verbatim** from
the Stitch project's generated exports (`design/stitch_quickpaper_ai_generator/*/code.html`) —
same color/typography/spacing/radius values, so the app matches what was actually designed and
screenshotted. Notable quirk: `rounded-full` maps to `0.75rem`, not a true circle — that's not a
bug, it's what every one of the 9 Stitch exports actually used. If the design system ever
changes, re-derive these tokens from fresh Stitch exports rather than hand-tuning colors here.

Material Symbols (icon font) and Google Fonts (Source Serif 4, Geist) are loaded in
`index.html`. KaTeX's CSS is imported once in `main.tsx`.

## Auth

Bearer token in `localStorage` (`getToken`/`setToken`/`clearToken` in `lib/api/http.ts`).
`useAuthGuard()` redirects unauthenticated visits to protected routes; `jsonFetch` redirects to
`/login` on any `401`. SSE and file-download URLs can't carry an `Authorization` header, so the
token rides as a `?token=` query param instead (`withToken()`/`resolveFileUrl()`) — see GOTCHAS
for the exact `&` vs `?` rule.

## Full generation flow (the complex one)

`generate.$threadId.tsx` drives everything off `useGenerationStatus(threadId, reconnectKey)`:

1. `POST /api/generate` → navigate here with the new `thread_id`.
2. SSE pushes `generating` → renders `ProgressPage` with live chapter progress.
3. SSE pushes `awaiting_review` → renders `ReviewPage`. The backend's own SSE generator ends
   its HTTP response at this point (it's in the backend's `TERMINAL_STATUSES`), and our hook
   closes to match.
4. User clicks Finalize → `POST /api/resume` → on success, bump `reconnectKey` to force a
   **fresh** SSE connection (the old one is dead, see GOTCHAS) → render a "Compiling…" waiting
   screen until the new connection pushes a real update.
5. SSE (on the new connection) pushes `completed` → renders `DownloadsPage` with the three
   resolved file URLs (PDF, DOCX, answer-key PDF).

Cancelling at any point calls `DELETE /api/cancel/{threadId}` and clears the draft.
