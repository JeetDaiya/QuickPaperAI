from abc import  ABC, abstractmethod
from core.models.schemas import Question, PaperRequest

class PaperFormatter(ABC):
    @abstractmethod
    def render_paper(self, paper_request : PaperRequest, questions: list[Question]):
        pass

    @abstractmethod
    def render_answer_key(self, paper_request : PaperRequest, questions: list[Question]):
        pass
