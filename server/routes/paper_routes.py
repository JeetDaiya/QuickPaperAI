from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from core.models.schemas import PaperRequest
from server.dependencies import get_current_user, get_paper_service
from server.services.paper_service import PaperService

paper_router = APIRouter(prefix='/api')


class ResumeRequest(BaseModel):
    selected_indices: list[int]


@paper_router.post('/generate')
async def generate_paper(
    req: Request,
    paper_request: PaperRequest,
    current_user: dict = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service)
):
    return await paper_service.generate_paper(req=req, paper_request=paper_request)


@paper_router.post('/resume/{thread_id}')
async def resume_generation(
    thread_id: str,
    payload: ResumeRequest,
    req: Request,
    current_user: dict = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service)
):
    return await paper_service.resume_generation(
        thread_id=thread_id,
        selected_indices=payload.selected_indices,
        req=req
    )


@paper_router.get('/status/{thread_id}')
async def get_generation_status(
    thread_id: str,
    req: Request,
    current_user: dict = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service)
):
    return await paper_service.get_generation_status(thread_id=thread_id, req=req)


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
    return await paper_service.cancel_generation(thread_id=thread_id, req=req)
