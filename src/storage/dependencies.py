from functools import lru_cache

from src.db.dependencies import supabase_client
from src.storage.interfaces.interface import StorageService
from src.storage.adapters.local_storage import LocalStorageService
from src.storage.adapters.supabase_storage import SupabaseStorageService


@lru_cache
def get_cloud_storage() -> StorageService:
    return SupabaseStorageService(supabase_client=supabase_client, bucket_name="question-papers")


@lru_cache
def get_local_storage() -> StorageService:
    return LocalStorageService(root_dir="outputs")
