from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

from src.base_settings import settings
from src.paper.graph.builder import graph
import src.paper.dependencies as paper_dependencies

compiled_agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global compiled_agent
    pool = AsyncConnectionPool(
        conninfo=settings.DB_URI,
        max_size=5,
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
        ("src.paper.models", "DifficultyDistribution"),
        ("src.paper.models", "QuestionTypes"),
        ("src.paper.models", "ChapterStatus"),
        ("src.paper.models", "DocumentType"),
        ("src.paper.models", "SubjectType"),
        ("src.paper.models", "PaperDifficulty"),
    ]
    serde = JsonPlusSerializer(allowed_msgpack_modules=allowed_types)
    checkpointer = AsyncPostgresSaver(pool, serde=serde)

    await checkpointer.setup()

    compiled_agent = graph.compile(checkpointer=checkpointer)

    app.state.agent = compiled_agent
    app.state.db_pool = pool

    yield

    await pool.close()
    if paper_dependencies.arq_pool_instance is not None:
        await paper_dependencies.arq_pool_instance.close()
    if paper_dependencies.pubsub_redis_instance is not None:
        await paper_dependencies.pubsub_redis_instance.aclose()
