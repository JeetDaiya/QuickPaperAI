from fastapi import HTTPException
from src.db.interfaces.interface import PaperRepository
from src.paper.schemas import PaperHistory


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
            raw_history_list = self.paper_repo.get_user_paper_history(user_id=user_id)
            paper_history_list : list[PaperHistory] = [
                PaperHistory(
                    thread_id=item.get('thread_id'),
                    created_at=item.get('created_at'),
                    institution_name=item.get('institution_name'),
                    chapters=item.get('chapters'),
                    subject=item.get('subject'),
                    standard=item.get('standard'),
                    allowed_types=item.get('allowed_types'),
                    objective_count=item.get('objective_count'),
                    difficulty=item.get('difficulty'),
                    subjective_count=item.get('subjective_count'),
                    id=item.get('id'),
                )
                for item in raw_history_list
            ]

            return paper_history_list
        except Exception as e:
            print(f"Error fetching paper history {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load paper history"
            )