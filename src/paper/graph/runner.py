1
from typing import Optional
from src.paper.graph.state import PaperState
from langgraph.graph.state import CompiledStateGraph
from langchain_core.runnables import RunnableConfig

async def run_graph(
    agent: CompiledStateGraph,
    paper_state: Optional[PaperState],
    dependencies: dict,
    thread_id: Optional[str] = None
):
    actual_thread_id = thread_id or (paper_state.get('thread_id') if isinstance(paper_state, dict) else None)
    if not actual_thread_id:
        raise ValueError("thread_id must be provided in paper_state or as thread_id argument to run_graph.")

    config = RunnableConfig(
        configurable={
            "thread_id": actual_thread_id,
            **dependencies
        },
        max_concurrency=3
    )
    
    return await agent.ainvoke(config=config, input=paper_state)

