from abc import ABC, abstractmethod
from pydantic import EmailStr

class ChunkRepository(ABC):
    @abstractmethod
    def get_chapter_chunks(self, subject: str, chapter: str) -> list[dict]:
        pass


class UserRepository(ABC):
    @abstractmethod
    def get_user(self, email: EmailStr):
        pass

    @abstractmethod
    def create_user(self, email: EmailStr, hashed_password: str, name: str):
        pass

    @abstractmethod
    def update_user_password(self, email: EmailStr, new_hashed_password: str):
        pass

class PaperRepository(ABC):
    @abstractmethod
    def get_user_paper_history(self, user_id: str):
        pass

    @abstractmethod
    def delete_paper_metadata(self, thread_id: str):
        pass

    @abstractmethod
    def upload_paper_metadata(self, metadata: dict):
        pass

    @abstractmethod
    def get_paper_metadata(self, thread_id: str, paper_name: str):


    @abstractmethod
    def get_chapters(self):
        pass





