from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI

from core.adapters.fastmail_mailer import FastMailService
from core.adapters.local_storage import LocalStorageService
from core.adapters.supabase_db import SupabaseChunkRepository, SupabaseUserRepository, SupabasePaperRepository
from core.adapters.supabase_storage import SupabaseStorageService
from core.graph.builder import graph
import os

from core.interfaces.db import ChunkRepository, UserRepository, PaperRepository
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, status
from jose import JWTError, jwt

from core.config.settings import SUPABASE_KEY, SUPABASE_URL
from supabase import create_client, Client

from core.interfaces.mail import EmailService
from core.interfaces.storage import StorageService
from server.core.config import SECRET_KEY, ALGORITHM

from fastapi import Request

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login', auto_error=False)



supabase_client : Client = create_client(supabase_key=SUPABASE_KEY, supabase_url=SUPABASE_URL)

def get_chunk_repository()-> ChunkRepository:
    return SupabaseChunkRepository(client=supabase_client)

def get_user_repository()-> UserRepository:
    return SupabaseUserRepository(client=supabase_client)
def get_paper_repository() -> PaperRepository:
    return SupabasePaperRepository(client=supabase_client)
def get_cloud_storage() -> StorageService:
    return SupabaseStorageService(supabase_client=supabase_client, bucket_name="question-papers")
def get_local_storage() -> StorageService:
    return LocalStorageService(root_dir="outputs")
def get_email_service() -> EmailService:
    return FastMailService()


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
    
def get_current_user(request: Request, token: str = Depends(oauth2_scheme), user_repo : UserRepository = Depends(get_user_repository)):
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
        email = str(payload.get("sub"))
        
        if email is None:
            raise credentials_exception
        
    except JWTError:
        raise credentials_exception
    
    user = user_repo.get_user(email=email)
    if user is None:
        raise credentials_exception
    else:
        return user


