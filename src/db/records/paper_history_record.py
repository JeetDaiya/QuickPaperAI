from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, computed_field
from src.paper.models import DifficultyDistribution


class PaperHistoryRecord(BaseModel):
    id: int
    thread_id: str
    created_at: str | datetime
    institution_name: str
    subject: str
    standard: str
    difficulty: Optional[str] = "Balanced"
    difficulty_distribution: DifficultyDistribution = Field(
        default_factory=lambda: DifficultyDistribution(easy=20, medium=50, hard=30)
    )
    chapters: list[str] = Field(default_factory=list)
    objective_count: int = 0
    subjective_count: int = 0
    allowed_types: list[str] = Field(default_factory=list)

    @computed_field
    def paper_pdf(self) -> str:
        return f"/api/download/{self.thread_id}/paper.pdf"

    @computed_field
    def answer_pdf(self) -> str:
        return f"/api/download/{self.thread_id}/answer.pdf"

    @computed_field
    def paper_docx(self) -> str:
        return f"/api/download/{self.thread_id}/paper.docx"
