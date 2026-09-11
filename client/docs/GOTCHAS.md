# Gotchas

Non-obvious constraints and past traps. One line each. Read before touching the related area.
If you hit something new and non-obvious, add a line here — don't bury it in a commit message.

## SSE / generation status (`useGenerationStatus.ts`, `generate.$threadId.tsx`)
- The backend's own SSE generator (`stream_generation_status` in the backend's
  `routes.py`) **ends its HTTP response** once status reaches `"awaiting_review"` — it's in the
  backend's own `TERMINAL_STATUSES`. Our hook closes its `EventSource` to match. This is only a
  *pause*, not the end: after the user resumes, the backend keeps working and will eventually
  push `"completed"` — but only to a connection that still exists. `generate.$threadId.tsx`
  bumps a `reconnectKey` right when the resume call succeeds, forcing `useGenerationStatus` to
  open a fresh connection. **Don't remove this** — without it, the UI silently gets stuck on
  the Review/"Compiling…" screen forever after Finalize, recoverable only by a manual refresh.
- The backend has no distinct "compiling" status — after Finalize it goes back to reporting
  `"generating"` with every chapter already `"completed"` (compiling only starts once all
  chapters are done, and the *first* time all chapters finish the backend jumps straight to
  `"awaiting_review"` instead, so `generating` + all-completed only ever means "post-resume
  compile"). `generate.$threadId.tsx`'s `isCompiling()` uses that combination to show the
  Compiling screen. Don't rely on the local `hasResumed` flag alone for this — it's `useState`
  and resets to `false` on every remount, so a refresh or navigating back into the thread mid
  Finalize used to show a frozen, non-advancing generic progress page instead of the Compiling
  screen (or briefly re-show the Review screen, in the narrow window where the checkpoint still
  reads `"awaiting_review"` right after Finalize — see the backend's own comment on
  `stream_generation_status` in `routes.py`).
- Never call `es.close()` on a generic `onerror` in that hook. The native `EventSource` already
  auto-retries transient errors (network blips, proxy timeouts) as long as you don't close it
  yourself — closing there permanently kills the connection with no way to recover except a
  full remount (i.e. the user has to refresh the page). Only treat `es.readyState ===
  EventSource.CLOSED` as a real, surfaceable error — that's the one case where the browser
  itself gave up (e.g. a non-retryable 401/403/404 on a reconnect attempt).
- Always clear `error` state on a successful `onopen`/`onmessage` — otherwise a transient error
  latches permanently even after the connection actually recovers.
- The SSE URL carries the auth token as `?token=`, never a header — `EventSource` can't set
  custom headers. See `withToken()`/`resolveFileUrl()` in `lib/api/http.ts`.

## Vercel deploy
- This is a client-side-routed SPA (TanStack Router, no server). Vercel's static file server
  otherwise serves by literal path, so refreshing or deep-linking into any route other than `/`
  (e.g. `/generate/<threadId>` while a paper is generating/reviewing) 404s instead of reaching
  the router. `vercel.json`'s catch-all rewrite (`/(.*) -> /index.html`) is what fixes this —
  don't remove it, and if you add a real static asset path that collides with a route name,
  rewrites still apply (Vercel only skips the rewrite for a file that actually exists on disk).

## CORS / dev server
- The backend's dev CORS allowlist (`QuickPaperAI/src/app.py`) only accepts
  `localhost:{5173,8080,3000,8000}` (and the `127.0.0.1` equivalents). Running `vite --port
  <anything else>` makes every request fail with a CORS error that looks like a network outage,
  not an auth problem — check the port first if "nothing works" in dev.
- The port is pinned in `vite.config.ts` (`VITE_DEV_PORT`, default 8080) with
  `strictPort: true`. Without that, Vite's default behaviour on an occupied 5173 is to hop to
  the next free one — off the allowlist — and print it in small text you don't read, so the app
  loads fine and every API call dies. With strictPort it refuses to start instead; if that
  happens, find the squatter (`ss -ltnp | grep 8080`) rather than changing the port.
- Every runtime-configurable value lives in `.env` (`.env.example` is the tracked template,
  `.env` is gitignored). Only `VITE_API_BASE_URL` is actually read by code — the `VITE_FIREBASE_*`
  entries are carried over from the old client and nothing imports them. Vite applies the **last**
  definition of a duplicated key, so a stray second `FOO=placeholder` line silently wins over the
  real value above it — check for duplicates before debugging a "wrong config" symptom.
- Preview/download URLs append params with `&`, not a second `?` — `?preview=true?token=...`
  silently breaks auth. Always route through `resolveFileUrl()`/`withToken()`, never
  string-concatenate a token onto a URL by hand.

## `Latex.tsx`
- Must always render as **one wrapping `<span>`**, never a bare `<>...</>` Fragment. A
  Fragment's children become independent items the instant the parent uses `flex` or `grid`
  (which several call sites do, e.g. the MCQ options row) — every text run and every KaTeX span
  gets pulled out and laid out as its own box instead of flowing as one sentence. This produced
  exactly the scrambled/columnar rendering bug that shipped once and had to be fixed — don't
  reintroduce it by "simplifying" the component back to a Fragment.
- Delimiter convention (`$$...$$` display, `$...$` inline) must match the backend's own
  `html_paper_formatter.py` KaTeX config exactly, or on-screen review won't match the compiled
  PDF. If the backend ever changes its delimiters, update `MATH_SEGMENT` in `Latex.tsx` too.
- If math renders as literal text (e.g. `\rightarrow` showing as the word "rightarrow" instead
  of an arrow), that's very likely a backend LLM-generation data issue (a missing backslash
  before it ever reached this app), not a frontend bug — verify by rendering the same LaTeX
  string through `Latex` directly before assuming the component is broken.

