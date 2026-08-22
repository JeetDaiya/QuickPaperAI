import os
import uuid
import asyncio
from typing import Optional

from fastapi import HTTPException
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from peewee import Database
from starlette.responses import FileResponse

from src.paper.graph.config import GraphConfig
from src.paper.graph.tracker import ProgressTracker
from src.db.interfaces.interface import PaperRepository, ChunkRepository, UserRepository
from src.paper.compilers.interfaces.interface import DocumentCompiler
from src.paper.formatters.interfaces.interface import PaperFormatter
from src.storage.interfaces.interface import StorageService
from src.paper.models import PaperRequest, ChapterStatus, DocumentType
from src.paper.task_manager import TaskManager
from src.notifications.adapters.firebase_notification_service import FirebaseNotificationService


class PaperService:
    def __init__(
        self, 
        paper_repo: PaperRepository, 
        cloud_storage: StorageService, 
        local_storage: StorageService, 
        task_manager: TaskManager, 
        progress_tracker: ProgressTracker, 
        html_paper_formatter: PaperFormatter, 
        markdown_paper_formatter: PaperFormatter, 
        document_compiler: DocumentCompiler, 
        chunk_repo: ChunkRepository,
        user_repo: UserRepository,
        notification_service: FirebaseNotificationService
    ):
        self.task_manager = task_manager
        self.paper_repo = paper_repo
        self.cloud_storage = cloud_storage
        self.local_storage = local_storage
        self.progress_tracker = progress_tracker
        self.html_paper_formatter = html_paper_formatter
        self.markdown_paper_formatter = markdown_paper_formatter
        self.document_compiler = document_compiler
        self.chunk_repo = chunk_repo
        self.user_repo = user_repo
        self.notification_service = notification_service

    async def save_to_cloud(self, thread_id: str, agent: CompiledStateGraph, user_id: str):
        try:
            config = {"configurable": {"thread_id": thread_id}}
            snapshot = await agent.aget_state(config)

            if not snapshot.values:
                print(f"[ERROR] No state found for thread {thread_id}")
                return {"status": "failed"}

            paper_request = snapshot.values.get("paper_request")
            if not paper_request:
                print(f"[ERROR] No paper request found for thread {thread_id}")
                return {"status": "failed"}

            paper_dict = paper_request.model_dump() if hasattr(paper_request, "model_dump") else paper_request

            institution_name = paper_dict.get("institution_name", "Unknown")
            subject = paper_dict.get("subject", "Unknown")
            chapters = paper_dict.get("chapters", [])
            standard = paper_dict.get("standard", [])
            difficulty = paper_dict.get("difficulty", "Balanced")
            objective_count = paper_dict.get("objective_count", 0)
            subjective_count = paper_dict.get("subjective_count", 0)
            allowed_types = [t.value if hasattr(t, "value") else str(t) for t in paper_dict.get("allowed_types", [])]

            filenames = [DocumentType.PAPER_PDF, DocumentType.ANSWER_PDF, DocumentType.PAPER_DOCX]
            files_data = {}

            try:
                for filename in filenames:
                    relative_path = f"{thread_id}/{filename}"
                    files_data[filename] = self.local_storage.get_file(file_path=relative_path)
            except FileNotFoundError:
                print(f"[WARN] Compiled files missing locally in outputs/{thread_id}/, aborting upload.")
                return {"status": "failed"}

            file_paths = {}
            for filename, file_bytes in files_data.items():
                storage_path = f"{thread_id}/{filename}"
                content_type = "application/pdf" if filename.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                try:
                    self.cloud_storage.put_file(
                        file_path=storage_path,
                        file_data=file_bytes,
                        content_type=content_type
                    )
                    file_paths[filename] = storage_path
                    print(f"[INFO] Uploaded {filename} to Cloud Storage: {storage_path}")
                except Exception as upload_err:
                    print(f"[ERROR] Failed to upload {filename} to cloud: {upload_err}")
                    return {"status": "failed"}

            try:
                insert_data = {
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "institution_name": institution_name,
                    "subject": subject,
                    "standard": standard,
                    "difficulty": difficulty,
                    "chapters": chapters,
                    "objective_count": objective_count,
                    "subjective_count": subjective_count,
                    "allowed_types": allowed_types,
                    "paper_pdf_path": file_paths[DocumentType.PAPER_PDF],
                    "answer_pdf_path": file_paths[DocumentType.ANSWER_PDF],
                    "paper_docx_path": file_paths[DocumentType.PAPER_DOCX]
                }
                self.paper_repo.upload_paper_metadata(metadata=insert_data)
                print(f"[INFO] Successfully synced metadata for thread {thread_id} to generated_papers DB table!")
            except Exception as db_err:
                print(f"[ERROR] Database insert failed: {db_err}")
                try:
                    for filename in filenames:
                        self.cloud_storage.delete_file(file_path=f"{thread_id}/{filename}")
                except Exception as e:
                    raise e
                return {"status": "failed"}

            return {"status": "success"}

        except Exception as e:
            print(f"[ERROR] Error Uploading completed paper to storage: {e}")
            return {"status": "failed"}

    async def download_file(self, thread_id: str, filename: str, preview: bool = False):
        output_dir = f"outputs/{thread_id}"
        local_path = f"{output_dir}/{filename}"

        if filename.endswith(".pdf"):
            media_type = "application/pdf"
        elif filename.endswith(".docx"):
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            media_type = "application/octet-stream"

        response_filename = None if preview else filename
        response_media_type = media_type if preview else "application/octet-stream"

        if os.path.exists(local_path):
            return FileResponse(local_path, media_type=response_media_type, filename=response_filename)

        print(f"[INFO] Cache miss: Local file outputs/{thread_id}/{filename} not found. Attempting cloud recovery...")

        column_mapping = {
            DocumentType.PAPER_PDF: "paper_pdf_path",
            DocumentType.ANSWER_PDF: "answer_pdf_path",
            DocumentType.PAPER_DOCX: "paper_docx_path"
        }

        target_column = column_mapping.get(filename)
        if not target_column:
            raise HTTPException(status_code=400, detail="Invalid filename")

        try:
            response = self.paper_repo.get_paper_metadata(thread_id=thread_id, paper_name=target_column)
            if not response.data:
                raise HTTPException(status_code=404, detail="Paper session record not found in database.")

            file_path = response.data[0].get(target_column)
            if not file_path:
                raise HTTPException(status_code=404, detail=f"{filename} not found in database.")

            file_bytes = self.cloud_storage.get_file(file_path)
            self.local_storage.put_file(file_data=file_bytes, file_path=f"{thread_id}/{filename}")

            print(f"[INFO] Recovered and hot-cached {filename} successfully from Supabase Storage.")
            return FileResponse(local_path, media_type=response_media_type, filename=response_filename)

        except Exception as e:
            print(f"[ERROR] Error recovering file from Supabase: {e}")
            raise HTTPException(status_code=500, detail="Failed to recover file from Supabase")

    async def cancel_generation(self, thread_id: str, db_pool: Database):
        try:
            self.task_manager.cancel_task(thread_id=thread_id)
            await self.progress_tracker.delete_progress(thread_id=thread_id)

            try:
                async with db_pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,))
                        await cur.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (thread_id,))
                        await cur.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (thread_id,))
                print(f"[INFO] Cleaned all checkpointer DB entries for thread {thread_id}")
            except Exception as dbe:
                print(f"[WARN] Could not clean Postgres checkpoints from Saver: {dbe}")

            try:
                self.paper_repo.delete_paper_metadata(thread_id=thread_id)
            except Exception as sqle:
                print(f"[WARN] Could not delete generated_papers metadata: {sqle}")

            try:
                self.cloud_storage.delete_file(file_path=f"{thread_id}/{DocumentType.PAPER_PDF}")
                self.cloud_storage.delete_file(file_path=f"{thread_id}/{DocumentType.ANSWER_PDF}")
                self.cloud_storage.delete_file(file_path=f"{thread_id}/{DocumentType.PAPER_DOCX}")
            except Exception as storee:
                print(f"[WARN] Cloud storage assets not found or could not be removed: {storee}")

            local_dir = f"outputs/{thread_id}"
            if self.local_storage.exists(file_path=f"{thread_id}/{DocumentType.PAPER_PDF}"):
                self.local_storage.delete_file(file_path=f"{thread_id}/{DocumentType.PAPER_PDF}")
                print(f"[INFO] Purged local server caches: {local_dir}")

            return {
                "status": "cancelled",
                "message": f"Successfully aborted and cleaned up thread {thread_id} completely."
            }
        except Exception as e:
            print(f"[ERROR] Error during active session cancellation: {e}")
            raise HTTPException(status_code=500, detail="Failed to cancel and clean up generation session")

    async def get_generation_status(self, thread_id: str, agent: CompiledStateGraph, user_id: str):
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = await agent.aget_state(config=config)

        is_awaiting_review = False
        interrupt_payload = {}

        if snapshot.tasks:
            for task in snapshot.tasks:
                if task.interrupts:
                    is_awaiting_review = True
                    interrupt_payload = task.interrupts[0].value
                    break

        if not is_awaiting_review and snapshot.next and any("review" in str(node).lower() for node in snapshot.next):
            is_awaiting_review = True
            if snapshot.metadata and "interrupts" in snapshot.metadata and snapshot.metadata["interrupts"]:
                interrupt_payload = snapshot.metadata["interrupts"][0]

        if is_awaiting_review:
            paper_req = snapshot.values.get("paper_request", {})
            if hasattr(paper_req, "model_dump"):
                paper_req_dict = paper_req.model_dump()
            elif isinstance(paper_req, dict):
                paper_req_dict = paper_req
            else:
                paper_req_dict = {}

            targets = {
                "objective": paper_req_dict.get("objective_count", 0),
                "subjective": paper_req_dict.get("subjective_count", 0)
            }

            return {
                "status": "awaiting_review",
                "questions": interrupt_payload.get("questions", []) if isinstance(interrupt_payload, dict) else [],
                "targets": targets
            }

        if not snapshot.next or not snapshot.tasks:
            if self.local_storage.exists(file_path=f"{thread_id}/{DocumentType.PAPER_PDF}"):
                return {
                    "status": "completed",
                    "files": {
                        "paper_pdf": f"/api/download/{thread_id}/{DocumentType.PAPER_PDF}",
                        "paper_docx": f"/api/download/{thread_id}/{DocumentType.PAPER_DOCX}",
                        "answer_pdf": f"/api/download/{thread_id}/{DocumentType.ANSWER_PDF}"
                    }
                }

            progress = await self.progress_tracker.get_chapter_progress(thread_id)
            if progress and any(item.get("status") == ChapterStatus.FAILED for item in progress.values()):
                return {
                    "status": "failed",
                    "progress": progress
                }

        progress = await self.progress_tracker.get_chapter_progress(thread_id)
        if progress:
            return {
                "status": "generating",
                "progress": progress
            }

        return {"status": "uninitialized"}

    async def generate_paper(self, paper_request: PaperRequest, agent: Optional[CompiledStateGraph] = None, user_fcm_token: Optional[str] = None):
        thread_id = str(uuid.uuid4())

        await self.progress_tracker.update_chapters_progress(
            thread_id=thread_id,
            chapters=paper_request.chapters,
            status=ChapterStatus.PENDING
        )

        await self.task_manager.register_task(
            thread_id=thread_id,
            payload=paper_request.model_dump(),
            user_fcm_token=user_fcm_token
        )

        return {"thread_id": thread_id, "status": "generating"}

    async def resume_generation(self, thread_id: str, selected_indices: list[int], agent: CompiledStateGraph):
        dependencies = GraphConfig(
            chunk_repo=self.chunk_repo,
            html_paper_formatter=self.html_paper_formatter,
            markdown_paper_formatter=self.markdown_paper_formatter,
            document_compiler=self.document_compiler,
            progress_tracker=self.progress_tracker
        )

        config = {
            "configurable": {
                "thread_id": thread_id,
                **dependencies
            }
        }

        snapshot = await agent.aget_state(config)
        has_interrupt = False
        if snapshot.tasks:
            for task in snapshot.tasks:
                if task.interrupts:
                    has_interrupt = True
                    break

        if not has_interrupt and snapshot.next and any("review" in str(node).lower() for node in snapshot.next):
            has_interrupt = True

        if not has_interrupt:
            print(f"[WARN] Cannot resume thread {thread_id}: snapshot.next={snapshot.next}, snapshot.tasks={snapshot.tasks}")
            raise HTTPException(status_code=400, detail="No active review interrupts found for this thread.")

        async def resume_worker():
            try:
                await agent.ainvoke(Command(resume=selected_indices), config)
            except Exception as e:
                print(f"[ERROR] LangGraph run crashed on resume thread {thread_id}: {e}")
                snapshot_err = await agent.aget_state(config)
                if snapshot_err.values and "paper_request" in snapshot_err.values:
                    req_obj = snapshot_err.values["paper_request"]
                    chapters = req_obj.chapters if hasattr(req_obj, "chapters") else req_obj.get("chapters", [])
                    await self.progress_tracker.update_chapters_progress(
                        thread_id=thread_id,
                        chapters=chapters,
                        status=ChapterStatus.FAILED
                    )

        asyncio.create_task(resume_worker())

        return {"status": "resuming"}
