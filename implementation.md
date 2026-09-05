# Section 2 Remediation — Concurrency, Async Safety & Task Management

Reference doc for `fix-concurrency-issues` branch. Each item below is independent and can be
approved/implemented one at a time. Nothing in this file has been applied to the code yet.

Source: `backend_review.md` Section 2, verified against current code (several audit findings
were already fixed by earlier unrelated work and are excluded — see PR #22 for pool-sizing
fixes, and the `_get_channel_key` typo fix already present in `tracker.py`).

---

## 1. LLM call has no timeout — hangs forever on a stalled Gemini call

**Not in the original audit — discovered live** when a real generation (thread
`74352147-9a57-445a-bb9e-a5c52021a004`, subject "ss", chapters 6/9/10) got stuck on chapter 9,
batch 3/4, with no error and no log line ever again. Prioritized first since it's an active bug
that just caused real user pain.

### Problem
`question_generator_node` (`src/paper/graph/nodes.py:89`) calls:
```python
batch_output = await generator_chain.ainvoke({...})
```
with no timeout. If the Gemini API stalls (network issue, provider-side stuck request), this
`await` blocks indefinitely — no exception is raised, so the existing `except Exception` never
fires, and no progress update happens. The only thing that eventually kills it is ARQ's
`job_timeout=3600` (1 hour) in `src/paper/worker/settings.py:32` — far too slow for a
UX-facing wait.

### Root Cause
No timeout wrapper around an external API call inside a loop that otherwise assumes failures
raise exceptions promptly.

### Files
- `src/paper/graph/nodes.py`
- `requirements.txt`

### Proposed Change
Add `tenacity` to `requirements.txt` (not currently a dependency — checked, only `upstash-redis`
is listed explicitly for Redis; `tenacity` is a new, small, pure-Python addition).

Pull the LLM call into a small, reusable, retry-decorated helper instead of hand-rolling the
retry loop inline:

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from langchain_core.exceptions import OutputParserException

@retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(2),
    retry=retry_if_exception_type((asyncio.TimeoutError, OutputParserException)),
    reraise=True
)
async def _generate_batch(generator_chain, batch_input: dict, timeout: int = 90):
    return await asyncio.wait_for(generator_chain.ainvoke(batch_input), timeout=timeout)
```

Call site in the existing batch loop (`nodes.py` ~line 88-96) becomes:
```python
try:
    batch_output = await _generate_batch(generator_chain, {
        "formatted_chunks": batch["content"],
        "previous_questions": previous_question,
        "required_quota_instructions": quota_instructions
    })
    question_list.extend(batch_output.question_list)
except Exception as e:
    print(f"  ⚠️ Batch {i+1} failed, skipping: {e}")
```

Behavior: a timeout or a bad structured-output parse gets up to 2 attempts (2s apart) since
both are typically transient (a hung call, or LLM sampling noise on schema — a re-sample often
succeeds). Any other exception (auth error, rate limit past `with_fallbacks`, real bug) still
fails immediately and skips the batch, same as today — no change to that path.

**Verified**: `generator_model.with_structured_output(schema=BatchOutput)` uses the default
`method="json_schema"`, which routes through `PydanticOutputParser`
(`langchain_core/output_parsers/pydantic.py`, langchain-core 1.4.0). Its `_parse_obj` explicitly
catches `pydantic.ValidationError` and re-raises it wrapped as
`langchain_core.exceptions.OutputParserException` — the raw `pydantic.ValidationError` never
escapes to caller code, and malformed/non-JSON output hits the same `OutputParserException` path
via the underlying `JsonOutputParser`. So `pydantic.ValidationError` doesn't belong in the retry
filter at all — confirmed by reading the installed library source, not guessed.

### Verification
- Trigger a timeout by temporarily lowering `timeout=` to something the API can't meet (e.g.
  `0.01`), confirm it retries once then skips the batch with the new log line, and the chapter
  still completes with whatever questions the other batches produced.
- Run a normal generation end-to-end, confirm no behavior change on the happy path.
- `python -m compileall src/`

---

## 2. CONC-CRIT-01 — `resume_generation` bypasses ARQ

### Problem
`PaperService.resume_generation` (`src/paper/service.py:294-319`):
```python
async def resume_generation(self, thread_id: str, selected_indices: list[int], agent: CompiledStateGraph):
    dependencies = GraphConfig(...)
    config = {"configurable": {"thread_id": thread_id, **dependencies}}
    resume_command = Command(resume={"selected_indices": selected_indices})
    asyncio.create_task(agent.ainvoke(input=resume_command, config=config))
    return {"status": "resumed", "thread_id": thread_id}
