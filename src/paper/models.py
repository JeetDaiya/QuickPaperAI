import re

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, Optional
from enum import StrEnum

class DifficultyDistribution(BaseModel):
    easy: int
    medium: int
    hard: int


    @model_validator(mode='after')
    def verify_total(self):
        total = self.easy + self.medium + self.hard
        if total != 100:
            raise ValueError('Difficulty distribution should sum to hundred')
        return self

class ChapterStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(StrEnum):
    PAPER_PDF = "paper.pdf"
    ANSWER_PDF = "answer.pdf"
    PAPER_DOCX = "paper.docx"


GENERATED_DOCUMENT_TYPES = (DocumentType.PAPER_PDF, DocumentType.ANSWER_PDF, DocumentType.PAPER_DOCX)


class SubjectType(StrEnum):
    SCIENCE = "science"
    SS = "ss"


class PaperDifficulty(StrEnum):
    EASY = "Easy"
    BALANCED = "Balanced"
    HARD = "Hard"
    MEDIUM = 'Medium'


class QuestionDistribution(BaseModel):
    question_difficulty : PaperDifficulty
    question_count : int



class QuestionTypes(StrEnum):
    FOUR_MARK_ANS = "4_MARKS"
    THREE_MARK_ANS = "3_MARKS"
    TWO_MARK_ANS = "2_MARKS"
    FILL_IN_THE_BLANK = "FILL_IN_THE_BLANK"
    MATCH_THE_COLUMN = "MATCH_THE_COLUMN"
    MCQ = "MCQ"
    TRUE_FALSE = "TRUE_FALSE"
    ONE_WORD_ANS = "ONE_WORD_ANS"
    
    @property
    def is_objective(self) -> bool:
        return self in (
            QuestionTypes.MCQ,
            QuestionTypes.FILL_IN_THE_BLANK,
            QuestionTypes.MATCH_THE_COLUMN,
            QuestionTypes.TRUE_FALSE,
            QuestionTypes.ONE_WORD_ANS
        )
        
    @property
    def is_subjective(self) -> bool:
        return self in (
            QuestionTypes.TWO_MARK_ANS,
            QuestionTypes.THREE_MARK_ANS,
            QuestionTypes.FOUR_MARK_ANS
        )


class PaperRequest(BaseModel):
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
    difficulty_distribution : Optional[DifficultyDistribution] = Field(default_factory= lambda: DifficultyDistribution(easy=30 , medium=50, hard=20))

    @model_validator(mode="after")
    def validate_counts_and_types(self) -> "PaperRequest":
        allowed_obj = [t for t in self.allowed_types if t.is_objective]
        allowed_subj = [t for t in self.allowed_types if t.is_subjective]
        
        if self.objective_count > 0 and not allowed_obj:
            raise ValueError(
                f"objective_count is {self.objective_count}, but allowed_types contains no objective question types."
            )
            
        if self.subjective_count > 0 and not allowed_subj:
            raise ValueError(
                f"subjective_count is {self.subjective_count}, but allowed_types contains no subjective question types."
            )
            
        return self


class EvaluationPoint(BaseModel):
    point_text: str = Field(description="Actionable grading criteria point.")
    allocated_marks: int = Field(description="Marks allocated for this grading point.")


# A LaTeX command whose name starts with one of these letters collides with a single-character
# JSON escape, so an under-escaped `\frac` arrives as a real formfeed followed by "rac". Mapping
# the control character back to its two-character form recovers the command.
# `\n` is deliberately absent: a real newline is legitimate in answers and evaluation points, so
# there's no way to tell a corrupted `\nu` from an intentional line break.
_CONTROL_CHAR_REPAIRS = {
    "\r": r"\r",   # \rightarrow, \rho
    "\t": r"\t",   # \theta, \times
    "\f": r"\f",   # \frac, \forall
    "\b": r"\b",   # \beta, \begin
}


def _canonicalize_latex(text: str) -> str:
    """Normalizes LLM LaTeX to single-backslash form, whichever way it was mangled.

    Repairs must run before the collapse: they produce single backslashes, so doing it the other
    way round would leave recovered commands untouched. The lookahead keeps a genuine LaTeX line
    break (`\\` before whitespace or end of string) intact while collapsing `\\text` to `\text`.
    """
    if not isinstance(text, str):
        return text

    for char, repair in _CONTROL_CHAR_REPAIRS.items():
        text = text.replace(char, repair)

    return re.sub(r"\\{2,}(?=[A-Za-z])", r"\\", text)


class Question(BaseModel):
    question_text: str
    question_type: QuestionTypes
    chapter: str
    marks: int
    difficulty: PaperDifficulty = Field(description="Cognitive difficulty of this specific question: Easy, Medium, or Hard.")
    options: list[str] = Field(default=[], description="List of options if MCQ.")
    correct_answer: str
    answer: str
    evaluation_scheme: list[EvaluationPoint] = Field(default=[], description="Detailed grading breakdown for subjective questions.")
    diagram_prompt: Optional[str] = Field(default=None, description="Detailed image generation prompt for the diagram, if this question is diagram-based.")

    @field_validator("options", mode="before")
    @classmethod
    def convert_options(cls, v):
        if isinstance(v, dict):
            return list(v.values())
        if v is None:
            return []
        return v

    @field_validator("difficulty", mode="before")
    @classmethod
    def normalize_difficulty(cls, v):
        if isinstance(v, str):
            return v.strip().capitalize()
        return v
        
    @model_validator(mode="after")
    def normalize_question(self) -> "Question":
        self.question_text = _canonicalize_latex(self.question_text)
        self.options = [_canonicalize_latex(opt) for opt in self.options]
        self.correct_answer = _canonicalize_latex(self.correct_answer)
        self.answer = _canonicalize_latex(self.answer)
        if self.diagram_prompt:
            self.diagram_prompt = _canonicalize_latex(self.diagram_prompt)
        for pt in self.evaluation_scheme:
            pt.point_text = _canonicalize_latex(pt.point_text)

        if self.question_type.is_subjective:
            # Subjective marks are fully determined by the type — correct a mismatch instead of
            # failing, and keep the marking scheme summing to the corrected total.
            expected_marks = {
                QuestionTypes.TWO_MARK_ANS: 2,
                QuestionTypes.THREE_MARK_ANS: 3,
                QuestionTypes.FOUR_MARK_ANS: 4,
            }.get(self.question_type)

            if expected_marks is not None:
                self.marks = expected_marks

                if self.evaluation_scheme:
                    total_scheme_marks = sum(pt.allocated_marks for pt in self.evaluation_scheme)
                    if total_scheme_marks != self.marks:
                        base = max(1, self.marks // len(self.evaluation_scheme))
                        for pt in self.evaluation_scheme:
                            pt.allocated_marks = base
                        remainder = self.marks - base * len(self.evaluation_scheme)
                        self.evaluation_scheme[0].allocated_marks += remainder

        return self


class BatchOutput(BaseModel):
    question_list: list[Question] = Field(
        default=[],
        description="List of questions generated."
    )