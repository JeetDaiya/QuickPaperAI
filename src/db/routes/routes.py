from fastapi import APIRouter, Depends

from src.dependencies import get_current_user, get_db_service
from src.db.services.service import DBService

db_router = APIRouter(prefix="/api/db")

@db_router.get("/get-chapters")
async def get_chapters(db_service : DBService = Depends(get_db_service)):
    return await db_service.get_chapters()


@db_router.get("/history")
async def get_history(current_user : dict = Depends(get_current_user),  db_service : DBService = Depends(get_db_service)):
    user_id = str(current_user["id"])
    return await db_service.get_history(user_id=user_id)


        

