from typing import TypedDict

from src.paper.graph.tracker import ProgressTracker
from src.db.interfaces.interface import ChunkRepository
from src.paper.formatters.interfaces.interface import  PaperFormatter
from src.paper.compilers.interfaces.interface import  DocumentCompiler

class GraphConfig(TypedDict):
    chunk_repo : ChunkRepository
    html_paper_formatter : PaperFormatter
    markdown_paper_formatter : PaperFormatter
    document_compiler : DocumentCompiler
    progress_tracker : ProgressTracker
