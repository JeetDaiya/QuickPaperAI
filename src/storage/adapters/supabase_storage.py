import os
from typing import Optional

from supabase import Client

from src.storage.interfaces.interface import StorageService


class SupabaseStorageService(StorageService):
    def __init__(self, supabase_client : Client, bucket_name : str):
        self.db = supabase_client
        self.bucket_name = bucket_name

    def _get_bucket(self, bucket_name : str):
        try:
            self.db.storage.get_bucket(bucket_name)
        except Exception as e:
            raise e


    def put_file(self, file_data: bytes, file_path: str, content_type: Optional[str] = None):
        try:
            self.db.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file_data,
                file_options={"content-type" : content_type, "x-upsert" : "true"},
            )
        except Exception as e:
            raise e

    def get_file(self, file_path : str):
        try:
            file_bytes = self.db.storage.from_(self.bucket_name).download(file_path)
            return file_bytes
        except Exception as e:
            raise e

    def delete_file(self, file_path : str):
        try:
            self.db.storage.from_(self.bucket_name).remove([file_path])
        except Exception as e:
            raise e

    def exists(self, file_path: str) -> bool:
        try:
            folder = os.path.dirname(file_path)
            filename = os.path.basename(file_path)

            # List files in the folder and see if filename matches
            files = self.db.storage.from_(self.bucket_name).list(folder)
            return any(f.get('name') == filename for f in files)
        except Exception as e:
            raise e


