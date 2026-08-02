import asyncio
import uuid
from langgraph.types import Command
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

from src.paper.graph.builder import graph
from src.paper.models import QuestionTypes, PaperRequest
from src.base_settings import settings
config = {"configurable": {"thread_id": str(uuid.uuid4())}, "max_concurrency": 3}


async def run_agent():
    print("=" * 60)
    print("🤖 Paper Generator CLI 🤖")
    print("=" * 60)
    
    async with AsyncConnectionPool(
        conninfo=settings.DB_URI,
        max_size=20,
        kwargs={
            "autocommit": True,
            "row_factory": dict_row,
            "prepare_threshold": None
        }
    ) as pool: 
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        
        agent = graph.compile(checkpointer=checkpointer)
        
        request = PaperRequest(
            subject="science",
            standard="10",
            institution_name="Test Balanced School",
            difficulty="Balanced",
            chapters=["1"],
            objective_count=5,
            subjective_count=3,
            allowed_types=list(QuestionTypes)
        )
        
        result = await agent.ainvoke({"paper_request": request}, config)
        
        snapshot = await agent.aget_state(config)
        interrupt_value = snapshot.tasks[0].interrupts[0].value
        questions = interrupt_value["questions"]
        print(f"\n{'='*60}")
        print(f"Generated {len(questions)} questions. Select which to keep:\n")
        for i, q in enumerate(questions):
            print(f"  [{i}] ({q['question_type']}) {q['question_text'][:80]}...")
        
        picks = input("\nEnter indices (comma-separated) or 'all' to select all: ")
        if picks.strip().lower() == "all":
            selected = list(range(len(questions)))
        else:
            selected = [int(x.strip()) for x in picks.split(",")]
            
        final = await agent.ainvoke(Command(resume=selected), config)
        print("\nDone! Exam paper saved to paper.pdf & paper.docx, and Answer Key saved to answer.pdf")


if __name__ == "__main__":
    asyncio.run(run_agent())