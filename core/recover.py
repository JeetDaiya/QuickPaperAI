import asyncio
import os
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command

from core.graph.builder import graph

# You MUST use the exact same thread_id that crashed!
CRASHED_THREAD_ID = "thread_12"
config = {"configurable": {"thread_id": CRASHED_THREAD_ID}, "max_concurrency": 2}

async def recover_session():
    print(f"🚑 Attempting to recover session: {CRASHED_THREAD_ID}")
    
    async with AsyncConnectionPool(
        conninfo=os.getenv("DB_URI"),
        max_size=5,
        kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": None}
    ) as pool: 
        
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        agent = graph.compile(checkpointer=checkpointer)
        
        # 1. Fetch the exact state from Supabase where the graph crashed
        snapshot = await agent.aget_state(config)
        
        # Check if there is actually a pending interrupt to recover
        if not snapshot.tasks or not snapshot.tasks[0].interrupts:
            print("❌ No pending interrupts found for this thread. It might have already finished.")
            return

        # 2. Extract the saved questions from the database blob
        interrupt_value = snapshot.tasks[0].interrupts[0].value
        questions = interrupt_value["questions"]
        
        print("\n✅ Session successfully recovered from Supabase!")
        print(f"{'='*60}")
        print(f"Recovered {len(questions)} questions. Select which to keep:\n")
        
        # 3. Reprint the questions so you know what you are approving
        for i, q in enumerate(questions):
            print(f"  [{i}] ({q['question_type']}) {q['question_text'][:80]}...")
            
        # 4. Ask for input again
        picks = input("\nEnter indices to approve (comma-separated): ")
        selected = [int(x.strip()) for x in picks.split(",")]
        
        # 5. Resume the graph normally
        print("\n🚀 Resuming execution...")
        final = await agent.ainvoke(Command(resume=selected), config)
        
        print("\nDone! Exam paper saved to output.pdf")

if __name__ == "__main__":
    asyncio.run(recover_session())