from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from core.graph.builder import graph
import os
from server.db import get_user
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, status
from jose import JWTError, jwt


from server.core.config import SECRET_KEY, ALGORITHM

from fastapi import Request

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login', auto_error=False)

compiled_agent = None
@asynccontextmanager
async def lifespan(app : FastAPI):
    global compiled_agent
    pool = AsyncConnectionPool(
        conninfo=os.getenv("DB_URI"),
        max_size=20,
        open=False,
        kwargs={
            "autocommit" : True,
            "row_factory" : dict_row,
            "prepare_threshold": None
        }
    )

    await pool.open()
    
    checkpointer = AsyncPostgresSaver(pool)
    
    await checkpointer.setup()
    
    compiled_agent = graph.compile(checkpointer=checkpointer)
    
    app.state.agent = compiled_agent
    app.state.db_pool = pool
    
    yield
    
    await pool.close()
    
def get_current_user(request: Request, token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Fallback to query parameter if header token is missing
    if not token:
        token = request.query_params.get("token")
        
    if not token:
        raise credentials_exception
    
    try:
        payload = jwt.decode(token, key=SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        
        if email is None:
            raise credentials_exception
        
    except JWTError:
        raise credentials_exception
    
    user = get_user(email=email)
    if user is None:
        raise credentials_exception
    else:
        return user