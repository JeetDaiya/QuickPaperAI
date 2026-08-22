`# Handoff Document — AI-Powered Question Paper Generator

## Project Overview

An agentic RAG application for a tuition teacher to generate formatted question papers from school textbook content. The teacher inputs subject, standard, chapters, and question counts → the system generates questions from textbook chunks → the teacher selects from generated candidates in a CLI/HITL loop or via interactive REST API polling endpoints → A4 exam paper and corresponding detailed answer sheets are generated in PDF and editable DOCX formats.

* **Workspace:** `/home/jeet-daiya/Storage/Teddy/QuickPaperAI`
* **Virtual env:** `/home/jeet-daiya/Storage/Teddy/venv`

---

## Architecture Decisions Made

### 1. Data Pipeline (COMPLETED — LlamaCloud Parsing)
* **PDF Extraction:** **LlamaCloud** (LlamaParse client) using `tier="agentic_plus"` and `expand=["markdown"]` to extract high-fidelity semantic markdown representations.
* **Layout Sanitization:** A custom regular expression pipeline `sanitize_ncert_markdown` that strips LlamaParse visual anomalies and forces clean structural hierarchies:
  * Reformats major topics (e.g., `1.1`) to `##` headers.
  * Reformats sub-topics (e.g., `1.1.1`) to `###` headers.
  * Reformats textbook activities (e.g., `Activity 1.1`) to `####` headers.
  * Captures textbook questions keywords to standardize as `### QUESTIONS` headers.
* **Semantic Chunks Splitting:** **LangChain's `MarkdownHeaderTextSplitter`** configured to split text on `##` (`Main_Topic`) and `###` (`Sub_Topic`) headers, yielding clean topic-oriented chunks instead of token-restricted boundaries.
* **Metadata Enriched Chunks:** Extracts `sub_topic` from header properties (defaulting to `"General"` if none exist) and maps each chunk to standard, subject, and chapter.
* **Concurrency:** Uses a `ThreadPoolExecutor` with `max_workers=5` to parse multiple textbook chapter PDFs concurrently.
* **Storage:** Supabase PostgreSQL table `chunks` with sequential indexing (`chunk_index` initialized from `0` per chapter).

### 2. Image and Vector Search Exclusions
* **Vector Embeddings Excluded:** Vector embeddings are not utilized for retrieval.
* **Pure Metadata Filtering:** Retrieval is guided strictly by custom PostgreSQL index filtering matching `subject`, `standard`, and `chapter_name`, sorted in raw textbook order (`chunk_index`).

### 3. Retrieval Strategy
* Query: `WHERE subject=X AND standard=Y AND chapter_name=Z ORDER BY chunk_index`
* Chunks stored with per-chapter `chunk_index` (not global).

### 4. Question Generation & Concurrency Strategy
* **Approach 2 (Iterative with Memory):** Process ALL chunk batches (5 chunks per batch, sequential order) per chapter.
* Each batch: LLM sees new chunks + list of previously generated questions (preventing duplicates).
* LLM **decides question types** dynamically based on content suitability.
* **Fan-out per chapter** via LangGraph `Send` API (parallel chapters run concurrently).
* **HITL Console Interaction:** The teacher selects from a generated pool at runtime.

### 5. LangGraph Architecture
```
START → distribute (pass-through) → [conditional_edges/Send API]
  → question_generator_node (per chapter, iterative loop)
  → review_node (HITL interrupt — teacher selects questions)
  → formatter_node (HTML generation)
  → END
```

### 6. Document Formats & Spacing (PDF + DOCX)
* The system produces both:
  1. Pixel-perfect **PDFs** (`paper.pdf` and `answer.pdf`) with fully-compiled KaTeX equations.
  2. Editable **DOCX** files (`paper.docx`) containing native MS Word Equation objects compiled via Pandoc.
* **Header Style:** Word header utilizes a borderless 2-column layout (Subject/Standard on the left, Date/Chapters on the right) with centered bold uppercase school banner and bold marks summary, bounded by a solid horizontal divider line.

### 7. Graceful Diagram Spacing
* For questions containing visual aids, the student's sheet displays a thin 1px solid black visual blank container box (height: `160px`) optimized for photocopy printing.
* The copy-pasteable image generation prompt is written **directly inside** the Word placeholder table cell (so the teacher can copy it inside MS Word, generate, paste, and delete) and listed inside the **Diagram Prompt Annex** at the very end of the Answer Key.

### 8. Decoupled FastAPI Server Backend with Cloud Integration
To support separate graphical web frontends, we re-architected the generation engine into a clean, decoupled client-server REST API:
* **Centralized DB Client (`server/db.py`)**: Uses a single instance initialized with `SUPABASE_SERVICE_ROLE_KEY` to guarantee master backend write permissions, cleanly decoupled from routers to avoid circular imports.
* **Chapter Query Filter (`GET /api/db/get-chapters`)**: Queries Supabase chunks for chapters matching subject and standard, deduplicating records in Python dynamically.
* **Supabase Storage & History Sync**: After a paper compiles on resume, it runs a background sync that uploads the files to a public `question-papers` storage bucket under `{thread_id}/` and logs metadata parameters into a dedicated `generated_papers` DB table.
* **History Recovery Endpoint (`GET /api/db/history`)**: Feeds draft recovery sidebars by querying all previously generated papers matching the authenticated user's ID, mapping raw cloud paths dynamically into secure server-proxied URLs.
* **Proxy-Streaming Download Cache (`GET /api/download/{thread_id}/{filename}`)**: Securely serves PDFs and DOCX files. Implements a local hot-caching layer: serves local files immediately (zero latency), and fallback-downloads files from Supabase Storage on cache misses to restore them locally before streaming.

### 9. Custom JWT Authentication (NEW — COMPLETED)
We implemented a custom, from-scratch authentication layer inside the FastAPI backend. It utilizes your Supabase PostgreSQL instance as the database store and secures all REST endpoints via standard OAuth2 protocols:
* **Password Encryption**: Employs `passlib[bcrypt]` to securely hash passwords during registration and verify them during login.
* **Token Handlers**: Generates signed JSON Web Tokens (JWTs) using the `python-jose` library. It includes customizable expiration parameters (defaulting to 7 days).
* **Route Guards (`get_current_user`)**: A FastAPI security dependency (`Depends`) that extracts the bearer token from HTTP headers using `OAuth2PasswordBearer`, decodes it, verifies its signature against the server's `SECRET_KEY`, and queries Supabase to return the active user's details. Any invalid or expired token automatically yields a `401 Unauthorized` response.
* **Dynamic Ownership Partitioning**: Replaced the legacy `DUMMY_USER_ID` system. Now, all paper generation states, database records, and history listings are strictly tied to the logged-in user's ID (`str(current_user["id"])`), creating isolated account scopes.

### 10. React Client Auth Integration & Auto-Save (NEW — COMPLETED)
We fully integrated the frontend client with the backend authentication system and added automatic draft recovery:
* **Interactive Sign In & Sign Up**: Wired up `/login` and `/signup` routes in TanStack Router to communicate directly with backend token exchange and registration endpoints.
* **Token Authorization & Interceptors**: Configured `client/src/lib/api.ts` to attach the JWT token dynamically via bearer authorization headers, fallback token parameters for downloads, and intercept expired requests (`401 Unauthorized`) to clear the session and force login redirection.
* **Redirection Guards & Status Notifications**:
  - Protected routes (`/new`, `/papers/*`) intercept unauthenticated users and redirect them to `/login` with an `auth_required` status banner ("you need to log in to continue.").
  - Signing out successfully redirects the user with a `signed_out` success banner ("signed out successfully").
