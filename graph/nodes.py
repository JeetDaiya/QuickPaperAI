from graph.state import PaperState, ChapterState
from config.prompts import QUESTION_GENERATOR_SYSTEM_PROMPT
from config.settings import generator_model
from models.schemas import BatchOutput, Question
from db.db import get_chapter_chunks
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Send, interrupt
from pdf.generator import generate_paper_html, generate_answer_html, generate_pdf
import time


generator_model = generator_model.with_structured_output(schema=BatchOutput)

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



def question_generator_node(state: ChapterState) -> dict:
    """
    Fetches chapter chunks, groups by sub-topic, and generates questions per topic group.
    """
    
    question_list : list[Question] = []
    
    chapter = state["chapter"]
    subject = state["subject"]
    
    chapter_chunks = get_chapter_chunks(subject=subject, chapter=chapter)
    topic_batches = group_by_subtopic(chapter_chunks)
    
    print(f"[{chapter}] {len(chapter_chunks)} chunks → {len(topic_batches)} topic batches")
    
    generator_prompt = ChatPromptTemplate([
        ("system", QUESTION_GENERATOR_SYSTEM_PROMPT),
        ("human", "TEXTBOOK CONTENT:\n{formatted_chunks}\n\nPREVIOUSLY GENERATED QUESTIONS (avoid repeating these):\n{previous_questions}")
    ])

    generator_chain = generator_prompt | generator_model
    
    for i, batch in enumerate(topic_batches):
        previous_question = "\n".join([q.question_text for q in question_list]) if question_list else "None yet"
        
        print(f"  Batch {i+1}/{len(topic_batches)}: {batch['topics']}")
        
        try:
            batch_output = generator_chain.invoke({
                "formatted_chunks": batch["content"],
                "previous_questions": previous_question
            })
            question_list.extend(batch_output.question_list)
        except Exception as e:
            print(f"  ⚠️ Batch {i+1} failed, skipping: {e}")
        
        time.sleep(5)

    
    return {
        "all_questions" : question_list
    }
    

def router_node(state: PaperState):
    
    """Takes the list of questions and parallely generates question for each chapter."""
    
    chapter_list = state["paper_request"].chapters
    subject = state["paper_request"].subject
    return [
        Send(node="question_generator_node", arg={"chapter": chapter, "subject": subject})
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
    
    paper_html = generate_paper_html(paper_request=state["paper_request"], selected_questions=selected_questions)
    answer_html = generate_answer_html(paper_request=state["paper_request"], selected_questions=selected_questions)

    generate_pdf(paper_string=paper_html, answer_string=answer_html, answer_output_path='answer.pdf', paper_output_path='paper.pdf')
    
    
    
    
    
    
    
    
    
    
    
    
    
    







