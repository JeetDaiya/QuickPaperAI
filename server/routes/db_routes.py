from fastapi import APIRouter, Depends, HTTPException

from core.interfaces.db import PaperRepository


from server.dependencies import get_current_user, get_paper_repository, get_db_service
from server.schemas.paper_schemas import PaperHistory, PaperHistoryResponse
from server.services.db_service import DBService

db_router = APIRouter(prefix="/api/db")

@db_router.get("/get-chapters")
async def get_chapters(paper_repo : PaperRepository = Depends(get_paper_repository), db_service : DBService = Depends(get_db_service)):
    try:
        chapter_data = await db_service.get_chapters()
        return{
            "chapters" : chapter_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail='Failed to load chapters. Please try again')

@db_router.get("/history")
async def get_history(current_user : dict = Depends(get_current_user), paper_repo : PaperRepository = Depends(get_paper_repository), db_service : DBService = Depends(get_db_service)):
    try:
        user_id = str(current_user["id"])
        history_list = await db_service.get_history(user_id=user_id)
        history_list_response : list[PaperHistoryResponse] = [
            history.to_response() for history in history_list
        ]
        return {"history": history_list_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail='Failed to load history. Please try again')
        