```
This runs the resume directly in the FastAPI web process via `asyncio.create_task`, not through
the ARQ worker queue.

### Root Cause
1. **Process lifecycle loss**: a web server restart/redeploy mid-resume silently kills the task
   — the paper is stuck in `awaiting_review` forever with no record anything went wrong.
2. **Wrong process for the work**: PDF/DOCX compilation (heavy, CPU-bound) runs in the API
   server instead of being distributed to ARQ workers.
3. **Silent failure**: `asyncio.create_task`'s exceptions are unobserved beyond a local
   `print()` inside the graph — nothing surfaces them.

### Files
- `src/paper/service.py`
- `src/paper/worker/tasks.py`
- `src/paper/task_manager.py`
- `src/paper/worker/settings.py`

### Proposed Change

`src/paper/worker/tasks.py` — new task, mirrors `generate_paper_task` but always resumes:
```python
async def resume_paper_task(ctx: dict, thread_id: str, selected_indices: list[int]):
    agent = ctx["agent"]
    dependencies = GraphConfig(
        chunk_repo=ctx["chunk_repo"],
        html_paper_formatter=ctx["html_paper_formatter"],
        markdown_paper_formatter=ctx["markdown_paper_formatter"],
        document_compiler=ctx["document_compiler"],
        progress_tracker=ctx["progress_tracker"]
    )
    config = {"configurable": {"thread_id": thread_id, **dependencies}}
    resume_command = Command(resume={"selected_indices": selected_indices})
    await agent.ainvoke(input=resume_command, config=config)
```
(Error handling / notification dispatch can reuse the same pattern as `generate_paper_task`'s
`except` block if desired — kept minimal here since the review step doesn't send a "ready for
review" push notification on resume.)

`src/paper/task_manager.py` — new method:
```python
async def register_resume_task(self, thread_id: str, selected_indices: list[int]) -> None:
    await self.redis_pool.enqueue_job(
        "resume_paper_task",
        thread_id,
        selected_indices,
        _job_id=f"{thread_id}-resume"
    )
    print(f"[INFO] Resume task for thread {thread_id} enqueued into ARQ Redis pool.")
```
(Distinct `_job_id` suffix so it doesn't collide with the original generation job's ID.)

`src/paper/worker/settings.py` — register the new function:
```python
functions = [generate_paper_task, resume_paper_task]
```

`src/paper/service.py` — `resume_generation` becomes:
```python
async def resume_generation(self, thread_id: str, selected_indices: list[int]):
    await self.task_manager.register_resume_task(thread_id=thread_id, selected_indices=selected_indices)
    return {"status": "resumed", "thread_id": thread_id}
```
(`agent` param can be dropped from this method's signature and its caller in `routes.py`, since
the web process no longer invokes the graph directly for resume.)

### Verification
- Resume a paper from the review step, confirm it completes via `docker compose logs -f worker`
  (should show `resume_paper_task` running in the worker, not the web process).
- Kill/restart the web container mid-resume, confirm the job still completes (proves it survived
  in ARQ, not in-process).
- `python -m compileall src/`

---

## 3. CONC-CRIT-03 — cancellation doesn't actually work

### Problem
Two gaps compound into "the Cancel button does nothing to a running generation":

1. `cancel_generation` (`src/paper/service.py:163-201`) never calls
   `progress_tracker.mark_cancelled(thread_id)` — the flag that's supposed to signal "stop" is
   never set, even though `mark_cancelled`/`is_cancelled` already exist in
   `src/paper/graph/tracker.py:102-109`.
2. The batch loop in `question_generator_node` (`src/paper/graph/nodes.py`) never calls
   `progress_tracker.is_cancelled(thread_id)` — even if the flag were set, nothing reads it.

### Root Cause
The cancellation primitives were built (tracker methods exist) but never wired into either end
of the flow — audit only calls out the missing check, not that the flag is never set either.

### Files
- `src/paper/service.py`
- `src/paper/graph/nodes.py`

### Proposed Change

`src/paper/service.py`, top of `cancel_generation` (before `self.task_manager.cancel_task(...)`):
```python
await self.progress_tracker.mark_cancelled(thread_id=thread_id)
```

`src/paper/graph/nodes.py`, top of the batch loop body (before the `rate_limiter.acquire()`
call, ~line 78):
```python
if await progress_tracker.is_cancelled(thread_id=thread_id):
    print(f"[{chapter}] Cancelled — stopping after {len(question_list)} questions")
    break
