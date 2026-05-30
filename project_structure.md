# 📂 Agentic Paper Generator: Project Structure

This document provides a comprehensive reference of the directory structure and file layout for the **Agentic Question Paper Generator** application. Use this as a map for navigating, maintaining, and extending the codebase.

---

## 🗺️ Directory Tree Layout

```text
Agentic_Paper_Generator/
│
├── config/
│   ├── __init__.py
│   ├── settings.py            # Supabase URL/keys, LLM config, chunk batch size
│   └── prompts.py             # All LLM prompts in one place (easy to tweak)
│
├── models/
│   ├── __init__.py
│   └── schemas.py             # Pydantic models: PaperRequest, Question, PaperState, ChapterState
│
├── db/
│   ├── __init__.py
│   └── supabase_client.py     # Supabase init + get_chapter_chunks() retrieval function
│
├── graph/
│   ├── __init__.py
│   ├── state.py               # Graph state definitions
│   ├── nodes.py               # All node functions (distribute, generate, collect)
│   └── builder.py             # Build and compile the LangGraph graph
│
├── pdf/
│   ├── __init__.py
│   └── generator.py           # PDF formatting + generation (ReportLab/WeasyPrint)
│
├── app.py                     # Phase 3: Streamlit web UI
├── main.py                    # Phase 2: Terminal-based CLI agent
├── requirements.txt
├── .env                       # API keys (gitignored)
└── .gitignore
```

---

## 🔍 Module Descriptions & Responsibilities

### ⚙️ `config/`
Houses system-wide configuration, environment variables, credentials, and central prompt templates.
*   **`settings.py`**: Initializes configuration variables (e.g., Supabase credentials, LLM model choice, chunk processing batch size).
*   **`prompts.py`**: A centralized repository for all LLM prompt templates, making it extremely easy to tweak and version prompts for question generation, grading, or synthesis.

### 📦 `models/`
Defines the core data structures and state definitions using Pydantic.
*   **`schemas.py`**: Contains strictly typed Pydantic models:
    *   `PaperRequest`: Defines input parameters for paper generation (e.g., chapters, grade level, difficulty, total marks, distribution).
    *   `Question`: Schema representing a single generated question (including text, choices, correct answer, mark weightage, and diagram reference).
    *   `PaperState` & `ChapterState`: State validation models used within the LangGraph orchestrator to maintain state during generation runs.

### 🗄️ `db/`
Handles external database integrations and data ingestion/retrieval.
*   **`supabase_client.py`**: Initializes the Supabase database connection and exposes functions like `get_chapter_chunks()` to retrieve processed textbook segments with metadata-based filtering.

### 🕸️ `graph/`
Implements the multi-agent orchestrator utilizing **LangGraph**.
*   **`state.py`**: Defines the shared state interface (schemas) passed between agents.
*   **`nodes.py`**: Contains individual execution nodes of the graph:
    *   *Distribute Node*: Splits a request into parallel sub-tasks per chapter.
    *   *Generate Node*: Generates questions for a single chapter utilizing context chunks.
    *   *Collect Node*: Merges, refines, and formats the output into a single unified paper.
*   **`builder.py`**: Builds the graph nodes, edges, conditional pathways, and compiles them into a runnable workflow.

### 📄 `pdf/`
Handles formatting and generating publish-ready documents.
*   **`generator.py`**: Converts the final paper state into a beautiful, styled PDF document utilizing libraries like ReportLab or WeasyPrint (supporting custom margins, headers, footers, page numbers, and textbook diagrams).

### 🚀 Top-level Scripts & Configs
*   **`app.py`**: Streamlit web interface featuring rich UI elements to trigger, monitor, and export question papers (Phase 3).
*   **`main.py`**: Terminal-based CLI tool to execute the question generation pipeline asynchronously with live progress logs (Phase 2).
*   **`requirements.txt`**: Project dependency definitions.
*   **`.env`**: Local environment variables (Supabase keys, OpenAI/Gemini API keys).
*   **`.gitignore`**: Excludes private configuration, build outputs, and `.env` files from version control.
