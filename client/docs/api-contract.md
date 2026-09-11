# QuickPaperAI API Contract

Source of truth: `QuickPaperAI/src/{auth,paper,db}/routes/routes.py` and their Pydantic
schemas/services (`src/auth/user_schemas.py`, `src/auth/token_schemas.py`, `src/paper/schemas.py`,
`src/paper/models.py`, `src/paper/service.py`, `src/db/schemas.py`, `src/db/services/service.py`).
Re-derive this doc from those files if the backend changes — do not hand-edit around a drift.

Base URL: `VITE_API_BASE_URL` (defaults to `http://localhost:8000` in dev). All paths below are
relative to that base.

## Auth (`/auth`)

### `POST /auth/register`
- Auth: none
- Request: `{ email: string, password: string (8-128 chars), name: string }`
- Response `200`: `{ id: string (uuid), email: string, name: string, is_active: boolean, created_at: string (ISO datetime) }`

### `POST /auth/login`
- Auth: none
- Request: `application/x-www-form-urlencoded` body with `username` (= email) and `password` — this
  is an OAuth2 password form, **not JSON**.
- Response `200`: `{ access_token: string, token_type: string }`

### `POST /auth/send-email`
- Auth: none
- Request: `{ email: string, purpose: "signup" | "reset_password" }`
- Response `200`: `{ message: string }` — always the same generic message regardless of whether the
  account exists or is eligible (anti-enumeration). `429` if requested again within 60s.

### `POST /auth/verify-otp`
- Auth: none
- Request: `{ email: string, otp: string, purpose: "signup" | "reset_password" }`
- Response `200` (purpose = signup): `{ message: string, access_token: string, token_type: string }`
- Response `200` (purpose = reset_password): `{ message: string, reset_token: string }`
- Errors: `400` invalid/expired OTP or invalid purpose, `403` locked out after too many attempts.

### `POST /auth/reset-password`
- Auth: none
- Request: `{ email: string, token: string (the reset_token from verify-otp), new_password: string (8-128 chars) }`
- Response `200`: `{ message: string }`
- Errors: `400` invalid/expired token or email mismatch.

### `GET /auth/me`
- Auth: Bearer
- Response `200`: `{ id: string (uuid), email: string, name: string, is_active: boolean, created_at: string (ISO datetime) }`

### `POST /auth/device-token`
- Auth: Bearer
- Request: `{ token: string }` (FCM device token)
- Response `200`: `{ message: string }`

### `POST /auth/notification-settings`
- Auth: Bearer
- Request: `{ notifications_enabled: boolean }`
- Response `200`: `{ message: string }`

### `GET /auth/notification-settings`
- Auth: Bearer
- Response `200`: `{ fcm_token: string | null, notifications_enabled: boolean }`

## Paper generation (`/api`)

### `POST /api/generate`
- Auth: Bearer
- Request (`PaperGenerateRequest`):
  ```ts
  {
    institution_name: string
    subject: string
    standard: string
    difficulty: "Easy" | "Balanced" | "Hard"
    chapters: string[]
    objective_count: number             // default 0
    subjective_count: number            // default 0
    allowed_types: QuestionType[]       // default: all 8 types, see below
    difficulty_distribution: { easy: number, medium: number, hard: number } | null  // must sum to 100 if provided
  }
  ```
  Do **not** include any field beyond these (e.g. no `paper_type_mode` — that concept doesn't exist
  on the backend; see Notes).
- Response `200`: `{ thread_id: string, status: "generating" }`