## Tailwind v4 theme (`styles.css`)
- `rounded-full` is `0.75rem` in this design system, **not** a true circle — verified against
  all 9 Stitch exports, it's consistent and deliberate, not a typo. Don't "fix" it.
- Color/typography/spacing tokens were transcribed verbatim from the Stitch HTML exports'
  inline `tailwind.config` blocks (all 9 screens use identical values) — if the design system
  changes, re-derive from fresh exports rather than hand-editing values here, to avoid drifting
  from what was actually designed.

## Backend data quirks the frontend has to compensate for
- `GET /api/db/get-chapters` returns one row **per textbook chunk**, not one per chapter — the
  same chapter name repeats many times. `SetupPage` dedupes by `chapter_name` before rendering
  checkboxes; don't remove that dedupe or the chapter list fills with duplicates.
- The backend's `PaperRequest` validator rejects a positive `objective_count`/`subjective_count`
  with no matching `allowed_types` in that category. `SetupPage` zeroes out the irrelevant count
  at submit time based on what's actually selected (see `hasObjectiveSelected`/
  `hasSubjectiveSelected`) — don't just pass the raw input state through.
- `history[].id` is a number, `PaperGenerateRequest`/`StatusResponse` have no `paper_type_mode`
  field — "Paper Type Mode" in `SetupPage` is a pure frontend UI concept for deriving
  `allowed_types`/counts and must never be sent in the request body. See `docs/api-contract.md`
  for the full list of corrections made against the old `QuickPaperAI/client` app's (wrong)
  assumptions about the contract.

## Testing SSE/network behavior locally
- Puppeteer's `setRequestInterception` will break CORS preflight (`OPTIONS`) requests if you
  route them through the same abort/mock logic as the real request — always let `OPTIONS`
  requests through untouched (`req.continue()`) and only intercept the actual `GET`/`POST`, or
  the browser blocks the real request with a generic `net::ERR_FAILED` that looks unrelated to
  interception.
