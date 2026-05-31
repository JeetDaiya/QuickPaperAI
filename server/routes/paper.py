from fastapi import FastAPI, BackgroundTasks, Request, APIRouter
from core.models.schemas import PaperRequest
from core.graph.runner import run_graph
import uuid
from core.graph.state import PaperState
from core.graph.tracker import update_chapter_progress,get_chapter_progress


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
    
    
@router.post('/generate')
def generate_paper(req : Request, paper_request : PaperRequest, background_task : BackgroundTasks):
    thread_id = str(uuid.uuid4())

    for chapter in paper_request.chapters:
        update_chapter_progress(
            thread_id=thread_id,
            chapter=chapter,
            status="pending",
            generated_count=0
        )    

        agent = req.app.state.agent

        background_task.add_task(graph_runner, agent, thread_id, paper_request)
    
    
    return {"thread_id": thread_id, "status" : "generating"}
    

@router.post('/resume/{thread_id}')
async def resume_generation(thread_id: str, payload: ResumeRequest, req: Request, background_tasks: BackgroundTasks):
    """Feeds approved question indices and resumes the execution."""
    agent = req.app.state.agent
    config = {"configurable": {"thread_id": thread_id}}
    
    # Verify thread is awaiting a review
    snapshot = await agent.aget_state(config)
    if not snapshot.tasks or not snapshot.tasks[0].interrupts:
        raise HTTPException(status_code=400, detail="No active review interrupts found for this thread.")
    
    async def resume_worker():
        await agent.ainvoke(Command(resume=payload.selected_indices), config)
        
    background_tasks.add_task(resume_worker)
    return {"status": "resuming"}

@router.get('/status/{thread_id}')
async def get_generation_status(thread_id: str, req: Request):
    """Polled by client to fetch live counts or review prompts."""
    agent = req.app.state.agent
    config = {"configurable": {"thread_id": thread_id}}
    
    snapshot = await agent.aget_state(config)
    
    # Case 1: Complete 
    if not snapshot.tasks:
        import os
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
        return {"status": "uninitialized"}

    # Case 2: Interrupt
    active_task = snapshot.tasks[0]
    if active_task.interrupts:
        interrupt_payload = active_task.interrupts[0].value
        return {
            "status": "awaiting_review",
            "questions": interrupt_payload.get("questions", [])
        }
        
    # Case 3: Return real-time chapter counts
    return {
        "status": "generating",
        "progress": get_chapter_progress(thread_id)
    }
