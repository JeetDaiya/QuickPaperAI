# QuickPaperAI Frontend — Agent Index

React SPA for QuickPaperAI: teachers configure a paper (subject/standard/chapters/counts),
watch AI generation progress live, review and select the generated questions, then download
the compiled PDF/DOCX/answer-key. Talks directly to the FastAPI backend in `../QuickPaperAI` —
no server of its own.

## Quick facts
- Workspace: `/home/jeet-daiya/Storage/Teddy/Quick_Paper_AI_Client`
- Backend (sibling repo, source of truth for the API): `/home/jeet-daiya/Storage/Teddy/QuickPaperAI`
- Dev server: `npm run dev` — **must** run on port 5173, 8080, or 3000 (or 8000), the only
  ports the backend's dev CORS allowlist accepts (`QuickPaperAI/src/app.py`). Any other port
  fails silently with a CORS error on every request.
- Build: `npm run build` (runs `tsc --noEmit` then `vite build`)
- Verify: `npx tsc --noEmit`
- Backend must be running (`uvicorn src.app:app` in `../QuickPaperAI`) for anything beyond the
  static pages to work — this app has no mock-data mode anymore, everything hits the real API.

## Where to look

| Need to... | Read |
|---|---|
| Understand the layers (routes/pages/hooks/lib), routing, design system, drafts | `docs/ARCHITECTURE.md` |
| Avoid re-breaking something that's broken before | `docs/GOTCHAS.md` — **read before touching the SSE hook, the Latex component, or CORS/deploy config** |
| Know what's deployed where (currently: nothing) and what a real deploy needs | `docs/DEPLOYMENT.md` |
| See why something is built the way it is / project history | `docs/CHANGELOG.md` |
| Check planned-but-not-built features (don't build unless asked) | `docs/ROADMAP.md` |
| Check the exact API contract this app is built against | `docs/api-contract.md` — **the source of truth is the backend code, not this file**; re-derive it from `../QuickPaperAI/src/{auth,paper,db}/routes/routes.py` if it ever looks stale |

## Working style
*(Applies to every task. Trivial one-liners don't need the full ceremony — use judgment.)*

**Think before coding**
- State assumptions explicitly; if genuinely uncertain or multiple interpretations exist, ask
  or lay them out rather than picking silently.
- If a simpler approach exists, say so — push back rather than build the elaborate version.

**Simplicity first**
- Minimum code that solves the problem. No speculative features, no unrequested
  configurability, no error handling for impossible cases.
- If it could be a third the size, rewrite it before calling it done.

**Surgical changes**
- Touch only what the request requires — don't refactor or "improve" adjacent code, comments,
  or formatting, and match existing style even if you'd do it differently.
- Remove imports/vars/functions your own change orphaned; if you notice unrelated dead code,
  mention it, don't delete it.
- Every changed line should trace back to the request.

**Goal-driven execution**
- Turn vague asks into verifiable goals ("fix the bug" → reproduce it with a test, then make
  that test pass) and state a short plan with a verify step per item on multi-step work.

## Repo-specific rules
- **Never invent backend behavior.** No endpoint path, request field, or response shape gets
  added to `src/lib/api/*` unless it's confirmed by reading the actual backend route/schema
  code in `../QuickPaperAI/src/`. If the contract is unclear, stop and ask — don't guess.
- **Layering is one-way**: `routes/*.tsx` are thin containers (hooks + navigation only) →
  `pages/*.tsx` are presentational (props in, JSX out, no fetch calls) → `lib/api/*` is the only
  code that knows about HTTP. Don't let a page import from `lib/api` directly.
- `ARCHITECTURE.md` and `GOTCHAS.md` are **living references** — edit them in place when the
  thing they describe changes. Never append a dated entry to them.
- `CHANGELOG.md` is an **append-only log** — add one short dated bullet when you finish
  something. Never put prose explanations there; that belongs in a commit message or PR.
- If you change something `ARCHITECTURE.md` or `GOTCHAS.md` describes, update that file in the
  same piece of work — don't leave it for later, that's how this file goes stale.
- This repo has a sibling, `../QuickPaperAI` — it has its own `CLAUDE.md`/`AGENTS.md` and
  `docs/`. Don't edit those from here; if backend behavior needs to change to support a
  frontend feature, say so and let that be a separate, explicit task.
