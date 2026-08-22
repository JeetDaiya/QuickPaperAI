import json
import asyncio

from fastapi import APIRouter, Depends, Request
from peewee import Database
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from src.paper.schemas import PaperGenerateRequest
from src.dependencies import get_current_user, get_paper_service
from src.paper.service import PaperService

paper_router = APIRouter(prefix='/api')


class ResumeRequest(BaseModel):
    selected_indices: list[int]


@paper_router.post('/generate')
async def generate_paper(
    req: Request,
    paper_request: PaperGenerateRequest,
    current_user: dict = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service)
):
    agent = req.app.state.agent
    fcm_token = current_user.get('fcm_token') if current_user.get("notifications_enabled", True) else None
    print(f"[DEBUG] POST /generate user: {current_user.get('email')}, fcm_token: {fcm_token}")
    return await paper_service.generate_paper(agent=agent, paper_request=paper_request.to_domain(), user_fcm_token=fcm_token)


@paper_router.post('/resume/{thread_id}')
async def resume_generation(
    thread_id: str,
    payload: ResumeRequest,
    req: Request,
    current_user: dict = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service)
):
    agent = req.app.state.agent
    return await paper_service.resume_generation(
        thread_id=thread_id,
        selected_indices=payload.selected_indices,
        agent=agent,
    )


@paper_router.get('/status/{thread_id}/stream')
async def stream_generation_status(
    thread_id: str,
    req: Request,
    current_user: dict = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service)
):
    async def generator():
        last_state = None

        while True:
            if await req.is_disconnected():
                break
            status_data = await paper_service.get_generation_status(thread_id=thread_id, agent=req.app.state.agent, user_id=str(current_user.get('user_id', "")))

            current_state = json.dumps(status_data)

            if current_state != last_state:
                yield f"data: {current_state}\n\n"
                last_state = current_state

            if status_data.get("status") in ("completed", "failed", "awaiting_review"):
                break
            await asyncio.sleep(1)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@paper_router.get('/download/{thread_id}/{filename}')
async def download_file(
    thread_id: str,
    filename: str,
    preview: bool = False,
    current_user: dict = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service)
):
    return await paper_service.download_file(thread_id=thread_id, filename=filename, preview=preview)


@paper_router.post('/save-to-cloud/{thread_id}')
async def save_to_cloud(
    thread_id: str,
    req: Request,
    current_user: dict = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service)
):
    user_id = str(current_user["id"])
    agent = req.app.state.agent
    return await paper_service.save_to_cloud(thread_id=thread_id, agent=agent, user_id=user_id)


@paper_router.delete('/cancel/{thread_id}')
async def cancel_generation(
    thread_id: str,
    req: Request,
    current_user: dict = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service)
):
    db_pool: Database = req.app.state.db_pool
    return await paper_service.cancel_generation(thread_id=thread_id, db_pool=db_pool)
