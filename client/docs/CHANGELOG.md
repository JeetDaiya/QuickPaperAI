# Changelog

Append-only log — one short dated bullet per finished piece of work. No prose explanations;
those belong in a commit message or PR description. Never edit or remove old entries.

- **2026-09-11** — Derived `docs/api-contract.md` from the live backend route/schema code;
  found and documented 6 contract mismatches in the old `QuickPaperAI/client` app.
- **2026-09-11** — Built the typed API client layer (`src/lib/api/*`), fixing the old client's
  contract bugs.
- **2026-09-11** — Generated Login/Sign Up/Verify OTP/Reset Password wireframes in Stitch
  (existing "Examiner's Desk" design system had no auth screens) and added a Notifications
  section to the Dashboard wireframe.
- **2026-09-11** — Built all 9 screens from the Stitch exports (`design/`), wired real
  TanStack Router routing + TanStack Query hooks against the live backend.
- **2026-09-11** — Fixed: chapters not deduped (backend returns one row per chunk); Setup form
  showing chapters before subject/standard selected; SSE connection not recovering after a
  transient drop; SSE connection never reopening after Resume (stuck on Review until manual
  refresh); `Latex` component breaking text layout inside flex/grid containers; Cloud Vault
  cards only exposing the paper PDF (not DOCX/answer-key).
- **2026-09-11** — Added: "Paper Type Mode" presets (Standard/MCQ-only/Objective-only/Custom)
  with locked vs. freely-editable question-type selection; LaTeX rendering via KaTeX matching
  the backend PDF's own delimiter convention; per-route dynamic document titles including live
  generation progress percentage; client-side "Recent Drafts" tracking (ported from the old
  client's `drafts.ts` logic, restyled) since the backend has no endpoint listing non-saved
  sessions.
- **2026-09-11** — Added per-question `difficulty` (Easy/Medium/Hard) to the `Question` type
  and a badge on each Review card, following a backend handoff; verified against the actual
  `Question` model in `../QuickPaperAI/src/paper/models.py` before implementing. Also removed
  the "N Device Registered" status pill from the Dashboard's Notifications section (backend
  data was misleading since FCM registration isn't actually implemented client-side yet — see
  `docs/ROADMAP.md`) in favor of a simple enabled/disabled-on-this-device indicator.

- **2026-09-11** — Moved all runtime config to `.env`: gitignored `.env`, added a tracked
  `.env.example`, de-duplicated the overriding placeholder keys in `.env`, and made
  `VITE_API_BASE_URL` throw on a production build instead of silently falling back to
  `localhost:8000`.

- **2026-09-11** — Pinned the dev server to `VITE_DEV_PORT` (default 5173) with
  `strictPort: true`, so an occupied port is a startup error instead of a silent hop to 5174
  and CORS failures on every request.

- **2026-09-12** — Fixed a bug where refreshing or navigating back into a paper that was
  compiling (post-Finalize) got stuck on a frozen, non-advancing progress page instead of the
  Compiling screen: `generate.$threadId.tsx` previously relied only on a local `hasResumed`
  flag that resets on remount. Now derives "compiling" from the status payload itself
  (`"generating"` with every chapter already `"completed"`), which survives a refresh.
