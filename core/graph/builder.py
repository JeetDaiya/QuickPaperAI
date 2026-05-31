from langgraph.graph import StateGraph, START, END
from graph.state import PaperState
from graph.nodes import question_generator_node, router_node, review_node, pdf_node




graph = StateGraph(state_schema=PaperState)
graph.add_node("distribute", lambda state: {})  # pass-through to initialize state
graph.add_node("question_generator_node", question_generator_node)
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