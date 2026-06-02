from fastapi import Depends, FastAPI, BackgroundTasks, Request, APIRouter, HTTPException
from fastapi.responses import FileResponse
from core.models.schemas import PaperRequest
from core.graph.runner import run_graph
import uuid
import os
import shutil
import asyncio
from core.graph.state import PaperState
from core.graph.tracker import update_chapter_progress, get_chapter_progress, PROGRESS_TRACKER
from pydantic import BaseModel
from langgraph.types import Command
from langgraph.graph.state import CompiledStateGraph
from server.db import db
from server.dependencies import get_current_user

paper_router = APIRouter(prefix='/api')

# Registry to track active background asyncio Tasks for thread cancellation
RUNNING_TASKS: dict[str, asyncio.Task] = {}

class ResumeRequest(BaseModel):
    selected_indices: list[int]


async def graph_runner(agent, thread_id: str, request: PaperRequest):
    """Function which runs the graph in background"""
    
    initial_state : PaperState = {
        "all_questions" : [],
        "selected_questions" : [],
        "paper_request": request, 
        "thread_id" : thread_id
    }
    
    try:
        await run_graph(agent, initial_state)
    except Exception as e:
        print(f"❌ LangGraph run crashed on thread {thread_id}: {e}")
        # Mark all chapters as failed in in-memory state tracker
        for chapter in request.chapters:
            update_chapter_progress(
                thread_id=thread_id,
                chapter=chapter,
                status="failed",
                generated_count=0
            )

async def upload_completed_paper_to_storage(thread_id : str, agent : CompiledStateGraph, config : dict, user_id : str):

    try:
        snapshot = await agent.aget_state(config)

        if not snapshot.values:
            print(f"❌ No state found for thread {thread_id}")
            return {"status" : "failed"}

        paper_request = snapshot.values["paper_request"]

        if not paper_request:
            print(f"❌ No paper request found for thread {thread_id}")
            return {"status" : "failed"}

        paper_dict = paper_request.model_dump()

        institution_name = paper_dict.get("institution_name", "Unknown")
        subject = paper_dict.get("subject", "Unknown")
        chapters = paper_dict.get("chapters", [])
        standard = paper_dict.get("standard", [])
        difficulty = paper_dict.get("difficulty", "Balanced")
        objective_count = paper_dict.get("objective_count", 0)
        subjective_count = paper_dict.get("subjective_count", 0)
        allowed_types = [t.value if hasattr(t, "value") else str(t) for t in paper_dict.get("allowed_types", [])]
        
        output_dir = f"outputs/{thread_id}"
        paper_pdf_local = f"{output_dir}/paper.pdf"
        paper_docx_local = f"{output_dir}/paper.docx"
        answer_pdf_local = f"{output_dir}/answer.pdf"

        if not (os.path.exists(paper_pdf_local) and os.path.exists(answer_pdf_local) and os.path.exists(paper_docx_local)):
            print(f"⚠️ Compiled files are missing locally in outputs/{thread_id}/, aborting upload.")
            return

        try:
            db.storage.get_bucket("question-papers")
        except Exception as e:
            print(f"❌ Bucket does not exist: {e}")
            return

        file_paths = {}
        for filename, local_path in [
            ("paper.pdf", paper_pdf_local),
            ("answer.pdf", answer_pdf_local),
            ("paper.docx", paper_docx_local)
        ]:
            storage_path = f"{thread_id}/{filename}"
            
            with open(local_path, "rb") as f:
                file_data = f.read()
                content_type = "application/pdf" if filename.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                
                
                try:
                    db.storage.from_("question-papers").upload(
                        path=f"{thread_id}/{filename}",
                        file=file_data,
                        file_options={"content-type": content_type, "x-upsert": "true"}
                    )

                    file_paths[filename] = storage_path
                    print(f"☁️ Uploaded {filename} to Supabase Storage: {storage_path}")
                except Exception as e:
                    print(f"❌ Failed to upload {filename}: {e}")
                    return {"status": "failed"}

        insert_data = {
            "user_id" : user_id,
            "thread_id" : thread_id,
            "institution_name" : institution_name,
            "subject" : subject,
            "standard" : standard,
            "difficulty" : difficulty,
            "chapters" : chapters,
            "objective_count" : objective_count,
            "subjective_count" : subjective_count,
            "allowed_types" : allowed_types,
            "paper_pdf_path" : file_paths["paper.pdf"],
            "answer_pdf_path" : file_paths["answer.pdf"],
            "paper_docx_path" : file_paths["paper.docx"]
        }

        db.table("generated_papers").insert(insert_data).execute()
        print(f"🎉 Successfully synced metadata for thread {thread_id} to generated_papers database table!")

        return {"status" : "success"}
        
    except Exception as e:
        print(f"❌ Error Uploading completed paper to storage: {e}")

        return {"status" : "failed"}
    
    
