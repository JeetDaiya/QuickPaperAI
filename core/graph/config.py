from typing import TypedDict

from core.graph.tracker import ProgressTracker
from core.interfaces.db import ChunkRepository
from core.interfaces.paper_formatter import  PaperFormatter
from core.interfaces.document_compiler import  DocumentCompiler

class GraphConfig(TypedDict):
    chunk_repo : ChunkRepository
    html_paper_formatter : PaperFormatter
    markdown_paper_formatter : PaperFormatter
    document_compiler : DocumentCompiler
    progress_tracker : ProgressTracker
