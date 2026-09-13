from functools import lru_cache

from fastapi import Depends
from supabase import create_client, Client

from src.base_settings import settings
from src.db.interfaces.interface import ChunkRepository, UserRepository, PaperRepository
from src.db.adapters.supabase_db import SupabaseChunkRepository, SupabaseUserRepository, SupabasePaperRepository
from src.db.services.service import DBService

supabase_client: Client = create_client(supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY, supabase_url=settings.SUPABASE_URL)


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
def get_db_service(paper_repo: PaperRepository = Depends(get_paper_repository)) -> DBService:
    return DBService(paper_repo=paper_repo)
