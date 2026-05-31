from typing import TypedDict, Literal


class ChapterProgress(TypedDict):
    chapter : str
    status : Literal["pending", "processing", "completed", "failed"]
    generated_count : int
    
    



PROGRESS_TRACKER : dict[str, dict[str, ChapterProgress]] = {}


def update_chapter_progress(thread_id: str, chapter : str | int, status : Literal["pending", "processing", "completed", "failed"], generated_count : int = 0):
    if thread_id not in PROGRESS_TRACKER:
        PROGRESS_TRACKER[thread_id] = {}

    PROGRESS_TRACKER[thread_id][str(chapter)] = ChapterProgress(
        chapter=str(chapter),
        status=status,
        generated_count=generated_count
    )
    



def get_chapter_progress(thread_id: str) -> dict[str, ChapterProgress]:
    return PROGRESS_TRACKER.get(thread_id, {})
    