def first_n_chapter_names(chapters: list[str], n: int) -> list[str]:
    """Chapter names in this DB are plain integer strings (e.g. "1", "2") in textbook order,
    so the lowest n numbers are the first n chapters of the subject."""
    return sorted(set(chapters), key=int)[:n]
