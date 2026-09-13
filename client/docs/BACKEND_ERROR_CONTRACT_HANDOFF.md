# Backend error-handling changes — handoff for frontend work

This documents backend work completed in a separate session, verified directly against the
current backend source (file:line citations below — re-verify against
`../QuickPaperAI/src/` yourself before relying on any of this, per this repo's own rule that
the backend code is the only source of truth). Frontend consumption of any of this was
explicitly **out of scope** for that session — nothing in `client/` has been touched. This
file is what a frontend agent needs to pick that work up.

## What changed

The backend introduced a domain exception hierarchy (`QuickPaperAI/src/exception/`) and wired
it into FastAPI. As of this handoff, error responses come in **three different shapes**
depending on which code path produced them — this inconsistency is real and current, not a
frontend bug to "fix around" silently.

### Shape 1 — classified `AppError` (the new, preferred shape)

Any error raised as one of the exception classes in
`QuickPaperAI/src/exception/exceptions.py` produces:

```json
{ "detail": "Human-readable message safe to show a user", "code": "MACHINE_READABLE_CODE" }
```

with a real HTTP status code. The full current catalog (`src/exception/exceptions.py:1-34`):

| `code` | HTTP status | Meaning |
|---|---|---|
| `NOT_FOUND` | 404 | resource doesn't exist |
| `UNAUTHENTICATED` | 401 | bad credentials / invalid or expired token |
| `RATE_LIMITED` | 429 | OTP cooldown / lockout |
| `PERMISSION_ERROR` | 403 | authenticated but not allowed |
| `VALIDATION_ERROR` | 400 | bad input (e.g. wrong/expired OTP) |
| `INTERNAL_SERVER_ERROR` | 500 | generic server-side failure |
| `REPOSITORY_ERROR` | 500 | a database/storage operation failed |
| `SERVICE_UNAVAILABLE` | 503 | a genuinely transient failure — safe to retry |

This is handled by `@app.exception_handler(AppError)` in `src/app.py:42-48`. This is new
compared to whatever the frontend was built against before — **`code` did not exist in any
error response prior to this work.**

**Update (later in the same session): `detail` is now genuinely, deliberately generic for
most codes — don't expect it to vary by what specifically failed.** Earlier in this work,
`detail` accidentally leaked technical detail (Redis, Pandoc stderr, raw file paths, internal
UUIDs) for ~40 of the 58 call sites, because the exception class's `message` argument was being
used both as the log line *and* the HTTP body. That's fixed now: `AppError.message` is optional
and falls back to a fixed per-class default (`src/exception/exceptions.py`) when the call site
doesn't override it — which is now true for every `RepositoryError`/`TransientError`/most
`NotFoundError` site. **Practical consequence: every database/storage/transient failure across
the whole backend now returns one of exactly these strings, regardless of which specific query
or file operation failed:**

| `code` | `detail` you'll actually see |
|---|---|
| `NOT_FOUND` | "The requested resource was not found." |
| `UNAUTHENTICATED` | "Authentication failed." *(default — see exception below for actual current text)* |
| `RATE_LIMITED` | "Too many requests. Please try again later." — **defined but not currently reachable**: all 3 existing `RateLimitError` call sites (auth/OTP) override it with specific text (see exception below); nothing raises this class without a message today. |
| `PERMISSION_ERROR` | "You don't have permission to do that." — **defined but not currently raised anywhere in the codebase.** Reserved for future use; don't build UI for a code that can't appear yet. |
| `VALIDATION_ERROR` | "The request was invalid." *(this default genuinely does appear — e.g. a Pandoc/DOCX compile failure — in addition to the auth sites below with their own text)* |
| `INTERNAL_SERVER_ERROR` | "Something went wrong. Please try again." |
| `REPOSITORY_ERROR` | "A database operation failed. Please try again." |
| `SERVICE_UNAVAILABLE` | "A temporary issue occurred. Please try again shortly." |