### `POST /api/resume/{thread_id}`
- Auth: Bearer + ownership (403 if the thread isn't yours)
- Request: `{ selected_indices: number[] }`
- Response `200`: `{ status: "resumed", thread_id: string }`

### `GET /api/status/{thread_id}/stream`
- Auth: Bearer + ownership. Since `EventSource` can't set headers, pass the token as
  `?token=<token>`.
- Response: `text/event-stream`. Each `data: <json>\n\n` line is one of the shapes below. The
  stream closes itself after a terminal status (`completed`, `failed`, `awaiting_review`) — it is
  push-based (server only re-checks on an internal pub/sub message), not a polling loop.
- There is **no** plain `GET /api/status/{thread_id}` (non-stream) endpoint. Only the `/stream`
  route exists.

Status payload shapes:
```ts
type ChapterProgress = {
  chapter: string
  status: "pending" | "processing" | "completed" | "failed"
  generated_count: number
}

type StatusResponse =
  | { status: "uninitialized" }
  | { status: "generating", progress: Record<string, ChapterProgress> }   // key = chapter name
  | { status: "awaiting_review", targets: { objective: number, subjective: number }, questions: Question[] }
  | { status: "completed", files: { paper_pdf: string, paper_docx: string, answer_pdf: string } } // values are /api/download/... paths
  | { status: "failed", progress?: Record<string, ChapterProgress> }
```

`Question`:
```ts
{
  question_text: string
  question_type: QuestionType
  chapter: string
  marks: number
  difficulty: "Easy" | "Medium" | "Hard"  // per-question cognitive difficulty — distinct from
                                           // the whole-paper Difficulty/DifficultyDistribution
                                           // set on the /api/generate request. Backend type is
                                           // a shared 4-value enum (also has "Balanced", used
                                           // elsewhere for whole-paper difficulty) but this
                                           // field's own docstring/prompt only ever intend
                                           // these three — don't assume the union is exhaustive.
  options: string[]                 // populated only for MCQ (always 4)
  correct_answer: string
  answer: string
  evaluation_scheme: { point_text: string, allocated_marks: number }[]  // subjective questions only
  diagram_prompt: string | null
}
```

`QuestionType` = `"MCQ" | "FILL_IN_THE_BLANK" | "MATCH_THE_COLUMN" | "TRUE_FALSE" | "ONE_WORD_ANS" | "2_MARKS" | "3_MARKS" | "4_MARKS"`
(first 5 are objective, last 3 are subjective).

### `GET /api/download/{thread_id}/{filename}`
- Auth: Bearer + ownership
- `filename` is one of `paper.pdf`, `answer.pdf`, `paper.docx` (the values returned in `completed.files` / history are already full paths, just append the token).
- Query: `preview?: boolean` — when true and the file is a PDF, `Content-Disposition: inline` (viewable in-browser); otherwise `attachment` (downloads).
- Response: binary file body (`application/pdf` or `application/vnd.openxmlformats-officedocument.wordprocessingml.document`).
- Token must be attached as `?token=` (or `&token=` if the URL already has `?preview=true`) since this is used as a direct `<a href>`/`<iframe src>`, not a `fetch` call with headers.

### `POST /api/save-to-cloud/{thread_id}`
- Auth: Bearer + ownership
- Request: none
- Response `200`: `{ status: "success" } | { status: "failed" }` — **note**: failure is returned as
  `200` with `status: "failed"` in the body, not an HTTP error. Treat it as a domain result.

### `DELETE /api/cancel/{thread_id}`
- Auth: Bearer + ownership
- Response `200`: `{ status: "cancelled", message: string }`
- Errors: `500` if cleanup fails internally.

## DB (`/api/db`)

### `GET /api/db/get-chapters`
- Auth: none
- Response `200`: `{ chapters: { chapter_name: string, subject: string, standard: string }[] }`

### `GET /api/db/history`
- Auth: Bearer
- Response `200`: `{ history: PaperHistory[] }`

`PaperHistory`:
```ts
{
  id: number                     // NOT a string
  thread_id: string
  created_at: string             // ISO datetime
  institution_name: string
  subject: string
  standard: string
  difficulty: string             // defaults to "Balanced" if absent
  difficulty_distribution: { easy: number, medium: number, hard: number }
  chapters: string[]
  objective_count: number
  subjective_count: number
  allowed_types: string[]
  paper_pdf: string               // computed: /api/download/{thread_id}/paper.pdf
  answer_pdf: string               // computed: /api/download/{thread_id}/answer.pdf
  paper_docx: string               // computed: /api/download/{thread_id}/paper.docx
}
```
Only rows with `status = "saved"` (i.e. after `save-to-cloud` succeeded) are returned.

## Cross-cutting notes

- **Auth header**: `Authorization: Bearer <token>` on every authenticated JSON request. For SSE and
  file links, use `?token=` / `&token=` instead (see above) since those can't carry headers.
- **401 handling**: any endpoint returns `401` for a missing/invalid/expired token — the frontend
  should clear the stored token and redirect to login.
- **CORS**: the backend's dev origins already include `localhost:5173/8080/3000/8000` (and the
  127.0.0.1 equivalents); production origins come from a comma-separated `ALLOWED_ORIGINS` env var
  on the backend. Nothing to configure on the frontend side beyond picking `VITE_API_BASE_URL`.
- Known backend-side issue (not a frontend TODO): CORS was last configured with a credentialed
  wildcard origin in some environments — flagged as an open security item in the backend's own
  `docs/GOTCHAS.md`. Not something the frontend can or should work around.

### Corrections vs. the old `QuickPaperAI/client` frontend

The old client (`QuickPaperAI/client/src/lib/api.ts` + `types.ts`) has several mismatches against
the actual backend that must **not** be carried into the new client:

1. `api.status(threadId)` calls `GET /api/status/{threadId}` — this route doesn't exist. Only
   `GET /api/status/{threadId}/stream` (SSE) exists; the dead function must be dropped.
2. `GenerateRequest` includes a `paper_type_mode: PaperTypeMode` field. The backend's
   `PaperGenerateRequest` has no such field — it's a frontend-only concept for deriving
   `allowed_types`/counts and must never be sent in the request body.
3. `GenerateResponse` was typed as `{ thread_id: string }` — the real response also includes
   `status: "generating"`.
4. `resume()`'s response was typed as `{ ok: true }` — the real response is
   `{ status: "resumed", thread_id: string }`.
5. `history[].id` was typed `string` — it's actually a `number`.
6. `FailedStatus` included an optional `error?: string` field the backend never sends — only
   `progress` is ever included alongside `status: "failed"`.
