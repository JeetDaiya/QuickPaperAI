from typing import Literal, Optional
from pydantic import Field, BaseModel, model_validator

from src.paper.models import PaperRequest, QuestionTypes, DocumentType, DifficultyDistribution


class PaperGenerateRequest(BaseModel) :
    institution_name: str
    subject: str
    standard: str
    difficulty: Literal["Easy", "Balanced", "Hard"]
    chapters: list[str]
    objective_count: int = Field(default=0, description="Total number of objective questions to generate.")
    subjective_count: int = Field(default=0, description="Total number of subjective questions to generate.")
    allowed_types: list[QuestionTypes] = Field(
        default_factory=lambda: list(QuestionTypes),
        description="List of allowed question types for this paper request."
    )
    difficulty_distribution : Optional[DifficultyDistribution] = Field(description="Distribution of difficulty.")

    def to_domain(self) -> PaperRequest:
        return PaperRequest(
            institution_name=self.institution_name,
            subject=self.subject,
            chapters=self.chapters,
            standard=self.standard,
            difficulty=self.difficulty,
            allowed_types=self.allowed_types,
            objective_count=self.objective_count,
            subjective_count=self.subjective_count,
            difficulty_distribution=self.difficulty_distribution
        )


class PaperHistory(BaseModel):
    id: int
    thread_id: str
    created_at: str
    institution_name: str
    subject: str
    standard: str
    difficulty: Literal["Easy", "Balanced", "Hard"]
    chapters: list[str]
    objective_count: int
    subjective_count: int
    allowed_types: list[str]
    difficulty_distribution: DifficultyDistribution = Field(default_factory=lambda: DifficultyDistribution(easy=30, medium=50, hard=20))


    def to_response(self) -> "PaperHistoryResponse":
        return PaperHistoryResponse(
            chapters=self.chapters,
            allowed_types=self.allowed_types,
            difficulty=self.difficulty,
            objective_count=int(self.objective_count),
            subjective_count=int(self.subjective_count),
            standard=self.standard,
            subject=self.subject,
            institution_name=self.institution_name,
            thread_id=self.thread_id,
            paper_pdf=f"/api/download/{self.thread_id}/{DocumentType.PAPER_PDF}",
            paper_docx=f"/api/download/{self.thread_id}/{DocumentType.PAPER_DOCX}",
            answer_pdf=f"/api/download/{self.thread_id}/{DocumentType.ANSWER_PDF}",
            created_at=self.created_at,
            difficulty_distribution=self.difficulty_distribution
        )


class PaperHistoryResponse(BaseModel):
    thread_id: str
    created_at: str
    institution_name: str
    subject: str
    standard: str
    difficulty: Literal["Easy", "Balanced", "Hard"]
    chapters: list[str]
    objective_count: int
    subjective_count: int
    allowed_types: list[str]
    paper_pdf: str
    paper_docx: str
    answer_pdf: str
    difficulty_distribution: Optional[DifficultyDistribution] = None
