from graph.builder import agent
from langgraph.types import Command
from models.schemas import QuestionTypes, PaperRequest

config = {"configurable" : {"thread_id" : "thread_12"}, "max_concurrency" : 2}

def run_agent():
    print("=" * 60)
    print("🤖 Paper Generator 🤖")
    print("=" * 60)
    
    request = PaperRequest(
        subject="science",
        standard="10",
        institution_name="Test School",
        difficulty="Balanced",
        chapters=["5", "1c"],
        question_count={QuestionTypes.MCQ: 5, QuestionTypes.TWO_MARK_ANS: 3}
    )
    
    result = agent.invoke({"paper_request": request}, config)
    
    # ── Show generated questions ──
    snapshot = agent.get_state(config)
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
    final = agent.invoke(Command(resume=selected), config)
    print("\nDone! Exam paper saved to output.pdf and Answer Key saved to output_answers.pdf")
    
if __name__ == "__main__":
    run_agent()