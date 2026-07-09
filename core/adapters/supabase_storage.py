import os
from typing import Optional

from supabase import Client

from core.interfaces.storage import StorageService


class SupabaseStorageService(StorageService):
    def __init__(self, supabase_client : Client, bucket_name : str):
        self.db = supabase_client
        self.bucket_name = bucket_name
        return

    def _get_bucket(self, bucket_name : str):
        try:
            self.db.storage.get_bucket(bucket_name)
        except Exception as e:
            raise  e


    def put_file(self, file_data: bytes, path: str, content_type: Optional[str] = None):
        try:
            self.db.storage.from_(self.bucket_name).upload(
                path=path,
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

    def delete_file(self,  path : str):
        try:
            self.db.storage.from_(self.bucket_name).remove([path])
        except Exception as e:
            raise e

    def exists(self, path: str) -> bool:
        try:
            folder = os.path.dirname(path)
            filename = os.path.basename(path)

            # List files in the folder and see if filename matches
            files = self.db.storage.from_(self.bucket_name).list(folder)
            return any(f.get('name') == filename for f in files)
        except Exception as e:
            raise e