@paper_router.post('/generate')
async def generate_paper(req : Request, paper_request : PaperRequest, current_user : dict = Depends(get_current_user)):
    thread_id = str(uuid.uuid4())

    # 1. Initialize pending status for all chapters
    for chapter in paper_request.chapters:
        update_chapter_progress(
            thread_id=thread_id,
            chapter=chapter,
            status="pending",
            generated_count=0
        )    

    # 2. Schedule cancelable background task in the event loop
    agent = req.app.state.agent
    task = asyncio.create_task(graph_runner(agent, thread_id, paper_request))
    RUNNING_TASKS[thread_id] = task
    task.add_done_callback(lambda t: RUNNING_TASKS.pop(thread_id, None))
    
    return {"thread_id": thread_id, "status" : "generating"}
    

@paper_router.post('/resume/{thread_id}')
async def resume_generation(thread_id: str, payload: ResumeRequest, req: Request, current_user : dict = Depends(get_current_user)):
    """Feeds approved question indices and resumes the execution."""
    agent = req.app.state.agent
    config = {"configurable": {"thread_id": thread_id}}
    
    # Verify thread is awaiting a review
    snapshot = await agent.aget_state(config)
    if not snapshot.tasks or not snapshot.tasks[0].interrupts:
        raise HTTPException(status_code=400, detail="No active review interrupts found for this thread.")
    
    async def resume_worker():
        try:
            await agent.ainvoke(Command(resume=payload.selected_indices), config)
        except Exception as e:
            print(f"❌ LangGraph run crashed on resume thread {thread_id}: {e}")
            # Mark all chapters as failed if it crashes during resume
            snapshot = await agent.aget_state(config)
            if snapshot.values and "paper_request" in snapshot.values:
                req_obj = snapshot.values["paper_request"]
                chapters = req_obj.chapters if hasattr(req_obj, "chapters") else req_obj.get("chapters", [])
                for chapter in chapters:
                    update_chapter_progress(
                        thread_id=thread_id,
                        chapter=chapter,
                        status="failed",
                        generated_count=0
                    )
        
    task = asyncio.create_task(resume_worker())
    RUNNING_TASKS[thread_id] = task
    task.add_done_callback(lambda t: RUNNING_TASKS.pop(thread_id, None))
    
    return {"status": "resuming"}


@paper_router.get('/status/{thread_id}')
async def get_generation_status(thread_id: str, req: Request, current_user : dict = Depends(get_current_user)):
    """Polled by client to fetch live counts or review prompts."""
    agent = req.app.state.agent
    config = {"configurable": {"thread_id": thread_id}}
    
    snapshot = await agent.aget_state(config)
    
    # 1. Interrupt Check FIRST (Check both snapshot.tasks and snapshot.next for robustness)
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
        # Extract the latest interrupt payload from snapshot metadata if tasks are empty
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
        
    # 2. Case 2: Complete Check
    if not snapshot.next or not snapshot.tasks:
        if os.path.exists(f"outputs/{thread_id}/paper.pdf"):
            return {
                "status": "completed",
                "files": {
                    "paper_pdf": f"/api/download/{thread_id}/paper.pdf",
                    "paper_docx": f"/api/download/{thread_id}/paper.docx",
                    "answer_pdf": f"/api/download/{thread_id}/answer.pdf"
                }
            }
            
        # Check if it was marked as failed
        progress = get_chapter_progress(thread_id)
        if progress and any(item.get("status") == "failed" for item in progress.values()):
            return {
                "status": "failed",
                "progress": progress
            }
            
    # 3. Default: Return active generation status
    progress = get_chapter_progress(thread_id)
    if progress:
        return {
            "status": "generating",
            "progress": progress
        }
        
    return {"status": "uninitialized"}


