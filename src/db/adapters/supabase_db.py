from typing import Any, Optional
from pydantic import EmailStr
from typing_extensions import override

from src.exception.exceptions import RepositoryError
from src.db.records.paper_record import PaperRecord, Status
from src.db.schemas import PaperHistory
from src.db.tables import Chunks, User, GeneratedPapers
from src.db.interfaces.interface import UserRepository, ChunkRepository, PaperRepository
from supabase import Client


class SupabaseChunkRepository(ChunkRepository):
    def __init__(self, client: Client) -> None:
        self.db = client

    @override
    def get_chapter_chunks(self, subject: str, chapter: str) -> list[dict]:
        try:
            response = (
                self.db.table(Chunks.TABLE)
                .select("*")
                .eq(Chunks.CHAPTER_NAME, chapter)
                .eq(Chunks.SUBJECT, subject)
                .order(Chunks.CHUNK_INDEX)
                .execute()
            )
            return response.data
        except Exception as e:
            raise RepositoryError(subject=subject, chapter=chapter) from e


class SupabaseUserRepository(UserRepository):
    def __init__(self, client: Client) -> None:
        self.db = client

    def get_user(self, email: EmailStr):
        try:
            data = self.db.table(User.TABLE).select("*").eq(User.EMAIL, email).execute()
            return data.data[0] if data.data else None
        except Exception as e:
            raise RepositoryError(email=email) from e

    def create_user(self, email: EmailStr, hashed_password: str, name: str):
        try:
            user_data = {
                User.EMAIL: email,
                User.HASHED_PASSWORD: hashed_password,
                User.NAME: name,
                User.IS_ACTIVE: False
            }
            response = self.db.table(User.TABLE).insert(user_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            raise RepositoryError(email=email, name=name) from e

    def update_user_password(self, email: EmailStr, new_hashed_password: str):
        try:
            response = self.db.table(User.TABLE).update({User.HASHED_PASSWORD: new_hashed_password}).eq(User.EMAIL, email).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            raise RepositoryError(email=email) from e

    def activate_user(self, email: EmailStr):
        try:
            response = self.db.table(User.TABLE).update({User.IS_ACTIVE: True}).eq(User.EMAIL, email).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            raise RepositoryError(email=email) from e

    def save_fcm_token(self, user_id: str, token: str):
        try:
            self.db.table(User.TABLE).update({User.FCM_TOKEN: token}).eq(User.USER_ID, user_id.strip()).execute()
            print(f"[INFO] FCM Token successfully saved to database for user {user_id}")
            return True
        except Exception as e:
            raise RepositoryError(user_id=user_id) from e

    def update_notification_perms(self, user_id: str, notifications_enabled: bool):
        try:
            self.db.table(User.TABLE).update({User.NOTIFICATIONS_ENABLED: notifications_enabled}).eq(User.USER_ID,
                                                                                                     user_id.strip()).execute()
            return True
        except Exception as e:
            raise RepositoryError(user_id=user_id) from e

    def get_notification_perms(self, user_id: str):
        try:
            response = self.db.table(User.TABLE).select(User.NOTIFICATIONS_ENABLED).eq(User.USER_ID, user_id.strip()).execute()
            return response.data
        except Exception as e:
            raise RepositoryError(user_id=user_id) from e

    def get_fcm_token(self, user_id: str):
        try:
            response = self.db.table(User.TABLE).select(User.FCM_TOKEN).eq(User.USER_ID, user_id.strip()).execute()
            return response.data  # empty list is a legitimate, distinguishable result
        except Exception as e:
            raise RepositoryError(user_id=user_id) from e


class SupabasePaperRepository(PaperRepository):
    def __init__(self, client: Client) -> None:
        self.db = client

    def get_user_paper_history(self, user_id: str) -> list[PaperHistory]:
        try:
            response = (
                self.db.table(GeneratedPapers.TABLE)
                .select("*")
                .eq(GeneratedPapers.USER_ID, user_id)
                .eq(GeneratedPapers.STATUS, Status.SAVED)
                .order(GeneratedPapers.CREATED_AT, desc=True)
                .execute()
            )

            history_list: list[PaperHistory] = [PaperHistory(**row) for row in response.data]

            return history_list

        except Exception as e:
            raise RepositoryError(user_id=user_id) from e

    def get_chapters(self) -> list[Any]:
        try:
            data = (
                self.db.table(Chunks.TABLE)
                .select(Chunks.CHAPTER_NAME, Chunks.SUBJECT, Chunks.STANDARD)
                .execute()
            )
            return data.data
        except Exception as e:
            raise RepositoryError() from e

    def upload_paper_metadata(self, metadata: dict):
        try:
            self.db.table(GeneratedPapers.TABLE).insert(metadata).execute()
        except Exception as e:
            raise RepositoryError(metadata=metadata) from e

    def get_paper_metadata(self, thread_id: str, paper_name: str):
        try:
            response = self.db.table(GeneratedPapers.TABLE).select(paper_name).eq(GeneratedPapers.THREAD_ID, thread_id).execute()
            return response
        except Exception as e:
            raise RepositoryError(thread_id=thread_id, paper_name=paper_name) from e

    def delete_paper_metadata(self, thread_id: str):
        try:
            self.db.table(GeneratedPapers.TABLE).delete().eq(GeneratedPapers.THREAD_ID, thread_id).execute()
        except Exception as e:
            raise RepositoryError(thread_id=thread_id) from e
    def create_paper_session(self, paper_record : PaperRecord):
        try:
            self.db.table(GeneratedPapers.TABLE).insert(paper_record.to_insert()).execute()
        except Exception as e:
            raise RepositoryError(paper_record=paper_record) from e

    def update_paper_session(self, thread_id: str, paper_record : PaperRecord):
        try:
            self.db.table(GeneratedPapers.TABLE).update(paper_record.to_update()).eq(GeneratedPapers.THREAD_ID, thread_id).execute()
        except Exception as e:
            raise RepositoryError(thread_id=thread_id, paper_record=paper_record) from e

    def get_paper_session(self, thread_id: str) -> Optional[PaperRecord]:
        try:
            response = self.db.table(GeneratedPapers.TABLE).select("*").eq(GeneratedPapers.THREAD_ID, thread_id).execute()
            return PaperRecord(**response.data[0]) if response.data else None
        except Exception as e:
            raise RepositoryError(thread_id=thread_id) from e

    def delete_paper_session(self, thread_id: str):
        try:
            self.db.table(GeneratedPapers.TABLE).delete().eq(GeneratedPapers.THREAD_ID, thread_id).execute()
        except Exception as e:
            raise RepositoryError(thread_id=thread_id) from e

