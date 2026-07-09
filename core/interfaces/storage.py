from abc import ABC, abstractmethod
from typing import Optional


class StorageService(ABC):

    @abstractmethod
    def put_file(self, file_data: bytes, path: str, content_type: Optional[str] = None):
        pass

    @abstractmethod
    def get_file(self, file_path : str):
        pass

    @abstractmethod
    def delete_file(self,  file_path : str):
        pass

    @abstractmethod
    def exists(self, file_path : str):
        pass