@paper_router.get('/download/{thread_id}/{filename}')
async def download_file(thread_id: str, filename: str, preview: bool = False, current_user : dict = Depends(get_current_user)):
    """Streams compiled paper/answer key files securely. Supports inline browser previewing."""
    output_dir = f"outputs/{thread_id}"
    local_path = f"{output_dir}/{filename}"

    # Set native content types for inline preview browser rendering
    if filename.endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        media_type = "application/octet-stream"

    # If previewing in-browser, do not send Content-Disposition: attachment header
    response_filename = None if preview else filename
    response_media_type = media_type if preview else "application/octet-stream"

    if os.path.exists(local_path):
        return FileResponse(local_path, media_type=response_media_type, filename=response_filename)
    
    print(f"🔄 Cache miss: Local file outputs/{thread_id}/{filename} not found. Attempting cloud recovery...")

    column_mapping = {
        "paper.pdf": "paper_pdf_path",
        "answer.pdf": "answer_pdf_path",
        "paper.docx": "paper_docx_path"
    }

    target_column = column_mapping.get(filename)
    if not target_column:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    try:
        response = db.table("generated_papers").select(target_column).eq("thread_id", thread_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Paper session record not found in database.")

        file_path = response.data[0].get(target_column)
        if not file_path:
            raise HTTPException(status_code=404, detail=f"{filename} not found in database.")
        
        bucket_name = "question-papers"

        file_bytes = db.storage.from_(bucket_name).download(file_path)

        os.makedirs(output_dir, exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(file_bytes)

        print(f"✅ Recovered and hot-cached {filename} successfully from Supabase Storage.")
        return FileResponse(local_path, media_type=response_media_type, filename=response_filename)
        
    except Exception as e:
        print(f"❌ Error recovering file from Supabase: {e}")
        raise HTTPException(status_code=500, detail="Failed to recover file from Supabase")
    
@paper_router.post('/save-to-cloud/{thread_id}', )
async def save_to_cloud(thread_id: str, req: Request, current_user : dict = Depends(get_current_user)):
    try:
        agent = req.app.state.agent
        config = {"configurable": {"thread_id": thread_id}}
        await upload_completed_paper_to_storage(thread_id, agent, config, str(current_user["id"]))
        return {"status": "success"}
    except Exception as e:
        print(f"❌ Error saving paper to cloud: {e}")
        raise HTTPException(status_code=500, detail="Failed to save paper to cloud")

@paper_router.delete('/cancel/{thread_id}')
async def cancel_generation(thread_id: str, req: Request, current_user : dict = Depends(get_current_user)):
    """Purges checkpoints, tracking states, active tasks, cloud storage files, and local caches for a thread."""
    try:
        # 1. Stop active background graph execution task if running
        if thread_id in RUNNING_TASKS:
            task = RUNNING_TASKS[thread_id]
            if not task.done():
                task.cancel()
                print(f"🛑 Cancelled active background task for thread {thread_id}")
            RUNNING_TASKS.pop(thread_id, None)

        # 2. Purge in-memory progressive tracker
        if thread_id in PROGRESS_TRACKER:
            del PROGRESS_TRACKER[thread_id]
            print(f"🧹 Purged progress tracker for thread {thread_id}")

        # 3. Purge PostgreSQL checkpointer checkpoints, blobs, and writes
        if hasattr(req.app.state, "db_pool") and req.app.state.db_pool:
            try:
                async with req.app.state.db_pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,))
                        await cur.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (thread_id,))
                        await cur.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (thread_id,))
                print(f"🗄️ Cleaned all checkpointer DB entries for thread {thread_id}")
            except Exception as dbe:
                print(f"⚠️ Warning: Could not clean Postgres checkpoints from Saver: {dbe}")

        # 4. Clean SQL history entry from generated_papers table
        try:
            db.table("generated_papers").delete().eq("thread_id", thread_id).execute()
            print(f"🗃️ Deleted metadata entry from generated_papers for thread {thread_id}")
        except Exception as sqle:
            print(f"⚠️ Warning: Could not delete generated_papers metadata: {sqle}")

        # 5. Clean cloud Supabase Storage assets
        try:
            db.storage.from_("question-papers").remove([
                f"{thread_id}/paper.pdf",
                f"{thread_id}/answer.pdf",
                f"{thread_id}/paper.docx"
            ])
            print(f"☁️ Purged cloud storage assets for thread {thread_id}")
        except Exception as storee:
            print(f"⚠️ Warning: Cloud storage assets not found or could not be removed: {storee}")

        # 6. Clean local outputs cache directory
        local_dir = f"outputs/{thread_id}"
        if os.path.exists(local_dir):
            shutil.rmtree(local_dir, ignore_errors=True)
            print(f"📂 Purged local server caches: {local_dir}")

        return {"status": "cancelled", "message": f"Successfully aborted and cleaned up thread {thread_id} completely."}

    except Exception as e:
        print(f"❌ Error during active session cancellation: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel and clean up generation session")
    
