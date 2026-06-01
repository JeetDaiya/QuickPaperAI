from core.graph.builder import graph
from langgraph.types import Command
from core.models.schemas import QuestionTypes, PaperRequest
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import os
import asyncio
import uuid


config = {"configurable" : {"thread_id" : str(uuid.uuid4())}, "max_concurrency" : 3}

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
        
    
        
        # =====================================================================
        # STANDARD BALANCED MODE (Active Default)
        # Allows all objective & subjective question types
        # =====================================================================
        request = PaperRequest(
            subject="science",
            standard="10",
            institution_name="Test Balanced School",
            difficulty="Balanced",
            chapters=["1"],
            objective_count=5,
            subjective_count=3,
            allowed_types=list(QuestionTypes)  # or omit completely to default to all
        )

        # =====================================================================
        # COMMENTED OUT INITIALIZATION EXAMPLES (For Future Reference)
        # =====================================================================
        #
        # 1. MCQ-Only Mode
        # ---------------------------------------------------------------------
        # request = PaperRequest(
        #     subject="science",
        #     standard="10",
        #     institution_name="Test MCQ School",
        #     difficulty="Balanced",
        #     chapters=["1"],
        #     objective_count=6,
        #     subjective_count=0,
        #     allowed_types=[QuestionTypes.MCQ]
        # )
        #
        # 2. Objective-Only Mode (MCQs, Fill-in-the-blanks, Match columns, etc.)
        # ---------------------------------------------------------------------
        # request = PaperRequest(
        #     subject="science",
        #     standard="10",
        #     institution_name="Test Objective School",
        #     difficulty="Balanced",
        #     chapters=["1"],
        #     objective_count=8,
        #     subjective_count=0,
        #     allowed_types=[
        #         QuestionTypes.MCQ,
        #         QuestionTypes.FILL_IN_THE_BLANK,
        #         QuestionTypes.MATCH_THE_COLUMN,
        #         QuestionTypes.TRUE_FALSE,
        #         QuestionTypes.ONE_WORD_ANS
        #     ]
        # )
        
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
        picks = input("\nEnter indices (comma-separated) or 'all' to select all: ")
        if picks.strip().lower() == "all":
            selected = list(range(len(questions)))
        else:
            selected = [int(x.strip()) for x in picks.split(",")]
        # ── Resume graph ──
        final = await agent.ainvoke(Command(resume=selected), config)
        print("\nDone! Exam paper saved to paper.pdf & paper.docx, and Answer Key & Annex saved to answer.pdf")
        
if __name__ == "__main__":
    asyncio.run(run_agent())