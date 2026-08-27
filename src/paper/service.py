import os
import uuid
import asyncio
from typing import Optional

from fastapi import HTTPException
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from peewee import Database
from starlette.responses import FileResponse

from src.db.records.paper_record import PaperRecord, Status
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
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = await agent.aget_state(config)

        if not snapshot.values or not snapshot.values.get("paper_request"):
            print(f"[ERROR] State or paper_request missing for thread {thread_id}")
            return {"status": "failed"}

        raw_req = snapshot.values.get("paper_request")
        paper_request = raw_req if isinstance(raw_req, PaperRequest) else PaperRequest(**raw_req)

        filenames = [DocumentType.PAPER_PDF, DocumentType.ANSWER_PDF, DocumentType.PAPER_DOCX]
        file_paths = {}

        try:
            # 1. Read locally compiled paper artifacts
            files_data = {}
            for filename in filenames:
                relative_path = f"{thread_id}/{filename}"
                files_data[filename] = self.local_storage.get_file(file_path=relative_path)

            # 2. Upload compiled artifacts to Cloud Storage
            for filename, file_bytes in files_data.items():
                storage_path = f"{thread_id}/{filename}"
                content_type = "application/pdf" if filename.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                self.cloud_storage.put_file(
                    file_path=storage_path,
                    file_data=file_bytes,
                    content_type=content_type
                )
                file_paths[filename] = storage_path
                print(f"[INFO] Uploaded {filename} to Cloud Storage: {storage_path}")

            # 3. Update database paper session record to SAVED with cloud file paths
            paper_record = PaperRecord.from_request(
                thread_id=thread_id,
                user_id=user_id,
                paper_request=paper_request,
                status=Status.SAVED,
                file_paths=file_paths
            )
            self.paper_repo.update_paper_session(thread_id=thread_id, paper_record=paper_record)
            print(f"[INFO] Successfully synced metadata for thread {thread_id} to generated_papers DB table!")
            return {"status": "success"}

        except Exception as e:
            print(f"[ERROR] Failed to save paper session to cloud for thread {thread_id}: {e}")

            # Single unified failure state update in DB
            failed_record = PaperRecord.from_request(
                thread_id=thread_id,
                user_id=user_id,
                paper_request=paper_request,
                status=Status.FAILED
            )
            try:
                self.paper_repo.update_paper_session(thread_id=thread_id, paper_record=failed_record)
            except Exception as update_err:
                print(f"[WARN] Failed to update session status to FAILED in DB: {update_err}")

            # Rollback any uploaded cloud files
            for storage_path in file_paths.values():
                try:
                    self.cloud_storage.delete_file(file_path=storage_path)
                except Exception:
                    pass

            return {"status": "failed"}

    async def download_file(self, thread_id: str, filename: str, preview: bool = False):
        output_dir = f"outputs/{thread_id}"
        local_path = f"{output_dir}/{filename}"

        is_pdf = filename.endswith('.pdf')
        response_media_type = 'application/pdf' if is_pdf else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        disposition = 'inline' if (preview and is_pdf) else 'attachment'
        response_filename = filename if not (preview and is_pdf) else None

        if self.local_storage.exists(file_path=f"{thread_id}/{filename}"):
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

    async def generate_paper(self, paper_request: PaperRequest, user_id: str, user_fcm_token: Optional[str] = None):
        thread_id = str(uuid.uuid4())
        paper_record = PaperRecord.from_request(
            thread_id=thread_id,
            user_id=user_id,
            paper_request=paper_request,
            status=Status.GENERATING
        )

        self.paper_repo.create_paper_session(paper_record=paper_record)

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

        resume_command = Command(
            resume={
                "selected_indices": selected_indices
            }
        )

        print(f"[INFO] Resuming paper generation for thread {thread_id} with selected indices: {selected_indices}")
        asyncio.create_task(agent.ainvoke(input=resume_command, config=config))

        return {"status": "resumed", "thread_id": thread_id}
