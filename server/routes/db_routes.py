from fastapi import APIRouter, Depends,HTTPException

from core.interfaces.db import PaperRepository


from server.dependencies import get_current_user, get_paper_repository

db_router = APIRouter(prefix="/api/db")

@db_router.get("/get-chapters")
async def get_chapters(paper_repo : PaperRepository = Depends(get_paper_repository)):
    try:
        chapter_data = paper_repo.get_chapters()
        return {"chapters" : chapter_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@db_router.get("/history")
async def get_history(current_user : dict = Depends(get_current_user), paper_repo : PaperRepository = Depends(get_paper_repository)):
    try:
        user_id = str(current_user["id"])
        # Query generated papers sorted by created_at DESC
        history_list = paper_repo.get_user_paper_history(user_id)
        return {"history": history_list}
        
    except Exception as e:
        print(f"❌ Error fetching paper history: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to load paper history: {str(e)}"
        )
