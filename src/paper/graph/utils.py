from collections import OrderedDict
import math
from typing import Optional

from src.paper.models import DifficultyDistribution, QuestionDistribution, PaperDifficulty, QuestionTypes


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


def distribute_difficulty(
    question_type_count: int,
    difficulty_distribution: Optional[DifficultyDistribution] = None
) -> list[QuestionDistribution]:
    if question_type_count <= 0:
        return [
            QuestionDistribution(question_count=0, question_difficulty=PaperDifficulty.EASY),
            QuestionDistribution(question_count=0, question_difficulty=PaperDifficulty.MEDIUM),
            QuestionDistribution(question_count=0, question_difficulty=PaperDifficulty.HARD),
        ]

    dist = difficulty_distribution or DifficultyDistribution(easy=20, medium=50, hard=30)

    easy_count = math.floor(question_type_count * (dist.easy / 100.0))
    medium_count = math.floor(question_type_count * (dist.medium / 100.0))
    hard_count = math.floor(question_type_count * (dist.hard / 100.0))

    dist_map = {
        PaperDifficulty.EASY: easy_count,
        PaperDifficulty.MEDIUM: medium_count,
        PaperDifficulty.HARD: hard_count,
    }

    remaining = question_type_count - (easy_count + medium_count + hard_count)
    order = [PaperDifficulty.MEDIUM, PaperDifficulty.EASY, PaperDifficulty.HARD]
    idx = 0
    while remaining > 0:
        dist_map[order[idx % 3]] += 1
        remaining -= 1
        idx += 1

    return [
        QuestionDistribution(question_count=dist_map[PaperDifficulty.EASY], question_difficulty=PaperDifficulty.EASY),
        QuestionDistribution(question_count=dist_map[PaperDifficulty.MEDIUM], question_difficulty=PaperDifficulty.MEDIUM),
        QuestionDistribution(question_count=dist_map[PaperDifficulty.HARD], question_difficulty=PaperDifficulty.HARD),
    ]


def build_quota_instructions(
    objective_count: int,
    subjective_count: int,
    allowed_types: list,
    difficulty_distribution: Optional[DifficultyDistribution] = None
) -> str:
    """Formulates dynamic quota prompt instructions including difficulty band targets."""
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

    # Partition difficulty bands for objective & subjective counts
    obj_dist = distribute_difficulty(objective_count, difficulty_distribution) if objective_count > 0 else []
    subj_dist = distribute_difficulty(subjective_count, difficulty_distribution) if subjective_count > 0 else []

    obj_map = {qd.question_difficulty: qd.question_count for qd in obj_dist}
    subj_map = {qd.question_difficulty: qd.question_count for qd in subj_dist}

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
                f"EXACT MARKS DISTRIBUTION REQUIRED:\n"
                f"- Exactly {four_mark_count} question{'s' if four_mark_count != 1 else ''} MUST be 4_MARKS (Long Answer/Case Study)\n"
                f"- Exactly {three_mark_count} question{'s' if three_mark_count != 1 else ''} MUST be 3_MARKS (System/Process Explanations)\n"
                f"- Exactly {two_mark_count} question{'s' if two_mark_count != 1 else ''} MUST be 2_MARKS (Differences/Short Conceptual)"
            )
        else:
            allowed_subj_values = ", ".join(t.value for t in allowed_subjective_types)
            subjective_breakdown_str = (
                f"EXACT MARKS DISTRIBUTION REQUIRED:\n"
                f"You MUST generate exactly {subjective_count} subjective questions choosing ONLY from these allowed types: {allowed_subj_values}."
            )

    # Build Pedagogical Difficulty Blueprint string
    diff_lines = []
    bands = [
        (PaperDifficulty.EASY, "EASY (Recall / Factual Definitions)"),
        (PaperDifficulty.MEDIUM, "MEDIUM (Application / Conceptual Reasoning)"),
        (PaperDifficulty.HARD, "HARD (Analysis / Synthesis / Case Studies / Complex Systems)"),
    ]

    for band_key, band_label in bands:
        o_c = obj_map.get(band_key, 0)
        s_c = subj_map.get(band_key, 0)
        if o_c > 0 or s_c > 0:
            parts = []
            if o_c > 0:
                parts.append(f"{o_c} Objective Question{'s' if o_c > 1 else ''}")
            if s_c > 0:
                parts.append(f"{s_c} Subjective Question{'s' if s_c > 1 else ''}")
            diff_lines.append(f"- {band_label}: Generate {', '.join(parts)}")

    difficulty_blueprint_str = ""
    if diff_lines:
        difficulty_blueprint_str = "PEDAGOGICAL DIFFICULTY BLUEPRINT:\n" + "\n".join(diff_lines)

    allowed_obj_values = ", ".join(t.value for t in allowed_objective_types) if allowed_objective_types else ""

    base_instruction = ""
    if objective_count > 0 and subjective_count > 0:
        base_instruction = (
            f"Please generate EXACTLY {objective_count} objective questions using ONLY these allowed types: {allowed_obj_values} and "
            f"EXACTLY {subjective_count} subjective questions based strictly on this textbook content. "
            f"Ensure all topics are covered evenly."
        )
    elif objective_count > 0:
        base_instruction = (
            f"Please generate EXACTLY {objective_count} objective questions using ONLY these allowed types: {allowed_obj_values} based strictly "
            "on this textbook content. Do NOT generate any objective questions."
        )
    elif subjective_count > 0:
        base_instruction = (
            f"Please generate EXACTLY {subjective_count} subjective questions based strictly on this textbook content. "
            f"Do NOT generate any objective questions."
        )
    else:
        allowed_all_values = ", ".join(t.value for t in typed_allowed_types)
        base_instruction = (
            f"Please generate 2-3 standard-compliant questions based strictly on this textbook content. "
            f"You are strictly allowed to generate only these question types: {allowed_all_values}."
        )

    blocks = [base_instruction]
    if subjective_breakdown_str:
        blocks.append(subjective_breakdown_str)
    if difficulty_blueprint_str:
        blocks.append(difficulty_blueprint_str)

    return "\n\n".join(blocks)