* **Public Landing Page**: Removed login requirement from the root route `/` so anonymous users can land on the site. Added a **Cloud Vault / Review History** section that loads their list of exam papers dynamically via TanStack Query when logged in, or shows a credentials lock prompting them to sign in.
* **Auto-Save & Soft Session Restorer**: Added form recovery to the `/new` setup screen. Current inputs are cached inside `localStorage` on modification. On remount/refresh, a recovered plan banner allows users to instantly **Restore settings** or **Discard** them.

### 11. Decoupled Provider-Agnostic Authentication Service Interface (NEW — IN PROGRESS)
To ensure the backend is fully protected but easily switchable to alternative identity providers (such as Google/Facebook OAuth, Supabase Auth, Firebase, or Clerk) in the future, we abstracted all authentication tasks behind a dedicated `AuthService` interface:
* **The Interface (`core/interfaces/auth.py`)**: Declares high-level asynchronous business actions: `register_user`, `authenticate_user`, and `get_user` instead of low-level hashing details.
* **Low-Level Isolation**: Low-level implementation details (like hashing algorithms or custom JWT signing keys) are fully isolated inside the concrete adapter, leaving the route endpoints cleanly decoupled.

### 12. Clean Architecture Interface-Adapter Ecosystem (NEW — COMPLETED)
To keep the core generation logic (`core/graph`) completely independent of external infrastructure, databases, and third-party APIs, we established a strict **Clean Architecture Interface-Adapter Ecosystem**. All key system capabilities are defined as abstract interfaces under `core/interfaces/` and fulfilled by modular, replaceable adapters under `core/adapters/`:

#### A. Database Services
* **Interfaces (`core/interfaces/db.py`)**:
  - `UserRepository`: Decouples operations on user records (retrieving details, registering users, activating accounts).
  - `ChunkRepository`: Decouples textbook chunk retrieval (fetching chapter contents).
  - `PaperRepository`: Decouples exam paper history tracking.
* **Adapters (`core/adapters/supabase_db.py`)**:
  - `SupabaseUserRepository`, `SupabaseChunkRepository`, `SupabasePaperRepository`: Concrete implementations communicating with Supabase PostgreSQL tables using the backend `SUPABASE_SERVICE_ROLE_KEY` (to bypass RLS locks safely).

#### B. Storage Services
* **Interface (`core/interfaces/storage.py`)**:
  - `StorageService`: Outlines unified file CRUD parameters (`put_file`, `get_file`, `delete_file`) using standard `file_path` declarations.
* **Adapters**:
  - `LocalStorageService` (`core/adapters/local_storage.py`): Manages local temporary file compilation and proxy downloads inside the `outputs/` folder.
  - `SupabaseStorageService` (`core/adapters/supabase_storage.py`): Synchronizes finalized documents to a public Supabase Storage bucket for permanent cloud hosting.

#### C. OTP (One-Time Password) Stores
* **Interface (`core/interfaces/otp_store.py`)**:
  - `OTPStore`: Declares asynchronous routines to save OTPs, fetch active codes, check resend cooldowns, increment attempts, and verify lockout states.
* **Adapters**:
  - `MemoryOTPStore` (`core/adapters/memory_otp_store.py`): Handles asynchronous, in-memory tracking as a fallback for offline development.
  - `RedisOTPStore` (`core/adapters/redis_otp_store.py`): Connects to **Upstash Redis** using a connectionless async HTTP client (`upstash-redis`), enabling stateless backend scaling and native TTL auto-expiration.

#### D. Email Delivery Services
* **Interface (`core/interfaces/mail.py`)**:
  - `EmailService`: Outlines generic email sending requirements.
* **Adapter (`core/adapters/fast_mail.py` / `fast_mail_service.py`)**:
  - Concrete adapter utilizing the `fastapi-mail` library (pinned to version `1.6.4` to fix older dependency NameErrors) to connect to SMTP servers (e.g. Brevo/SendGrid).

---

## Current File Structure (`src/` Feature Layout)

```
QuickPaperAI/
├── src/                         # 🚀 Unified Application Source Package
│   ├── auth/                    # 🔒 Authentication Feature Module
│   │   ├── interface/           # AuthService & OTPStore abstract contracts
│   │   ├── adapters/            # CustomAuthService (JWT + bcrypt) & RedisOTPStore
│   │   ├── routes/              # FastAPI /auth HTTP endpoints
│   │   ├── user_schemas.py      # Pydantic DTOs: UserRegister, UserResponse, OTPVerification
│   │   ├── token_schemas.py     # Pydantic DTOs: Token, TokenData
│   │   └── email_template.py    # HTML email template renderer for OTP verification
│   │
│   ├── paper/                   # 📄 Question Paper Generation Feature Module
│   │   ├── models.py            # PaperRequest, Question, EvaluationPoint, Domain Enums
│   │   ├── schemas.py           # Web DTOs: PaperGenerateRequest, PaperHistoryResponse
│   │   ├── service.py           # PaperService (generation, status, cloud sync, downloads)
│   │   ├── task_manager.py      # In-memory background task registry
│   │   ├── rate_limiter.py       # TokenBucket rate limiter for Gemini API
│   │   ├── routes/              # FastAPI /api/generate, /resume, /status endpoints
│   │   ├── graph/               # LangGraph Workflow (builder, nodes, state, tracker, utils)
│   │   ├── formatters/          # HTML & Markdown paper formatters
│   │   ├── compilers/           # CustomDocumentCompiler & generator.py
│   │   └── templates/           # Jinja2 HTML/CSS document templates
│   │
│   ├── db/                      # 🗄️ Database & Chunks Feature Module
│   │   ├── interfaces/          # ChunkRepository, UserRepository, PaperRepository contracts
│   │   ├── adapters/            # Supabase database repository implementations
│   │   ├── services/            # DBService
│   │   └── routes/              # FastAPI /api/db HTTP endpoints (get-chapters, history)
│   │
│   ├── storage/                 # ☁️ File Storage Feature Module
│   │   ├── interfaces/          # StorageService abstract contract
│   │   └── adapters/            # LocalStorageService & SupabaseStorageService
│   │
│   ├── mail/                    # 📧 Mail Delivery Feature Module
│   │   ├── interfaces/          # EmailService abstract contract
│   │   └── adapters/            # FastMailService
│   │
│   ├── config/                  # ⚙️ Application Configuration
│   │   ├── settings.py          # LLM configurations & fallback model chains
│   │   └── prompts.py           # System prompts, few-shots, KaTeX setups
│   │
│   ├── base_settings.py         # Pydantic Settings loaded from .env
│   ├── dependencies.py          # Dependency injection container & App lifespan
│   ├── app.py                   # FastAPI app factory & middleware configuration
│   └── main.py                  # Uvicorn server entrypoint
│
├── scripts/                     # 🛠️ Standalone CLI Utilities & Ingestion Notebooks
│   ├── parse_textbooks.ipynb    # LlamaParse textbook ingestion notebook
│   ├── run_cli.py               # Standalone CLI paper generator
│   └── recover_paper.py         # Draft recovery utility
│
├── data/                        # 📚 Source Data Assets
│   └── Std_10_Chapters/         # Grade 10 NCERT textbook PDF sources
│
├── outputs/                     # 📄 Local compiled PDF & DOCX output caches (gitignored)
├── walkthrough.md               # Unified project documentation
├── Dockerfile                   # Production Docker build specification
└── requirements.txt             # Python dependencies
```

---

## Database Schema (Supabase)

