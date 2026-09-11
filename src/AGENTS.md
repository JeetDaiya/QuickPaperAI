# GuruSahay (QuickPaperAI) — Agent Index

Agentic RAG app for a tuition teacher: input subject/standard/chapters/counts → generate
candidate questions from textbook chunks → teacher selects via HITL review (CLI or web) →
exam paper + answer key compiled to PDF and editable DOCX.

## Quick facts
- Workspace: `/home/jeet-daiya/Storage/Teddy/QuickPaperAI`
- Venv: `/home/jeet-daiya/Storage/Teddy/venv`
- Backend: `uvicorn src.app:app` (or `python -m src.main`)
- Worker: `arq src.paper.worker.settings.WorkerSettings`
- Standalone CLI: `python scripts/run_cli.py`
- Verify: `python -m compileall src/` (Python), `npx tsc --noEmit` in `client/` (TS)

## Where to look

| Need to... | Read |
|---|---|
| Understand layers, interfaces/adapters, DB schema, current folder layout | `docs/ARCHITECTURE.md` |
| Avoid re-breaking something that's broken before | `docs/GOTCHAS.md` — **read before touching auth, Gemini calls, Playwright, or LangGraph checkpoints** |
| Know what's deployed where, CI/CD, env vars | `docs/DEPLOYMENT.md` |
| See why something is built the way it is / project history | `docs/CHANGELOG.md` |
| Check planned-but-not-built features (don't build unless asked) | `docs/ROADMAP.md` |

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
- `ARCHITECTURE.md` and `GOTCHAS.md` are **living references** — edit them in place when the
  thing they describe changes. Never append a dated entry to them.
- `CHANGELOG.md` is an **append-only log** — add one short dated bullet when you finish
  something. Never put prose explanations there; that belongs in a commit message or PR.
- If you change something `ARCHITECTURE.md` or `GOTCHAS.md` describes, update that file in the
  same piece of work — don't leave it for later, that's how this file went stale last time.