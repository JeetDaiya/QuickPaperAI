import os
from typing import Optional

from core.interfaces.storage import StorageService


class LocalStorageService(StorageService):
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        pass

    def put_file(self,file_data: bytes, file_path: str, content_type: Optional[str] = None):
        try:
            full_path = os.path.join(self.root_dir, file_path)

            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            with open(full_path, "wb") as f:
                f.write(file_data)
        except Exception as e:
            raise e

    def get_file(self, file_path: str, content_type: Optional[str] = None):
        try:
            full_path = os.path.join(self.root_dir, file_path)

            if not os.path.exists(full_path):
                raise FileNotFoundError(f"Local file not found")

            with open(full_path, "rb") as f:
                return f.read()

        except Exception as e:
            raise e

    def delete_file(self,  file_path : str):
        try:
            full_path = os.path.join(self.root_dir, file_path)

            if os.path.exists(full_path):
                os.remove(full_path)

        except Exception as e:
            raise e

    def exists(self, file_path : str):
        try:
            full_path = os.path.join(self.root_dir, file_path)
            if os.path.exists(full_path):
                return True
            else:
                return False
        except Exception as e:
            raise e