```sql
-- Chunks table storing textbook parsed content
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

-- Users table storing custom authentication accounts
CREATE TABLE public.users (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    name            TEXT,
    is_active       BOOLEAN DEFAULT TRUE NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at      TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Generated papers table tracking metadata and file paths
CREATE TABLE public.generated_papers (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             UUID REFERENCES public.users(id) ON DELETE CASCADE,
    thread_id           UUID NOT NULL,
    institution_name    TEXT NOT NULL,
    subject             TEXT NOT NULL,
    standard            TEXT NOT NULL,
    difficulty          TEXT NOT NULL,
    chapters            TEXT[] NOT NULL,
    objective_count     INT DEFAULT 0,
    subjective_count    INT DEFAULT 0,
    allowed_types       TEXT[] NOT NULL,
    paper_pdf_path      TEXT NOT NULL,
    answer_pdf_path      TEXT NOT NULL,
    paper_docx_path     TEXT NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
```

---

## Key Models & Pydantic Refactorings

### 1. Count-Target Paper Schema
We refactored the complex `question_count` dictionary input into two plain integer fields to simplify UI integration and support objective-only exams cleanly:
```python
class PaperRequest(BaseModel):
    subject : str
    standard : str
    institution_name : str
    difficulty : str
    chapters : list[str]
    objective_count : int  # Direct count of objective questions
    subjective_count : int  # Direct count of subjective questions
```

### 2. Schema Compatibility with Gemini API
We refactored array structures to be flat lists with default empty lists. This avoids complex `anyOf` / `null` union types or `minItems`/`maxItems` constraints in the generated JSON Schema, which are **strictly prohibited** by the Gemini structured output engine:
```python
class EvaluationPoint(BaseModel):
    point_text : str
    allocated_marks : int

class Question(BaseModel):
    question_text : str
    question_type : QuestionTypes
    chapter : str
    marks : int
    options : list[str] = Field(default=[])  # Clean array (no nulls/limits)
    correct_answer : str
    answer : str
    evaluation_scheme : list[EvaluationPoint] = Field(default=[], description="Detailed grading breakdown for subjective questions.")
    diagram_prompt : Optional[str] = Field(default=None) # Dynamic visual image prompt

class BatchOutput(BaseModel):
    question_list : list[Question] = Field(default=[])  # No min_length or max_length
```

---

## Current Status of Issues & Core Bug Fixes

### 1. Codebase Sibling Package Imports (FIXED)
* **The Problem**: When executing the backend server, sibling package imports in `core/` (e.g. `from graph.state import ...`) failed to resolve, resulting in immediate `ModuleNotFoundError: No module named 'graph'` crashes.
* **The Fix**: Re-packaged all imports inside `core/` to use absolute, standardized `core.*` paths (e.g. `from core.graph.state import ...`). This completely eliminated startup errors and deprecated temporary `sys.path` injection hacks.

### 2. Postgrest AttributeError: 'SyncSelectRequestBuilder' object has no attribute 'distinct' (FIXED)
* **The Problem**: Querying textbook chapters crashed with an `AttributeError` because the Postgrest python client does not support `.distinct()` queries on select statements.
* **The Fix**: Removed `.distinct()` from the Supabase chain in `chapter_info.py`. Chunks are now queried cleanly and filtered dynamically in Python using a set key deduplication, preserving perfect runtime safety.

### 3. Psycopg deprecation warnings on Lifespan Construction (FIXED)
* **The Problem**: Initializing `AsyncConnectionPool` produced warnings stating that synchronous construction is deprecated and pools must be opened asynchronously.
* **The Fix**: Added `open=False` to the `AsyncConnectionPool` constructor in `server/dependencies.py`, fully delegating the pool initialization to the asynchronous `await pool.open()` step inside the lifespan manager.

### 4. Gemini structured output 400 `INVALID_ARGUMENT` crashes (FIXED)
* **The Problem:** The pipeline previously crashed when calling the structured chain on the newer Gemini 3.1 & 3.5 series.
* **The Root Causes:**
  1. **Thinking Parameter Conflict:** The model was initialized with `thinking_level="medium"`. Combining reasoning/thinking parameters with structured output schemas (`with_structured_output`) is strictly forbidden by the Gemini API.
  2. **Array Length Constraints:** The schema included `min_length` and `max_length` properties, compiling to unsupported `minItems` and `maxItems` in JSON Schema.
* **The Fix:** Removed `thinking_level="medium"` from models that don't support it in JSON-mode, and cleaned up list validators from `BatchOutput`. Standard Gemini 3.1 Flash and Lite models now generate structured question pools seamlessly.

### 5. Match the Columns rendering failure (FIXED)
* **The Problem:** Matching column questions did not format nicely as two columns or were flat-collapsed inside the PDF.
* **The Fix:**
  1. **Prompt instructions:** Instructed the model in `prompts.py` to write only the introductory matching prompt inside `question_text`, and populate the matched items inside `options` using a pipe (`|`) character (e.g., `"(i) Burning of magnesium | (a) Evolution of hydrogen"`).
  2. **PDF Parser:** Refactored `_render_question_html` inside `generator.py` to preserve raw newlines in `question_text` by replacing them with HTML `<br>` tags, and automatically parse pipe-separated options into a beautiful, standard two-column HTML table.

### 6. LaTeX `\rightarrow` / `ightarrow` Carriage Return Corruption (FIXED)
* **The Problem:** Single backslashes in JSON (such as `\r` or `\t`) are interpreted as escaped control bytes (carriage return/tab), corrupting `\rightarrow` into `ightarrow`.
* **The Double-Insurance Fix:**
  * **System Prompt:** Commanded the LLM to output double backslashes (`\\rightarrow`, `\\theta`) for perfect JSON parsing.
  * **Regex Post-Processing:** Implemented a robust `clean_latex(text)` utility in `nodes.py` that automatically scans LLM outputs and restores any accidentally decoded tab and carriage return characters back into raw latex symbols.

### 7. Subjective Mark Skipping Bias (FIXED)
* **The Problem:** In earlier runs, 2-mark and 4-mark questions were routinely skipped, defaulting strictly to 3-marks due to prompt bias.
* **The Fix:** Expanded `prompts.py` to provide explicit, premium few-shot examples for structured 2-mark conceptual and 4-mark multi-part diagrams/scenarios, and added a strict quota directive to the generator node.

### 8. CLI Keyword-Based "all" Selection (FIXED)
* **The Fix:** Refactored the console selection input in `main.py` to allow teachers to type `all` (case-insensitive) to select the entire candidate pool instantly.

### 9. Persistence & Serialization Thread Errors (FIXED)
* **The Fix:** Configured `AsyncPostgresSaver` in `graph/builder.py` for full production persistence (retaining HITL states across server crashes or refreshes), and updated `main.py` to initialize thread configurations using string-based `str(uuid.uuid4())` to prevent Msgpack threading serialization errors.

### 10. Dynamic Question Type Filtering (FIXED)
* Forwarded type boundaries in `router_node` and stripped LLM schema hallucinations dynamically at the generator node boundary.

### 11. Smart MCQ Option Prefixing (FIXED)
* **The Fix:** Integrated a regex-based prefix validator inside `_render_question_html` that dynamically detects existing option prefixes and suppresses double-labeling while maintaining standard prefix fallbacks.

### 12. Diagram-Based Questions & Copy-Paste Annex (COMPLETED)
* **The Fix:** Integrated a standard 1px solid black-bordered blank diagram box on the student's paper and stored image prompts directly inside Word placeholder cells and Answer Key Annexes.

