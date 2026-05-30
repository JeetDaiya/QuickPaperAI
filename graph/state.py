from typing import TypedDict, Annotated
from models.schemas import Question, PaperRequest
import operator


class PaperState(TypedDict):
    paper_request: PaperRequest
    all_questions: Annotated[list[Question], operator.add]
    selected_questions: list[Question]

class ChapterState(TypedDict):
    chapter: str
    subject: str
    objective_count: int
    subjective_count: int
