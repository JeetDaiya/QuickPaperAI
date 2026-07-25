from typing import Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from functools import lru_cache

from core.adapters.custom_auth_service import CustomAuthService
from core.adapters.document_compiler import CustomDocumentCompiler
from core.adapters.fastmail_mailer import FastMailService
from core.adapters.html_paper_formatter import HTMLPaperFormatter
from core.adapters.local_storage import LocalStorageService
from core.adapters.markdown_paper_formatter import MarkdownPaperFormatter
from core.adapters.supabase_db import SupabaseChunkRepository, SupabaseUserRepository, SupabasePaperRepository
from core.adapters.supabase_storage import SupabaseStorageService
from core.graph.builder import graph

from core.graph.tracker import ProgressTracker
from core.interfaces.auth import AuthService
from core.interfaces.db import ChunkRepository, UserRepository, PaperRepository
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, status

from core.config.settings import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL
from supabase import create_client, Client

from core.interfaces.document_compiler import DocumentCompiler
from core.interfaces.mail import EmailService
from core.interfaces.paper_formatter import PaperFormatter
from core.interfaces.storage import StorageService
from server.config import settings

from fastapi import Request

from core.interfaces.otp_store import OTPStore
from core.adapters.redis_otp_store import RedisOTPStore
from upstash_redis.asyncio import Redis

from server.services.db_service import DBService
from server.services.paper_service import PaperService
from server.services.task_manager import TaskManager

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login', auto_error=False)

supabase_client : Client = create_client(supabase_key=SUPABASE_SERVICE_ROLE_KEY, supabase_url=SUPABASE_URL)
otp_store : Optional[OTPStore] = None

@lru_cache
def get_chunk_repository()-> ChunkRepository:
    return SupabaseChunkRepository(client=supabase_client)

@lru_cache
def get_user_repository()-> UserRepository:
    return SupabaseUserRepository(client=supabase_client)

@lru_cache
def get_paper_repository() -> PaperRepository:
    return SupabasePaperRepository(client=supabase_client)

@lru_cache()
def get_cloud_storage() -> StorageService:
    return SupabaseStorageService(supabase_client=supabase_client, bucket_name="question-papers")

@lru_cache
def get_local_storage() -> StorageService:
    return LocalStorageService(root_dir="outputs")

@lru_cache
def get_email_service() -> EmailService:
    return FastMailService()

@lru_cache
def get_otp_store() -> OTPStore:
    global otp_store
    if otp_store is None:
        redis_client = Redis(url=settings.UPSTASH_REDIS_REST_URL, token=settings.UPSTASH_REDIS_REST_TOKEN)
        otp_store = RedisOTPStore(redis_client=redis_client)
        return  otp_store
    else:
        return otp_store

@lru_cache
def get_authentication_service(user_repo : UserRepository = Depends(get_user_repository)) -> AuthService:
    return CustomAuthService(algorithm=settings.ALGORITHM, secret_key=settings.SECRET_KEY, user_repo=user_repo, token_expire_minutes=10080)

@lru_cache
def get_html_formatter() -> PaperFormatter:
    return HTMLPaperFormatter()

@lru_cache
def get_markdown_formatter() -> PaperFormatter:
    return MarkdownPaperFormatter()

@lru_cache
def get_document_compiler() -> DocumentCompiler:
    return CustomDocumentCompiler()

@lru_cache
def get_progress_tracker() -> ProgressTracker:
    redis_client = Redis(url=settings.UPSTASH_REDIS_REST_URL, token=settings.UPSTASH_REDIS_REST_TOKEN)
    return ProgressTracker(redis_client=redis_client, ttl_seconds=86400)

@lru_cache
def get_task_manager() -> TaskManager:
    return TaskManager()

@lru_cache
def get_paper_service(paper_repo: PaperRepository = Depends(get_paper_repository), cloud_storage : StorageService = Depends(get_cloud_storage), local_storage : StorageService = Depends(get_local_storage), task_manager : TaskManager = Depends(get_task_manager), progress_tracker : ProgressTracker = Depends(get_progress_tracker), html_paper_formatter : PaperFormatter = Depends(get_html_formatter), markdown_paper_formatter = Depends(get_markdown_formatter), chunk_repo : ChunkRepository = Depends(get_chunk_repository), document_compiler : DocumentCompiler = Depends(get_document_compiler)) -> PaperService:
    return PaperService(
        progress_tracker=progress_tracker,
        local_storage=local_storage,
        cloud_storage=cloud_storage,
        task_manager=task_manager,
        paper_repo=paper_repo,
        html_paper_formatter=html_paper_formatter,
        markdown_paper_formatter=markdown_paper_formatter,
        chunk_repo=chunk_repo,
        document_compiler=document_compiler
    )

@lru_cache
def get_db_service(paper_repo : PaperRepository = Depends(get_paper_repository)) -> DBService:
    return DBService(
        paper_repo=paper_repo
    )

compiled_agent = None
@asynccontextmanager
async def lifespan(app : FastAPI):
    global compiled_agent
    pool = AsyncConnectionPool(
        conninfo=settings.DB_URI,
        max_size=20,
        open=False,
        kwargs={
            "autocommit" : True,
            "row_factory" : dict_row,
            "prepare_threshold": None
        }
    )

    await pool.open()
    
    allowed_types = [
        ("core.models.schemas", "PaperRequest"),
        ("core.models.schemas", "Question"),
        ("core.models.schemas", "EvaluationPoint"),
    ]
    serde = JsonPlusSerializer(allowed_msgpack_modules=allowed_types)
    checkpointer = AsyncPostgresSaver(pool, serde=serde)
    
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