**Exception to the exception**: the auth/OTP call sites in `src/auth/adapters/custom_auth_service.py`
and `src/auth/services/service.py` (login, OTP send/verify, reset-password — roughly 12 sites)
were deliberately left with their own specific, varied text (e.g. *"Incorrect email or
password"*, *"Too many failed verification, Please try again after 15 minutes."*, *"Invalid
OTP."*) because that copy was already user-appropriate and worth keeping distinguishable. **So:
auth/OTP error `detail` text is still specific and can be matched on if truly needed; almost
everything else now collapses to one of the eight generic strings above.** If you were relying
on `detail` text to distinguish *which* database/storage operation failed for anything outside
auth, that signal is gone — use `code` (still present) plus HTTP status only; the specific
identifiers (file paths, thread IDs, table names) are still captured server-side in each
exception's `context`, but that's log-only and never reaches the response body.

### Shape 2 — unhandled/unexpected exceptions (also new)

A second, separate middleware (`src/app.py`, the `ServerErrorMiddleware` registration) now
catches anything that isn't Shape 1 or a raw `HTTPException`, and returns:

```json
{ "detail": "Something went wrong. Please try again.", "code": "INTERNAL_SERVER_ERROR" }
```

with status `500`. Before this, an exception here returned a bare `text/plain` body with **no
CORS headers**, which the browser reported as a CORS failure rather than a 500 — verified this
was actually invisible in DevTools prior to the fix. If you've built any workaround for that
specific symptom, it should no longer be necessary; verify and remove it rather than keep it as
dead code.

### Shape 3 — not-yet-migrated endpoints (still exists, still current)

**Not every backend code path has been converted.** Several places still raise a raw
`fastapi.HTTPException` directly, which returns FastAPI's default shape — **`detail` only, no
`code` field**:

```json
{ "detail": "Email already registered" }
```

Confirmed still-unconverted, as of this handoff:
- `src/auth/adapters/custom_auth_service.py:73,76,83,87,94,100` — `register_user`,
  `authenticate_user`'s DB-error and not-yet-verified branches. **This means `/auth/register`
  and `/auth/login` do not currently return a `code` field on any of their error paths.**
- `src/dependencies.py` — `get_current_user`'s "could not validate credentials" (401) and
  `verify_thread_ownership`'s 403 "access denied" paths.

**Do not assume `code` is present on every error response.** Any error-handling code must
treat `code` as optional and fall back to `detail`-only string handling when it's absent —
this is a real, current split in the backend, not a transitional detail that's about to
disappear.

### `PaperState.errors` — new field on the paper-generation "failed" status

`GET /api/status/{thread_id}/stream` and whatever reads its payload: the `status: "failed"`
response now includes a new `errors` field (`src/paper/service.py`, the `get_generation_status`
method's `"failed"` branch):

```json
{
  "status": "failed",
  "progress": { "3": { "chapter": "3", "status": "failed", "generated_count": 0 }, ... },
  "errors": [
    { "chapter": "3", "message": "All question batches failed for this chapter" }
  ]
}
```

- `errors` is a **list of objects** (`{chapter, message}`), always present on this response
  (defaults to `[]` if nothing failed at the field level — though if you're seeing
  `status: "failed"` at all, `errors` will usually be non-empty).
- **This directly corrects a documented gap**: `client/docs/api-contract.md:216` currently
  says *"`FailedStatus` included an optional `error?: string` field the backend never sends —
  only `progress` is ever included."* That line is now **stale** — the backend does send
  structured failure data, just not in the shape that line describes (plural `errors: object[]`,
  not singular `error?: string`). Whoever picks up frontend work should update
  `api-contract.md` accordingly once the actual TypeScript type is decided, and should verify
  against `src/paper/service.py`'s `get_generation_status` directly rather than trust this
  summary if time has passed.

## What's explicitly NOT done (don't assume otherwise)

- No frontend code was touched. The current frontend's error parsing, display, and any
  substring-based message matching are unmodified and unaudited as of this handoff — this repo
  was recently restructured (the `client/` layout now uses `src/pages/` + `src/lib/api/` as a
  directory; older references to a flat `src/lib/api.ts`/`types.ts` describe a prior iteration,
  per `api-contract.md`'s own "Corrections vs. the old client" section) — re-derive current
  frontend behavior from the actual current files, don't assume anything from an older audit.
- The SSE stream's error path is unchanged: a crash mid-stream (after headers/first chunk are
  sent) still just ends the connection with no error frame — this was verified explicitly this
  session (a `ServerErrorMiddleware`-level fix cannot inject a response into an already-started
  stream; that's a protocol constraint, not an oversight). If the stream needs to communicate a
  failure mid-flight, that requires the SSE generator itself to yield an error event — not
  built.
- `429` responses (OTP cooldown/lockout) don't include a `Retry-After` header. If a countdown
  UI needs a real duration, that's a backend gap to request, not something to reverse-engineer
  from the message text.

## Suggested frontend tasks (verify each against current code before acting — don't assume)

1. Wherever HTTP error bodies are parsed, capture `code` when present, keep it on whatever
   error representation propagates through the app (not just a flattened string message) — but
   keep the existing string-message fallback working for the Shape 3 endpoints above.
2. Anywhere the app currently branches on the *text* of an error message (e.g. checking a
   status message for specific words to distinguish rate-limiting or lockout from other
   failures) — evaluate replacing that with a `code`-based check, but only for the specific
   codes above, and only where the corresponding backend path is actually Shape 1 (converted).
   Login/register (Shape 3) must keep working without `code`.
3. Update whatever type represents the paper-generation "failed" status to match the real
   `errors: {chapter: string, message: string}[]` shape, and decide how to render it (e.g. one
   line per failed chapter) instead of relying on a field the backend never actually sends.
4. Update `client/docs/api-contract.md`'s line 216 (or wherever it lands after other edits) to
   reflect the real `errors` field once the above is implemented — that file's own header says
   to re-derive it from backend code, not hand-edit around drift.
