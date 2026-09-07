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
    def normalize_question(self) -> "Question":
        # NOTE: this validator NORMALIZES rather than raises. The LLM returns a whole batch of
        # ~10 questions as one BatchOutput, so if any single question raised here, the entire
        # batch failed to parse and was silently dropped (see nodes.question_generator_node) —
        # producing papers short of the requested count. Since a human reviews and selects
        # questions before the paper is compiled, it's far better to let an imperfect question
        # through to that review screen than to drop ten good ones because of it.
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