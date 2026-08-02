from collections import OrderedDict
from src.paper.models import QuestionTypes


def clean_latex(text: str) -> str:
    if not isinstance(text, str):
        return text
    return text.replace('\r', '\\r').replace('\t', '\\t')


def format_batch(chunks: list[dict]) -> str:
    """Takes the chunks and formats them for prompt input"""
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
    topic_groups = OrderedDict()
    for chunk in chunks:
        topic = chunk.get("sub_topic", "General") or "General"
        if topic not in topic_groups:
            topic_groups[topic] = []
        topic_groups[topic].append(chunk["content"])
    
    batches = []
    current_topics = []
    current_content = ""

    for topic, contents in topic_groups.items():
        topic_text = f"--- {topic} ---\n" + "\n\n".join(contents)
        
        if len(current_content) + len(topic_text) < min_chars:
            current_topics.append(topic)
            current_content += "\n\n" + topic_text
        else:
            if current_content.strip():
                batches.append({
                    "topics": current_topics,
                    "content": current_content.strip()
                })
            current_topics = [topic]
            current_content = topic_text
    
    if current_content.strip():
        batches.append({
            "topics": current_topics,
            "content": current_content.strip()
        })
    
    return batches


def build_quota_instructions(
    objective_count: int,
    subjective_count: int,
    allowed_types: list
) -> str:
    """Formulates dynamic quota prompt instructions to preserve variance and coverage."""
    typed_allowed_types: list[QuestionTypes] = []
    for t in allowed_types or []:
        if isinstance(t, QuestionTypes):
            typed_allowed_types.append(t)
        elif isinstance(t, str):
            try:
                typed_allowed_types.append(QuestionTypes(t))
            except ValueError:
                try:
                    typed_allowed_types.append(QuestionTypes[t.upper()])
                except (KeyError, AttributeError):
                    pass

    allowed_objective_types = [t for t in typed_allowed_types if t.is_objective]
    allowed_subjective_types = [t for t in typed_allowed_types if t.is_subjective]

    subjective_breakdown_str = ""
    if subjective_count > 0 and allowed_subjective_types:
        has_all_subj = all(
            t in allowed_subjective_types for t in [
                QuestionTypes.TWO_MARK_ANS,
                QuestionTypes.THREE_MARK_ANS,
                QuestionTypes.FOUR_MARK_ANS
            ]
        )
        if has_all_subj:
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
            allowed_subj_values = ", ".join(t.value for t in allowed_subjective_types)
            subjective_breakdown_str = (
                f"EXACT DISTRIBUTION REQUIRED:\n"
                f"You MUST generate exactly {subjective_count} subjective questions choosing ONLY from these allowed types: {allowed_subj_values}."
            )

    allowed_obj_values = ", ".join(t.value for t in allowed_objective_types) if allowed_objective_types else ""
    
    if objective_count > 0 and subjective_count > 0:
        return (
            f"Please generate EXACTLY {objective_count} objective questions using ONLY these allowed types: {allowed_obj_values} and "
            f"EXACTLY {subjective_count} subjective questions based strictly on this textbook content. "
            f"Ensure all topics are covered evenly.\n\n{subjective_breakdown_str}"
        )
    elif objective_count > 0:
        return (
            f"Please generate EXACTLY {objective_count} objective questions using ONLY these allowed types: {allowed_obj_values} based strictly "
            "on this textbook content. Do NOT generate any subjective questions."
        )
    elif subjective_count > 0:
        return (
            f"Please generate EXACTLY {subjective_count} subjective questions based strictly on this textbook content. "
            f"Do NOT generate any objective questions.\n\n{subjective_breakdown_str}"
        )
    else:
        allowed_all_values = ", ".join(t.value for t in typed_allowed_types)
        return (
            f"Please generate 2-3 standard-compliant questions based strictly on this textbook content. "
            f"You are strictly allowed to generate only these question types: {allowed_all_values}."
        )
