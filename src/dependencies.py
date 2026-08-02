from typing import Optional
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from supabase import create_client, Client
from upstash_redis.asyncio import Redis

from src.base_settings import settings
from src.auth.interface.interface import AuthService
from src.auth.interface.otp_store import OTPStore
from src.auth.adapters.custom_auth_service import CustomAuthService
from src.auth.adapters.redis_otp_store import RedisOTPStore
from src.db.interfaces.interface import ChunkRepository, UserRepository, PaperRepository
from src.db.adapters.supabase_db import SupabaseChunkRepository, SupabaseUserRepository, SupabasePaperRepository
from src.db.services.service import DBService
from src.notifications.adapters.firebase_notification_service import FirebaseNotificationService
from src.paper.compilers.interfaces.interface import DocumentCompiler
from src.paper.compilers.adapters.document_compiler import CustomDocumentCompiler
from src.paper.formatters.interfaces.interface import PaperFormatter
from src.paper.formatters.adapters.html_paper_formatter import HTMLPaperFormatter
from src.paper.formatters.adapters.markdown_paper_formatter import MarkdownPaperFormatter
from src.paper.graph.builder import graph
from src.paper.graph.tracker import ProgressTracker
from src.paper.service import PaperService
from src.paper.task_manager import TaskManager
from src.storage.interfaces.interface import StorageService
from src.storage.adapters.local_storage import LocalStorageService
from src.storage.adapters.supabase_storage import SupabaseStorageService
from arq import create_pool
from arq.connections import RedisSettings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login', auto_error=False)
supabase_client: Client = create_client(supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY, supabase_url=settings.SUPABASE_URL)
otp_store: Optional[OTPStore] = None


@lru_cache
def get_chunk_repository() -> ChunkRepository:
    return SupabaseChunkRepository(client=supabase_client)


@lru_cache
def get_user_repository() -> UserRepository:
    return SupabaseUserRepository(client=supabase_client)


@lru_cache
def get_paper_repository() -> PaperRepository:
    return SupabasePaperRepository(client=supabase_client)


@lru_cache
def get_cloud_storage() -> StorageService:
    return SupabaseStorageService(supabase_client=supabase_client, bucket_name="question-papers")


@lru_cache
def get_local_storage() -> StorageService:
    return LocalStorageService(root_dir="outputs")


@lru_cache
def get_email_service():
    from src.mail.adapters.fastmail_mailer import FastMailService
    return FastMailService()

@lru_cache
def get_notification_service()-> FirebaseNotificationService:
    return FirebaseNotificationService()


@lru_cache
def get_otp_store() -> OTPStore:
    global otp_store
    if otp_store is None:
        redis_client = Redis(url=settings.UPSTASH_REDIS_REST_URL, token=settings.UPSTASH_REDIS_REST_TOKEN)
        otp_store = RedisOTPStore(redis_client=redis_client)
        return otp_store
    else:
        return otp_store


@lru_cache
def get_authentication_service(user_repo: UserRepository = Depends(get_user_repository)) -> AuthService:
    return CustomAuthService(
        algorithm=settings.ALGORITHM,
        secret_key=settings.SECRET_KEY,
        user_repo=user_repo,
        token_expire_minutes=10080
    )


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


arq_pool_instance = None

async def get_arq_pool():
    global arq_pool_instance
    if arq_pool_instance is None:
        redis_settings = RedisSettings.from_dsn(settings.REDIS_URL) if settings.REDIS_URL else RedisSettings()
        arq_pool_instance = await create_pool(redis_settings)
    return arq_pool_instance


async def get_task_manager() -> TaskManager:
    pool = await get_arq_pool()
    return TaskManager(redis_pool=pool)


@lru_cache
def get_paper_service(
    paper_repo: PaperRepository = Depends(get_paper_repository),
    cloud_storage: StorageService = Depends(get_cloud_storage),
    local_storage: StorageService = Depends(get_local_storage),
    task_manager: TaskManager = Depends(get_task_manager),
    progress_tracker: ProgressTracker = Depends(get_progress_tracker),
    html_paper_formatter: PaperFormatter = Depends(get_html_formatter),
    markdown_paper_formatter: PaperFormatter = Depends(get_markdown_formatter),
    chunk_repo: ChunkRepository = Depends(get_chunk_repository),
    document_compiler: DocumentCompiler = Depends(get_document_compiler),
    user_repo: UserRepository = Depends(get_user_repository),
    notification_service : FirebaseNotificationService = Depends(get_notification_service)

) -> PaperService:
    return PaperService(
        progress_tracker=progress_tracker,
        local_storage=local_storage,
        cloud_storage=cloud_storage,
        task_manager=task_manager,
        paper_repo=paper_repo,
        html_paper_formatter=html_paper_formatter,
        markdown_paper_formatter=markdown_paper_formatter,
        chunk_repo=chunk_repo,
        document_compiler=document_compiler,
        user_repo=user_repo,
        notification_service=notification_service
    )


@lru_cache
def get_db_service(paper_repo: PaperRepository = Depends(get_paper_repository)) -> DBService:
    return DBService(paper_repo=paper_repo)


compiled_agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global compiled_agent
    pool = AsyncConnectionPool(
        conninfo=settings.DB_URI,
        max_size=20,
        open=False,
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
