from fastapi import HTTPException
from src.db.interfaces.interface import PaperRepository
from src.db.schemas import PaperHistory


class DBService:
    def __init__(self, paper_repo : PaperRepository):
        self.paper_repo = paper_repo

    async def get_chapters(self):
        try:
            chapter_data = self.paper_repo.get_chapters()
            return chapter_data
        except Exception as e:
            print(f"Error fetching paper history {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load chapters"
            )


    async def get_history(self, user_id : str) -> list[PaperHistory]:
        try:
            paper_history_list = self.paper_repo.get_user_paper_history(user_id=user_id)
            return paper_history_list
        except Exception as e:
            print(f"Error fetching paper history {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load paper history"
            )