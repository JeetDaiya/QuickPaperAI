# Architecture

Living document — reflects the system **as it currently is**. Edit in place; don't append
dated notes here (use `CHANGELOG.md` for that).

## Data pipeline
- **Extraction**: LlamaCloud/LlamaParse (`tier="agentic_plus"`, `expand=["markdown"]`).
- **Sanitization**: `sanitize_ncert_markdown` regex pipeline normalizes headers
  (`1.1`→`##`, `1.1.1`→`###`, `Activity 1.1`→`####`, question sections→`### QUESTIONS`).
- **Chunking**: LangChain `MarkdownHeaderTextSplitter` on `##`/`###`, giving topic-oriented
  chunks (not token-bounded). Each chunk tagged with `sub_topic`, `standard`, `subject`, `chapter`.
- **Retrieval**: no vector embeddings — pure metadata filter:
  `WHERE subject=X AND standard=Y AND chapter_name=Z ORDER BY chunk_index` (per-chapter index).
- Chapter PDFs parsed concurrently (`ThreadPoolExecutor`, `max_workers=5`).

## Question generation
- Iterative-with-memory: process chunk batches (5/batch) per chapter sequentially; each batch
  sees prior generated questions to avoid duplicates. LLM picks question types dynamically.
- Chapters fan out in parallel via LangGraph `Send` API.
- Difficulty is steered via `DifficultyDistribution` (easy/medium/hard %, must sum to 100) →
  `distribute_difficulty` computes per-band counts → injected into the prompt as a
  "PEDAGOGICAL DIFFICULTY BLUEPRINT".

## LangGraph pipeline
```
START → distribute → [Send: per chapter, parallel]
  → question_generator_node (iterative loop, one chapter)
  → review_node (HITL interrupt — teacher selects questions)
  → formatter_node → pdf_node
  → END
```
- Checkpointed via `AsyncPostgresSaver` — survives crashes/restarts; resumable by `thread_id`.
- Cancellation: `progress_tracker.is_cancelled(thread_id)` should be checked between batches
  inside `question_generator_node` — verify this is actually wired before assuming cancel works.
- Retries: `RetryPolicy` on fanned-out nodes, up to 3 attempts, exponential backoff + jitter,
  for 429 / 503 / structural decode failures.

## Background execution
- Durable ARQ (Redis-backed) worker, not in-process `asyncio.Task`.
- `TaskManager.register_task` enqueues `generate_paper_task` with `_job_id=thread_id` (dedup).
- Worker resumes from Postgres checkpoint if one exists for the thread; otherwise fresh run.
- Progress: `ProgressTracker` (Upstash Redis) — `HSET progress:{thread_id}`, 2h TTL,
  best-effort (read/write/delete failures are swallowed; generation continues on Redis outage).
- Real-time updates: Redis Pub/Sub channel `channel:progress:{thread_id}`, consumed by an SSE
  endpoint (`GET /api/status/{thread_id}/stream`) that closes on `completed`/`failed`/
  `awaiting_review`.

## Document compilation
- PDF: Playwright, **async API** (`async_playwright`) — must not use sync API inside the
  asyncio event loop (see GOTCHAS).
- DOCX: Pandoc, wrapped in a soft-fail try/except — PDF is the critical path, DOCX failure
  degrades gracefully with a warning.
- Diagram questions: 1px-bordered blank box on the student sheet, sized for photocopying;
  copy-pasteable image-gen prompt embedded in the Word placeholder cell and repeated in a
  "Diagram Prompt Annex" at the end of the answer key.
- Matching-column questions: intro text in `question_text`, matched pairs pipe-separated in
  `options` (e.g. `"(i) Burning of magnesium | (a) Evolution of hydrogen"`), rendered
  server-side into a 2-column HTML table.

## Auth
- Custom JWT auth (`python-jose`), not a third-party identity provider — but abstracted behind
  an `AuthService` interface specifically so it can be swapped later (Google/Supabase
  Auth/Clerk) without touching routes.
- Password hashing via `passlib[bcrypt]` (see GOTCHAS for the version pin).
- OTP flow (signup + reset_password) is purpose-namespaced and Redis-backed (Upstash), with
  cooldown + attempt-lockout state.
