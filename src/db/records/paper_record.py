from typing import Optional, Union
from pydantic import BaseModel
from enum import StrEnum, auto

from src.paper.models import PaperRequest, DocumentType, DifficultyDistribution


class Status(StrEnum):
    GENERATING = auto()
    FAILED = auto()
    SUCCESS = auto()
    SAVED = auto()
    CANCELED = auto()



class PaperRecord(BaseModel):
    thread_id: str
    user_id: str
    status: Status

    # Populated at creation (from PaperRequest)
    institution_name: Optional[str] = None
    subject: Optional[str] = None
    standard: Optional[str] = None
    difficulty: Optional[str] = None
    difficulty_distribution: Optional[Union[DifficultyDistribution, dict]] = None
    chapters: Optional[list[str]] = None
    objective_count: Optional[int] = None
    subjective_count: Optional[int] = None
    allowed_types: Optional[list[str]] = None

    # Populated after compilation (by save_to_cloud)
    paper_pdf_path: Optional[str] = None
    answer_pdf_path: Optional[str] = None
    paper_docx_path: Optional[str] = None

    @classmethod
    def from_request(
        cls,
        thread_id: str,
        user_id: str,
        paper_request: PaperRequest,
        status: Status = Status.GENERATING,
        file_paths: Optional[dict[str, str]] = None
    ) -> "PaperRecord":
        file_paths = file_paths or {}
        allowed_types_serialized = [
            t.value if hasattr(t, "value") else str(t) for t in (paper_request.allowed_types or [])
        ]
        diff_dist = (
            paper_request.difficulty_distribution.model_dump()
            if hasattr(paper_request.difficulty_distribution, "model_dump")
            else paper_request.difficulty_distribution
        )
        return cls(
            thread_id=thread_id,
            user_id=user_id,
            status=status,
            chapters=paper_request.chapters,
            subject=paper_request.subject,
            standard=paper_request.standard,
            difficulty=paper_request.difficulty,
            difficulty_distribution=diff_dist,
            institution_name=paper_request.institution_name,
            subjective_count=paper_request.subjective_count,
            objective_count=paper_request.objective_count,
            allowed_types=allowed_types_serialized,
            paper_pdf_path=file_paths.get(DocumentType.PAPER_PDF),
            answer_pdf_path=file_paths.get(DocumentType.ANSWER_PDF),
            paper_docx_path=file_paths.get(DocumentType.PAPER_DOCX),
        )

    def to_insert(self) -> dict:
        """For initial creation — only non-None fields."""
        return self.model_dump(exclude_none=True)

    def to_update(self) -> dict:
        """For completion — excludes immutable keys."""
        return self.model_dump(
            exclude_none=True,
            exclude={"thread_id", "user_id"}
        )