### 13. Firebase Cloud Messaging (FCM) Environment Migration & GitHub Safety (COMPLETED)
We migrated all Firebase Web credentials, VAPID public keys, and Service Worker configurations strictly to environment variables for GitHub repository security:
* **Firebase Client Config (`client/src/lib/firebase.ts`)**: Consumes `import.meta.env.VITE_FIREBASE_*` variables without hardcoded secrets in source files.
* **Dynamic Service Worker (`client/public/firebase-messaging-sw.js`)**: Refactored static Service Worker to dynamically parse initialization parameters from `self.location.search` query parameters passed during `navigator.serviceWorker.register()`.
* **FCM Hook & VAPID Resolution (`client/src/hooks/useFCMNotification.ts`)**: Dynamically passes `firebaseConfig` URL parameters to the Service Worker registration and consumes `import.meta.env.VITE_FIREBASE_VAPID_PUBLIC_KEY`.
* **Environment Templates & Git Protection (`.env.example`)**: Added `client/.env.example` and root `.env.example` templates; ensured `.env` and `firebase-credentials.json` are strictly ignored in `.gitignore`.

---

### 14. Automatic Exponential Backoff Retry Policy (FIXED)
* **The Fix:** Configured a native `RetryPolicy` on fanned-out chapter generation nodes (`question_generator_node`). Transient API rate limits (`429`), network dropouts (`503`), or LLM structural decode issues are automatically retried up to 3 times with exponential backoff and randomized jitter before throwing a crash.

### 15. Document Compilation Soft Isolation (FIXED)
* **The Fix:** Wrapped the non-critical Word document generation step (`generate_docx`) in `pdf_node` in a safe try-catch wrapper. While PDF generation remains strict and critical, any system-level DOCX compilation error (e.g. missing Pandoc utility) will print a graceful warning rather than crash the entire pipeline, guaranteeing the teacher always receives their print-ready PDFs.

### 16. Horizontal Chapter Tab Navigation & Pure Numeric Display (NEW — FIXED)
* **The Problem:** The review page previously showed questions for all chapters in a single massive list, cluttering the view, particularly on mobile and laptop viewports. Furthermore, labels displayed messy chapter prefixes and titles (e.g., `Ch 11: Atmospheric Refraction` vs. `11`), resulting in inconsistent tabs.
* **The Fix:**
  * **Chapter Tab Bar**: Replaced the vertical list with a premium, horizontally scrollable index card-like tab header (`client/src/routes/papers.$threadId.review.tsx`).
  * **Pure Numeric Labels**: Filtered and mapped labels to display *only* pure chapter numbers (e.g., `11`, `14`) corresponding directly to database identifiers.
  * **Scroll indicators**: Configured a thin scrollbar (`.tabs-scroll`) in `client/src/styles.css` along with a fade gradient and `"scroll →"` helper tag to ensure visual discoverability on smaller viewports.
  * **Grouped Filtering**: Selecting a tab isolates questions to that specific chapter, grouped cleanly by question type (MCQ, Short Answer, etc.), while preserving the global checkbox state and selected tally counters.

### 17. Backend Chapter Key Standardization (NEW — FIXED)
* **The Problem:** When generating questions, the LLM sometimes outputted chapter names (e.g., `"ACIDS, BASES AND SALTS"`) or prefixes (e.g., `"Chapter 11"`) inside the `Question`'s `chapter` field. Since the frontend groups questions by whatever unique string the LLM returns, this led to duplicate tabs (e.g., multiple `11` tabs, or tabs with full text titles) on the review page.
* **The Fix:** Added a standardizing assignment (`q.chapter = str(chapter)`) in the post-processing loop of `question_generator_node` in `core/graph/nodes.py`. This guarantees that questions always carry the exact numeric string identifier matching the database (e.g., `"2"`, `"11"`), resolving all duplicate tabs.

### 18. Answer Key Legibility Upgrades (NEW — FIXED)
* **The Problem:** The interactive answer key toggle button was too small (`text-[10px]`) and the answer text was hard to read (`text-sm italic`), causing friction during examiner review.
* **The Fix**:
  * **Interactive Button Badge**: Replaced the raw text button with a styled pill button (`border border-[var(--paper-rule)] bg-[var(--card)] px-2.5 py-1 text-xs`) that houses an expand indicator icon (`▼` / `▶`) and a colored points badge (e.g., `3 pts`).
  * **Answer Box**: Wrapped the opened answer in a box styled with a bold vermillion left accent border (`border-l-4`), drop shadow (`stamp-shadow`), and a solid background.
  * **Readability**: Increased the Ideal Answer text to `text-base` (full opacity, `font-serif`) and the Marking Scheme points to `text-sm` (with a bold `+marks` badge) to ensure high scan-readability.

### 19. Bcrypt Password Verification Legacy Bug (NEW — FIXED)
* **The Problem:** When running user authentication, calls to `pwd_context.verify()` crashed with `ValueError: password cannot be longer than 72 bytes`, even when entering a short 8-character password. This was caused by an incompatibility between `passlib` and newer versions of the `bcrypt` library (specifically `bcrypt 5.0.0+` which was installed in the environment).
* **The Fix:** Downgraded the `bcrypt` package inside the virtual environment to `3.2.2`. This is the last version fully compatible with `passlib`'s metadata parsing logic, resolving the misleading error.

### 20. Frontend Vercel Deploy Output Alignment (NEW — FIXED)
* **The Problem:** The `@lovable.dev/vite-tanstack-config` utility library hardcoded the `publicDir` and `serverDir` options to `dist/client` and `dist/server`. Even if Vercel set `.vercel/output` as the output directory, Nitro's compiled static assets and server functions were placed in the wrong folder, resulting in a blank site showing a Vercel 404.
* **The Fix:** Configured explicit path overrides in `client/vite.config.ts` for all three Nitro output properties:
  - `dir`: `.vercel/output`
  - `publicDir`: `.vercel/output/static`
  - `serverDir`: `.vercel/output/functions/__server.func`
  This aligns the build perfectly with Vercel's Build Output API v3 specifications.

### 21. Relative-to-Absolute API URL Self-Healing (NEW — FIXED)
* **The Problem:** Setting `VITE_API_BASE_URL` without a protocol prefix (e.g. `quickpaperai-production.up.railway.app`) caused the browser to treat fetches as relative URLs (e.g., `https://quick-paper-ai-ruddy.vercel.app/quickpaperai-production.up.railway.app/auth/login`), triggering 500 router errors.
* **The Fix:** Added a self-healing protocol check in `client/src/lib/api.ts` that prepends `https://` if `VITE_API_BASE_URL` lacks a protocol scheme:
  ```typescript
  if (base && !base.startsWith("http://") && !base.startsWith("https://")) {
    base = `https://${base}`;
  }
  ```

### 22. PDF Preview Double Query Parameter Bug (NEW — FIXED)
* **The Problem:** The PDF preview URL generated in `papers.$threadId.done.tsx` was appending `?preview=true` to an already token-appended URL, yielding `?token=...?preview=true`. This invalidated token authentication on the backend, triggering 401 errors.
* **The Fix:** Passed the preview parameter inside the `api.fileUrl` method itself (e.g. `api.fileUrl(`${files.paper_pdf}?preview=true`)`), allowing the helper to correctly parse and join parameters using the proper ampersand separator (`&token=...`).

### 23. Playwright and Uvicorn Timeouts on Railway (NEW — FIXED)
* **The Problem:** The LangGraph generation pipeline can take over a minute to run, occasionally causing connection dropouts or Playwright render failures during HTML-to-PDF rendering when loading external fonts/CDN assets inside container environments.
* **The Fix:** 
  1. Configured Uvicorn in the `Dockerfile` with `--timeout-keep-alive 120` to prevent early socket closures on Railway.
  2. Increased Playwright's `wait_for_load_state` networkidle timeout to 90 seconds (`timeout=90000`) in `core/pdf/generator.py`.

### 24. Cleaned Vercel Overrides and .lovable Folder (NEW — FIXED)
* **The Fix:** Deleted the static routing overrides file `vercel.json` which interfered with TanStack Start's serverless handler mapping. Ignored `.vercel/` build caches and purged the `.lovable/` sandbox configuration metadata folder to maintain git repo cleanliness.

---

## Verification & Local Execution

### 1. Standalone CLI Generation
1. **Activate Virtual Env:**
   ```bash
   source /home/jeet-daiya/Storage/Teddy/venv/bin/activate
   ```
2. **Run Engine:**
   ```bash
   python core/main.py
   ```

### 2. Asynchronous API Server Generation
1. **Activate Virtual Env:**
   ```bash
   source /home/jeet-daiya/Storage/Teddy/venv/bin/activate
   ```
2. **Start Server:**
   ```bash
   python -m server.main
   ```
3. **Execute Interactive Test Client:**
   Open a separate tab and run:
   ```bash
   python server/test.py
   ```

### 3. Deployed Production Environments
1. **Frontend Web App (Vercel):**
   * **URL:** `https://quick-paper-ai-ruddy.vercel.app/`
   * **CI/CD:** Automatically builds and deploys on pushes to the `main` branch.
   * **Root Directory:** Configured to `client/` inside the Vercel dashboard.
