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


class Question(BaseModel):
    question_text: str
    question_type: QuestionTypes
    chapter: str
    marks: int
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
        
    @model_validator(mode="after")
    def validate_question_logic(self) -> "Question":
        if self.question_type == QuestionTypes.MCQ:
            if not self.options or len(self.options) != 4:
                raise ValueError("MCQ questions must have exactly 4 options.")
            
            ans = self.correct_answer.strip()
            option_matches = any(ans == opt or opt == ans or ans in opt or opt in ans for opt in self.options)
            prefix_match = any(ans.lower().startswith(f"({c})") or ans.lower().startswith(f"{c})") for c in "abcd")
            if not (option_matches or prefix_match):
                raise ValueError(f"MCQ correct_answer '{self.correct_answer}' does not match any of the options: {self.options}")
        
        if self.question_type.is_subjective:
            expected_marks = {
                QuestionTypes.TWO_MARK_ANS: 2,
                QuestionTypes.THREE_MARK_ANS: 3,
                QuestionTypes.FOUR_MARK_ANS: 4,
            }[self.question_type]
            
            if self.marks != expected_marks:
                raise ValueError(f"Question of type {self.question_type} must have {expected_marks} marks, got {self.marks}")
            
            if self.evaluation_scheme:
                total_scheme_marks = sum(pt.allocated_marks for pt in self.evaluation_scheme)
                if total_scheme_marks != self.marks:
                    raise ValueError(f"Sum of evaluation_scheme marks ({total_scheme_marks}) must equal total question marks ({self.marks})")
        
        return self


class BatchOutput(BaseModel):
    question_list: list[Question] = Field(
        default=[],
        description="List of questions generated."
    )