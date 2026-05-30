# Handoff Document — AI-Powered Question Paper Generator

## Project Overview

An agentic application for a tuition teacher to generate formatted question papers from school textbook content. The teacher inputs subject, standard, chapters, and question types → the system generates questions from textbook chunks → teacher selects from candidates → PDF is generated.

**Workspace:** `/home/jeet-daiya/Storage/Teddy/Agentic_Paper_Generator`
**Virtual env:** `/home/jeet-daiya/Storage/Teddy/venv`

---

## Architecture Decisions Made

### Data Pipeline (COMPLETED — runs on Google Colab)
- **PDF extraction:** Docling with `generate_picture_images=True`
- **Chunking:** Docling HybridChunker, `max_tokens=450`, `merge_peers=True`, tokenizer: `BAAI/bge-base-en-v1.5`
- **Image handling:** Images extracted via Docling → uploaded to Cloudinary → URLs linked to chunks via **document-order mapping** (not through chunker, since HybridChunker excludes PictureItems from `chunk.meta.doc_items`)
- **Storage:** Supabase (PostgreSQL) — chunks table with metadata filtering
- **Embeddings model:** `BAAI/bge-base-en-v1.5` (512 max tokens) — chosen for the HybridChunker tokenizer, but retrieval is metadata-based, NOT semantic search

### Image-to-Chunk Linking (Key Bug Fixed)
The HybridChunker does NOT include PictureItems in `chunk.meta.doc_items`. Fix: walk `doc.iterate_items()` in document order, map each image to the preceding text item's `self_ref`, then match against chunk doc_items which DO contain text refs (`#/texts/X`).

### Retrieval Strategy
- **Pure metadata filtering** — no semantic/vector search needed
- Query: `WHERE subject=X AND standard=Y AND chapter_name=Z ORDER BY chunk_index`
- Chunks stored with per-chapter `chunk_index` (not global)

### Question Generation Strategy
- **Approach 2 (Iterative with Memory):** Process ALL chunk batches (5 chunks per batch, sequential order) per chapter
- Each batch: LLM sees new chunks + list of previously generated questions (dedup)
- LLM **decides question types** based on content suitability (not forced)
- **Fan-out per chapter** via LangGraph Send API (parallel chapters)
- **No consolidation LLM step** — teacher selects from over-generated pool (HITL)

### LangGraph Architecture
```
START → distribute (pass-through) → [conditional_edges/Send API]
  → question_generator_node (per chapter, iterative loop)
  → review_node (HITL interrupt — teacher selects questions)
  → formatter_node (HTML generation)
  → END
```

### PDF Generation
- HTML-based with KaTeX for LaTeX rendering
- Template-based formatting (not LLM-formatted)
- Sections grouped by question type with marks display

---

## Current File Structure

```
Agentic_Paper_Generator/
├── config/
│   ├── __init__.py
│   ├── settings.py          # LLM models, Supabase config, constants
│   └── prompts.py           # System prompt for question generation
├── models/
│   ├── __init__.py
│   └── schemas.py           # Pydantic models: PaperRequest, Question, BatchOutput, QuestionTypes
├── graph/
│   ├── __init__.py
│   ├── state.py             # PaperState, ChapterState (graph states)
│   ├── nodes.py             # All node functions
│   └── builder.py           # Graph construction and compilation
├── db/
│   ├── __init__.py
│   └── db.py                # Supabase client + get_chapter_chunks()
├── pdf/
│   ├── __init__.py
│   └── generator.py         # HTML question paper generator
├── main.py                  # CLI entry point for testing
├── .env                     # API keys (gitignored)
└── requirements.txt
```

---

## Database Schema (Supabase)

```sql
CREATE TABLE chunks (
    id              BIGSERIAL PRIMARY KEY,
    standard        TEXT NOT NULL,
    subject         TEXT NOT NULL,
    chapter_name    TEXT NOT NULL,
    sub_topic       TEXT,
    chunk_index     INT NOT NULL,
    content         TEXT NOT NULL,
    has_image       BOOLEAN DEFAULT FALSE,
    image_urls      TEXT[] DEFAULT '{}',
    UNIQUE(standard, subject, chapter_name, chunk_index)
);
CREATE INDEX idx_chunks_filter ON chunks(subject, standard, chapter_name);
```

**Data loaded:** Class 10 Science chapters (multiple chapters ingested from Docling pipeline on Colab)

---

## Key Models

```python
class QuestionTypes(StrEnum):
    FOUR_MARK_ANS = "4_MARKS"
    THREE_MARK_ANS = "3_MARKS"
    TWO_MARK_ANS = "2_MARKS"
    FILL_IN_THE_BLANK = "FILL_IN_THE_BLANK"
    MATCH_THE_COLUMN = "MATCH_THE_COLUMN"
    MCQ = "MCQ"
    TRUE_FALSE = "TRUE_FALSE"
    ONE_WORD_ANS = "ONE_WORD_ANS"

class PaperState:  # Graph state — needs Optional defaults
    paper_request: Optional[PaperRequest] = None
    all_questions: Annotated[list[Question], operator.add] = []
    selected_questions: list[Question] = []

class ChapterState:  # Send API per-chapter state
    chapter: str
    subject: str
    generated_questions: Annotated[list[Question], operator.add]
```

---

## Current Status of Issues

### 1. LLM Output Parsing Errors (SOLVED)
- **Status:** Fully resolved. Configured **`gemini-2.5-flash`** as the main model which has robust native support for JSON schema structured output.
- **Answer Formats:** Configured the prompt to output concise, structured bulleted marking/evaluation key points instead of paragraphs. This completely eliminates large token sizes and JSON truncation errors while providing a highly usable grading key for the teacher.

### 2. `formula-not-decoded` Placeholders (PENDING)
- Some chunks contain `<!-- formula-not-decoded -->` where Docling couldn't extract chemical formulas. Accept as tradeoff for v1 — surrounding text usually covers the same content.

### 3. Missing Text Near Images/Page Boundaries (PENDING)
- Docling's layout model occasionally misses text near diagrams and page breaks. One-time manual data quality pass needed before production use (~6 hours for 4-5 textbooks).

### 4. Prompt Typo (FIXED)
- Typo in `prompts.py` corrected from `coAmparisons` to `comparisons`.


---

## What's Working
- ✅ Supabase data loaded (Class 10 Science chapters)
- ✅ Graph compiles and runs (distribute → generate → review → PDF)
- ✅ Send API fan-out per chapter
- ✅ HITL interrupt in review node
- ✅ HTML paper generation with KaTeX, sections, marks
- ✅ Metadata-based retrieval from Supabase
- ✅ Iterative generation with memory (dedup)
- ✅ LLM output parsing reliability (solved via Gemini 2.5 Flash + structured evaluation points format)
- ✅ Answer key & marking scheme generation as a separate high-quality PDF document (`output_answers.pdf`)

## What's NOT Done Yet
- ❌ Web UI (Phase 3)
- ❌ Data quality review of chunks
- ❌ VLM image descriptions for diagram-based questions (v2 feature)

---

## Config Notes
- **LLM:** Currently using gemini-2.5-flash (fully native structured outputs).
- **Two model instances:** `generator_model` (temp=0.1) for questions,
- **Chunk batch size:** 5 chunks per LLM call
- **Rate limiting:** `time.sleep(2)` between batch calls needed for free tiers
- **Checkpointer:** `MemorySaver` for HITL interrupt/resume
- **Graph state issue:** PaperState uses Pydantic BaseModel — ALL fields need defaults. Conditional edges from `__start__` don't work; a pass-through `distribute` node was added as workaround

