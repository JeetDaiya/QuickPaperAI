from langgraph.graph import StateGraph, START, END

from src.exception.global_exception_handler import AppError
from src.exception.exceptions import TransientError
from src.paper.graph.config import GraphConfig
from src.paper.graph.state import PaperState
from src.paper.graph.nodes import question_generator_node, router_node, review_node, pdf_node

from langgraph.types import RetryPolicy


def _node_retry_on(exc: Exception) -> bool:
    # Our own exception hierarchy explicitly marks what's retryable (TransientError) vs
    # permanent (NotFoundError, ValidationError_, etc.) — trust that classification instead
    # of retrying every AppError indiscriminately.
    if isinstance(exc, AppError):
        return isinstance(exc, TransientError)
    return not isinstance(exc, (ValueError, TypeError, LookupError, NameError, SyntaxError))


graph = StateGraph(state_schema=PaperState, context_schema=GraphConfig)
graph.add_node("distribute", lambda state: {})  # pass-through to initialize state
graph.add_node(
    "question_generator_node",
    question_generator_node,
    retry=RetryPolicy(max_attempts=3, initial_interval=2.0, backoff_factor=2.0, jitter=True, retry_on=_node_retry_on)
)
graph.add_node("review_node", review_node)
graph.add_node("pdf_node", pdf_node)

graph.add_edge(START, "distribute")
graph.add_conditional_edges(
    "distribute",
    router_node,
    ["question_generator_node"]
)
graph.add_edge("question_generator_node", "review_node")
graph.add_edge("review_node", "pdf_node")
graph.add_edge("pdf_node", END)

