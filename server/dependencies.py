from typing import Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI

from core.adapters.custom_auth_service import CustomAuthService
from core.adapters.fastmail_mailer import FastMailService
from core.adapters.local_storage import LocalStorageService
from core.adapters.supabase_db import SupabaseChunkRepository, SupabaseUserRepository, SupabasePaperRepository
from core.adapters.supabase_storage import SupabaseStorageService
from core.graph.builder import graph
import os

from core.interfaces.auth import AuthService
from core.interfaces.db import ChunkRepository, UserRepository, PaperRepository
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, status
from jose import JWTError, jwt

from core.config.settings import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL
from supabase import create_client, Client

from core.interfaces.mail import EmailService
from core.interfaces.otp_store import OTPStore
from core.interfaces.storage import StorageService
from server.core.config import SECRET_KEY, ALGORITHM

from fastapi import Request

from core.interfaces.otp_store import OTPStore
from core.adapters.redis_otp_store import RedisOTPStore
from upstash_redis.asyncio import Redis


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login', auto_error=False)



supabase_client : Client = create_client(supabase_key=SUPABASE_SERVICE_ROLE_KEY, supabase_url=SUPABASE_URL)
otp_store : Optional[OTPStore] = None

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
def get_otp_store() -> OTPStore:
    global otp_store
    if otp_store is None:
        redis_client = Redis(url=os.getenv("UPSTASH_REDIS_REST_URL"), token=os.getenv("UPSTASH_REDIS_REST_TOKEN"))
        otp_store = RedisOTPStore(redis_client=redis_client)
        return  otp_store
    else:
        return otp_store
def get_authentication_service(user_repo : UserRepository = Depends(get_user_repository)) -> AuthService:
    return CustomAuthService(algorithm=ALGORITHM, secret_key=SECRET_KEY, user_repo=user_repo, token_expire_minutes=10080)


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
    
async def get_current_user(
    request: Request, 
    token: str = Depends(oauth2_scheme), 
    auth_service: AuthService = Depends(get_authentication_service)
):
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
        user = await auth_service.verify_session(token=token)
        return user
    except HTTPException as e:
        raise e
    except Exception:
        raise credentials_exception



