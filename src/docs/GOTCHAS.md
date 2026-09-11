# Gotchas

Non-obvious constraints and past traps. One line each. Read before touching the related area.
If you hit something new and non-obvious, add a line here — don't bury it in a commit message.

## Gemini / LLM
- `with_structured_output()` + `thinking_level` together → 400 `INVALID_ARGUMENT`. Don't combine them.
- Gemini's structured-output JSON Schema forbids `minItems`/`maxItems` and complex `anyOf`/null
  unions — keep list fields flat with `Field(default=[])`, no length constraints on the schema.
- LaTeX backslashes: prompts ask for **single** backslashes (`\rightarrow`) — normal `.tex` form.
  `with_structured_output` already decodes the JSON layer, so the old "double-escape everything"
  instruction was wrong and made the LLM emit literal `\\text`, which means *line break* in
  TeX/KaTeX and renders as raw gibberish in the DOCX, the PDF **and** the review UI (three
  renderers, all silent except Pandoc). `Question.normalize_question` canonicalizes either
  convention via `_canonicalize_latex` (`src/paper/models.py`) — don't remove it, and don't
  "fix" escaping in a formatter instead. Known limitation: an under-escaped `\nu`/`\neq` decodes
  to a real newline and is unrecoverable, since a genuine line break looks identical (`\r`/`\t`/
  `\f`/`\b` → `\rho`/`\theta`/`\frac`/`\beta` *are* recovered).
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
  explicitly registered in the `JsonPlusSerializer` allow-list in **both** `src/dependencies.py`
  and `src/paper/worker/settings.py` — they must stay identical. Missing types cause silent
  deserialization failures on resume.
- ARQ retry backoff: `generate_paper_task` uses `Retry(defer=current_try * 30)` (import `Retry`
  from `arq`, not `arq.jobs` — it's defined in `arq/worker.py` and re-exported at the top level)
  for linear backoff on transient failures — don't replace with a bare `raise` or retries fire
  immediately.
- The `app` and `worker` containers both write/read `outputs/{thread_id}/...` (PDF/DOCX local
  cache) and must share the `paper_outputs` Docker volume (`docker-compose.yml`) — `pdf_node`
  runs wherever the graph resumes (the ARQ worker, since resume always happens there), and
  `get_generation_status`/`download_file`/`save_to_cloud` run in the `app` container. Without
  the shared volume, the app container never sees the compiled files and generation appears to
  hang forever even though the worker finished successfully.
- `stream_generation_status` (`routes.py`) is push-based, not polling: it subscribes to Redis
  channel `channel:progress:{thread_id}` (via a raw TCP `redis.asyncio` connection from
  `get_pubsub_redis()` — the REST-based `upstash_redis` client used elsewhere can't hold a
  blocking `SUBSCRIBE`) and only re-checks `get_generation_status()` when a message arrives,
  instead of polling Redis every second. `ProgressTracker.update_chapter_progress` already
  publishes on chapter updates; `ProgressTracker.notify_thread_updated()` covers the rest (PDF
  compilation has no chapter-progress state of its own) and is called from `generate_paper_task`/
  `resume_paper_task` in `worker/tasks.py` **after** `run_graph`/`agent.ainvoke` returns — never
  from inside a graph node — so the checkpoint state is guaranteed durable before the notification
  fires. If you add a new terminal outcome to the graph, make sure something calls
  `notify_thread_updated()` (or an equivalent publish) after it. The stream subscribes **before**
  its initial `check_status()` (pub/sub doesn't buffer for absent subscribers — checking first
  would let a "finished" shout land in the gap and be lost), and on each `get_message` timeout it
  re-checks status anyway as a self-healing safety net, so a dropped/mistimed shout costs at most
  ~10s of lag, never a browser tab stuck until manual refresh. Don't turn that timeout back into a
  bare `continue` — that reintroduces the "completed paper needs a refresh" bug.

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