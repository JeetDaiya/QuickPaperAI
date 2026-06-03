from core.graph.state import PaperState, ChapterState
from core.config.prompts import QUESTION_GENERATOR_SCIENCE_SYSTEM_PROMPT, QUESTION_GENERATOR_SYSTEM_SS_PROMPT
from core.config.settings import generator_model
from core.models.schemas import BatchOutput, Question
from core.db.db import get_chapter_chunks
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Send, interrupt
from core.pdf.generator import generate_paper_html, generate_answer_html, generate_pdf, generate_docx
from core.config.rate_limiter import TokenBucket
from core.graph.tracker import update_chapter_progress, get_chapter_progress
import os

generator_model = generator_model.with_structured_output(schema=BatchOutput)
rate_limiter = TokenBucket(max_capacity=5, refil_rate=0.0833)


def format_batch(chunks: list[dict]) -> str:
    "Takes the chunks and formats them for input"
    sections = []
    for i, chunk in enumerate(chunks, 1):
        sections.append(f"--- Chunk {i} ---\n{chunk['content']}")
    return "\n\n".join(sections)


def group_by_subtopic(chunks: list[dict], min_chars: int = 1500) -> list[dict]:
    """
    Groups chunks by sub_topic. Merges small sub-topics together 
    until the combined content exceeds min_chars.
    
    Returns a list of dicts: [{"topics": ["topic1", "topic2"], "content": "..."}]
    """
    from collections import OrderedDict

    
    # Step 1: Group chunks by sub_topic (preserving order)
    topic_groups = OrderedDict()
    for chunk in chunks:
        topic = chunk.get("sub_topic", "General") or "General"
        if topic not in topic_groups:
            topic_groups[topic] = []
        topic_groups[topic].append(chunk["content"])
    
    # Step 2: Merge small groups together
    batches = []
    current_topics = []
    current_content = ""
    
    for topic, contents in topic_groups.items():
        topic_text = f"--- {topic} ---\n" + "\n\n".join(contents)
        
        if len(current_content) + len(topic_text) < min_chars:
            # Too small — merge with current batch
            current_topics.append(topic)
            current_content += "\n\n" + topic_text
        else:
            # Save current batch if it exists
            if current_content.strip():
                batches.append({
                    "topics": current_topics,
                    "content": current_content.strip()
                })
            # Start new batch
            current_topics = [topic]
            current_content = topic_text
    
    # Don't forget the last batch
    if current_content.strip():
        batches.append({
            "topics": current_topics,
            "content": current_content.strip()
        })
    
    return batches



def clean_latex(text: str) -> str:
    if not isinstance(text, str):
        return text
    return text.replace('\r', '\\r').replace('\t', '\\t')


