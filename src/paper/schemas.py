from typing import Literal, Optional
from pydantic import Field, BaseModel

from src.paper.models import PaperRequest, QuestionTypes, DifficultyDistribution


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


