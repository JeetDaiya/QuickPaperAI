from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from arq.connections import RedisSettings
from tenacity import retry, stop_after_attempt, wait_exponential

from src.base_settings import settings
from src.dependencies import (
    get_notification_service,
    get_progress_tracker,
    get_chunk_repository,
    get_html_formatter,
    get_markdown_formatter,
    get_document_compiler,
    get_paper_repository,
    get_user_repository,
)
from src.paper.graph.builder import graph
from src.paper.worker.tasks import generate_paper_task, resume_paper_task, MAX_TRIES


def get_redis_settings() -> RedisSettings:
    if settings.REDIS_URL:
        return RedisSettings.from_dsn(settings.REDIS_URL)
    return RedisSettings()


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
async def _open_pool_with_retry() -> AsyncConnectionPool:
    # Postgres (Supabase) may still be coming up when the worker container starts (e.g. in
    # docker-compose) — retry a few times before giving up, instead of crashing the whole
    # worker process on the first transient connection failure.
    #
    # A pool that fails to open (wait=True raises PoolTimeout on failure) closes itself and
    # cannot be reopened, so each retry attempt builds a fresh pool rather than reusing one.
    pool = AsyncConnectionPool(
        conninfo=settings.DB_URI,
        max_size=10,
        open=False,
        check=AsyncConnectionPool.check_connection,
        kwargs={
            "autocommit": True,
            "row_factory": dict_row,
            "prepare_threshold": None
        }
    )
    try:
        await pool.open(wait=True, timeout=10)
        return pool
    except Exception as e:
        print(f"[WARN] DB pool connection attempt failed: {e} — retrying...")
        raise


class WorkerSettings:
    functions = [generate_paper_task, resume_paper_task]
    max_tries = MAX_TRIES
    job_timeout = 3600
    allow_abort_jobs = True
    redis_settings = get_redis_settings()
    poll_delay = 5.0

    @staticmethod
    async def on_startup(ctx: dict) -> None:
        print("[INFO] Starting ARQ Worker & initializing services...")
        pool = await _open_pool_with_retry()

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

        serde = JsonPlusSerializer(allowed_msgpack_modules=allowed_types)
        checkpointer = AsyncPostgresSaver(pool, serde=serde)
        await checkpointer.setup()

        compiled_agent = graph.compile(checkpointer=checkpointer)

        # Inject into ctx for worker tasks
        ctx["db_pool"] = pool
        ctx["checkpointer"] = checkpointer
        ctx["agent"] = compiled_agent
        ctx["notification_service"] = get_notification_service()
        ctx["progress_tracker"] = get_progress_tracker()
        ctx["chunk_repo"] = get_chunk_repository()
        ctx["html_paper_formatter"] = get_html_formatter()
        ctx["markdown_paper_formatter"] = get_markdown_formatter()
        ctx["document_compiler"] = get_document_compiler()
        ctx["paper_repo"] = get_paper_repository()
        ctx["user_repo"] = get_user_repository()
        print("[INFO] ARQ Worker services successfully initialized!")

    @staticmethod
    async def on_shutdown(ctx: dict) -> None:
        print("[INFO] Shutting down ARQ Worker...")
        pool = ctx.get("db_pool")
        if pool:
            await pool.close()
        print("[INFO] Database pool closed successfully.")

