async def question_generator_node(state: ChapterState) -> dict:
    """
    Fetches chapter chunks, groups by sub-topic, and generates questions per topic group.
    """
    from core.models.schemas import QuestionTypes
    question_list : list[Question] = []
    
    chapter = state["chapter"]
    subject = state["subject"]
    objective_count = state["objective_count"]
    subjective_count = state["subjective_count"]
    allowed_types = state["allowed_types"]
    thread_id = state["thread_id"]
    
    allowed_objective_types = [t for t in allowed_types if t.is_objective]
    allowed_subjective_types = [t for t in allowed_types if t.is_subjective]
    
    chapter_chunks = get_chapter_chunks(subject=subject, chapter=chapter)
    topic_batches = group_by_subtopic(chapter_chunks)
    
    print(f"[{chapter}] {len(chapter_chunks)} chunks → {len(topic_batches)} topic batches")

    update_chapter_progress(
        thread_id=state["thread_id"],
        chapter=chapter,
        status="processing",
        generated_count=0
    )
    
    # ── Formulate dynamic quota instructions to preserve variance and coverage ──
    subjective_breakdown_str = ""
    if subjective_count > 0 and allowed_subjective_types:
        # Check if we have the standard balanced combination (all three subjective types allowed)
        has_all_subj = all(t in allowed_subjective_types for t in [QuestionTypes.TWO_MARK_ANS, QuestionTypes.THREE_MARK_ANS, QuestionTypes.FOUR_MARK_ANS])
        if has_all_subj:
            # Calculate strict quotas in Python (LLMs are bad at math, do it for them)
            four_mark_count = max(1, subjective_count // 3) if subjective_count >= 3 else 0
            three_mark_count = max(1, (subjective_count - four_mark_count) // 2) if subjective_count >= 2 else (1 if subjective_count == 1 else 0)
            two_mark_count = subjective_count - four_mark_count - three_mark_count

            subjective_breakdown_str = (
                f"EXACT DISTRIBUTION REQUIRED:\n"
                f"- Exactly {four_mark_count} questions MUST be 4_MARKS (Long Answer/Case Study)\n"
                f"- Exactly {three_mark_count} questions MUST be 3_MARKS (System/Process Explanations)\n"
                f"- Exactly {two_mark_count} questions MUST be 2_MARKS (Differences/Short Conceptual)\n"
            )
        else:
            # Option B: Let LLM choose between custom subjective subset
            allowed_subj_values = ", ".join(t.value for t in allowed_subjective_types)
            subjective_breakdown_str = (
                f"EXACT DISTRIBUTION REQUIRED:\n"
                f"You MUST generate exactly {subjective_count} subjective questions choosing ONLY from these allowed types: {allowed_subj_values}."
            )

    # Now build your final prompt strings
    allowed_obj_values = ", ".join(t.value for t in allowed_objective_types) if allowed_objective_types else ""
    if objective_count > 0 and subjective_count > 0:
        quota_instructions = (
            f"Please generate EXACTLY {objective_count} objective questions using ONLY these allowed types: {allowed_obj_values} and "
            f"EXACTLY {subjective_count} subjective questions based strictly on this textbook content. "
            f"Ensure all topics are covered evenly.\n\n{subjective_breakdown_str}"
        )
    elif objective_count > 0:
        quota_instructions = (
            f"Please generate EXACTLY {objective_count} objective questions using ONLY these allowed types: {allowed_obj_values} based strictly "
            "on this textbook content. Do NOT generate any subjective questions."
        )
    elif subjective_count > 0:
        quota_instructions = (
            f"Please generate EXACTLY {subjective_count} subjective questions based strictly on this textbook content. "
            f"Do NOT generate any objective questions.\n\n{subjective_breakdown_str}"
        )
    else:
        allowed_all_values = ", ".join(t.value for t in allowed_types)
        quota_instructions = (
            f"Please generate 2-3 standard-compliant questions based strictly on this textbook content. "
            f"You are strictly allowed to generate only these question types: {allowed_all_values}."
        )

    if subject == "ss":
        system_prompt = QUESTION_GENERATOR_SYSTEM_SS_PROMPT
    else :
        system_prompt = QUESTION_GENERATOR_SCIENCE_SYSTEM_PROMPT
    
    generator_prompt = ChatPromptTemplate([
        ("system", system_prompt),
        ("human", (
            "TEXTBOOK CONTENT:\n{formatted_chunks}\n\n"
            "PREVIOUSLY GENERATED QUESTIONS (avoid repeating these):\n{previous_questions}\n\n"
            "REQUIRED QUESTION TYPES TO GENERATE:\n{required_quota_instructions}"
        ))
    ])

    generator_chain = generator_prompt | generator_model
    
    for i, batch in enumerate(topic_batches):
        previous_question = "\n".join([q.question_text for q in question_list][-(subjective_count+objective_count):]) if question_list else "None yet"
        
        print(f"  Batch {i+1}/{len(topic_batches)}: {batch['topics']}")
        
        await rate_limiter.acquire()
        update_chapter_progress(
            thread_id=thread_id,
            chapter=chapter,
            status="processing",
            generated_count=len(question_list)
        )
        try:
            batch_output = await generator_chain.ainvoke({
                "formatted_chunks": batch["content"],
                "previous_questions": previous_question,
                "required_quota_instructions": quota_instructions
            })
            question_list.extend(batch_output.question_list)

        except Exception as e:
            print(f"  ⚠️ Batch {i+1} failed, skipping: {e}")
    
        

    # ── Post-generation dynamic filtering (Option B Enforcer) ──
    question_list = [q for q in question_list if q.question_type in allowed_types]

    # ── Post-process to fix LaTeX carriage return/tab JSON decoding issues system-wide ──
    for q in question_list:
        q.chapter = str(chapter)
        q.question_text = clean_latex(q.question_text)
        if q.options:
            q.options = [clean_latex(opt) for opt in q.options]
        q.correct_answer = clean_latex(q.correct_answer)
        q.answer = clean_latex(q.answer)
        if q.diagram_prompt:
            q.diagram_prompt = clean_latex(q.diagram_prompt)


    update_chapter_progress(
        thread_id=thread_id,
        chapter=chapter,
        status="completed",
        generated_count=len(question_list)
    )

    return {
        "all_questions" : question_list
    }
    

def router_node(state: PaperState):
    """Takes the list of questions and parallely generates question for each chapter."""
    chapter_list = state["paper_request"].chapters
    subject = state["paper_request"].subject
    objective_count = state["paper_request"].objective_count
    subjective_count = state["paper_request"].subjective_count
    allowed_types = state["paper_request"].allowed_types
    thread_id = state["thread_id"]
    
    return [
        Send(node="question_generator_node", arg={
            "chapter": chapter,
            "subject": subject,
            "objective_count": objective_count,
            "subjective_count": subjective_count,
            "allowed_types": allowed_types,
            "thread_id" : thread_id
        })
        for chapter in chapter_list
    ]
    
def review_node(state: PaperState):
    """Sends the generated questions for review purposes."""
    
    selected_questions_indices = interrupt(value={
        "messages": "Here are your generated questions. Please review them to proceed ahead.",
        "questions": [question.model_dump() for question in state["all_questions"]]
    })
    
    # Validate teacher's input
    if not selected_questions_indices:
        raise ValueError("No questions selected. Please select at least one question.")
    
    if not all(isinstance(i, int) for i in selected_questions_indices):
        raise ValueError("Invalid input. Please provide question indices as integers.")
    
    if any(i < 0 or i >= len(state["all_questions"]) for i in selected_questions_indices):
        raise ValueError(f"Index out of range. Valid range: 0 to {len(state['all_questions']) - 1}")
    
    selected_questions = [state["all_questions"][i] for i in selected_questions_indices]
    
    return {
        "selected_questions": selected_questions
    }

    
    

def pdf_node(state: PaperState):
    """Generates the pdf from list of selected questions"""
    selected_questions = state["selected_questions"]
    
    thread_id = state["thread_id"]
    output_dir = f"outputs/{thread_id}"
    os.makedirs(output_dir, exist_ok=True)
    
    paper_html = generate_paper_html(paper_request=state["paper_request"], selected_questions=selected_questions)
    answer_html = generate_answer_html(paper_request=state["paper_request"], selected_questions=selected_questions)

    # 1. Compile PDFs (Critical)
    try:
        generate_pdf(
            paper_string=paper_html, 
            answer_string=answer_html, 
            answer_output_path=f'{output_dir}/answer.pdf', 
            paper_output_path=f'{output_dir}/paper.pdf'
        )
    except Exception as e:
        print(f"❌ Critical Failure: Failed to generate PDF documents: {e}")
        raise e
        
    # 2. Compile DOCX (Soft Isolation - non-critical)
    try:
        generate_docx(
            selected_questions=selected_questions, 
            paper_request=state["paper_request"], 
            output_path=f'{output_dir}/paper.docx'
        )
    except Exception as e:
        print(f"⚠️ Soft Failure: Failed to generate DOCX document (continuing gracefully): {e}")
    
    
    
    
    
    
    
    
    
    
    
    
    
    