```

### Verification
- Start a generation with multiple chapters, cancel it mid-run, confirm via worker logs that the
  batch loop stops within one batch iteration instead of running to completion.
- Confirm a *non*-cancelled generation is unaffected (flag check reads `False`/absent normally).
- `python -m compileall src/`

---

## 4. CONC-HIGH-02 — serializer allowlist incomplete

### Problem
`allowed_msgpack_modules` is defined identically in two places and both are missing types that
are actually part of the checkpointed state:

`src/dependencies.py:190-194` and `src/paper/worker/settings.py:51-55`:
```python
allowed_types = [
    ("src.paper.models", "PaperRequest"),
    ("src.paper.models", "Question"),
    ("src.paper.models", "EvaluationPoint"),
]
```
But `src/paper/graph/nodes.py` imports and uses `DifficultyDistribution`, `QuestionTypes`,
`ChapterStatus`, `DocumentType`, `SubjectType` from `src.paper.models` — all of which can end up
in `PaperState`/`ChapterState` and therefore in a checkpoint.

### Root Cause
The allowlist was written for the original state shape and not updated as more typed fields were
added to `PaperState`/`ChapterState`.

### Files
- `src/dependencies.py`
- `src/paper/worker/settings.py`

### Proposed Change
In both files, extend the list:
```python
allowed_types = [
    ("src.paper.models", "PaperRequest"),
    ("src.paper.models", "Question"),
    ("src.paper.models", "EvaluationPoint"),
    ("src.paper.models", "DifficultyDistribution"),
    ("src.paper.models", "QuestionTypes"),
    ("src.paper.models", "ChapterStatus"),
    ("src.paper.models", "DocumentType"),
    ("src.paper.models", "SubjectType"),
]
```
Must be kept identical in both files — the web process and worker process read/write the same
checkpoint table and must agree on what's deserializable.

### Verification
- Run a full generation (uses all five newly-allowed types across the state), confirm
  `checkpointer.aget_state`/resume works with no deserialization error in either web or worker
  logs.
- `python -m compileall src/`

---

## 5. CONC-HIGH-03 — no backoff on ARQ retry

### Problem
`generate_paper_task`'s exception handler (`src/paper/worker/tasks.py:77-117`) ends with a bare
`raise e` on non-final tries. ARQ's default retry behavior for an unhandled exception is an
**immediate** retry (no delay) up to `max_tries=3`. A transient failure (rate limit, brief
network blip) gets hammered three times back-to-back instead of getting a chance to clear.

### Root Cause
ARQ supports delayed retries via `arq.jobs.Retry(defer=...)`, but the task doesn't use it — it
relies on the default immediate-retry behavior.

### Files
- `src/paper/worker/tasks.py`

### Proposed Change
```python
from arq.jobs import Retry
```
At the bottom of the `except Exception as e:` block, replace the final `raise e` with:
```python
if current_try >= max_tries:
    raise e
