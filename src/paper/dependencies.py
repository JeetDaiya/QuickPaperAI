from typing import Optional
from functools import lru_cache

from fastapi import Depends
from upstash_redis.asyncio import Redis
import redis.asyncio as redis_asyncio

from src.base_settings import settings
from src.db.interfaces.interface import ChunkRepository, UserRepository, PaperRepository
from src.db.dependencies import get_chunk_repository, get_paper_repository, get_user_repository
from src.storage.interfaces.interface import StorageService
from src.storage.dependencies import get_cloud_storage, get_local_storage
from src.notifications.adapters.firebase_notification_service import FirebaseNotificationService
from src.notifications.dependencies import get_notification_service
from src.paper.compilers.interfaces.interface import DocumentCompiler
from src.paper.compilers.adapters.document_compiler import CustomDocumentCompiler
from src.paper.formatters.interfaces.interface import PaperFormatter
from src.paper.formatters.adapters.html_paper_formatter import HTMLPaperFormatter
from src.paper.formatters.adapters.markdown_paper_formatter import MarkdownPaperFormatter
from src.paper.graph.tracker import ProgressTracker
from src.paper.service import PaperService
from src.paper.task_manager import TaskManager
from arq import create_pool
from arq.connections import RedisSettings


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


pubsub_redis_instance: Optional[redis_asyncio.Redis] = None


def get_pubsub_redis() -> redis_asyncio.Redis:
    """Raw TCP Redis connection (as opposed to the REST-based `upstash_redis` client used
    elsewhere) — needed because REST clients can't hold a blocking pub/sub SUBSCRIBE."""
    global pubsub_redis_instance
    if pubsub_redis_instance is None:
        pubsub_redis_instance = redis_asyncio.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return pubsub_redis_instance


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
