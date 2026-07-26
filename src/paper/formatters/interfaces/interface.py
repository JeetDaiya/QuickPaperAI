from abc import ABC, abstractmethod
from src.paper.models import Question, PaperRequest


class PaperFormatter(ABC):
    @abstractmethod
    def render_paper(self, paper_request: PaperRequest, questions: list[Question]) -> str:
        pass

    @abstractmethod
    def render_answer_key(self, paper_request: PaperRequest, questions: list[Question]) -> str:
        pass