raise Retry(defer=current_try * 30)
```
(Linear backoff: 30s after try 1, 60s after try 2, then fails permanently on try 3 — matches
`max_tries=3` in `WorkerSettings`.) Everything above this in the except block (progress FAILED
update, DB status update, FCM failure notification on final try) stays exactly as-is.

### Verification
- Force an exception on try 1 (e.g. temporarily raise inside the try block), confirm via worker
  logs a ~30s delay before try 2 fires, and ~60s before try 3.
- Confirm the final-try failure path (progress/DB/notification) still fires unchanged after try 3.
- `python -m compileall src/`

---

## 6. CONC-MED-01 — ARQ pool never closed on shutdown

### Problem
`src/dependencies.py:120-127`:
```python
arq_pool_instance = None

async def get_arq_pool():
    global arq_pool_instance
    if arq_pool_instance is None:
        redis_settings = RedisSettings.from_dsn(settings.REDIS_URL) if settings.REDIS_URL else RedisSettings()
        arq_pool_instance = await create_pool(redis_settings)
    return arq_pool_instance
```
This singleton is opened lazily but never explicitly closed anywhere. Minor connection leak on
web process shutdown (not user-facing, but sloppy — `db_pool` right next to it in `lifespan()`
*is* closed properly).

### Files
- `src/dependencies.py`

### Proposed Change
In `lifespan()`'s teardown (`src/dependencies.py:205-207`), after `await pool.close()`:
```python
global arq_pool_instance
if arq_pool_instance is not None:
    await arq_pool_instance.close()
```

### Verification
- Start and stop the web app locally, confirm no unclosed-connection warnings in logs and the
  ARQ pool's close is observable (add a temporary print if needed to confirm the branch is hit).

---

## 7. CONC-MED-02 — non-transactional checkpoint deletion (+ cleanup)

### Problem
`cancel_generation` (`src/paper/service.py:169-173`):
```python
async with db_pool.connection() as conn:
    async with conn.cursor() as cur:
        await cur.execute("DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,))
        await cur.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (thread_id,))
        await cur.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (thread_id,))
```
Three separate, non-transactional statements. A crash between them leaves orphaned rows in one
table referencing a thread_id already gone from another. Also just messy — three near-identical
copy-pasted lines.

### Root Cause
No explicit transaction boundary; the connection pool uses `autocommit=True`
(`src/dependencies.py` pool kwargs), so each `execute` commits independently by default.

### Files
- `src/paper/service.py`

### Proposed Change
```python
async with db_pool.connection() as conn:
    async with conn.transaction():
        async with conn.cursor() as cur:
            for table in ("checkpoints", "checkpoint_blobs", "checkpoint_writes"):
                await cur.execute(f"DELETE FROM {table} WHERE thread_id = %s", (thread_id,))
```
`conn.transaction()` overrides `autocommit` for its scope, making all three deletes atomic.
Table names are hardcoded constants (not user input) — the f-string is safe from injection.

### Verification
- Cancel a generation with existing checkpoint rows across all three tables, confirm all three
  are cleared together.
- `python -m compileall src/`

---

## 8. CONC-LOW-02 — hardcoded `max_concurrency=3`

### Problem
`src/paper/graph/runner.py:22` hardcodes `max_concurrency=3` in the `RunnableConfig` passed to
the graph. Changing this value requires a code change + redeploy instead of an env var.

### Files
- `src/paper/graph/runner.py`
- `src/base_settings.py`

### Proposed Change
`src/base_settings.py` — add a setting:
```python
LANGGRAPH_MAX_CONCURRENCY: int = 3
```
`src/paper/graph/runner.py` — reference it instead of the literal:
```python
from src.base_settings import settings
...
max_concurrency=settings.LANGGRAPH_MAX_CONCURRENCY
```

### Verification
- Override `LANGGRAPH_MAX_CONCURRENCY` via env var, confirm the graph honors the new value
  (observe chapter fan-out concurrency in worker logs during a multi-chapter generation).
- `python -m compileall src/`

---

## Overall verification (after all items implemented)
- `python -m compileall src/`
- Full end-to-end generation run (multi-chapter, review, resume, PDF/DOCX output) via
  `docker compose logs -f worker` / `web`.
- Cancel-mid-generation scenario.
- No PR/commit until explicitly approved — implementation happens on this branch,
  `fix-concurrency-issues`, matching the Section 1 workflow.