2. **Backend API Server (Railway):**
   * **URL:** `https://quickpaperai-production.up.railway.app/`
   * **CI/CD:** Automatically builds the root `Dockerfile` and deploys on pushes to the `main` branch.
   * **Port Binding:** Dynamically binds to the `$PORT` environment variable assigned by Railway.

---

## Future Work

### 1. Python-Level Dynamic Subjective Quota Partitioning
For future releases with highly customized allowed type configurations, implement a Python-level round-robin subjective quota distributor to guarantee perfect and balanced sub-type spreads instead of delegating the count division to the LLM.
* **The Proposed Algorithm:**
  ```python
  allowed_subjective_types = [t for t in allowed_types if t.is_subjective]
  subjective_quotas = {t: 0 for t in allowed_subjective_types}
  
  if allowed_subjective_types:
      for idx in range(subjective_count):
          # Distribute quotas evenly in a round-robin loop
          target_type = allowed_subjective_types[idx % len(allowed_subjective_types)]
          subjective_quotas[target_type] += 1
  ```
  This guarantees that exact type sub-quotas are passed directly into the LLM system prompts, ensuring 100% predictable paper layouts.

### 2. Collaborative Reviews & Co-Authorship
A workspace feature allowing educators to share draft exam configurations and layouts for peer review or approval before final PDF compile.

- **Shared Links**: Owners can click a "Share Draft" button to generate a unique view-only or edit-enabled share link (e.g., `/papers/shared/[token]`).
- **Access Permissions**:
  - `view`: Reviewers can read the syllabus, standard, and generated question candidates.
  - `comment`: Reviewers can leave comments or reactions on individual questions (e.g., "Too difficult for standard 10").
  - `edit`: Reviewers (co-authors) can actively replace questions, regenerate chapters, and update counts.
- **Database Additions**:
  - `paper_shares` table: Maps share tokens to specific thread IDs and expiration timestamps.
  - `draft_comments` table: Stores comments linked to question IDs, authors, and timestamps.

### 3. 💾 Preset Templates & Syllabi Quick-Loaders
The Idea: Teachers frequently draft exams for the same subjects, standards, and chapters across semesters.
The UX: Allow saving a configuration (e.g., Grade 10 Physics · Chapters 1, 2 & 4 · 40% Objective, 60% Subjective) as a preset template directly on the new paper screen. This saves the teacher from re-selecting presets every single time.


### 4. 🗂️ Global Searchable Question Bank & "My Favorites"
The Idea: When a teacher regenerates questions or selects specific candidates, the unused or highly-rated questions vanish.
The UX: Allow teachers to "star" or save individual high-quality AI-generated questions into a personal "Examiner's Question Bank". While creating a new paper, they can search and drag-and-drop these saved questions directly into the exam flow.

### 5. 🔌 Standardized REST API Error Handling & HTTP Status Migration
The Idea: Migrating the backend REST API responses away from the Option A status payload contract (`{"status": "failed"}` with a `200 OK` code) to a standard HTTP status code-driven design.
The Action:
*   Raise explicit `HTTPException(status_code=502/500/400, detail="...")` on adapter or service-level failures.
*   Refactor the frontend React application's API query layer (e.g., TanStack Query fetchers) to capture rejected promises and handle errors centrally (using error boundary toasts and network banners).

### 6. 📄 Decoupled Document Compiler Interface Integration in LangGraph
The Idea: Decouple the hardcoded HTML-to-PDF and DOCX compilation logic out of `core/graph/nodes.py` by retrieving a runtime-injected `DocumentCompiler` adapter from the execution config.
The Action:
*   Create a `core/adapters/local_document_compiler.py` implementing the `DocumentCompiler` interface.
*   Inject the compiler dependency inside `server/dependencies.py` and pass it down within `graph_runner` using `RunnableConfig`'s `configurable` parameters.
*   Retrieve and call the compiler dynamically inside the `pdf_node` in `core/graph/nodes.py`.

---

## Session Handoff Log (COMPLETED — 2026-07-19)

We completed end-to-end backend authentication decoupling, account activation guards, type-safe OTP purposes, and the full React frontend OTP verification UI workflow.

### 1. Work Accomplished

