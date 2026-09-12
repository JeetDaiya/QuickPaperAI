import asyncio

from src.db.interfaces.interface import PaperRepository
from src.db.schemas import PaperHistory


class DBService:
    def __init__(self, paper_repo : PaperRepository):
        self.paper_repo = paper_repo

    async def get_chapters(self):
        chapter_data = await asyncio.to_thread(self.paper_repo.get_chapters)
        return {
            "chapters" : chapter_data
        }


    async def get_history(self, user_id : str) -> dict[str, list[PaperHistory]]:
        paper_history_list = await asyncio.to_thread(self.paper_repo.get_user_paper_history, user_id=user_id)
        return {"history": paper_history_list}