# Gotchas

Non-obvious constraints and past traps. One line each. Read before touching the related area.
If you hit something new and non-obvious, add a line here — don't bury it in a commit message.

## Gemini / LLM
- `with_structured_output()` + `thinking_level` together → 400 `INVALID_ARGUMENT`. Don't combine them.
- Gemini's structured-output JSON Schema forbids `minItems`/`maxItems` and complex `anyOf`/null
  unions — keep list fields flat with `Field(default=[])`, no length constraints on the schema.
- LLM must emit **double** backslashes for LaTeX (`\\rightarrow`, `\\theta`) or single-backslash
  JSON decodes `\r`/`\t` into control characters and corrupts the symbol. There's a
  `clean_latex()` regex post-processor as a second line of defense — don't remove it even if
  the prompt looks like it's handling it.
- 2-mark / 4-mark subjective questions get skipped in favor of 3-mark by default — needs
  explicit few-shot examples and a quota directive in the prompt, not just a count.

## Auth
- `bcrypt` must stay pinned to `3.2.2` with `passlib` — `bcrypt>=5.0.0` breaks
  `pwd_context.verify()` with a misleading `password cannot be longer than 72 bytes` error even
  on short passwords. If a dependency bump touches bcrypt, check this first.
- Reset-password OTP and signup OTP are namespaced by `purpose` in the Redis key
  (`otp:{purpose}:{email}`, and likewise for cooldown/attempts/lockout keys) — a code issued
  for one purpose cannot verify the other. OTPs are stored SHA-256-hashed and compared with
  `hmac.compare_digest`; every OTP-store call must pass `purpose`.

## Async / infra
- Playwright: must use `async_playwright` / `async_api`, never the sync API — sync calls inside
  an active asyncio loop (FastAPI or ARQ worker) throw immediately.
- `AsyncConnectionPool` must be constructed with `open=False` and opened explicitly
  (`await pool.open()`) inside the lifespan handler, or you get deprecation warnings / races.
- Postgrest's Python client has no `.distinct()` on select — dedupe chapter lists in Python.
- LangGraph checkpoint state: every Pydantic type that can appear inside graph state
  (`PaperRequest`, `Question`, `EvaluationPoint`, `DifficultyDistribution`, enums, etc.) must be
  explicitly registered in the `JsonPlusSerializer` allow-list, or resumed/crashed runs fail to
  deserialize silently.

## Frontend
- `VITE_API_BASE_URL` needs an explicit `http(s)://` prefix or the browser treats API calls as
  relative paths and 500s. There's a self-healing prepend in `client/src/lib/api.ts` — don't
  regress it.
- Preview/download URLs append params with `&`, not a second `?` — a second `?token=` on an
  already-parameterized URL silently breaks auth (`?preview=true?token=...` invalidates token).

## Security — known open item
- ⚠️ CORS in `src/app.py` was last set to `allow_origin_regex=".*"` with `allow_credentials=True`
  to unblock a credentialed cross-origin request. This combination was independently flagged as
  **critical** in the most recent security audit (wildcard origin + credentials = any site can
  make authenticated requests as the logged-in user). Check the current state of `src/app.py`
  before assuming this is still open — if it hasn't been fixed, an explicit origin allowlist is
  the correct fix, not disabling `allow_credentials`.
- The `{"status": "failed"}` + HTTP 200 error envelope pattern ("Option A") exists in
  `PaperService` in places — check `docs/ROADMAP.md`, this is a known-wanted migration to real
  HTTP status codes, don't treat 200-with-failed-body as a new bug if you see it.