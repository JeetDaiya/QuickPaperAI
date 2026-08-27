import os
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Send, interrupt

from src.config.prompts import QUESTION_GENERATOR_SCIENCE_SYSTEM_PROMPT, QUESTION_GENERATOR_SYSTEM_SS_PROMPT
from src.config.model_settings import generator_model
from src.paper.compilers.interfaces.interface import DocumentCompiler
from src.paper.formatters.interfaces.interface import PaperFormatter
from src.paper.models import BatchOutput, Question, QuestionTypes, ChapterStatus, DocumentType, SubjectType
from src.paper.rate_limiter import TokenBucket
from src.paper.graph.config import GraphConfig
from src.paper.graph.state import PaperState, ChapterState
from src.paper.graph.tracker import ProgressTracker
from src.paper.graph.utils import clean_latex, group_by_subtopic, build_quota_instructions

rate_limiter = TokenBucket(max_capacity=5, refil_rate=0.0833)


async def question_generator_node(state: ChapterState, config: RunnableConfig) -> dict:
    """Fetches chapter chunks, groups by sub-topic, and generates questions per topic group."""
    question_list: list[Question] = []
    
    chapter = state["chapter"]
    subject = state["subject"]
    objective_count = state["objective_count"]
    subjective_count = state["subjective_count"]
    allowed_types = state["allowed_types"]
    thread_id = state["thread_id"]
    difficulty_distribution = state['difficulty_distribution']

    configurable: GraphConfig = config.get("configurable", {})
    chunk_repo = configurable.get("chunk_repo")
    chapter_chunks = chunk_repo.get_chapter_chunks(subject=subject, chapter=chapter)
    topic_batches = group_by_subtopic(chapter_chunks)

    progress_tracker: ProgressTracker = configurable.get("progress_tracker")
    print(f"[{chapter}] {len(chapter_chunks)} chunks → {len(topic_batches)} topic batches")

    await progress_tracker.update_chapter_progress(
        thread_id=thread_id,
        chapter=chapter,
        status=ChapterStatus.PROCESSING,
        generated_count=0
    )

    quota_instructions = build_quota_instructions(
        objective_count=objective_count,
        subjective_count=subjective_count,
        allowed_types=allowed_types,
        difficulty_distribution=difficulty_distribution
    )

    system_prompt = (
        QUESTION_GENERATOR_SYSTEM_SS_PROMPT 
        if subject == SubjectType.SS or subject == "ss" 
        else QUESTION_GENERATOR_SCIENCE_SYSTEM_PROMPT
    )
    
    generator_prompt = ChatPromptTemplate([
        ("system", system_prompt),
        ("human", (
            "TEXTBOOK CONTENT:\n{formatted_chunks}\n\n"
            "PREVIOUSLY GENERATED QUESTIONS (avoid repeating these):\n{previous_questions}\n\n"
            "REQUIRED QUESTION TYPES TO GENERATE:\n{required_quota_instructions}"
        ))
    ])

    structured_model = generator_model.with_structured_output(schema=BatchOutput)
    generator_chain = generator_prompt | structured_model
    
    for i, batch in enumerate(topic_batches):
        previous_question = (
            "\n".join([q.question_text for q in question_list][-(subjective_count + objective_count):]) 
            if question_list else "None yet"
        )
        
        print(f"  Batch {i+1}/{len(topic_batches)}: {batch['topics']}")
        await rate_limiter.acquire()
        
        await progress_tracker.update_chapter_progress(
            thread_id=thread_id,
            chapter=chapter,
            status=ChapterStatus.PROCESSING,
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

    question_list = [q for q in question_list if q.question_type in allowed_types]

    for q in question_list:
        q.chapter = str(chapter)
        q.question_text = clean_latex(q.question_text)
        if q.options:
            q.options = [clean_latex(opt) for opt in q.options]
        q.correct_answer = clean_latex(q.correct_answer)
        q.answer = clean_latex(q.answer)
        if q.diagram_prompt:
            q.diagram_prompt = clean_latex(q.diagram_prompt)

    await progress_tracker.update_chapter_progress(
        thread_id=thread_id,
        chapter=chapter,
        status=ChapterStatus.COMPLETED,
        generated_count=len(question_list)
    )

    return {"all_questions": question_list}


def router_node(state: PaperState):
    """Takes the list of questions and parallely generates question for each chapter."""
    chapter_list = state["paper_request"].chapters
    subject = state["paper_request"].subject
    objective_count = state["paper_request"].objective_count
    subjective_count = state["paper_request"].subjective_count
    allowed_types = state["paper_request"].allowed_types
    thread_id = state["thread_id"]
    difficulty_distribution = state['paper_request'].difficulty_distribution
    
    return [
        Send(node="question_generator_node", arg={
            "chapter": chapter,
            "subject": subject,
            "objective_count": objective_count,
            "subjective_count": subjective_count,
            "allowed_types": allowed_types,
            "thread_id": thread_id,
            "difficulty_distribution" : difficulty_distribution
        })
        for chapter in chapter_list
    ]


def review_node(state: PaperState):
    """Sends the generated questions for review purposes."""
    selected_questions_indices = interrupt(value={
        "messages": "Here are your generated questions. Please review them to proceed ahead.",
        "questions": [question.model_dump() for question in state["all_questions"]]
    })
    
    if isinstance(selected_questions_indices, dict):
        selected_questions_indices = selected_questions_indices.get("selected_indices", [])

    if not selected_questions_indices:
        raise ValueError("No questions selected. Please select at least one question.")
    
    if not all(isinstance(i, int) for i in selected_questions_indices):
        raise ValueError("Invalid input. Please provide question indices as integers.")
    
    if any(i < 0 or i >= len(state["all_questions"]) for i in selected_questions_indices):
        raise ValueError(f"Index out of range. Valid range: 0 to {len(state['all_questions']) - 1}")
    
    selected_questions = [state["all_questions"][i] for i in selected_questions_indices]
    
    return {"selected_questions": selected_questions}


async def pdf_node(state: PaperState, config: RunnableConfig):
    """Generates the pdf from list of selected questions"""
    selected_questions = state["selected_questions"]
    thread_id = state["thread_id"]
    output_dir = f"outputs/{thread_id}"
    os.makedirs(output_dir, exist_ok=True)

    configurable: GraphConfig = config.get("configurable", {})
    paper_request = state["paper_request"]

    document_compiler: DocumentCompiler = configurable.get("document_compiler")
    html_paper_formatter: PaperFormatter = configurable.get("html_paper_formatter")
    markdown_paper_formatter: PaperFormatter = configurable.get("markdown_paper_formatter")

    paper_html = html_paper_formatter.render_paper(paper_request=paper_request, questions=selected_questions)
    answer_html = html_paper_formatter.render_answer_key(paper_request=paper_request, questions=selected_questions)
    paper_md = markdown_paper_formatter.render_paper(paper_request=paper_request, questions=selected_questions)

    try:
        await document_compiler.generate_pdf(
            paper_html=paper_html,
            answer_html=answer_html,
            paper_output_path=f'{output_dir}/{DocumentType.PAPER_PDF}',
            answer_output_path=f'{output_dir}/{DocumentType.ANSWER_PDF}'
        )
    except Exception as e:
        print(f"[ERROR] Critical Failure: Failed to generate PDF documents: {e}")
        raise e

    try:
        await document_compiler.generate_docx(
            markdown=paper_md,
            output_path=f'{output_dir}/{DocumentType.PAPER_DOCX}',
        )
    except Exception as e:
        print(f"[WARN] Soft Failure: Failed to generate DOCX document (continuing gracefully): {e}")
