from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from arq.connections import RedisSettings

from src.base_settings import settings
from src.dependencies import (
    get_paper_service,
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
from src.paper.worker.tasks import generate_paper_task


def get_redis_settings() -> RedisSettings:
    if settings.REDIS_URL:
        return RedisSettings.from_dsn(settings.REDIS_URL)
    return RedisSettings()


class WorkerSettings:
    functions = [generate_paper_task]
    max_tries = 3
    job_timeout = 3600
    redis_settings = get_redis_settings()

    @staticmethod
    async def on_startup(ctx: dict) -> None:
        print("[INFO] Starting ARQ Worker & initializing services...")
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
        await pool.open()

        allowed_types = [
            ("src.paper.models", "PaperRequest"),
            ("src.paper.models", "Question"),
            ("src.paper.models", "EvaluationPoint"),
        ]

        serde = JsonPlusSerializer(allowed_msgpack_modules=allowed_types)
        checkpointer = AsyncPostgresSaver(pool, serde=serde)
        await checkpointer.setup()

        compiled_agent = graph.compile(checkpointer=checkpointer)

        # Inject into ctx for worker tasks
        ctx["db_pool"] = pool
        ctx["checkpointer"] = checkpointer
        ctx["agent"] = compiled_agent
        ctx["paper_service"] = get_paper_service()
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

















