from core.graph.state import PaperState
from langgraph.graph.state import CompiledStateGraph

async def run_graph(agent: CompiledStateGraph, paper_state: PaperState, dependencies: dict):
    thread_id = paper_state['thread_id']
    config = {
        "configurable" : {
            "thread_id" : thread_id,
            **dependencies
        },
        "max_concurrency" : 3
    }
    
    return await agent.ainvoke(config=config, input=paper_state)
