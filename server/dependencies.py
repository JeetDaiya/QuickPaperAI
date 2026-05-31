from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.graph.builder import graph
import os


compiled_agent = None
@asynccontextmanager
async def lifespan(app : FastAPI):
    global compiled_agent
    pool = AsyncConnectionPool(
        conninfo=os.getenv("DB_URI"),
        max_size=20,
        kwargs={
            "autocommit" : True,
            "row_factory" : dict_row,
            "prepare_threshold": None
        }
    )
    
    checkpointer = AsyncPostgresSaver(pool)
    
    await checkpointer.setup()
    
    compiled_agent = graph.compile(checkpointer=checkpointer)
    
    app.state.agent = compiled_agent
    app.state.db_pool = pool
    
    yield
    
    await pool.close()
    