#### A. Backend Authentication & Account Activation (Completed)
*   **Decoupled Authentication Adapter (`AuthService`)**:
    *   Wired up user authentication and registration completely behind the `AuthService` interface in [auth.py](file:///home/jeet-daiya/Storage/Teddy/QuickPaperAI/core/interfaces/auth.py) and [custom_auth_service.py](file:///home/jeet-daiya/Storage/Teddy/QuickPaperAI/core/adapters/custom_auth_service.py).
    *   Wired up user authentication and registration completely behind the `AuthService` interface in [auth.py](file:///home/jeet-daiya/Storage/Teddy/QuickPaperAI/src/auth/interface.py) and [custom_auth_service.py](file:///home/jeet-daiya/Storage/Teddy/QuickPaperAI/src/auth/adapter.py).
    *   Wrapped all Supabase database queries in try-except blocks, logging issues on the server and raising user-friendly `500` HTTPExceptions.
*   **Enforced Account Activation Guards**:
    *   Blocked logins for unverified users directly at the adapter layer inside `authenticate_user`.
    *   Added account activation methods (`activate_user`) to the `UserRepository` interface and `SupabaseUserRepository` database adapter.
*   **Type-Safe OTP Purposes (`OTPPurpose`)**:
    *   Defined the `OTPPurpose` string enum in [user_schemas.py](file:///home/jeet-daiya/Storage/Teddy/QuickPaperAI/src/auth/user_schemas.py) supporting `"signup"` and `"reset_password"`.
    *   Refactored the request validators (`EmailRequest` and `OTPVerification`) to use the Enum.
    *   Secured `/send-email` to validate user existence based on purpose: checks that signup users exist but are inactive, and checks that reset password users exist and are active.
*   **Refactored Routes & Dependencies**:
    *   Updated the register, login, and verify routes to be fully asynchronous (`async def`/`await`).
    *   Cleaned up double-OTP generation bugs inside `/send-email`.
    *   Updated `get_current_user` in [dependencies.py](file:///home/jeet-daiya/Storage/Teddy/QuickPaperAI/src/dependencies.py) to consume the decoupled asynchronous `auth_service.verify_session` method.
*   **Created Frontend Integration Handoff**:
    *   Created [frontend_handoff.md](file:///home/jeet-daiya/.gemini/antigravity/brain/d55bfc1e-eb80-4f0e-964e-9a41204208f7/frontend_handoff.md) summarizing payload schemas, HTTP response statuses, and integration guidelines.

#### B. Frontend Auth Flow & OTP Verification (Completed)
*   **Frontend API Methods (`client/src/lib/api.ts`)**:
    *   Added `sendOtp` (`POST /auth/send-email`) with `{ email, purpose }`.
    *   Added `verifyOtp` (`POST /auth/verify-otp`) with `{ email, otp, purpose }`.
*   **Registration Flow (`client/src/routes/signup.tsx`)**:
    *   Updated submit logic so that after `/auth/register`, it automatically calls `api.sendOtp({ email, purpose: "signup" })` and navigates to `/verify-otp?email=${encodeURIComponent(email)}`.
*   **Dedicated OTP Verification Route (`client/src/routes/verify-otp.tsx`)**:
    *   Built `/verify-otp` route matching the Examiner's Desk notebook theme (`surface-paper`, `stamp-shadow`, paper rule borders, perforated edge).
    *   Embedded 6-digit `InputOTP` component from `@/components/ui/input-otp`.
    *   Added 60-second countdown timer for resending OTP codes (disabling the button during cooldown).
    *   Persisted JWT token `localStorage.setItem("token", data.access_token)` on verification success and redirected to home (`/`).
    *   Mapped specific error states: wrong OTP (`"incorrect code"`), 3-attempt 15-minute lockout (403), and rate limit cooldowns (429).
*   **Unverified Login Handling (`client/src/routes/login.tsx`)**:
    *   Intercepted 403 unverified user error responses on login.
    *   Added an inline action (`Verify Code →`) that dispatches `sendOtp` and navigates to `/verify-otp?email=...`.
*   **Build Verification**:
    *   Verified build with `npm run build` in `client/` (passed TypeScript type checking and TanStack router code generation).

#### C. OTP Delivery Fix & Forgot Password Workflow (Completed)
*   **Backend Environment Loading Fix (`server/main.py` & `fastmail_mailer.py`)**:
    *   Moved `load_dotenv()` to the top of `server/main.py` before importing `server.app`, ensuring `MAIL_FROM`, `MAIL_USERNAME`, and `MAIL_PASSWORD` are populated before `FastMailService` initialization.
    *   Added `load_dotenv()` to `core/adapters/fastmail_mailer.py`.
*   **Password Reset Backend Endpoints (`server/routes/auth_routes.py`)**:
    *   Added `update_password` to `AuthService` interface and `CustomAuthService` adapter using `UserRepository.update_user_password`.
    *   Added `ResetPasswordRequest` schema and `POST /auth/reset-password` endpoint validating reset tokens and updating user password hashes.
    *   Enforced `email.lower().strip()` across all auth routes (`/send-email`, `/verify-otp`, `/reset-password`).
*   **Frontend Forgot Password Integration (`client/src/routes/login.tsx` & `verify-otp.tsx`)**:
    *   Enhanced "Forgot password?" button visibility on the login card (vibrant vermillion uppercase font next to Password label).
    *   Submitting the forgot password email triggers `api.sendOtp({ email, purpose: "reset_password" })` and **instantly redirects** the user to `/verify-otp?email=...&purpose=reset_password`.
    *   Updated `/verify-otp` route to handle `purpose: "reset_password"`, providing a 6-digit passcode + new password form and executing `api.verifyOtp` followed by `api.resetPassword`.
    *   **Lockout Handling**: Automatically detects 15-minute rate lockout errors, hides the "Resend Code" button, disables submit buttons, and displays a clear `🔒 Account locked for 15 minutes` warning indicator.

#### D. LangGraph Checkpoint MSGPACK Serialization allowed list registration (Completed)
*   **Prevented Future Checkpoint Failures**:
    *   Configured the `JsonPlusSerializer` inside [dependencies.py](file:///home/jeet-daiya/Storage/Teddy/QuickPaperAI/server/dependencies.py) with a dedicated allowed module list: `core.models.schemas.PaperRequest`, `core.models.schemas.Question`, and `core.models.schemas.EvaluationPoint`.
    *   Passed this custom serializer to the `AsyncPostgresSaver` checkpointer instance in the lifespan startup block.
    *   This successfully resolves the `Deserializing unregistered type` warning logs in the console and prevents any future msgpack decoding blocks.


### 2. Core Architecture Interface-Adapter Refactoring (NEW — 2026-07-19)
We decoupled the core document formatting and compilation layers from the graph logic:
*   **PaperFormatter Abstraction (`core/interfaces/paper_formatter.py`)**:
    *   Defined abstract rendering contracts (`render_paper`, `render_answer_key`).
    *   Added concrete implementations: `HTMLPaperFormatter` (renders print-ready HTML files with KaTeX) and `MarkdownPaperFormatter` (renders semantic Markdown tables/paragraphs).
*   **DocumentCompiler Abstraction (`core/interfaces/document_compiler.py`)**:
    *   Defined conversion contracts (`generate_pdf`, `generate_docx`) independent of specific rendering engines.
    *   Implemented `CustomDocumentCompiler` (`core/adapters/document_compiler.py`) wrapping Playwright PDF printing and Pandoc DOCX conversions.
*   **Dependency Injection in Graph Nodes (`core/graph/config.py`)**:
    *   Designed a centralized `GraphConfig` schema (`TypedDict`) encapsulating formatting and compilation dependencies.
    *   Updated the graph runner (`runner.py`) and routers (`paper_routes.py`) to inject singletons (`Depends`) via the `RunnableConfig`'s `configurable` parameters.
    *   Refactored the `pdf_node` in `core/graph/nodes.py` to extract dependencies from configuration and retrieve them with type casting (`typing.cast`), guaranteeing 100% IDE type-safety and autocomplete in PyCharm.

  ### 3. Redis-Based Best-Effort Progress Tracker (NEW — 2026-07-19)
We migrated the in-memory progress tracking logic to a Redis-backed store using `upstash-redis` to support state sharing across multiple server/Uvicorn worker processes:
*   **ProgressTracker Class (`core/graph/tracker.py`)**:
    *   Stores chapter progress inside a Redis Hash (`HSET`) keyed by `progress:{thread_id}`.
    *   Serializes the progress payloads as JSON and sets a TTL of 2 hours (`EXPIRE`) to prevent memory leaks in Redis.
    *   Implements **best-effort graceful degradation**: read, write, and delete exceptions are caught, logged, and silenced. If Redis is down, paper generation continues normally, and read operations safely return an empty dict `{}`.
*   **Dependency Injection Integration**:
    *   Registered `get_progress_tracker` in [dependencies.py](file:///home/jeet-daiya/Storage/Teddy/QuickPaperAI/src/dependencies.py) to manage the Redis client lifecycle.
    *   Injected the tracker into `GraphConfig` so fanned-out graph nodes (`question_generator_node`) can update chapter progress concurrently and safely without race conditions.
    *   Updated `/generate`, `/status/{thread_id}`, and `/cancel/{thread_id}` routes in [routes.py](file:///home/jeet-daiya/Storage/Teddy/QuickPaperAI/src/paper/routes/routes.py) to utilize the new async progress tracker.

### 3. To-Do / Future Roadmap Items

*   **Redis-Backed Durable Progress Tracker & Task Manager**:
    *   **Goal**: Replace the in-memory progress tracker (`PROGRESS_TRACKER`) and task registry (`RUNNING_TASKS`) with a Redis-backed adapter (`core/graph/tracker.py`) to make paper generation tasks durable across server crashes, worker restarts, and multi-process horizontal scaling (Uvicorn `--workers > 1`).
    *   **State Persistence**: Store chapter progress inside Redis Hashes (`HSET`) keyed by `progress:{thread_id}` with a 2-hour TTL (`EXPIRE`).
    *   **Cooperative Cancellation & Pub/Sub**: Implement cooperative task cancellation and Redis Pub/Sub cancellation broadcasting so that `/cancel/{thread_id}` requests routed to *any* worker instance can abort running background tasks across all processes.
    *   **Graceful Degradation**: Maintain silent fallback to safe defaults (empty dict / log warnings) if Redis or the network connection goes down, ensuring paper generation is never blocked.

### 4. Feature-Based Modular Architecture (`src/`) Completion (COMPLETED — 2026-07-25)

We consolidated the legacy `core/` and `server/` packages into a unified, industry-standard **Feature-Based Modular Architecture** under `src/`:

#### A. Unified Feature Modules (`src/`)
- **`src/auth/`**: Autonomous authentication package (`interface.py`, `adapter.py`, `otp_store.py`, `routes.py`, `schemas.py`, `email_template.py`).
- **`src/paper/`**: Question paper generation package (`models.py`, `schemas.py`, `service.py`, `task_manager.py`, `routes.py`, `rate_limiter.py`, `graph/`, `compilers/`, `formatters/`).
- **`src/db/`**: Database repositories and services package (`interfaces.py`, `adapters.py`, `service.py`, `routes.py`).
- **`src/storage/`**: File storage package (`interfaces/`, `adapters/`).
- **`src/mail/`**: Mail delivery package (`interfaces/`, `adapters/`).
- **`src/config.py`**: Centralized application settings (`Settings`).
- **`src/dependencies.py`**: FastAPI dependency provider container.
- **`src/app.py` & `src/main.py`**: FastAPI application factory and Uvicorn entrypoint.

#### B. Domain Enums & Graph Modularization
- Created `ChapterStatus`, `DocumentType`, `SubjectType`, and `PaperDifficulty` enums in `src/paper/models.py`.
- Extracted `src/paper/graph/utils.py` (`clean_latex`, `format_batch`, `group_by_subtopic`, `build_quota_instructions`).
- Refactored `src/paper/graph/nodes.py` to purge top-level import-time side effects and consume `utils.py`.

#### C. Clean Folder Layout & CLI Scripts
- Moved NCERT Grade 10 PDFs to `data/Std_10_Chapters/`.
- Moved notebooks and CLI tools to `scripts/` (`parse_textbooks.ipynb`, `run_cli.py`, `recover_paper.py`).
- Purged all root test PDFs (`core/paper.pdf`, `core/answer.pdf`), legacy dead code (`server/db.py`, `core/db/db.py`), and redundant markdown files.
- Updated root `Dockerfile` to copy `src/` and `data/` and execute `uvicorn src.app:app`.
- Verified 100% syntax compilation across all files in `src/` and `scripts/` using `py_compile`.

### 5. Firebase Cloud Messaging (FCM) Push Notifications & Device Token Endpoints (COMPLETED — 2026-07-26)

We implemented a full-stack, autonomous **FCM Push Notification** system across the backend (`src/`) and frontend client (`client/`):

#### A. Backend Service Adapter & Messages (`src/notifications/` & `src/db/`)
- **Messages**: Created `NotificationMessages` class in `src/notifications/constants/notification_messages.py` managing template titles, bodies, and review redirection URLs (`/papers/{thread_id}/review`).
- **Adapter**: Created `FirebaseNotificationService` in `src/notifications/adapters/firebase_notification_service.py` consuming `firebase-admin` SDK with dynamic `FRONTEND_URL` resolution and HTTPS webpush link validation.
- **Database Repository**: Extended `UserRepository` & `SupabaseUserRepository` (`src/db/adapters/supabase_db.py`) with `save_fcm_token`, `update_notification_perms`, `get_fcm_token`, and `get_notification_perms` using `user_id.strip()`.
- **REST APIs (`src/auth/routes/routes.py`)**:
  - `POST /auth/device-token`: Saves FCM token to Supabase `users.fcm_token`.
  - `POST /auth/notification-settings`: Updates user notification permissions (`data: NotificationToggleRequest`).
  - `GET /auth/notification-settings`: Fetches current notification status and active FCM token.

#### B. Frontend FCM Client Hook & Service Worker (`client/`)
- **Firebase Initialization (`client/src/lib/firebase.ts`)**: Configured Web App credentials (`quickpaperai-fc0db`) with `messagingSenderId: "286258662494"`.
- **Service Worker (`client/public/firebase-messaging-sw.js`)**: Background notification handler and `notificationclick` redirection listener opening `/papers/${thread_id}/review`. Suppresses duplicate manual `showNotification` calls when `payload.notification` is present.
- **Custom React Hook (`client/src/hooks/useFCMNotification.ts`)**: Manages browser permission prompts, device token registration, preference toggling, auto-prompting on authenticated user visits, and foreground messaging with interactive Sonner toast alerts ("View Paper →").
- **UI Integration**: Rendered interactive Permission Prompt Cards and Notification Settings toggles in `/new` setup screen and root home desk (`/`).

#### C. Async Trigger Hooks & Logging Verification
- Injected `FirebaseNotificationService` into `PaperService` via `src/dependencies.py`.
- **Review Ready Notification**: Dispatches non-blocking async push notifications inside `graph_runner()` when question generation reaches the `review_node` HITL interrupt.
- **Failure Notification**: Dispatches failure notifications inside exception handlers if question generation crashes.
- Standardized ASCII log formatting (`[INFO]`, `[DEBUG]`, `[WARN]`, `[ERROR]`).
- Verified 100% syntax compilation across all Python files using `python -m compileall src/`.

### 6. Durable Task Queue Architecture & Worker Implementation (COMPLETED — 2026-08-01)

We migrated the background paper generation system from in-memory single-process `asyncio.Task` execution to a production-grade, crash-resilient **Durable Task Worker Architecture** powered by **ARQ (Async Redis Queue)** and **LangGraph PostgreSQL Checkpoints**:

#### A. Durable Task Manager & Dependency Injection (`src/paper/task_manager.py` & `src/dependencies.py`)
- **Durable `TaskManager`**: Replaced in-memory `dict[str, asyncio.Task]` with ARQ Redis pool.
  - `register_task`: Enqueues jobs into Upstash Redis via `enqueue_job("generate_paper_task", thread_id, payload, user_fcm_token, _job_id=thread_id)` with `_job_id` deduplication.
  - `cancel_task`: Aborts active or queued jobs via `Job(thread_id, redis_pool).abort()`.
  - `is_running`: Queries job status via `job.status()` (`queued`, `in_progress`).
- **Dependencies (`src/dependencies.py`)**: Added `get_arq_pool()` and updated `get_task_manager()` to inject `ArqRedis` instances.

#### B. Worker Settings & Services (`src/paper/worker/settings.py`)
- **`WorkerSettings`**: Configured ARQ worker settings (`functions = [generate_paper_task]`, `max_tries = 3`, `job_timeout = 3600`).
- **TLS Redis Connection (`get_redis_settings`)**: Parses `settings.REDIS_URL` (`rediss://...`) for SSL/TLS connections to Upstash Redis.
- **Worker Lifecycle Hooks**:
  - `on_startup(ctx)`: Initializes persistent `AsyncConnectionPool` for PostgreSQL `AsyncPostgresSaver`, compiles LangGraph `agent`, and populates `ctx` with all singletons (`progress_tracker`, `notification_service`, `chunk_repo`, `html_paper_formatter`, `markdown_paper_formatter`, `document_compiler`, `paper_repo`, `user_repo`).
  - `on_shutdown(ctx)`: Gracefully closes the database connection pool.

#### C. Worker Task Runner & PostgreSQL Checkpoint Resumption (`src/paper/worker/tasks.py`)
- **`generate_paper_task`**: Executes or resumes paper generation jobs in background worker processes.
  - Reconstructs `PaperRequest` domain Pydantic model from `paper_request_dict` payload.
  - Queries `agent.aget_state({"configurable": {"thread_id": thread_id}})` from PostgreSQL.
  - **Resumption Logic**: If a checkpoint exists (after a worker or server crash), calls `run_graph(agent, paper_state=None, dependencies=dependencies, thread_id=thread_id)` to skip completed chapters and resume execution at the exact interrupted step.
  - **Fresh Execution**: If no checkpoint exists, initializes `PaperState` and runs from `START`.
  - **FCM Push Dispatch**: Inspects `post_run_snapshot` for `review_node` interrupts and dispatches FCM "Questions Ready for Review!" push notifications.
  - **Retry & Failure Handling**: Retries transient errors up to 3 times (`job_try`). On final retry failure, marks all chapters as `FAILED` in Redis and dispatches the "Generation Failed" push notification.

#### D. Graph Runner & Service Refactoring (`src/paper/graph/runner.py` & `src/paper/service.py`)
- **`run_graph` ([src/paper/graph/runner.py](file:///home/jeet-daiya/Storage/Teddy/QuickPaperAI/src/paper/graph/runner.py))**: Updated to handle both initial state generation (`paper_state` dict) and checkpoint resumption runs (`paper_state=None` with explicit `thread_id`).
- **`PaperService.generate_paper` ([src/paper/service.py](file:///home/jeet-daiya/Storage/Teddy/QuickPaperAI/src/paper/service.py#L292-L305))**: Delegates job registration to `TaskManager.register_task()`, returning `{"thread_id": thread_id, "status": "generating"}` to FastAPI in **<50ms**.
- **`PaperService.resume_generation` ([src/paper/service.py](file:///home/jeet-daiya/Storage/Teddy/QuickPaperAI/src/paper/service.py#L323-L345))**: Refactored interrupt detection to scan all tasks in `snapshot.tasks` and `snapshot.next`. Removed invalid `task_manager.register_task` call.

#### E. Defensive Type Coercion & CORS Fixes (`src/paper/graph/utils.py` & `src/app.py`)
- **`build_quota_instructions` ([src/paper/graph/utils.py](file:///home/jeet-daiya/Storage/Teddy/QuickPaperAI/src/paper/graph/utils.py#L61-L80))**: Added defensive type coercion converting raw string elements in `allowed_types` to `QuestionTypes` Enum instances, preventing `AttributeError: 'str' object has no attribute 'is_objective'`.
- **CORS Support ([src/app.py](file:///home/jeet-daiya/Storage/Teddy/QuickPaperAI/src/app.py#L12-L18))**: Updated `CORSMiddleware` to use `allow_origin_regex=".*"` for full credentialed cross-origin requests.

#### F. Verification & Durability
- Verified 100% syntax compilation across all files in `src/` using `python3 -m compileall src/`.
- Verified worker daemon CLI startup: `arq src.paper.worker.settings.WorkerSettings`.

---

### 7. Real-Time SSE Progress Streaming & Redis Pub/Sub Integration (COMPLETED — 2026-08-02)

We implemented an end-to-end **Real-Time Server-Sent Events (SSE)** progress streaming pipeline across the backend (`src/`) and frontend client (`client/`):

#### A. Backend Redis Pub/Sub & Streaming (`src/paper/graph/tracker.py` & `src/paper/routes/routes.py`)
- **Pub/Sub Channel Key**: Added `_get_chanel_key(thread_id)` in `ProgressTracker` returning `channel:progress:{thread_id}`.
- **Event Publishing (`update_chapter_progress`)**: Publishes JSON progress payloads (`chapter`, `status`, `generated_count`) to Redis Pub/Sub channel `channel:progress:{thread_id}` via `await self.redis_client.publish(channel=channel, message=json.dumps(payload))` as each chapter generates.
- **FastAPI SSE Stream Endpoint (`GET /api/status/{thread_id}/stream`)**: Created streaming response endpoint using `text/event-stream` media type. Streams real-time progress events over 1 long-lived HTTP connection and terminates stream automatically when reaching `completed`, `failed`, or `awaiting_review` states.

#### B. Frontend Stream URL Builder & Custom React Status Hook (`client/`)
- **Stream URL Builder (`client/src/lib/api.ts`)**: Added `api.statusStreamUrl(threadId: string)` helper in `client/src/lib/api.ts` appending JWT token in query parameter (`?token=...`) for native browser `EventSource` authentication.
- **Exclusive SSE Status Hook (`client/src/hooks/useGenerationStatus.ts`)**: Updated `useGenerationStatus(threadId: string)` to consume the SSE stream exclusively (`GET /api/status/${threadId}/stream?token=...`).
  - **SSE Connection**: Establishes native `EventSource` stream connection.
  - **Automatic Connection Termination**: Automatically closes stream connection (`es.close()`) when status reaches terminal states (`completed`, `failed`, or `awaiting_review`).
  - **Unmount Cleanup**: Calls `eventSource.close()` inside `useEffect` cleanup callback to prevent open connections.

#### C. UI Route Integration & PDF Preview (`client/src/routes/`)
- **Progress Route (`client/src/routes/papers.$threadId.progress.tsx`)**: Consumes `useGenerationStatus(threadId)`. Renders `SSE Real-Time` indicator badge and zero-latency chapter progress statuses (`✓ complete`, `✗ failed`, `● processing`, `○ pending`).
- **Review Route (`client/src/routes/papers.$threadId.review.tsx`)**: Consumes `useGenerationStatus(threadId)` with narrowed TypeScript discriminant union types.
- **Done & Preview Route (`client/src/routes/papers.$threadId.done.tsx`)**: Updated to consume `useGenerationStatus(threadId)` and render the PDF iframe viewer using `${API_BASE}${files.paper_pdf}?preview=true&token=${token}` upon completion.
- Verified 100% syntax compilation across `src/` (`python3 -m compileall src/`) and TypeScript type-checking across `client/` (`npx tsc --noEmit`).

---

### 8. Async Playwright PDF Generation Fix (COMPLETED — 2026-08-17)

We resolved a critical runtime error in PDF document compilation:

#### A. Root Cause
- The old PDF compiler (`CustomDocumentCompiler`) was calling `sync_playwright()` inside `pdf_node` within Python's `asyncio` event loop (FastAPI & ARQ Background Worker).
- Python's Playwright library throws `playwright._impl._errors.Error: It looks like you are using Playwright Sync API inside the asyncio loop` when synchronous Playwright methods are invoked inside an active `asyncio` loop.

#### B. Async Conversion & Verification
- **Interface (`src/paper/compilers/interfaces/interface.py`)**: Converted `generate_pdf` and `generate_docx` methods on `DocumentCompiler(ABC)` to `async def`.
- **Adapter (`src/paper/compilers/adapters/document_compiler.py`)**: Converted `CustomDocumentCompiler` to consume `playwright.async_api.async_playwright` (`async with async_playwright() as p:`, `await p.chromium.launch()`, `await page.pdf(...)`).
- **Graph Nodes (`src/paper/graph/nodes.py`)**: Converted `pdf_node` to `async def pdf_node` and added `await document_compiler.generate_pdf(...)` and `await document_compiler.generate_docx(...)`.
- **Standalone Generator (`src/paper/compilers/generator.py`)**: Converted standalone CLI helper `generate_pdf` to `async def` using `async_playwright`.
- Verified 100% compilation across `src/` (`python3 -m compileall src/`) and ran live headless Chromium test generating `/tmp/test_paper.pdf`.

---

## Suggested Skills for Next Agent

* **handoff**: Use the `handoff` skill to update or compact session context into `walkthrough.md` for team handoffs.
* **grill-me**: Use `grill-me` when interviewing the user or stress-testing technical designs, API schemas, and feature proposals before implementation.`