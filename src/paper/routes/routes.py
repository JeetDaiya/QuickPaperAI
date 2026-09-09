import json

from fastapi import APIRouter, Depends, Request
from peewee import Database
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from src.paper.schemas import PaperGenerateRequest
from src.dependencies import get_current_user, get_paper_service, verify_thread_ownership, extract_user_id, get_pubsub_redis
from src.paper.service import PaperService

TERMINAL_STATUSES = ("completed", "failed", "awaiting_review")

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
    user_id = extract_user_id(current_user)
    return await paper_service.generate_paper(
        paper_request=paper_request.to_domain(),
        user_id=user_id,
        user_fcm_token=fcm_token
    )


@paper_router.post('/resume/{thread_id}')
async def resume_generation(
    thread_id: str,
    payload: ResumeRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(verify_thread_ownership),
    paper_service: PaperService = Depends(get_paper_service)
):
    return await paper_service.resume_generation(
        thread_id=thread_id,
        selected_indices=payload.selected_indices,
    )


@paper_router.get('/status/{thread_id}/stream')
async def stream_generation_status(
    thread_id: str,
    req: Request,
    wait_past_review: bool = False,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(verify_thread_ownership),
    paper_service: PaperService = Depends(get_paper_service)
):
    user_id = extract_user_id(current_user)

    # The done page opens this stream right after POSTing /resume, which only enqueues the
    # ARQ job — the checkpoint can still read "awaiting_review" for a moment before the worker
    # picks it up. Treating that stale read as terminal would close the stream before the real
    # "completed"/"failed" transition ever arrives, leaving the page stuck until a manual refresh.
    close_statuses = ("completed", "failed") if wait_past_review else TERMINAL_STATUSES

    async def check_status() -> tuple[str, dict]:
        status_data = await paper_service.get_generation_status(thread_id=thread_id, agent=req.app.state.agent, user_id=user_id)
        return json.dumps(status_data), status_data

    async def generator():
        # Subscribe BEFORE the initial status check. Redis pub/sub doesn't buffer for absent
        # subscribers, so if we checked first and a "finished" shout landed in the gap before
        # subscribing, it would be lost and the stream would hang until a manual refresh. By
        # subscribing first, any shout after this point is buffered for us; any shout that fired
        # earlier means the state is already durable, so the initial check below catches it.
        channel = f"channel:progress:{thread_id}"
        pubsub = get_pubsub_redis().pubsub()
        await pubsub.subscribe(channel)

        try:
            current_state, status_data = await check_status()
            last_state = current_state
            yield f"data: {current_state}\n\n"

            if status_data.get("status") in TERMINAL_STATUSES:
                return

            while True:
                if await req.is_disconnected():
                    break

                # Push-based: a message means real progress happened, re-check status then.
                # On timeout (no message) we still re-check as a self-healing safety net — a
                # dropped pub/sub message would otherwise leave the stream waiting forever. The
                # 10s cadence keeps this cheap (only while generation is in flight), unlike the
                # old 1s poll.
                await pubsub.get_message(ignore_subscribe_messages=True, timeout=10)

                current_state, status_data = await check_status()
                if current_state != last_state:
                    last_state = current_state
                    yield f"data: {current_state}\n\n"

                if status_data.get("status") in close_statuses:
                    break
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

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
    _: None = Depends(verify_thread_ownership),
    paper_service: PaperService = Depends(get_paper_service)
):
    return await paper_service.download_file(thread_id=thread_id, filename=filename, preview=preview)


@paper_router.post('/save-to-cloud/{thread_id}')
async def save_to_cloud(
    thread_id: str,
    req: Request,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(verify_thread_ownership),
    paper_service: PaperService = Depends(get_paper_service)
):
    user_id = extract_user_id(current_user)
    agent = req.app.state.agent
    return await paper_service.save_to_cloud(thread_id=thread_id, agent=agent, user_id=user_id)


@paper_router.delete('/cancel/{thread_id}')
async def cancel_generation(
    thread_id: str,
    req: Request,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(verify_thread_ownership),
    paper_service: PaperService = Depends(get_paper_service)
):
    db_pool: Database = req.app.state.db_pool
    return await paper_service.cancel_generation(thread_id=thread_id, db_pool=db_pool)
