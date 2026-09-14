from fastapi import APIRouter, Depends

from src.auth.dependencies import get_current_user, ip_rate_limit
from src.db.dependencies import get_db_service
from src.db.services.service import DBService

db_router = APIRouter(prefix="/api/db")

@db_router.get(
    "/get-chapters",
    dependencies=[Depends(ip_rate_limit("get-chapters", limit=30, window_seconds=600))],
)
async def get_chapters(db_service : DBService = Depends(get_db_service)):
    return await db_service.get_chapters()


@db_router.get("/history")
async def get_history(current_user : dict = Depends(get_current_user),  db_service : DBService = Depends(get_db_service)):
    user_id = str(current_user["id"])
    return await db_service.get_history(user_id=user_id)


        

