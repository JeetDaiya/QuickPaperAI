from fastapi import FastAPI, BackgroundTasks, Request, APIRouter, HTTPException
from fastapi.responses import FileResponse
from core.models.schemas import PaperRequest
from core.graph.runner import run_graph
import uuid
import os
from core.graph.state import PaperState
from core.graph.tracker import update_chapter_progress, get_chapter_progress
from pydantic import BaseModel
from langgraph.types import Command

paper_router = APIRouter(prefix='/api')

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
    
    
@paper_router.post('/generate')
def generate_paper(req : Request, paper_request : PaperRequest, background_task : BackgroundTasks):
    thread_id = str(uuid.uuid4())

    # 1. Initialize pending status for all chapters
    for chapter in paper_request.chapters:
        update_chapter_progress(
            thread_id=thread_id,
            chapter=chapter,
            status="pending",
            generated_count=0
        )    

    # 2. Add background task EXACTLY ONCE to avoid duplicate running
    agent = req.app.state.agent
    background_task.add_task(graph_runner, agent, thread_id, paper_request)
    
    return {"thread_id": thread_id, "status" : "generating"}
    

@paper_router.post('/resume/{thread_id}')
async def resume_generation(thread_id: str, payload: ResumeRequest, req: Request, background_tasks: BackgroundTasks):
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
        
    background_tasks.add_task(resume_worker)
    return {"status": "resuming"}


@paper_router.get('/status/{thread_id}')
async def get_generation_status(thread_id: str, req: Request):
    """Polled by client to fetch live counts or review prompts."""
    agent = req.app.state.agent
    config = {"configurable": {"thread_id": thread_id}}
    
    snapshot = await agent.aget_state(config)
    
    # Case 1: Complete 
    if not snapshot.tasks:
        # Check output files exist or not
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
            
        return {"status": "uninitialized"}

    # Case 2: Interrupt
    active_task = snapshot.tasks[0]
    if active_task.interrupts:
        interrupt_payload = active_task.interrupts[0].value
        return {
            "status": "awaiting_review",
            "questions": interrupt_payload.get("questions", [])
        }
        
    # Case 3: Return real-time chapter counts (check if any chapter has failed)
    progress = get_chapter_progress(thread_id)
    if progress and any(item.get("status") == "failed" for item in progress.values()):
        return {
            "status": "failed",
            "progress": progress
        }
        
    return {
        "status": "generating",
        "progress": progress
    }


@paper_router.get('/download/{thread_id}/{filename}')
async def download_file(thread_id: str, filename: str):
    """Streams compiled paper/answer key files securely."""
    file_path = f"outputs/{thread_id}/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Requested file not found or still compiling.")
    return FileResponse(file_path)
