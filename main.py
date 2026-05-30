from graph.builder import graph
from langgraph.types import Command
from models.schemas import QuestionTypes, PaperRequest
from langgraph.checkpoint.memory import MemorySaver
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import os
import asyncio


config = {"configurable" : {"thread_id" : "thread_12"}, "max_concurrency" : 2}

async def run_agent():
    
    print("=" * 60)
    print("🤖 Paper Generator 🤖")
    print("=" * 60)
    
    async with AsyncConnectionPool(
        conninfo=os.getenv("DB_URI"),
        max_size=20,
        kwargs={
            "autocommit" : True,
            "row_factory" : dict_row,
            "prepare_threshold": None
        }
    ) as pool: 
        checkpointer = AsyncPostgresSaver(pool)
        
        await checkpointer.setup()
        
        agent = graph.compile(checkpointer=checkpointer)
        
    
        
        request = PaperRequest(
            subject="science",
            standard="10",
            institution_name="Test School",
            difficulty="Balanced",
            chapters=["1"],
            objective_count=5,
            subjective_count=3
        )
        
        result = await agent.ainvoke({"paper_request": request}, config)
        
        # ── Show generated questions ──
        snapshot = await agent.aget_state(config)
        interrupt_value = snapshot.tasks[0].interrupts[0].value
        questions = interrupt_value["questions"]
        print(f"\n{'='*60}")
        print(f"Generated {len(questions)} questions. Select which to keep:\n")
        for i, q in enumerate(questions):
            print(f"  [{i}] ({q['question_type']}) {q['question_text'][:80]}...")
        # ── Get teacher selection ──
        picks = input("\nEnter indices (comma-separated): ")
        selected = [int(x.strip()) for x in picks.split(",")]
        # ── Resume graph ──
        final = await agent.ainvoke(Command(resume=selected), config)
        print("\nDone! Exam paper saved to output.pdf and Answer Key saved to output_answers.pdf")
        
if __name__ == "__main__":
    asyncio.run(run_agent())