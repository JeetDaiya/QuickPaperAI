## QuickPaperAI — React Frontend Plan

A React (TanStack Start) client for your existing FastAPI + LangGraph backend at `http://localhost:8000`. No backend logic moves into Lovable — we only call your endpoints (`/api/generate`, `/api/status/{thread_id}`, `/api/resume/{thread_id}`, `/api/download/{thread_id}/{filename}`).

### Design direction (opinionated, non-generic)

**Concept: "Examiner's Desk"** — an editorial, paper-craft metaphor that nods to the physical act of setting a question paper, then sharpens it with a dark technical layer for the live generation. Avoids the generic "AI chatbot card grid" look.

- **Palette:** Two-surface system. Warm ivory paper (`oklch(0.97 0.012 85)`) for input/review screens where teachers do considered work; deep ink (`oklch(0.16 0.018 250)`) with a single restrained vermillion accent (`oklch(0.62 0.20 25)`) for the live generation and selector screens where focus matters.
- **Typography:** `Instrument Serif` for display headings (subject/chapter names, paper titles — feels like a printed exam header), `JetBrains Mono` for thread IDs, counts, marks, and log streams, `Inter` for body/UI.
- **Signature moves:**
  - Margin rule + line numbers down the left edge of the request form, like ruled foolscap.
  - Chapter progress shown as a vertical "stitched ledger" — each chapter is a row that fills with a hand-drawn-style underline as chunks → subtopics → candidates complete, with the live count rendered in mono.
  - Question candidate cards styled as index cards with a perforated edge and a hand-stamped checkbox; selecting one slides it into a right-rail "selected stack" with subtle paper-shuffle motion.
  - Floating selector dashboard reads like a tally sheet: `MCQ ▮▮▮▯▯ 3/5 · Subjective ▮▮▯ 2/3 · Σ 16 marks`.
  - Success screen renders the generated paper as a folded-letter preview before the download row.

### Screens & routes

```text
/                            Recent drafts dashboard + "New paper" CTA
/new                         Screen 1 — Paper Request form
/papers/$threadId/progress   Screen 2 — Live generation tracker (polls /status)
/papers/$threadId/review     Screen 3 — Candidate selector (HITL)
/papers/$threadId/done       Screen 4 — Previews + downloads
```

### Screen breakdown

1. **Request form (`/new`)**
   - Institution, Subject (dropdown), Standard (dropdown), Chapters (multi-select fed from a `/api/metadata` call — see Open questions), Difficulty (segmented), Paper Type Mode (segmented), Allowed Question Types (multi-select; auto-filled/locked based on mode to mirror Pydantic), Objective Count (default 5), Subjective Count (default 3).
   - Submit → `POST /api/generate` → store returned `thread_id` in `sessionStorage` + recent-drafts list → navigate to `/papers/$threadId/progress`.

2. **Live progress (`/papers/$threadId/progress`)**
   - Polls `GET /api/status/{thread_id}` every 1.5s via TanStack Query `refetchInterval`.
   - Renders the stitched-ledger of chapters with state (pending / processing / done) and per-chapter generated-candidate count.
   - Streaming-style log feed in a collapsible mono panel.
   - When status reports `ui_step === "review"` with candidates, auto-navigate to review.

3. **Candidate selector (`/papers/$threadId/review`)**
   - Tabs grouped by chapter; within each tab, candidates sorted by question type per `SECTION_CONFIG`.
   - Index-card UI: checkbox, question text, marks chip, expandable evaluation key, `[📷 Diagram Prompt]` badge when applicable.
   - Floating tally bar at the top showing selected vs requested counts and total marks; soft warning banner (not a hard block) when counts mismatch.
   - Selections stored locally in `useState`; "Submit selections" → `POST /api/resume/{thread_id}` with selected indices → navigate to done.

4. **Done (`/papers/$threadId/done`)**
   - Folded-paper preview (CSS) + embedded PDF preview via `<iframe>` on the file response URL.
   - Three download buttons hitting `/api/download/{thread_id}/{filename}` for student PDF, student DOCX, marking scheme PDF.

### Session recovery & recent drafts

- `sessionStorage` holds the currently active `thread_id`; on `/` we read `localStorage.recentDrafts` (array of `{ threadId, institution, subject, standard, createdAt, status }`) and render a sidebar list.
- On any page reload while a thread is active, restore via `thread_id` and re-poll status; the backend is the source of truth for `ui_step`, so the UI re-enters at the correct screen.

### Technical details

- **API client:** small `src/lib/api.ts` wrapper around `fetch` with `VITE_API_BASE_URL` (default `http://localhost:8000`). All calls happen from the browser; no `createServerFn` needed since the backend is external and same-origin is not required (your FastAPI must allow CORS for the Lovable preview origin — flagged below).
- **Data fetching:** TanStack Query for `/status` polling with `refetchInterval: 1500` and `enabled` gated by `ui_step !== "done"`.
- **Routing:** TanStack Start file routes as listed above; each route sets its own `head()` meta.
- **State:** Form state via `react-hook-form` + `zod` schema that mirrors your Pydantic constraints (so mode → allowed types validation runs client-side too).
- **Design tokens:** Add ivory/ink/vermillion + serif/mono/sans font tokens to `src/styles.css` as `oklch` variables; import Google Fonts in `__root.tsx` head.
- **Components:** Build custom `MarginRuledForm`, `StitchedLedger`, `IndexCard`, `TallyBar`, `FoldedPaperPreview`. Reuse shadcn `Tabs`, `Checkbox`, `Select`, `Button` underneath but restyle to match the metaphor — no default shadcn look will be visible.

### Out of scope

- No changes to your FastAPI, LangGraph, Pydantic, or document export code.
- No Lovable Cloud / Supabase — pure client app.

### Open questions (won't block — sensible defaults assumed)

1. Is there a `GET /api/metadata` (subjects, standards, chapters per standard) on your FastAPI, or should the frontend hardcode an initial list and you'll add one later?
2. Exact shape of `/api/status/{thread_id}` response (especially how chapter progress and the candidate list are keyed). I'll code against an assumed shape and adjust once you share a sample.
3. CORS — your FastAPI must allow the Lovable preview origin (`*.lovable.app`) and `localhost:8080`. If you haven't set `CORSMiddleware`, calls will fail in browser.

I'll proceed with the assumed shape and a clearly isolated `src/lib/api.ts` so swapping to your real response shape is a one-file change.
