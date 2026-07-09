from typing import Any

from pydantic import EmailStr
from typing_extensions import override
from core.interfaces.db import  UserRepository, ChunkRepository, PaperRepository
from supabase import Client, SupabaseException


class SupabaseChunkRepository(ChunkRepository):
    def __init__(self, client: Client) -> None:
        self.db = client
    @override
    def get_chapter_chunks(self, subject: str, chapter: str) -> list[dict]:
        try:
            response = (
                self.db.table("chunks")
                .select("*")
                .eq("chapter_name", chapter)
                .eq("subject", subject)
                .order("chunk_index")
                .execute()
            )

            paper_chunks = response.data

            return paper_chunks
        except SupabaseException as e:
            raise e
class SupabaseUserRepository(UserRepository):
    def __init__(self, client: Client) -> None:
        self.db = client

    def get_user(self, email: EmailStr):
        try:
            data = self.db.table("users").select("*").eq("email", email).execute()
            return data.data[0] if data.data else None
        except Exception as e:
            raise e

    def create_user(self, email: EmailStr, hashed_password: str, name: str):
        try:
            user_data = {
                "email": email,
                "hashed_password": hashed_password,
                "name": name,
                "is_active": False
            }
            response = self.db.table("users").insert(user_data).execute()
            return response.data[0] if response.data else None
        except SupabaseException as e:
            raise e

    def update_user_password(self, email: EmailStr, new_hashed_password: str):
        try:
            response = self.db.table("users").update({"hashed_password": new_hashed_password}).eq("email", email).execute()
            return response.data[0] if response.data else None
        except SupabaseException as e:
            raise e

class SupabasePaperRepository(PaperRepository):
    def __init__(self, client: Client) -> None:
        self.db = client

    def get_user_paper_history(self, user_id: str):
        try:
            response = (
                self.db.table("generated_papers")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )

            history_list = []
            for row in response.data:
                thread_id = row.get("thread_id")
                history_list.append({
                    "id": row.get("id"),
                    "thread_id": thread_id,
                    "created_at": row.get("created_at"),
                    "institution_name": row.get("institution_name"),
                    "subject": row.get("subject"),
                    "standard": row.get("standard"),
                    "difficulty": row.get("difficulty"),
                    "chapters": row.get("chapters"),
                    "objective_count": row.get("objective_count", 0),
                    "subjective_count": row.get("subjective_count", 0),
                    "allowed_types": row.get("allowed_types", []),
                    # Map raw Supabase paths to server-proxied download routes
                    "paper_pdf": f"/api/download/{thread_id}/paper.pdf",
                    "paper_docx": f"/api/download/{thread_id}/paper.docx",
                    "answer_pdf": f"/api/download/{thread_id}/answer.pdf"
                })

            return  history_list

        except SupabaseException as e:
            raise e

    def get_chapters(self) -> list[Any]:
        try:
            data = (
                self.db.table("chunks")
                .select("chapter_name", "subject", "standard")
                .execute()
            )
            return data.data
        except Exception as e:
            raise e


    def upload_paper_metadata(self, metadata: dict):
        try:
            self.db.table("generated_papers").insert(metadata).execute()
        except Exception as e:
            raise e

    def get_paper_metadata(self, thread_id: str, paper_name: str):
        try:
            response = self.db.table("generated_papers").select(paper_name).eq("thread_id", thread_id).execute()
            return response
        except Exception as e:
            raise e
    def delete_paper_metadata(self, thread_id: str):
        try:
            self.db.table("generated_papers").delete().eq("thread_id", thread_id).execute()
        except Exception as e:
            raise e


