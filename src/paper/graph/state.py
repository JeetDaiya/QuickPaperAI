from typing import TypedDict, Annotated
import operator
from src.paper.models import Question, PaperRequest, QuestionTypes, DifficultyDistribution


class PaperState(TypedDict):
    paper_request: PaperRequest
    all_questions: Annotated[list[Question], operator.add]
    selected_questions: list[Question]
    thread_id: str


class ChapterState(TypedDict):
    chapter: str
    subject: str
    objective_count: int
    subjective_count: int
    allowed_types: list[QuestionTypes]
    thread_id: str
    difficulty_distribution: DifficultyDistribution
