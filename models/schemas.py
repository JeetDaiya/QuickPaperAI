from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, Annotated
from enum import StrEnum
import operator


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


# To store the user input from the form
class PaperRequest(BaseModel):
    institution_name : str
    subject: str
    standard: str
    difficulty: Literal["Easy", "Balanced", "Hard"]
    chapters : list[str]
    objective_count: int = Field(default=0, description="Total number of objective questions to generate.")
    subjective_count: int = Field(default=0, description="Total number of subjective questions to generate.")
    
        
class Question(BaseModel):
    question_text : str
    question_type : QuestionTypes
    chapter : str
    marks : int
    options : Optional[list[str]]
    correct_answer : str
    answer : str
    
    @field_validator("options", mode="before")
    @classmethod
    def convert_options(cls, v):
        if isinstance(v, dict):
            return list(v.values())
        return v
        


class BatchOutput(BaseModel):
    question_list : list[Question] = Field(
        default=[],
        description="List of questions generated.",
        min_length=1,
        max_length=20
)