- **Tenant isolation (BOLA/IDOR)**: `verify_thread_ownership` FastAPI dependency enforced on
  every `thread_id`-parameterized route (`/resume`, `/status/stream`, `/download`,
  `/save-to-cloud`, `/cancel`) — checks `session.user_id == current_user["id"]`, 403 on
  mismatch. `extract_user_id` in `src/dependencies.py` centralizes the `"id"` vs `"user_id"`
  key resolution.

## Clean Architecture layers
All cross-cutting capabilities are `interfaces/` + swappable `adapters/`:

| Capability | Interface | Adapter(s) |
|---|---|---|
| Users/chunks/papers | `UserRepository`, `ChunkRepository`, `PaperRepository` | `Supabase*Repository` (uses service-role key, bypasses RLS — routes must enforce ownership themselves) |
| File storage | `StorageService` | `LocalStorageService` (temp/cache), `SupabaseStorageService` (permanent) |
| OTP | `OTPStore` | `MemoryOTPStore` (dev fallback), `RedisOTPStore` (Upstash, prod) |
| Email | `EmailService` | `FastMailService` (`fastapi-mail==1.6.4`, pinned) |
| Paper rendering | `PaperFormatter` | `HTMLPaperFormatter` (KaTeX), `MarkdownPaperFormatter` |
| PDF/DOCX compilation | `DocumentCompiler` | `CustomDocumentCompiler` (Playwright + Pandoc) |
| Push notifications | (not yet abstracted — direct `FirebaseNotificationService`) | — |
| Task queue | (not yet abstracted — direct ARQ `TaskManager`) | — |

Formatters/compiler are injected into graph nodes via `GraphConfig` (`RunnableConfig`'s
`configurable`), not imported directly in `nodes.py`.

## Current file structure
```
QuickPaperAI/
├── src/
│   ├── auth/        # interface/, adapters/ (JWT+bcrypt, RedisOTPStore), routes/, schemas
│   ├── paper/        # models, schemas, service, task_manager, rate_limiter, routes/,
│   │                #   graph/ (builder, nodes, state, tracker, utils), formatters/, compilers/
│   ├── db/           # interfaces/, adapters/ (Supabase), services/, routes/
│   ├── storage/       # interfaces/, adapters/ (local, supabase)
│   ├── mail/          # interfaces/, adapters/ (fastmail)
│   ├── config/         # settings.py (LLM + fallback chains), prompts.py
│   ├── base_settings.py, dependencies.py, app.py, main.py
├── scripts/            # parse_textbooks.ipynb, run_cli.py, recover_paper.py
├── data/Std_10_Chapters/
├── outputs/            # local PDF/DOCX cache (gitignored)
├── Dockerfile, requirements.txt
```
(Migrated from a legacy `core/` + `server/` split — if you see `core.*` imports or paths
anywhere, that's dead/historical, not current.)

## Database schema (Supabase Postgres)
```sql
chunks(id, standard, subject, chapter_name, sub_topic, chunk_index, content,
       has_image, image_urls[], UNIQUE(standard, subject, chapter_name, chunk_index))

users(id uuid pk, email unique, hashed_password, name, is_active, created_at, updated_at)

generated_papers(id, user_id → users.id, thread_id, institution_name, subject, standard,
                  difficulty, chapters[], objective_count, subjective_count, allowed_types[],
                  paper_pdf_path, answer_pdf_path, paper_docx_path, created_at)
```

## Key domain models
```python
class PaperRequest(BaseModel):
    subject: str; standard: str; institution_name: str; difficulty: str
    chapters: list[str]; objective_count: int; subjective_count: int

class Question(BaseModel):
    question_text: str; question_type: QuestionTypes; chapter: str; marks: int
    options: list[str] = Field(default=[])          # flat, no minItems/maxItems (Gemini rejects those)
    correct_answer: str; answer: str
    evaluation_scheme: list[EvaluationPoint] = Field(default=[])
    diagram_prompt: Optional[str] = None

class DifficultyDistribution(BaseModel):   # easy + medium + hard must == 100
    easy: int; medium: int; hard: int
```
`Question.chapter` is normalized to `str(chapter)` (numeric string matching the DB) in
post-processing — don't let the LLM's raw chapter name/prefix leak through, it breaks
frontend tab grouping.