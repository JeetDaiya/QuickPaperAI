from langgraph.graph import StateGraph, START, END
from core.graph.state import PaperState
from core.graph.nodes import question_generator_node, router_node, review_node, pdf_node




from langgraph.types import RetryPolicy

graph = StateGraph(state_schema=PaperState)
graph.add_node("distribute", lambda state: {})  # pass-through to initialize state
graph.add_node(
    "question_generator_node",
    question_generator_node,
    retry=RetryPolicy(max_attempts=3, initial_interval=2.0, backoff_factor=2.0, jitter=True)
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

# checkpointer = MemorySaver()

# agent = graph.compile(checkpointer=checkpointer)