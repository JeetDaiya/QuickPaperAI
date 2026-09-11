# Changelog

Append-only. One line per completed item, newest at bottom. No prose/rationale — if it needs
explaining, that belongs in a commit message, not here. If it's still true today, it belongs in
`ARCHITECTURE.md` or `GOTCHAS.md` instead, not just here.

## Pre-2026-07-19 (early build, undated)
- LlamaCloud parsing + sanitize/chunk pipeline built (chunks table, metadata filtering).
- Iterative-with-memory generation + LangGraph `Send` fan-out per chapter.
- FastAPI server decoupled from CLI; Supabase storage sync + history endpoints; download cache.
- Custom JWT auth (passlib/bcrypt + python-jose) replacing dummy-user system.
- React client wired to auth (login/signup/session interceptors), auto-save drafts.
- Fixed: sibling-package imports, Postgrest `.distinct()` crash, async pool `open=False`,
  Gemini 400s (thinking+structured-output conflict, array length constraints), matching-column
  rendering, LaTeX backslash corruption, subjective mark skew, CLI "select all", checkpoint
  serialization threading, dynamic type filtering, MCQ option prefix duplication, diagram
  placeholder + prompt annex, FCM env var migration, DOCX soft-fail isolation, retry/backoff
  policy on generation nodes.

## 2026-07-19
- Decoupled `AuthService` interface; account activation guards; `OTPPurpose` enum
  (signup/reset_password); OTP delivery env-loading fix; forgot-password endpoint + flow;
  frontend OTP verification route with lockout/cooldown handling.
- `PaperFormatter` / `DocumentCompiler` interfaces introduced; DI via `GraphConfig`.
- Redis-backed `ProgressTracker` (best-effort, graceful degradation on Redis outage).

## 2026-07-25
- Consolidated legacy `core/` + `server/` into unified `src/` feature-module layout; domain
  enums (`ChapterStatus`, `DocumentType`, `SubjectType`, `PaperDifficulty`) extracted; CLI/
  notebook scripts moved to `scripts/`.

## 2026-07-26
- Full FCM push notification stack: backend adapter + device-token/settings endpoints,
  frontend hook + service worker, review-ready and failure notifications.

## 2026-08-01
- Migrated background execution from in-memory `asyncio.Task` to durable ARQ worker +
  LangGraph Postgres checkpoint resumption. `PaperService.generate_paper` now returns in <50ms.
- (Also touched CORS during this pass — see `docs/GOTCHAS.md`, flagged in a later audit.)

## 2026-08-02
- Real-time SSE progress streaming via Redis Pub/Sub, replacing 1s DB/Redis polling.

## 2026-08-17
- Fixed Playwright sync-API-inside-asyncio-loop crash; compiler converted fully async.

## 2026-08-22
- Difficulty-weighted mark distribution (easy/medium/hard %) end-to-end, backend + frontend
  (preset cards, custom allocator, history badges).

## 2026-08-27
- BOLA/IDOR fix: `verify_thread_ownership` dependency enforced across all `thread_id` routes.
- LangGraph HITL resume dict-unpacking fix; dependency propagation fix for resumed runs
  (formatters/compiler were `None` on resume, now passed through `config["configurable"]`).