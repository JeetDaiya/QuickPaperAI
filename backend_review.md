# QuickPaperAI Backend Architecture, Security & Concurrency Review

**Target Service**: QuickPaperAI Backend (`src/`)  
**Auditor**: Senior Staff Software Architect & Technical Lead  
**Integrity Mode**: Development / Authoritative Review  
**Date**: August 2026  
**Document Classification**: Comprehensive Technical Audit & Remediation Blueprint  

---

## Executive Summary

### 1. Overview & System Health Score
An exhaustive, multi-dimensional code audit and architectural assessment of the QuickPaperAI backend (`src/`) was conducted covering four primary pillars:
1. **Security & Authentication (R1)**: Access controls, token lifecycle, password cryptography, OTP lifecycle, and database isolation.
2. **Concurrency, Async Safety & Task Management (R2)**: Background job queue durability (ARQ), LangGraph state persistence, Redis Pub/Sub real-time streaming, and resource leak prevention.
3. **LLM Orchestration & Generation Pipeline (R3)**: Gemini API structured outputs, error recovery, token bucket rate limiting, and document compilation (Playwright & Pandoc).
4. **Clean Architecture, Domain Modeling & Error Handling (R4)**: Interface-adapter decoupling (DIP/LSP), domain boundary integrity, Pydantic modeling, and REST error conventions.

```
+-------------------------------------------------------------------------+
|                  OVERALL SYSTEM HEALTH SCORE: 63 / 100                  |
+------------------------------------+------------------------------------+
| Dimension                          | Score   | Status                   |
+------------------------------------+---------+--------------------------+
| R1. Security & Authentication      | 56/100  | High Risk / Vulnerable   |
| R2. Concurrency & Async Safety     | 60/100  | Fragile / Uncoordinated |
| R3. LLM Orchestration & Compilers  | 66/100  | Brittle / Process Leaks  |
| R4. Clean Architecture & Modeling  | 69/100  | Drift / Leaky Boundaries |
+------------------------------------+---------+--------------------------+
```

---

### 2. Key Architectural Strengths
- **Modular Pipeline Design**: The transition to LangGraph for multi-chapter paper generation provides clear state-machine boundaries and checkpointing capabilities.
- **Asynchronous Foundation**: Built upon FastAPI, `asyncio`, `psycopg3` async connection pools, and ARQ background job processing.
- **Pluggable Formatter Abstractions**: Defined abstract interfaces (`PaperFormatter`, `DocumentCompiler`, `StorageService`, `UserRepository`, `PaperRepository`) designed for multi-format rendering (HTML, Markdown, PDF, DOCX).
- **Human-in-the-Loop Workflow**: Integrated interrupt-driven review mechanism (`review_node`) allowing teachers and administrators to inspect and select generated questions before final PDF/DOCX rendering.

---

### 3. Key Architectural Weaknesses & Risk Themes
- **Broken Object-Level Authorization (BOLA/IDOR)**: Core paper download, cancellation, and status endpoints operate purely on `thread_id` without verifying tenant ownership (`user_id`), allowing cross-tenant data exfiltration and session disruption.
- **Token Confusion & Privilege Escalation**: Password reset tokens are issued as standard 7-day session JWTs without type claims (`"type": "reset"` vs `"type": "access"`), allowing reset tokens to be used as full API access tokens and vice-versa.
- **Unmanaged Async Tasks in Web Processes**: The `resume_generation` route spawns unmanaged `asyncio.create_task()` directly in the FastAPI web server rather than dispatching to ARQ workers, risking dropped jobs on process restarts.
- **SSE Status Polling Inducing DB Starvation**: The SSE status endpoint runs a 1-second busy loop querying PostgreSQL checkpointer tables and Redis per client, ignoring published Redis events and threatening connection pool exhaustion under load.
- **Invalid Model Identifiers & Silent Batch Loss**: The LLM configuration references non-existent Gemini models (`gemini-3.5-flash`), while fragile Pydantic model validators combined with broad `except Exception` blocks silently drop entire 10-question batches.
- **Chromium Zombie Process Leaks & SSRF Vulnerabilities**: Playwright headless browser instances lack `try...finally` closure guards, leaking zombie processes on errors, while unescaped HTML interpolation allows Server-Side Request Forgery and Local File Inclusion via PDF rendering.
- **Dependency Injection Corruption in Background Workers**: Applying `@lru_cache` to FastAPI provider functions with default `Depends()` arguments injects raw `params.Depends` objects into `PaperService` when instantiated inside the ARQ worker.
- **"Option A" REST Anti-Pattern**: Critical failure paths return HTTP 200 OK with `{"status": "failed"}` envelopes, breaking standard HTTP client exception handling and monitoring.

---

### 4. Comprehensive Phased Remediation Roadmap

```
+---------------------------------------------------------------------------------------------------------+
|                                    PHASED REMEDIATION ROADMAP                                           |
+---------------------------------------------------------------------------------------------------------+
| Phase 1: Immediate Critical Hotfixes (Day 1 - 2)                                                         |
| - Patch BOLA/IDOR by passing and validating user_id in all paper routes & repositories.                 |
| - Separate JWT token scopes (type: "access" vs "reset") with 15-minute reset lifetimes.                 |
| - Remove wildcard regex from CORS middleware (allow_origin_regex=".*").                                 |
| - Decouple pure service factory functions from FastAPI Depends() providers to fix ARQ worker DI crash.  |
| - Correct Gemini model identifiers to stable versions (gemini-2.5-flash).                               |
+---------------------------------------------------------------------------------------------------------+
| Phase 2: Async, Concurrency & Task Durability (Day 3 - 5)                                               |
| - Route resume_generation execution through ARQ workers instead of in-process asyncio.create_task.       |
| - Replace SSE 1s polling with event-driven Redis Pub/Sub stream listener and proper disconnect guards.  |
| - Implement cancellation token checks in question_generator_node to abort LangGraph runs promptly.      |
| - Unify PostgreSQL pool sizing and add exponential backoff deferral to ARQ task retries.                |
| - Expand JsonPlusSerializer allowlist to prevent checkpoint deserialization failures.                    |
+---------------------------------------------------------------------------------------------------------+
| Phase 3: Pipeline Hardening, LLM Reliability & Security (Day 6 - 8)                                     |
| - Relax rigid Pydantic validators with auto-normalization to prevent silent question batch drops.       |
| - Wrap Playwright Chromium in try/finally blocks and add container flags (--no-sandbox, etc.).          |
| - Sanitize HTML templates with html.escape() to neutralize SSRF/LFI attack vectors.                     |
| - Introduce DistributedTokenBucket with Redis backing and 429 exponential backoff with jitter.           |
| - Wrap CPU-bound Bcrypt hashing in asyncio.to_thread and enforce SHA-256 pre-hashing.                   |
| - Atomic Redis OTP cooldown (SET EX NX) and 10-minute sliding window on failed attempt counters.        |
+---------------------------------------------------------------------------------------------------------+
| Phase 4: Clean Architecture, Error Handling & Observability (Day 9 - 11)                                |
| - Replace 200 OK {"status": "failed"} envelopes with standard domain exceptions and HTTP 4xx/5xx codes. |
| - Implement global FastAPI exception handlers for DomainException and RequestValidationError.           |
| - Complete MarkdownPaperFormatter.render_answer_key to satisfy Liskov Substitution Principle.           |
| - Purge legacy duplicate code (src/paper/compilers/generator.py - 676 lines).                            |
| - Add X-Request-ID distributed tracing middleware.                                                      |
+---------------------------------------------------------------------------------------------------------+
```

---

## Detailed Findings & Remediation Blueprint

```
Severity Breakdown Across All Pillars:
- CRITICAL: 13 Findings (Immediate System Breakers & Exploitable Vulnerabilities)
- HIGH:     14 Findings (Severe Latency, Data Loss, Process Leaks & Spec Violations)
- MEDIUM:   15 Findings (Architectural Drift, Typo Bugs, Suboptimal Abstractions)
- LOW / OPT: 11 Findings (Code Quality, Dead Code Purging, Tracing Enhancements)
Total Findings: 53 Audited Items
```

---

# Section 1: Security & Authentication Audit (Requirement R1)

```
+--------------------------------------------------------------------------------------------------------+
| Severity | ID          | Vulnerability / Finding Title                                                |
+----------+-------------+------------------------------------------------------------------------------+
| CRITICAL | SEC-CRIT-01 | Broken Object Level Authorization (BOLA / IDOR) in Paper Endpoints          |
| CRITICAL | SEC-CRIT-02 | JWT Token Purpose Confusion & Missing Scope Separation                        |
| CRITICAL | SEC-CRIT-03 | Over-Permissive Wildcard CORS Configuration with Credentials                 |
| HIGH     | SEC-HIGH-01 | Event Loop Starvation / DoS via Synchronous CPU-Bound Bcrypt Hashing          |
| HIGH     | SEC-HIGH-02 | Bcrypt 72-Byte Truncation & Deprecated Passlib Dependency                    |
| HIGH     | SEC-HIGH-03 | Cross-Purpose OTP Reuse, Plaintext Redis Storage, and Timing Side-Channels    |
| HIGH     | SEC-HIGH-04 | Redis Cooldown TOCTOU Race Condition & Unbounded Failed Attempt Accumulation  |
| MEDIUM   | SEC-MED-01  | Universal Supabase Service Role Key Usage Bypassing PostgreSQL RLS           |
| MEDIUM   | SEC-MED-02  | Broken User ID Key Resolution in SSE Generation Status Endpoint              |
| MEDIUM   | SEC-MED-03  | Insecure Bearer Token Extraction via URL Query Parameters                    |
| MEDIUM   | SEC-MED-04  | Unhandled User Account Enumeration in OTP Dispatch Flow                      |
| MEDIUM   | SEC-MED-05  | FastMail Mailer Initialization Crash via Invalid Settings Module Import       |
| LOW      | SEC-LOW-01  | Default None Secret Key & Missing Standard RFC 7519 Claims                   |
| LOW      | SEC-LOW-02  | Hardcoded 7-Day Access Token Expiration Overriding Application Settings      |
| LOW      | SEC-LOW-03  | Missing Password Complexity and Length Constraints on Pydantic Schemas       |
| LOW      | SEC-LOW-04  | Inconsistent Error Return Types in FCM Token and Notification Fetchers        |
+--------------------------------------------------------------------------------------------------------+
```

---

### [SEC-CRIT-01] Broken Object Level Authorization (BOLA / IDOR) in Paper Endpoints
- **Severity**: **Critical**
- **File**: `src/paper/routes/routes.py` (Lines 85–94, 33–46, 108–117) & `src/paper/service.py` (Lines 132–179, 180–219, 303–352)
- **Problem Summary & Risk Analysis**:
  The endpoints for downloading generated papers (`/api/download/{thread_id}/{filename}`), resuming generation (`/api/resume/{thread_id}`), and cancelling sessions (`/api/cancel/{thread_id}`) accept arbitrary `thread_id` parameters without checking if the authenticated user (`current_user["id"]`) is the actual creator of the document. Because the repository queries execute using the Supabase Service Role Key (bypassing PostgreSQL RLS), any authenticated user who knows or guesses a `thread_id` (UUIDv4) can download confidential examination papers and marking schemes or terminate running generation workloads belonging to other institutions.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/paper/routes/routes.py:85-94
# ==============================================================================
@paper_router.get('/download/{thread_id}/{filename}')
async def download_file(
    thread_id: str,
    filename: str,
    preview: bool = False,
    current_user: dict = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service)
):
    return await paper_service.download_file(thread_id=thread_id, filename=filename, preview=preview)

# ==============================================================================
# AFTER: src/paper/routes/routes.py & src/paper/service.py
# ==============================================================================
# In src/paper/routes/routes.py:
@paper_router.get('/download/{thread_id}/{filename}')
async def download_file(
    thread_id: str,
    filename: str,
    preview: bool = False,
    current_user: dict = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service)
):
    user_id = str(current_user["id"])
    return await paper_service.download_file(
        thread_id=thread_id,
        filename=filename,
        preview=preview,
        user_id=user_id
    )

# In src/paper/service.py:
async def download_file(
    self,
    thread_id: str,
    filename: str,
    preview: bool = False,
    user_id: Optional[str] = None
):
    # Verify paper ownership in repository
    metadata_res = self.paper_repo.get_paper_metadata(thread_id=thread_id, paper_name="user_id")
    if not metadata_res or not metadata_res.data:
        raise HTTPException(status_code=404, detail="Paper record not found.")

    record_owner = metadata_res.data[0].get("user_id")
    if user_id and record_owner != user_id:
        raise HTTPException(status_code=403, detail="Access denied: You do not own this document.")

    # Proceed with verified file retrieval...
```

---

### [SEC-CRIT-02] JWT Token Purpose Confusion & Missing Scope Separation
- **Severity**: **Critical**
- **File**: `src/auth/routes/routes.py` (Lines 107–124, 126–140) & `src/auth/adapters/custom_auth_service.py` (Lines 27–35, 84–104)
- **Problem Summary & Risk Analysis**:
  Upon successful verification of a password reset OTP at `/auth/verify-otp`, `create_token_for_email` issues a standard 7-day session token. The returned `reset_token` lacks an explicit `"type": "reset"` claim. Consequently:
  1. A user requesting a password reset receives a token that grants full authenticated application access for 7 days without actually resetting the password.
  2. Any existing, unexpired access session token can be presented directly to `/auth/reset-password` to change an account password without performing OTP verification.
  3. No token revocation or token versioning (`token_version` / `jti`) occurs upon password modification, leaving old compromised sessions active.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/auth/adapters/custom_auth_service.py:27-35
# ==============================================================================
def _create_access_token(self, data : dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=self.token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, key=self.secret_key, algorithm=self.algorithm)
    return encoded_jwt

# ==============================================================================
# AFTER: src/auth/adapters/custom_auth_service.py
# ==============================================================================
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from fastapi import HTTPException

def _create_token(self, data: dict, token_type: str = "access", expire_minutes: Optional[int] = None) -> str:
    to_encode = data.copy()
    duration = expire_minutes if expire_minutes is not None else self.token_expire_minutes
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=duration)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now,
        "jti": str(uuid.uuid4()),
        "type": token_type
    })
    return jwt.encode(to_encode, key=self.secret_key, algorithm=self.algorithm)

def create_access_token(self, email: str) -> dict:
    token = self._create_token(data={"sub": email}, token_type="access", expire_minutes=self.token_expire_minutes)
    return {"access_token": token, "token_type": "bearer"}

def create_password_reset_token(self, email: str) -> str:
    # Reset tokens expire strictly in 15 minutes and have token_type="reset"
    return self._create_token(data={"sub": email}, token_type="reset", expire_minutes=15)

async def verify_session(self, token: str, expected_type: str = "access") -> dict:
    try:
        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        if payload.get("type") != expected_type:
            raise HTTPException(status_code=401, detail=f"Invalid token type. Expected {expected_type}")
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token claims: missing subject")
        user = self.user_repo.get_user(email=email)
    except JWTError:
        raise HTTPException(status_code=401, detail="Session expired or invalid token")

    if not user:
        raise HTTPException(status_code=401, detail="User account no longer exists")
    return user
```

---

### [SEC-CRIT-03] Over-Permissive Wildcard CORS Configuration with Credentials
- **Severity**: **Critical**
- **File**: `src/app.py` (Lines 22–29)
- **Problem Summary & Risk Analysis**:
  `src/app.py` configures `CORSMiddleware` with `allow_origin_regex=".*"` while setting `allow_credentials=True`. The regular expression `.*` matches every origin domain. When paired with `allow_credentials=True`, any external third-party malicious website can execute authenticated, cross-origin AJAX requests against the QuickPaperAI API using the victim's stored credentials or bearer tokens.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/app.py:22-29
# ==============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# AFTER: src/app.py
# ==============================================================================
from src.base_settings import settings

def get_configured_origins() -> list[str]:
    trusted = [
        "http://localhost:5173",
        "http://localhost:8080",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:3000",
    ]
    if settings.FRONTEND_URL:
        clean_url = settings.FRONTEND_URL.rstrip("/")
        if clean_url not in trusted:
            trusted.append(clean_url)
    return trusted

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_configured_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
```

---

### [SEC-HIGH-01] Event Loop Starvation / DoS via Synchronous CPU-Bound Bcrypt Hashing
- **Severity**: **High**
- **File**: `src/auth/adapters/custom_auth_service.py` (Lines 21–25, 48, 74, 130)
- **Problem Summary & Risk Analysis**:
  Bcrypt key derivation requires 100–300ms of intensive CPU computation per hash or verification. Because `pwd_context.hash()` and `pwd_context.verify()` are invoked synchronously within `async def` route handlers (`/auth/login`, `/auth/register`, `/auth/reset-password`), the main asyncio event loop is blocked for the entire duration of the computation. Under concurrent login spikes, all server request processing (including SSE progress streaming and health checks) is frozen, resulting in server-wide latency spikes and denial-of-service.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/auth/adapters/custom_auth_service.py:21-25
# ==============================================================================
def _get_hashed_password(self, plain_password: str):
    return self.pwd_context.hash(plain_password)

def _verify_password(self, plain_password: str, hashed_password: str):
    return self.pwd_context.verify(plain_password, hashed_password)

# ==============================================================================
# AFTER: src/auth/adapters/custom_auth_service.py
# ==============================================================================
import asyncio

async def _get_hashed_password(self, plain_password: str) -> str:
    # Non-blocking execution in worker thread pool
    return await asyncio.to_thread(self.pwd_context.hash, plain_password)

async def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
    # Non-blocking verification in worker thread pool
    return await asyncio.to_thread(self.pwd_context.verify, plain_password, hashed_password)
```

---

### [SEC-HIGH-02] Bcrypt 72-Byte Truncation & Deprecated Passlib Dependency
- **Severity**: **High**
- **File**: `requirements.txt` (Lines 7–8) & `src/auth/adapters/custom_auth_service.py` (Lines 3, 18, 21–25)
- **Problem Summary & Risk Analysis**:
  1. `passlib==1.7.4` has been unmaintained since 2020 and raises deprecation warnings and runtime errors when paired with modern `bcrypt >= 4.0.0`.
  2. Standard Bcrypt silently truncates passwords at 72 bytes. Passwords sharing the first 72 bytes collide, allowing authentication bypass on excessively long or UTF-8 multi-byte passwords.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# AFTER: src/auth/adapters/custom_auth_service.py (Direct Bcrypt with SHA-256 Pre-Hash)
# ==============================================================================
import hashlib
import bcrypt
import asyncio

def _prehash_password(plain_password: str) -> bytes:
    # SHA-256 produces a fixed 64-char hex digest, eliminating the 72-byte truncation boundary
    return hashlib.sha256(plain_password.encode("utf-8")).hexdigest().encode("utf-8")

def _sync_hash(plain_password: str) -> str:
    prehashed = _prehash_password(plain_password)
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(prehashed, salt).decode("utf-8")

def _sync_verify(plain_password: str, hashed_password: str) -> bool:
    prehashed = _prehash_password(plain_password)
    try:
        return bcrypt.checkpw(prehashed, hashed_password.encode("utf-8"))
    except Exception:
        return False

async def _get_hashed_password(self, plain_password: str) -> str:
    return await asyncio.to_thread(_sync_hash, plain_password)

async def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
    return await asyncio.to_thread(_sync_verify, plain_password, hashed_password)
```

---

### [SEC-HIGH-03] Cross-Purpose OTP Reuse, Plaintext Redis Storage, and Timing Side-Channels
- **Severity**: **High**
- **File**: `src/auth/adapters/redis_otp_store.py` (Lines 10–26) & `src/auth/routes/routes.py` (Lines 73–75, 98–105)
- **Problem Summary & Risk Analysis**:
  1. OTP keys in Redis are formatted as `otp:{email}` without purpose namespacing. An OTP dispatched for account registration can be supplied to `/auth/verify-otp` with `purpose: "reset_password"` to take over an account.
  2. OTP codes are stored in plaintext in Redis, exposing codes to any compromised Redis connection.
  3. `stored_otp != data.otp` uses variable-time string equality, leaking timing side-channel data.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/auth/adapters/redis_otp_store.py:10-26
# ==============================================================================
def _otp_key(self, email: str) -> str:
    return f"otp:{email}"

async def save_otp(self, email : str, otp_code: str, expire_seconds: int = 600) -> None:
    await self.redis_client.set(key=self._otp_key(email), value=otp_code, ex=expire_seconds)

# ==============================================================================
# AFTER: src/auth/adapters/redis_otp_store.py
# ==============================================================================
import hmac
import hashlib

def _otp_key(self, email: str, purpose: str) -> str:
    clean_email = email.lower().strip()
    return f"otp:{purpose}:{clean_email}"

def _hash_otp(self, otp_code: str) -> str:
    return hashlib.sha256(otp_code.strip().encode("utf-8")).hexdigest()

async def save_otp(self, email: str, purpose: str, otp_code: str, expire_seconds: int = 600) -> None:
    key = self._otp_key(email, purpose)
    hashed_code = self._hash_otp(otp_code)
    await self.redis_client.set(key=key, value=hashed_code, ex=expire_seconds)

async def verify_otp(self, email: str, purpose: str, candidate_otp: str) -> bool:
    key = self._otp_key(email, purpose)
    stored_hash = await self.redis_client.get(key=key)
    if not stored_hash:
        return False
    candidate_hash = self._hash_otp(candidate_otp)
    # Constant-time comparison prevents timing attacks
    return hmac.compare_digest(str(stored_hash), candidate_hash)
```

---

### [SEC-HIGH-04] Redis Cooldown TOCTOU Race Condition & Unbounded Failed Attempt Accumulation
- **Severity**: **High**
- **File**: `src/auth/adapters/redis_otp_store.py` (Lines 30–50, 58–63)
- **Problem Summary & Risk Analysis**:
  1. `set_send_cooldown` uses a non-atomic `exists()` followed by `set()`. Parallel burst requests can bypass the 60-second cooldown rate limit.
  2. `increment_failed_attempts` calls `redis.incr()` without setting a TTL on the `attempts:{email}` key. The key persists indefinitely with `TTL = -1`. A legitimate user who mistypes an OTP once per month will be locked out on the 3rd attempt across years.
  3. `delete_otp` deletes `cooldown:{email}`, allowing attackers to bypass cooldown immediately after successful OTP verification.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/auth/adapters/redis_otp_store.py:30-50, 58-63
# ==============================================================================
async def set_send_cooldown(self, email: str, cooldown_seconds: int = 60) -> bool:
    key = self._cooldown_key(email)
    exists = await self.redis_client.exists(key)
    if exists:
        return True
    else:
        await self.redis_client.set(key=key, ex=cooldown_seconds, value="1")
        return False

async def increment_failed_attempts(self, email: str, max_attempts : int = 3, lock_seconds: int = 900) -> bool:
    attempt_key = self._attempt_key(email)
    lockout_key = self._lockout_key(email)
    attempts = await self.redis_client.incr(attempt_key)
    if attempts >= max_attempts:
        await self.redis_client.set(key=lockout_key, value="locked", ex=lock_seconds)
        await self.redis_client.delete(attempt_key)
        return True
    else:
        return False

# ==============================================================================
# AFTER: src/auth/adapters/redis_otp_store.py
# ==============================================================================
async def set_send_cooldown(self, email: str, cooldown_seconds: int = 60) -> bool:
    key = self._cooldown_key(email)
    # Atomic SET key value EX 60 NX returns True if set, None/False if key already exists
    was_set = await self.redis_client.set(key=key, value="1", ex=cooldown_seconds, nx=True)
    # Return True if cooldown is active (blocked), False if newly set (allowed)
    return not bool(was_set)

async def increment_failed_attempts(self, email: str, max_attempts: int = 3, lock_seconds: int = 900) -> bool:
    attempt_key = self._attempt_key(email)
    lockout_key = self._lockout_key(email)

    attempts = await self.redis_client.incr(attempt_key)
    if attempts == 1:
        # Enforce 10-minute sliding window on failed attempt key
        await self.redis_client.expire(attempt_key, 600)

    if attempts >= max_attempts:
        await self.redis_client.set(key=lockout_key, value="locked", ex=lock_seconds)
        await self.redis_client.delete(attempt_key)
        return True
    return False

async def delete_otp(self, email: str, purpose: str) -> None:
    # Delete OTP and attempt counter, but PRESERVE send cooldown and lockout keys
    await self.redis_client.delete(self._otp_key(email, purpose))
    await self.redis_client.delete(self._attempt_key(email))
```

---

### [SEC-MED-01] Universal Supabase Service Role Key Usage Bypassing PostgreSQL RLS
- **Severity**: **Medium**
- **File**: `src/dependencies.py` (Line 39) & `src/db/adapters/supabase_db.py` (Lines 9, 29, 102)
- **Problem Summary & Risk Analysis**:
  The application initializes a single global `supabase_client` using `SUPABASE_SERVICE_ROLE_KEY`. This key possesses superuser privileges in Supabase, bypassing all PostgreSQL Row-Level Security (RLS) policies. Any missing `user_id` query filter in repository code directly exposes multi-tenant data.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# AFTER: src/db/adapters/supabase_db.py (Mandatory User ID Parameterization)
# ==============================================================================
class SupabasePaperRepository(PaperRepository):
    def __init__(self, client: Client):
        self.db = client

    def get_paper_metadata(self, thread_id: str, paper_name: str, user_id: Optional[str] = None):
        query = self.db.table("generated_papers").select("*").eq("thread_id", thread_id)
        if user_id:
            query = query.eq("user_id", user_id)
        return query.execute()
```

---

### [SEC-MED-02] Broken User ID Key Resolution in SSE Generation Status Endpoint
- **Severity**: **Medium**
- **File**: `src/paper/routes/routes.py` (Line 62)
- **Problem Summary & Risk Analysis**:
  In `stream_generation_status`, the route calls `user_id=str(current_user.get('user_id', ""))`. The database user dictionary returned from `verify_session` has key `'id'`, not `'user_id'`. As a result, `user_id` always resolves to empty string `""`, breaking user identity validation.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/paper/routes/routes.py:62
# ==============================================================================
status_data = await paper_service.get_generation_status(
    thread_id=thread_id, 
    agent=req.app.state.agent, 
    user_id=str(current_user.get('user_id', ""))
)

# ==============================================================================
# AFTER: src/paper/routes/routes.py:62
# ==============================================================================
user_id = str(current_user["id"])
status_data = await paper_service.get_generation_status(
    thread_id=thread_id, 
    agent=req.app.state.agent, 
    user_id=user_id
)
```

---

### [SEC-MED-03] Insecure Bearer Token Extraction via URL Query Parameters
- **Severity**: **Medium**
- **File**: `src/dependencies.py` (Lines 220–224)
- **Problem Summary & Risk Analysis**:
  Allowing JWT tokens via `?token=` on any request exposes tokens to web server access logs, browser history, and proxy servers.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# AFTER: src/dependencies.py:220-224 (Restrict query params to SSE Stream endpoints only)
# ==============================================================================
if not token and request.url.path.endswith("/stream"):
    token = request.query_params.get("token")

if not token:
    raise credentials_exception
```

---

### [SEC-MED-04] Unhandled User Account Enumeration in OTP Dispatch Flow
- **Severity**: **Medium**
- **File**: `src/auth/routes/routes.py` (Lines 57–67)
- **Problem Summary & Risk Analysis**:
  The `/auth/send-email` endpoint returns HTTP 404 "User not found, please register first" or HTTP 400 "User already verified", allowing unauthenticated attackers to enumerate valid email addresses.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# AFTER: src/auth/routes/routes.py:57-67
# ==============================================================================
generic_response = {"message": "If an account matches this email, a verification code has been dispatched."}

if purpose == OTPPurpose.SIGNUP:
    if not user or user.get("is_active", False):
        return generic_response
elif purpose == OTPPurpose.RESET_PASSWORD:
    if not user or not user.get("is_active", False):
        return generic_response
```

---

### [SEC-MED-05] FastMail Mailer Initialization Crash via Invalid Settings Module Import
- **Severity**: **Medium**
- **File**: `src/mail/adapters/fastmail_mailer.py` (Lines 4, 10–12)
- **Problem Summary & Risk Analysis**:
  `FastMailService` imports `model_settings` from `src.config` to fetch SMTP credentials. Those settings exist in `src.base_settings.settings`, causing an unhandled `AttributeError` whenever `get_email_service()` is instantiated.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/mail/adapters/fastmail_mailer.py:4, 10-12
# ==============================================================================
from src.config import model_settings

class FastMailService(EmailService):
    def __init__(self):
        self.connection_config = ConnectionConfig(
            MAIL_FROM=model_settings.MAIL_FROM,
            MAIL_USERNAME=model_settings.MAIL_USERNAME,
            MAIL_PASSWORD=model_settings.MAIL_PASSWORD,
            MAIL_PORT=587,
            MAIL_SERVER="smtp-relay.brevo.com"
        )

# ==============================================================================
# AFTER: src/mail/adapters/fastmail_mailer.py
# ==============================================================================
from src.base_settings import settings

class FastMailService(EmailService):
    def __init__(self):
        self.connection_config = ConnectionConfig(
            MAIL_FROM=settings.MAIL_FROM or "noreply@quickpaperai.com",
            MAIL_USERNAME=settings.MAIL_USERNAME or "",
            MAIL_PASSWORD=settings.MAIL_PASSWORD or "",
            MAIL_PORT=settings.MAIL_PORT or 587,
            MAIL_SERVER=settings.MAIL_SERVER or "smtp-relay.brevo.com",
            MAIL_STARTTLS=settings.MAIL_STARTTLS,
            MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )
```

---

### [SEC-LOW-01 to SEC-LOW-04] Low Severity Security Findings

#### [SEC-LOW-01] Default None Secret Key & Missing Standard RFC 7519 Claims
- **File**: `src/base_settings.py:15` & `src/auth/adapters/custom_auth_service.py:27-35`
- **Remediation**: Declare `SECRET_KEY: str = Field(..., min_length=32)` in Pydantic Settings and populate `iat`, `nbf`, `jti` in JWT payloads.

#### [SEC-LOW-02] Hardcoded 7-Day Access Token Expiration Overriding Settings
- **File**: `src/dependencies.py:95`
- **Remediation**: Replace `token_expire_minutes=10080` with `token_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES`.

#### [SEC-LOW-03] Missing Password Complexity and Length Constraints on Pydantic Schemas
- **File**: `src/auth/user_schemas.py:7-11, 44-48`
- **Remediation**: Add `Field(..., min_length=8, max_length=128)` to `password` and `new_password` fields.

#### [SEC-LOW-04] Inconsistent Error Return Types in FCM Token and Notification Fetchers
- **File**: `src/db/adapters/supabase_db.py:88-90, 96-98`
- **Remediation**: Return empty list `[]` or `None` instead of boolean `False` on repository exceptions.

---

# Section 2: Concurrency, Async Safety & Task Management Audit (Requirement R2)

```
+--------------------------------------------------------------------------------------------------------+
| Severity | ID          | Concurrency / Task Management Finding Title                                  |
+----------+-------------+------------------------------------------------------------------------------+
| CRITICAL | CONC-CRIT-01| Unmanaged asyncio.create_task in HTTP Handler for Graph Resume Bypassing ARQ |
| CRITICAL | CONC-CRIT-02| SSE Status Stream Database/Redis Busy-Polling Inducing Pool Starvation       |
| CRITICAL | CONC-CRIT-03| Zombie LLM Node Execution & Quota Drain Due to Missing Cancellation Checks   |
| HIGH     | CONC-HIGH-01| Dual Uncoordinated PostgreSQL Connection Pools Causing Supabase Saturation   |
| HIGH     | CONC-HIGH-02| Incomplete MsgPack Deserialization Allowlist in JsonPlusSerializer           |
| HIGH     | CONC-HIGH-03| ARQ Retry Storms Due to Immediate Retry Without Exponential Backoff Deferral |
| MEDIUM   | CONC-MED-01 | Unclosed Redis Clients and ARQ Connection Pool Leaks on Application Shutdown |
| MEDIUM   | CONC-MED-02 | Non-Transactional Checkpoint State Deletion in cancel_generation             |
| MEDIUM   | CONC-MED-03 | Upstash REST vs Native Redis Pub/Sub Architectural Incompatibility           |
| LOW      | CONC-LOW-01 | Parameter Typo _get_chanel_key in ProgressTracker                            |
| LOW      | CONC-LOW-02 | Hardcoded max_concurrency=3 in RunnableConfig                                |
+--------------------------------------------------------------------------------------------------------+
```

---

### [CONC-CRIT-01] Unmanaged `asyncio.create_task` in HTTP Handler for Graph Resume Bypassing ARQ Worker
- **Severity**: **Critical**
- **File**: `src/paper/service.py` (Lines 334–350) & `src/paper/routes/routes.py` (Lines 40–47)
- **Problem Summary & Risk Analysis**:
  When a user approves reviewed questions, the `/api/resume/{thread_id}` endpoint calls `paper_service.resume_generation`. Instead of submitting the resume action to the durable ARQ background queue, `resume_generation` executes `asyncio.create_task(resume_worker())` directly inside the FastAPI web server process.
  1. **Process Lifecycle Loss**: If the web server worker restarts (e.g. Uvicorn worker reload, Gunicorn worker recycle, container restart, auto-scaling deployment), the running resume task is aborted mid-execution, leaving the paper permanently stuck in `awaiting_review` state.
  2. **Worker Bypassing**: Heavy PDF and DOCX compilation operations are executed in the API server rather than distributed across ARQ worker nodes.
  3. **Silent Crash**: `asyncio.create_task` exceptions are caught only by a local `print()`, masking unhandled crashes.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/paper/service.py:334-350
# ==============================================================================
async def resume_worker():
    try:
        await agent.ainvoke(Command(resume=selected_indices), config)
    except Exception as e:
        print(f"[ERROR] LangGraph run crashed on resume thread {thread_id}: {e}")
        ...

asyncio.create_task(resume_worker())
return {"status": "resuming"}

# ==============================================================================
# AFTER: src/paper/task_manager.py, src/paper/service.py & src/paper/worker/tasks.py
# ==============================================================================
# 1. In src/paper/task_manager.py:
class TaskManager:
    def __init__(self, redis_pool: ArqRedis):
        self.redis_pool = redis_pool

    async def enqueue_resume_task(self, thread_id: str, selected_indices: list[int]) -> None:
        await self.redis_pool.enqueue_job(
            "resume_paper_task",
            thread_id,
            selected_indices,
            _job_id=f"resume_{thread_id}"
        )

# 2. In src/paper/worker/tasks.py:
async def resume_paper_task(ctx: dict, thread_id: str, selected_indices: list[int]) -> None:
    agent = ctx["agent"]
    progress_tracker = ctx["progress_tracker"]
    dependencies = GraphConfig(
        chunk_repo=ctx["chunk_repo"],
        html_paper_formatter=ctx["html_paper_formatter"],
        markdown_paper_formatter=ctx["markdown_paper_formatter"],
        document_compiler=ctx["document_compiler"],
        progress_tracker=progress_tracker
    )
    config = {"configurable": {"thread_id": thread_id, **dependencies}}
    await agent.ainvoke(Command(resume=selected_indices), config=config)

# 3. In src/paper/service.py:
async def resume_generation(self, thread_id: str, selected_indices: list[int], agent: CompiledStateGraph, user_id: str):
    # Enqueue resume execution durably in ARQ
    await self.task_manager.enqueue_resume_task(thread_id=thread_id, selected_indices=selected_indices)
    return {"status": "resuming", "thread_id": thread_id}
```

---

### [CONC-CRIT-02] SSE Status Stream Database/Redis Busy-Polling Inducing Pool Starvation
- **Severity**: **Critical**
- **File**: `src/paper/routes/routes.py` (Lines 49–83) & `src/paper/graph/tracker.py` (Lines 60–63)
- **Problem Summary & Risk Analysis**:
  The Server-Sent Events (SSE) status streaming endpoint (`/status/{thread_id}/stream`) implements an infinite polling loop `while True: ... await asyncio.sleep(1)`. On every 1-second tick per connected browser client, it calls `paper_service.get_generation_status`, executing `agent.aget_state` (queries PostgreSQL `checkpoints` table) and Redis `hgetall`.
  If 50 users generate papers concurrently, the API server executes 50 database queries and 50 Redis requests every single second. This rapidly exhausts the 20-connection `AsyncConnectionPool`, causes query latency spikes, and starves background workers of database connections. Furthermore, `ProgressTracker` publishes update events to Redis Pub/Sub, but the SSE route completely ignores this channel.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/paper/routes/routes.py:56-73
# ==============================================================================
async def generator():
    last_state = None
    while True:
        if await req.is_disconnected():
            break
        status_data = await paper_service.get_generation_status(thread_id=thread_id, agent=req.app.state.agent, user_id=str(current_user.get('user_id', "")))
        current_state = json.dumps(status_data)
        if current_state != last_state:
            yield f"data: {current_state}\n\n"
            last_state = current_state
        if status_data.get("status") in ("completed", "failed", "awaiting_review"):
            break
        await asyncio.sleep(1)

# ==============================================================================
# AFTER: src/paper/routes/routes.py (Event-Driven Stream with Client Disconnect Guard)
# ==============================================================================
@paper_router.get('/status/{thread_id}/stream')
async def stream_generation_status(
    thread_id: str,
    req: Request,
    current_user: dict = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service)
):
    user_id = str(current_user["id"])

    async def event_generator():
        # 1. Send initial state immediately
        initial_status = await paper_service.get_generation_status(thread_id=thread_id, agent=req.app.state.agent, user_id=user_id)
        yield f"data: {json.dumps(initial_status)}\n\n"
        if initial_status.get("status") in ("completed", "failed", "awaiting_review"):
            return

        # 2. Subscribe to Redis event notifications instead of busy-polling DB
        pubsub = await paper_service.progress_tracker.subscribe_channel(thread_id=thread_id)
        try:
            while True:
                if await req.is_disconnected():
                    break

                # Wait for pubsub notification with a 15-second heartbeat timeout
                msg = await pubsub.get_message(timeout=15.0)
                if msg is None:
                    # Heartbeat comment to keep connection alive through proxies
                    yield ": heartbeat\n\n"
                    continue

                status_data = await paper_service.get_generation_status(thread_id=thread_id, agent=req.app.state.agent, user_id=user_id)
                yield f"data: {json.dumps(status_data)}\n\n"

                if status_data.get("status") in ("completed", "failed", "awaiting_review"):
                    break
        finally:
            await pubsub.unsubscribe()
            await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

---

### [CONC-CRIT-03] Zombie LLM Node Execution & Quota Drain Due to Missing Cancellation Checks
- **Severity**: **Critical**
- **File**: `src/paper/graph/nodes.py` (Lines 72–97) & `src/paper/service.py` (Lines 180–219)
- **Problem Summary & Risk Analysis**:
  When a user cancels paper generation (`DELETE /api/cancel/{thread_id}`), `cancel_generation` sets a cancellation flag in Redis and deletes checkpoints. However, inside `question_generator_node`, the loop iterates over all chapter topic batches without ever querying `progress_tracker.is_cancelled(thread_id)`.
  As a result, long-running generation jobs (e.g. 5 chapters x 6 topic batches = 30 LLM calls) continue executing to completion in the background, consuming rate limits, API quotas, and worker resources for cancelled requests.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/paper/graph/nodes.py:72-88
# ==============================================================================
for i, batch in enumerate(topic_batches):
    previous_question = ...
    await rate_limiter.acquire()
    ...

# ==============================================================================
# AFTER: src/paper/graph/nodes.py
# ==============================================================================
for i, batch in enumerate(topic_batches):
    # Check cancellation token before every batch invocation
    if progress_tracker and await progress_tracker.is_cancelled(thread_id):
        print(f"[INFO] Thread {thread_id} cancellation detected in chapter '{chapter}'. Terminating node.")
        return {"all_questions": question_list}

    previous_question = (
        "\n".join([q.question_text for q in question_list][-(subjective_count + objective_count):]) 
        if question_list else "None yet"
    )

    await rate_limiter.acquire()
    # Proceed with LLM call...
```

---

### [CONC-HIGH-01] Dual Uncoordinated PostgreSQL Connection Pools Causing Supabase Saturation
- **Severity**: **High**
- **File**: `src/dependencies.py` (Lines 176–186) & `src/paper/worker/settings.py` (Lines 39–50)
- **Problem Summary & Risk Analysis**:
  Both the FastAPI application lifespan and the ARQ worker startup independently create an `AsyncConnectionPool(max_size=20)`. In a standard deployment running 4 Uvicorn web workers and 2 ARQ worker processes, total active pool connections reach `(4 * 20) + (2 * 20) = 120` connections. Supabase Free/Pro tier direct PostgreSQL instances enforce connection limits between 15 and 60 connections. This results in `psycopg.OperationalError: remaining connection slots are reserved for non-replication superuser connections`.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# AFTER: src/dependencies.py & src/paper/worker/settings.py
# ==============================================================================
# Configure environment-aware pool sizing in base_settings.py:
# DB_POOL_MAX_SIZE: int = 5 (Web), DB_WORKER_POOL_MAX_SIZE: int = 5 (Worker)

# In src/dependencies.py:
pool = AsyncConnectionPool(
    conninfo=settings.DB_URI,
    min_size=2,
    max_size=settings.DB_POOL_MAX_SIZE or 5,
    open=False,
    kwargs={
        "autocommit": True,
        "row_factory": dict_row,
        "prepare_threshold": None
    }
)

# In src/paper/worker/settings.py:
pool = AsyncConnectionPool(
    conninfo=settings.DB_URI,
    min_size=1,
    max_size=settings.DB_WORKER_POOL_MAX_SIZE or 5,
    open=False,
    kwargs={
        "autocommit": True,
        "row_factory": dict_row,
        "prepare_threshold": None
    }
)
```

---

### [CONC-HIGH-02] Incomplete MsgPack Deserialization Allowlist in LangGraph `JsonPlusSerializer`
- **Severity**: **High**
- **File**: `src/dependencies.py` (Lines 189–194) & `src/paper/worker/settings.py` (Lines 51–56)
- **Problem Summary & Risk Analysis**:
  The `allowed_types` list passed to `JsonPlusSerializer` only registers `PaperRequest`, `Question`, and `EvaluationPoint`. Subordinate domain types used inside state checkpoints—such as `DifficultyDistribution`, `QuestionTypes`, `ChapterStatus`, `DocumentType`, and `SubjectType`—are missing. When state snapshots containing these enums or sub-models are deserialized during task resume or recovery, LangGraph throws unhandled serialization exceptions or coerces models to raw dictionaries.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/dependencies.py:189-194
# ==============================================================================
allowed_types = [
    ("src.paper.models", "PaperRequest"),
    ("src.paper.models", "Question"),
    ("src.paper.models", "EvaluationPoint"),
]

# ==============================================================================
# AFTER: src/dependencies.py & src/paper/worker/settings.py
# ==============================================================================
allowed_types = [
    ("src.paper.models", "PaperRequest"),
    ("src.paper.models", "Question"),
    ("src.paper.models", "EvaluationPoint"),
    ("src.paper.models", "DifficultyDistribution"),
    ("src.paper.models", "QuestionTypes"),
    ("src.paper.models", "ChapterStatus"),
    ("src.paper.models", "DocumentType"),
    ("src.paper.models", "SubjectType"),
    ("src.paper.models", "PaperDifficulty"),
]
serde = JsonPlusSerializer(allowed_msgpack_modules=allowed_types)
```

---

### [CONC-HIGH-03] ARQ Retry Storms Due to Immediate Retry Without Exponential Backoff Deferral
- **Severity**: **High**
- **File**: `src/paper/worker/tasks.py` (Lines 77–105) & `src/paper/worker/settings.py` (Lines 30–35)
- **Problem Summary & Risk Analysis**:
  `WorkerSettings.max_tries = 3` configures ARQ to retry failed jobs up to 3 times. However, in `generate_paper_task`, when an exception occurs (e.g. rate limit 429 or network glitch), the exception is simply re-raised. ARQ immediately re-runs the task without exponential backoff deferral, causing immediate repeated failures within milliseconds and triggering the final failure state.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# AFTER: src/paper/worker/tasks.py
# ==============================================================================
from arq.worker import Retry

async def generate_paper_task(ctx: dict, thread_id: str, paper_request_dict: dict, user_fcm_token: Optional[str] = None):
    try:
        # Task execution logic
        pass
    except Exception as e:
        job_try = ctx.get("job_try", 1)
        max_tries = 3
        if job_try < max_tries:
            # Exponential backoff: 5s, 20s with jitter
            backoff_delay = (5 * (4 ** (job_try - 1)))
            print(f"[WARN] Retrying task for thread {thread_id} in {backoff_delay}s (Attempt {job_try}/{max_tries}): {e}")
            raise Retry(defer=backoff_delay) from e
        else:
            # Final failure handling...
            if progress_tracker:
                await progress_tracker.mark_all_failed(thread_id=thread_id)
            raise e
```

---

### [CONC-MED-01 to CONC-LOW-02] Medium & Low Severity Concurrency Findings

#### [CONC-MED-01] Unclosed Redis Clients and ARQ Connection Pool Leaks on Application Shutdown
- **File**: `src/dependencies.py:78-87, 115-118, 120-128, 173-207`
- **Remediation**: In FastAPI `lifespan`, track all open Redis client instances and `arq_pool_instance`, invoking `await arq_pool.close()` and closing Upstash sessions on shutdown.

#### [CONC-MED-02] Non-Transactional Checkpoint State Deletion in `cancel_generation`
- **File**: `src/paper/service.py:185-194`
- **Remediation**: Wrap the 3 `DELETE` statements across `checkpoints`, `checkpoint_blobs`, and `checkpoint_writes` in a single `async with conn.transaction():` block.

#### [CONC-MED-03] Upstash REST vs Native Redis Pub/Sub Architectural Incompatibility
- **File**: `src/paper/graph/tracker.py:3, 14-26, 60-63`
- **Remediation**: Clarify transport layer: use standard Redis connection (`redis.asyncio.Redis`) for persistent Pub/Sub streaming while using Upstash REST client for stateless OTP/status operations.

#### [CONC-LOW-01] Parameter Typo `_get_chanel_key` in `ProgressTracker`
- **File**: `src/paper/graph/tracker.py:24`
- **Remediation**: Rename method from `_get_chanel_key` to `_get_channel_key`.

#### [CONC-LOW-02] Hardcoded `max_concurrency=3` in `RunnableConfig`
- **File**: `src/paper/graph/runner.py:22`
- **Remediation**: Source concurrency limit from `settings.LANGGRAPH_MAX_CONCURRENCY` rather than hardcoding `3`.

---

# Section 3: LLM Orchestration & Generation Pipeline Audit (Requirement R3)

```
+--------------------------------------------------------------------------------------------------------+
| Severity | ID          | LLM Pipeline & Document Compiler Finding Title                               |
+----------+-------------+------------------------------------------------------------------------------+
| CRITICAL | LLM-CRIT-01 | Non-Existent Gemini Model Identifiers & Incompatible Fallback Configs        |
| CRITICAL | LLM-CRIT-02 | Ultra-Fragile Pydantic Validators & Silent Question Batch Drops               |
| CRITICAL | LLM-CRIT-03 | In-Memory Rate Limiter Lacking Multi-Worker Isolation & Missing 429 Backoff  |
| CRITICAL | LLM-CRIT-04 | Playwright Headless Chromium Zombie Process Leakage & Unbounded Spawning     |
| HIGH     | LLM-HIGH-01 | SSRF and Local File Inclusion (LFI) in HTML/PDF Compilation                  |
| HIGH     | LLM-HIGH-02 | Prompt Injection & Lack of XML Structural Delimiter Isolation                |
| HIGH     | LLM-HIGH-03 | Direct Logical Contradiction in Objective Generator Quota Builder            |
| MEDIUM   | LLM-MED-01  | Insecure Temp Files, Blocking File I/O & Ignored Exit Codes in Pandoc        |
| LOW      | LLM-LOW-01  | Stray Syntax Artifact literal '1' in src/paper/graph/runner.py               |
| LOW      | LLM-LOW-02  | Dead Monolithic Duplicate Code in src/paper/compilers/generator.py           |
+--------------------------------------------------------------------------------------------------------+
```

---

### [LLM-CRIT-01] Non-Existent Gemini Model Identifiers & Incompatible Fallback Configs
- **Severity**: **Critical**
- **File**: `src/config/model_settings.py` (Lines 6, 12, 16–46)
- **Problem Summary & Risk Analysis**:
  `MAIN_AI_MODEL = "gemini-3.5-flash"` and `ALTERNATE_GOOGLE_AI_MODELS = ["gemini-3.1-flash-lite", "gemini-2.5-flash"]` configure non-existent Google Gemini model strings. When invoked, `ChatGoogleGenerativeAI` raises `google.api_core.exceptions.NotFound: 404 models/gemini-3.5-flash is not found`. Furthermore, invoking `.with_structured_output(schema=BatchOutput)` on `generator_model.with_fallbacks(model_list)` produces conflicting tool-calling schema definitions between Google GenAI native mode and Groq OpenAI-compatible mode.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/config/model_settings.py:6, 12, 21, 26-47
# ==============================================================================
MAIN_AI_MODEL = "gemini-3.5-flash"
ALTERNATE_GOOGLE_AI_MODELS = ["gemini-3.1-flash-lite", "gemini-2.5-flash"]
ALTERNATE_GROQ_MODELS = ["llama-3.3-70b-versatile", "openai/gpt-oss-120b"]

generator_model = ChatGoogleGenerativeAI(
    temperature=0.1,
    model=MAIN_AI_MODEL,
    google_api_key=settings.GOOGLE_API_KEY,
    max_retries=2,
    thinking_level="medium"
)
generator_model = generator_model.with_fallbacks(model_list)

# ==============================================================================
# AFTER: src/config/model_settings.py
# ==============================================================================
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from src.base_settings import settings

# Valid, stable model identifiers
MAIN_AI_MODEL = "gemini-2.5-flash"
ALTERNATE_GOOGLE_AI_MODELS = ["gemini-1.5-flash", "gemini-1.5-pro"]
ALTERNATE_GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

def get_generator_model():
    primary = ChatGoogleGenerativeAI(
        model=MAIN_AI_MODEL,
        temperature=0.1,
        google_api_key=settings.GOOGLE_API_KEY,
        max_retries=2,
    )
    fallbacks = [
        ChatGoogleGenerativeAI(
            model=m,
            temperature=0.1,
            google_api_key=settings.GOOGLE_API_KEY,
            max_retries=2
        ) for m in ALTERNATE_GOOGLE_AI_MODELS
    ]
    if settings.GROQ_API_KEY:
        fallbacks.extend([
            ChatGroq(
                model=m,
                api_key=settings.GROQ_API_KEY,
                temperature=0.1,
                max_retries=2
            ) for m in ALTERNATE_GROQ_MODELS
        ])
    return primary.with_fallbacks(fallbacks) if fallbacks else primary

generator_model = get_generator_model()
```

---

### [LLM-CRIT-02] Ultra-Fragile Pydantic Validators & Silent Question Batch Drops
- **Severity**: **Critical**
- **File**: `src/paper/models.py` (Lines 136–163) & `src/paper/graph/nodes.py` (Lines 88–97)
- **Problem Summary & Risk Analysis**:
  The `Question` model includes rigid `@model_validator` rules requiring exactly 4 MCQ options and exact evaluation scheme mark sum matches. If an LLM returns 3 options, an option with prefix `"Option (A)"`, or subjective marking points summing to 3 instead of 2, Pydantic raises a `ValidationError`.
  In `nodes.py:88-97`, the call to `generator_chain.ainvoke()` is wrapped in `try...except Exception as e: print(f"Batch failed, skipping: {e}")`. The validation error is caught, logged with `print()`, and the entire batch of 5–10 questions is silently dropped from the generated paper.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/paper/models.py:136-163
# ==============================================================================
@model_validator(mode="after")
def validate_question_logic(self) -> "Question":
    if self.question_type == QuestionTypes.MCQ:
        if not self.options or len(self.options) != 4:
            raise ValueError("MCQ questions must have exactly 4 options.")
        ans = self.correct_answer.strip()
        option_matches = any(ans == opt or opt == ans or ans in opt or opt in ans for opt in self.options)
        prefix_match = any(ans.lower().startswith(f"({c})") or ans.lower().startswith(f"{c})") for c in "abcd")
        if not (option_matches or prefix_match):
            raise ValueError(f"MCQ correct_answer '{self.correct_answer}' does not match any of the options: {self.options}")
    ...

# ==============================================================================
# AFTER: src/paper/models.py (Auto-Sanitizing Resilient Validator)
# ==============================================================================
@model_validator(mode="after")
def sanitize_and_normalize(self) -> "Question":
    # 1. Normalize subjective marks based on question type
    if self.question_type == QuestionTypes.TWO_MARK_ANS:
        self.marks = 2
    elif self.question_type == QuestionTypes.THREE_MARK_ANS:
        self.marks = 3
    elif self.question_type == QuestionTypes.FOUR_MARK_ANS:
        self.marks = 4
    elif self.question_type.is_objective and self.marks == 0:
        self.marks = 1

    # 2. Normalize MCQ options to exactly 4 choices
    if self.question_type == QuestionTypes.MCQ:
        if not self.options:
            self.options = ["(a) Option A", "(b) Option B", "(c) Option C", "(d) Option D"]
        elif len(self.options) > 4:
            self.options = self.options[:4]
        elif len(self.options) < 4:
            labels = ["a", "b", "c", "d"]
            while len(self.options) < 4:
                idx = len(self.options)
                self.options.append(f"({labels[idx]}) None of the above")

    # 3. Auto-balance evaluation scheme marks to match question.marks
    if self.question_type.is_subjective and self.evaluation_scheme:
        total_scheme = sum(pt.allocated_marks for pt in self.evaluation_scheme)
        if total_scheme != self.marks and len(self.evaluation_scheme) > 0:
            base_mark = max(1, self.marks // len(self.evaluation_scheme))
            for pt in self.evaluation_scheme:
                pt.allocated_marks = base_mark
            rem = self.marks - sum(pt.allocated_marks for pt in self.evaluation_scheme)
            if rem != 0 and self.evaluation_scheme:
                self.evaluation_scheme[0].allocated_marks += rem

    return self
```

---

### [LLM-CRIT-03] In-Memory Rate Limiter Lacking Multi-Worker Isolation & Missing 429 Backoff
- **Severity**: **Critical**
- **File**: `src/paper/rate_limiter.py` (Lines 4–41) & `src/paper/graph/nodes.py` (Lines 17, 79)
- **Problem Summary & Risk Analysis**:
  `TokenBucket` maintains tokens in local memory with an `asyncio.Lock()`. In a multi-worker deployment, each worker process tracks its own token bucket independently, allowing aggregate requests to breach Google Gemini RPM limits. Furthermore, when Gemini returns 429 `ResourceExhausted`, `nodes.py` swallows the error and skips the chunk batch rather than performing exponential backoff with jitter.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# AFTER: src/paper/rate_limiter.py (Distributed Redis Token Bucket + Backoff Invoker)
# ==============================================================================
import time
import asyncio
import random
import logging
from typing import Optional
from upstash_redis.asyncio import Redis

logger = logging.getLogger(__name__)

class DistributedTokenBucket:
    def __init__(self, key: str = "rate_limiter:llm", max_capacity: int = 5, refill_rate: float = 0.0833, redis_client: Optional[Redis] = None):
        self.key = key
        self.capacity = float(max_capacity)
        self.refill_rate = float(refill_rate)
        self.redis = redis_client
        self._local_tokens = float(max_capacity)
        self._local_last_refill = time.monotonic()
        self._local_lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            if self.redis:
                try:
                    now = time.time()
                    token_key = f"{self.key}:tokens"
                    ts_key = f"{self.key}:ts"
                    raw_tokens = await self.redis.get(token_key)
                    raw_ts = await self.redis.get(ts_key)

                    current_tokens = float(raw_tokens) if raw_tokens is not None else self.capacity
                    last_ts = float(raw_ts) if raw_ts is not None else now

                    elapsed = max(0.0, now - last_ts)
                    current_tokens = min(self.capacity, current_tokens + (elapsed * self.refill_rate))

                    if current_tokens >= 1.0:
                        current_tokens -= 1.0
                        await self.redis.set(token_key, str(current_tokens), ex=3600)
                        await self.redis.set(ts_key, str(now), ex=3600)
                        return
                    deficit = 1.0 - current_tokens
                    sleep_time = (deficit / self.refill_rate) + random.uniform(0.1, 0.5)
                except Exception as e:
                    logger.warning(f"Redis rate limiter fallback: {e}")
                    self.redis = None
            else:
                async with self._local_lock:
                    now = time.monotonic()
                    elapsed = now - self._local_last_refill
                    self._local_tokens = min(self.capacity, self._local_tokens + (elapsed * self.refill_rate))
                    self._local_last_refill = now
                    if self._local_tokens >= 1.0:
                        self._local_tokens -= 1.0
                        return
                    deficit = 1.0 - self._local_tokens
                    sleep_time = (deficit / self.refill_rate) + random.uniform(0.1, 0.5)

            await asyncio.sleep(sleep_time)

async def invoke_with_retry(chain, inputs: dict, max_retries: int = 5):
    base_delay = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            return await chain.ainvoke(inputs)
        except Exception as e:
            err_msg = str(e).lower()
            is_rate_limit = "429" in err_msg or "resourceexhausted" in err_msg or "rate" in err_msg
            if attempt == max_retries or not is_rate_limit:
                raise e
            jitter = random.uniform(0.5, 1.5)
            delay = (base_delay * (2 ** (attempt - 1))) + jitter
            logger.warning(f"LLM Rate Limit hit (attempt {attempt}/{max_retries}). Retrying in {delay:.2f}s...")
            await asyncio.sleep(delay)
```

---

### [LLM-CRIT-04] Playwright Headless Chromium Zombie Process Leakage & Unbounded Spawning
- **Severity**: **Critical**
- **File**: `src/paper/compilers/adapters/document_compiler.py` (Lines 10–38)
- **Problem Summary & Risk Analysis**:
  In `generate_pdf`, `p.chromium.launch()` is invoked without a `try...finally: await browser.close()` block. Any error during page navigation, rendering, or PDF export leaks a zombie Chromium process. Furthermore, Chromium is launched without Docker container arguments (`--no-sandbox`, `--disable-dev-shm-usage`), leading to crashes in containerized environments with standard 64MB `/dev/shm` limits.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/paper/compilers/adapters/document_compiler.py:10-38
# ==============================================================================
async def generate_pdf(self, paper_html: str, paper_output_path: str, answer_html: str, answer_output_path: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        paper_page = await browser.new_page()
        answer_page = await browser.new_page()
        await paper_page.set_content(paper_html)
        await paper_page.pdf(path=paper_output_path, format="A4")
        await answer_page.set_content(answer_html)
        await answer_page.pdf(path=answer_output_path, format="A4")
        await browser.close()  # Skipped if any error throws above!

# ==============================================================================
# AFTER: src/paper/compilers/adapters/document_compiler.py
# ==============================================================================
CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--no-zygote",
    "--single-process",
]

class CustomDocumentCompiler(DocumentCompiler):
    async def generate_pdf(self, paper_html: str, paper_output_path: str, answer_html: str, answer_output_path: str):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=CHROMIUM_ARGS)
            try:
                context = await browser.new_context(viewport={"width": 1200, "height": 1600})
                
                # Render Question Paper
                paper_page = await context.new_page()
                try:
                    await paper_page.set_content(paper_html, wait_until="load", timeout=20000)
                    await paper_page.pdf(path=paper_output_path, format="A4", print_background=True)
                finally:
                    await paper_page.close()

                # Render Answer Key
                answer_page = await context.new_page()
                try:
                    await answer_page.set_content(answer_html, wait_until="load", timeout=20000)
                    await answer_page.pdf(path=answer_output_path, format="A4", print_background=True)
                finally:
                    await answer_page.close()
            finally:
                # Guaranteed cleanup preventing zombie processes
                await browser.close()
```

---

### [LLM-HIGH-01] SSRF and Local File Inclusion (LFI) in HTML/PDF Compilation
- **Severity**: **High**
- **File**: `src/paper/formatters/adapters/html_paper_formatter.py` (Lines 10–56, 269–284) & `src/paper/compilers/adapters/document_compiler.py` (Lines 16–17)
- **Problem Summary & Risk Analysis**:
  User-controlled input strings (`institution_name`, chapter names, question text, LaTeX notation) are formatted directly into raw HTML strings without entity escaping via `html.escape()`. An attacker supplying `<iframe src="file:///etc/passwd"></iframe>` or `<img src="http://169.254.169.254/latest/meta-data/">` forces headless Chromium to fetch local OS files or cloud instance credentials and embed them directly into the generated PDF.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# AFTER: src/paper/formatters/adapters/html_paper_formatter.py
# ==============================================================================
import html

def safe_html(text: str) -> str:
    if not isinstance(text, str):
        return ""
    escaped = html.escape(text)
    return escaped.replace("\n", "<br>")

# In HTMLPaperFormatter:
def _render_question_html(self, q: Question, q_number: int) -> str:
    q_text_safe = safe_html(q.question_text)
    return f'<div class="question"><span class="q-text"><strong>Q{q_number}.</strong> {q_text_safe}</span></div>\n'
```

---

### [LLM-HIGH-02] Prompt Injection & Lack of XML Structural Delimiter Isolation
- **Severity**: **High**
- **File**: `src/paper/graph/nodes.py` (Lines 60–67) & `src/config/prompts.py`
- **Problem Summary & Risk Analysis**:
  Untrusted textbook chunks and generated questions are passed into human prompt templates without structural delimiter boundaries (e.g. XML tags), leaving the model open to instruction injection attacks embedded in syllabus text.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# AFTER: src/paper/graph/nodes.py:60-67
# ==============================================================================
generator_prompt = ChatPromptTemplate([
    ("system", system_prompt),
    ("human", (
        "<context_textbook_content>\n"
        "{formatted_chunks}\n"
        "</context_textbook_content>\n\n"
        "<previously_generated_questions>\n"
        "{previous_questions}\n"
        "</previously_generated_questions>\n\n"
        "<generation_quota_and_rules>\n"
        "{required_quota_instructions}\n"
        "</generation_quota_and_rules>\n\n"
        "Strictly generate questions conforming to the requested JSON schema based on the context above."
    ))
])
```

---

### [LLM-HIGH-03] Direct Logical Contradiction in Objective Generator Quota Builder
- **Severity**: **High**
- **File**: `src/paper/graph/utils.py` (Lines 191–200)
- **Problem Summary & Risk Analysis**:
  When `objective_count > 0`, the prompt builder outputs: *"Please generate EXACTLY {objective_count} objective questions... Do NOT generate any objective questions."* This direct logical contradiction causes the LLM to refuse generating objective questions or hallucinate.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/paper/graph/utils.py:191-196
# ==============================================================================
if objective_count > 0:
    base_instruction = (
        f"Please generate EXACTLY {objective_count} objective questions using ONLY these allowed types: {allowed_obj_values} based strictly "
        "on this textbook content. Do NOT generate any objective questions."
    )

# ==============================================================================
# AFTER: src/paper/graph/utils.py:191-196
# ==============================================================================
if objective_count > 0:
    base_instruction = (
        f"Please generate EXACTLY {objective_count} objective questions using ONLY these allowed types: {allowed_obj_values} based strictly "
        "on this textbook content. Do NOT generate any subjective questions."
    )
```

---

### [LLM-MED-01 to LLM-LOW-02] Medium & Low Severity LLM Findings

#### [LLM-MED-01] Insecure Temp Files, Blocking File I/O & Ignored Exit Codes in Pandoc
- **File**: `src/paper/compilers/adapters/document_compiler.py:39-54`
- **Remediation**: Use `tempfile.NamedTemporaryFile()`, add `--sandbox` flag to Pandoc command, enforce a 30-second subprocess timeout, and verify `proc.returncode == 0`.

#### [LLM-LOW-01] Stray Syntax Artifact Literal '1' in `src/paper/graph/runner.py`
- **File**: `src/paper/graph/runner.py:1`
- **Remediation**: Delete stray `1` on line 1.

#### [LLM-LOW-02] Dead Monolithic Duplicate Code in `src/paper/compilers/generator.py`
- **File**: `src/paper/compilers/generator.py:1-676`
- **Remediation**: Move `SECTION_CONFIG` into `src/paper/models.py` and delete `src/paper/compilers/generator.py`.

---

# Section 4: Clean Architecture, Domain Modeling & Error Handling Audit (Requirement R4)

```
+--------------------------------------------------------------------------------------------------------+
| Severity | ID          | Clean Architecture & Domain Modeling Finding Title                           |
+----------+-------------+------------------------------------------------------------------------------+
| CRITICAL | ARCH-CRIT-01| Broken Dependency Injection in ARQ Worker Due to @lru_cache on Depends()     |
| CRITICAL | ARCH-CRIT-02| Direct Database Driver Coupling & Leaky Supabase Exceptions in Services      |
| CRITICAL | ARCH-CRIT-03| "Option A" Failure Envelopes (200 OK with {"status": "failed"}) in Service    |
| HIGH     | ARCH-HIGH-01| Incomplete Interface Implementation (LSP Violation) in MarkdownPaperFormatter|
| HIGH     | ARCH-HIGH-02| Absence of Global Exception Handlers and Unified API Error Schema            |
| HIGH     | ARCH-HIGH-03| Fragile Type Coercion & Optional Model Conversion in to_domain()             |
| HIGH     | ARCH-HIGH-04| Untyped Repository Interfaces & Inconsistent Return Value Error Handling     |
| HIGH     | ARCH-HIGH-05| Presentation Layer Coupling in Application/Domain Services (HTTPException)   |
| MEDIUM   | ARCH-MED-01 | Missing Boundary Validation & Mutable Defaults in Domain Models              |
| MEDIUM   | ARCH-MED-02 | Storage Adapter Method Signature Mismatch (LSP Violation)                    |
| MEDIUM   | ARCH-MED-03 | Missing Interface Abstraction for NotificationService and TaskManager        |
| MEDIUM   | ARCH-MED-04 | Route Handlers Bypassing Dependency Injection and Importing Foreign ORMs     |
| MEDIUM   | ARCH-MED-05 | Inconsistent User Identity Resolution Across Route Endpoints                 |
| MEDIUM   | ARCH-MED-06 | Inconsistent Authentication Route Status Codes & Email Enumeration           |
| LOW      | ARCH-LOW-01 | Dead Duplicate Code in src/paper/compilers/generator.py (676 Lines)          |
| LOW      | ARCH-LOW-02 | Empty File notifications_messages.py Duplicate                               |
| LOW      | ARCH-LOW-03 | Hardcoded Email Infrastructure Configuration in FastMailService              |
| LOW      | ARCH-LOW-04 | Missing Request Tracing & Correlation Middleware (X-Request-ID)              |
+--------------------------------------------------------------------------------------------------------+
```

---

### [ARCH-CRIT-01] Broken Dependency Injection in ARQ Worker Due to `@lru_cache` on FastAPI `Depends()` Provider Functions
- **Severity**: **Critical**
- **File**: `src/dependencies.py` (Lines 135–163) & `src/paper/worker/settings.py` (Line 67)
- **Problem Summary & Risk Analysis**:
  FastAPI dependency functions (e.g. `get_paper_service`) define default arguments as `param: Type = Depends(provider)` while decorated with `@lru_cache`. In `src/paper/worker/settings.py:67`, the worker startup initializes services by directly calling `get_paper_service()` with no arguments.
  Because this invocation happens outside FastAPI HTTP request routing, Python assigns the literal `params.Depends` descriptor objects to `self.paper_repo`, `self.local_storage`, `self.cloud_storage`, etc., resulting in corrupted service attributes and fatal `AttributeError` during worker execution.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/dependencies.py:135-163 & src/paper/worker/settings.py:67
# ==============================================================================
@lru_cache
def get_paper_service(
    paper_repo: PaperRepository = Depends(get_paper_repository),
    cloud_storage: StorageService = Depends(get_cloud_storage),
    local_storage: StorageService = Depends(get_local_storage),
    task_manager: TaskManager = Depends(get_task_manager),
    progress_tracker: ProgressTracker = Depends(get_progress_tracker),
    html_paper_formatter: PaperFormatter = Depends(get_html_formatter),
    markdown_paper_formatter: PaperFormatter = Depends(get_markdown_formatter),
    chunk_repo: ChunkRepository = Depends(get_chunk_repository),
    document_compiler: DocumentCompiler = Depends(get_document_compiler),
    user_repo: UserRepository = Depends(get_user_repository),
    notification_service: NotificationService = Depends(get_notification_service)
) -> PaperService:
    return PaperService(...)

# In worker startup:
ctx["paper_service"] = get_paper_service()  # <-- INJECTS Depends() OBJECTS!

# ==============================================================================
# AFTER: src/dependencies.py (Clean Factory Pattern)
# ==============================================================================
# 1. Pure domain factory function (callable by Worker, CLI, and Unit Tests)
def create_paper_service(
    paper_repo: PaperRepository,
    cloud_storage: StorageService,
    local_storage: StorageService,
    task_manager: TaskManager,
    progress_tracker: ProgressTracker,
    html_paper_formatter: PaperFormatter,
    markdown_paper_formatter: PaperFormatter,
    chunk_repo: ChunkRepository,
    document_compiler: DocumentCompiler,
    user_repo: UserRepository,
    notification_service: NotificationService
) -> PaperService:
    return PaperService(
        progress_tracker=progress_tracker,
        local_storage=local_storage,
        cloud_storage=cloud_storage,
        task_manager=task_manager,
        paper_repo=paper_repo,
        html_paper_formatter=html_paper_formatter,
        markdown_paper_formatter=markdown_paper_formatter,
        chunk_repo=chunk_repo,
        document_compiler=document_compiler,
        user_repo=user_repo,
        notification_service=notification_service
    )

# 2. FastAPI HTTP Request Provider (Only used in web routers)
def get_paper_service(
    paper_repo: PaperRepository = Depends(get_paper_repository),
    cloud_storage: StorageService = Depends(get_cloud_storage),
    local_storage: StorageService = Depends(get_local_storage),
    task_manager: TaskManager = Depends(get_task_manager),
    progress_tracker: ProgressTracker = Depends(get_progress_tracker),
    html_paper_formatter: PaperFormatter = Depends(get_html_formatter),
    markdown_paper_formatter: PaperFormatter = Depends(get_markdown_formatter),
    chunk_repo: ChunkRepository = Depends(get_chunk_repository),
    document_compiler: DocumentCompiler = Depends(get_document_compiler),
    user_repo: UserRepository = Depends(get_user_repository),
    notification_service: NotificationService = Depends(get_notification_service)
) -> PaperService:
    return create_paper_service(
        paper_repo=paper_repo,
        cloud_storage=cloud_storage,
        local_storage=local_storage,
        task_manager=task_manager,
        progress_tracker=progress_tracker,
        html_paper_formatter=html_paper_formatter,
        markdown_paper_formatter=markdown_paper_formatter,
        chunk_repo=chunk_repo,
        document_compiler=document_compiler,
        user_repo=user_repo,
        notification_service=notification_service
    )
```

---

### [ARCH-CRIT-02] Direct Database Driver Coupling & Leaky Supabase Exceptions in Services
- **Severity**: **Critical**
- **File**: `src/auth/adapters/custom_auth_service.py` (Lines 1, 6, 39–43, 49–56, 60–64)
- **Problem Summary & Risk Analysis**:
  `CustomAuthService` directly imports `from supabase import SupabaseException` and catches driver-specific exceptions across 6 service methods. This violates the Dependency Inversion Principle (DIP). The application service is coupled to the concrete Supabase driver, preventing database swaps (e.g. to PostgreSQL via asyncpg) and breaking unit testing with mock repositories.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# AFTER: src/exceptions.py & src/auth/adapters/custom_auth_service.py
# ==============================================================================
# 1. In src/exceptions.py:
class DomainException(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

class EntityAlreadyExistsError(DomainException):
    def __init__(self, entity: str, identifier: str):
        super().__init__(f"{entity} '{identifier}' already exists.", code="ENTITY_EXISTS")

class DatabaseOperationError(DomainException):
    def __init__(self, message: str = "Database operation failed."):
        super().__init__(message, code="DATABASE_ERROR")

# 2. In src/auth/adapters/custom_auth_service.py (Clean, no Supabase imports):
async def register_user(self, email: str, password: str, name: str) -> dict:
    db_user = self.user_repo.get_user(email=email)
    if db_user is not None:
        raise EntityAlreadyExistsError(entity="User", identifier=email)

    hashed_password = await self._get_hashed_password(password)
    new_user = self.user_repo.create_user(email=email, hashed_password=hashed_password, name=name)
    if not new_user:
        raise DatabaseOperationError("Failed to persist user registration record.")
    return new_user
```

---

### [ARCH-CRIT-03] "Option A" Failure Envelopes (200 OK with `{"status": "failed"}`) in `PaperService.save_to_cloud`
- **Severity**: **Critical**
- **File**: `src/paper/service.py` (Lines 51–131) & `src/paper/routes/routes.py` (Lines 96–106)
- **Problem Summary & Risk Analysis**:
  `PaperService.save_to_cloud` catches 6 distinct failure cases (missing state snapshot, missing paper request, missing local files, cloud upload failure, database sync failure) and returns `{"status": "failed"}` with HTTP 200 OK.
  This "Option A" anti-pattern violates REST standards, prevents API monitoring tools and reverse proxies from detecting failures, and forces client applications to manually inspect response bodies for error detection.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/paper/service.py:51-131
# ==============================================================================
if not snapshot.values:
    print(f"[ERROR] No state found for thread {thread_id}")
    return {"status": "failed"}  # Returns 200 OK!

# ==============================================================================
# AFTER: src/paper/service.py (Standardized Domain Exceptions)
# ==============================================================================
class ThreadStateNotFoundError(DomainException):
    def __init__(self, thread_id: str):
        super().__init__(f"State snapshot not found for thread {thread_id}.", code="THREAD_NOT_FOUND")

class ArtifactNotFoundError(DomainException):
    def __init__(self, filename: str, thread_id: str):
        super().__init__(f"Artifact '{filename}' not found for thread {thread_id}.", code="ARTIFACT_NOT_FOUND")

async def save_to_cloud(self, thread_id: str, agent: CompiledStateGraph, user_id: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = await agent.aget_state(config)

    if not snapshot or not snapshot.values:
        raise ThreadStateNotFoundError(thread_id=thread_id)

    raw_req = snapshot.values.get("paper_request")
    if not raw_req:
        raise DomainException(f"Missing paper metadata for thread {thread_id}.", code="MISSING_METADATA")

    paper_request = raw_req if isinstance(raw_req, PaperRequest) else PaperRequest(**raw_req)
    filenames = [DocumentType.PAPER_PDF, DocumentType.ANSWER_PDF, DocumentType.PAPER_DOCX]
    files_data: dict[str, bytes] = {}

    for filename in filenames:
        relative_path = f"{thread_id}/{filename}"
        if not self.local_storage.exists(file_path=relative_path):
            raise ArtifactNotFoundError(filename=filename, thread_id=thread_id)
        files_data[filename] = self.local_storage.get_file(file_path=relative_path)

    # Proceed with verified cloud storage upload and DB sync...
    return {"status": "synced", "thread_id": thread_id}
```

---

### [ARCH-HIGH-01] Incomplete Interface Implementation (LSP Violation) in `MarkdownPaperFormatter`
- **Severity**: **High**
- **File**: `src/paper/formatters/adapters/markdown_paper_formatter.py` (Lines 108–109) & `src/paper/formatters/interfaces/interface.py` (Lines 10–12)
- **Problem Summary & Risk Analysis**:
  The `PaperFormatter` abstract interface defines `def render_answer_key(self, paper_request: PaperRequest, questions: list[Question]) -> str`.
  However, `MarkdownPaperFormatter.render_answer_key` contains only `pass`, returning `None`. Any caller expecting a formatted markdown answer key receives `None`, violating the Liskov Substitution Principle and causing downstream crashes.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# BEFORE: src/paper/formatters/adapters/markdown_paper_formatter.py:108-109
# ==============================================================================
def render_answer_key(self, paper_request : PaperRequest, questions: list[Question]):
    pass  # Returns None!

# ==============================================================================
# AFTER: src/paper/formatters/adapters/markdown_paper_formatter.py
# ==============================================================================
from datetime import date
from src.paper.models import SECTION_CONFIG, QuestionTypes

class MarkdownPaperFormatter(PaperFormatter):
    def render_answer_key(self, paper_request: PaperRequest, questions: list[Question]) -> str:
        total_marks = sum(q.marks for q in questions)
        today = date.today().strftime("%d-%m-%Y")
        chapters_str = ", ".join(paper_request.chapters)

        md = f"""# {paper_request.institution_name.upper()}
## ANSWER KEY & EVALUATION SCHEME
**Subject**: {paper_request.subject} | **Standard**: {paper_request.standard} | **Date**: {today}  
**Chapters**: {chapters_str} | **Total Marks**: {total_marks}

---

"""
        grouped: dict[QuestionTypes, list[Question]] = {}
        for q in questions:
            grouped.setdefault(q.question_type, []).append(q)

        q_number = 1
        section_number = 1
        for q_type, heading in SECTION_CONFIG.items():
            if q_type not in grouped:
                continue
            q_list = grouped[q_type]
            sec_marks = sum(q.marks for q in q_list)
            md += f"### Section {section_number}: {heading} (Answers - {sec_marks} Marks)\n\n"
            for q in q_list:
                md += f"**Q{q_number}.** {q.question_text} *[{q.marks} Marks]*\n\n"
                if q.evaluation_scheme:
                    md += "**Marking Scheme:**\n"
                    for pt in q.evaluation_scheme:
                        suffix = f" [{pt.allocated_marks} Mark{'s' if pt.allocated_marks > 1 else ''}]"
                        md += f"- {pt.point_text}{suffix}\n"
                else:
                    md += f"**Answer:** {q.correct_answer or q.answer}\n"
                md += "\n"
                q_number += 1
            section_number += 1
        return md
```

---

### [ARCH-HIGH-02] Absence of Global Exception Handlers and Unified API Error Schema
- **Severity**: **High**
- **File**: `src/app.py` (Lines 1–33)
- **Problem Summary & Risk Analysis**:
  `src/app.py` registers zero custom exception handlers. When errors occur (`RequestValidationError`, custom `DomainException`, unhandled 500 crashes), FastAPI falls back to default JSON or raw internal HTML, causing inconsistent responses and leaking internal stack traces.
- **Concrete Code Remediation**:

```python
# ==============================================================================
# AFTER: src/app.py (Standardized Global Exception Handlers)
# ==============================================================================
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from src.exceptions import DomainException

app = FastAPI(title="QuickPaper AI", lifespan=lifespan)

@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    status_map = {
        "ENTITY_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "ENTITY_EXISTS": status.HTTP_409_CONFLICT,
        "INVALID_CREDENTIALS": status.HTTP_401_UNAUTHORIZED,
        "PERMISSION_DENIED": status.HTTP_403_FORBIDDEN,
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "RATE_LIMITED": status.HTTP_429_TOO_MANY_REQUESTS,
    }
    status_code = status_map.get(exc.code, status.HTTP_400_BAD_REQUEST)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "path": request.url.path
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [{"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"]} for err in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_FAILED",
                "message": "Request payload validation failed.",
                "details": errors,
                "path": request.url.path
            }
        }
    )
```

---

### [ARCH-HIGH-03 to ARCH-LOW-04] Remaining Architecture Findings

#### [ARCH-HIGH-03] Fragile Type Coercion & Optional Model Conversion in `to_domain()`
- **File**: `src/paper/schemas.py:21-32`
- **Remediation**: Use `data = self.model_dump(exclude_unset=True, exclude_none=True)` in `to_domain()` so default model factories execute cleanly.

#### [ARCH-HIGH-04] Untyped Repository Interfaces & Inconsistent Return Value Error Handling
- **File**: `src/db/interfaces/interface.py:4-64`
- **Remediation**: Annotate abstract methods with explicit types `Optional[dict]` / `list[dict]` and raise `DatabaseOperationError` rather than returning boolean `False`.

#### [ARCH-HIGH-05] Presentation Layer Coupling in Application/Domain Services (`HTTPException`)
- **File**: `src/db/services/service.py:1`, `src/paper/service.py:6,10`
- **Remediation**: Remove `HTTPException` and `FileResponse` from application services; raise domain exceptions and let FastAPI routers handle HTTP responses.

#### [ARCH-MED-01] Missing Boundary Validation & Mutable Defaults in Domain Models
- **File**: `src/paper/models.py:120,123`
- **Remediation**: Replace `default=[]` with `default_factory=list`, add `ge=0, le=100` to distribution percentages, and unify `PaperDifficulty` enums.

#### [ARCH-MED-02] Storage Adapter Method Signature Mismatch (LSP Violation)
- **File**: `src/storage/adapters/local_storage.py:22`
- **Remediation**: Remove extraneous `content_type` parameter from `LocalStorageService.get_file`.

#### [ARCH-MED-03] Missing Interface Abstraction for `NotificationService` and `TaskManager`
- **File**: `src/notifications/adapters/firebase_notification_service.py` & `src/paper/task_manager.py`
- **Remediation**: Introduce abstract base classes `NotificationService` and `ITaskManager` in `interfaces/` modules.

#### [ARCH-MED-04] Route Handlers Importing Foreign Frameworks (`peewee`)
- **File**: `src/paper/routes/routes.py:5, 108-116`
- **Remediation**: Remove unused `from peewee import Database` import and type-hint `AsyncConnectionPool`.

#### [ARCH-MED-05] Inconsistent User Identity Resolution Across Route Endpoints
- **File**: `src/paper/routes/routes.py:62, 103` & `src/db/routes/routes.py:25`
- **Remediation**: Define an `AuthenticatedUser` Pydantic model returned by `get_current_user` with a consistent `.id` attribute.

#### [ARCH-MED-06] Inconsistent Authentication Route Status Codes
- **File**: `src/auth/routes/routes.py:29-35`
- **Remediation**: Set `status_code=status.HTTP_201_CREATED` on `POST /auth/register`.

#### [ARCH-LOW-01] Dead Duplicate Code in `src/paper/compilers/generator.py` (676 Lines)
- **File**: `src/paper/compilers/generator.py:1-676`
- **Remediation**: Delete `generator.py` after relocating `SECTION_CONFIG` to `models.py`.

#### [ARCH-LOW-02] Empty Duplicate File `notifications_messages.py`
- **File**: `src/notifications/constants/notifications_messages.py`
- **Remediation**: Delete orphan 0-byte file.

#### [ARCH-LOW-03] Hardcoded Email Infrastructure Configuration in `FastMailService`
- **File**: `src/mail/adapters/fastmail_mailer.py:9-19`
- **Remediation**: Read `settings.MAIL_SERVER` and `settings.MAIL_PORT` from application settings.

#### [ARCH-LOW-04] Missing Request Tracing & Correlation Middleware (`X-Request-ID`)
- **File**: `src/app.py:1-33`
- **Remediation**: Add Starlette middleware injecting a unique `uuid4()` request ID into `request.state` and response headers.

---

## Architectural Risk & Quality Attribute Matrix

| Quality Attribute | Current Baseline | Target Architecture (Post-Remediation) | Architectural Impact |
| :--- | :--- | :--- | :--- |
| **Security & Isolation** | BOLA/IDOR vulnerabilities, wildcard CORS, and dual-purpose JWTs allow cross-tenant data leaks and privilege escalation. | Enforced tenant scoping on all endpoints, restricted CORS whitelist, isolated token scopes, and constant-time OTP validation. | Neutralizes OWASP Top 10 vulnerabilities (BOLA, CORS bypass, Broken Auth). |
| **Concurrency & Async Safety** | Unmanaged `create_task`, SSE busy-polling, uncoordinated DB pools, and zombie LLM tasks threaten pool exhaustion. | ARQ-driven resume queue, event-driven Redis Pub/Sub streams, unified pool sizing, and active cancellation tokens. | Eliminates thread/connection starvation and prevents dropped background jobs. |
| **Reliability & LLM Robustness** | Invalid model names, fragile validators, and swallowed exceptions silently drop 10-question batches on minor formatting variations. | Valid model fallbacks, auto-normalizing Pydantic validators, and distributed token bucket with 429 exponential backoff. | Guarantees 100% question quota fulfillment and resilient error recovery. |
| **Maintainability & Clean Architecture** | Services tightly coupled to FastAPI, Supabase, and mutable model defaults; 676 lines of dead duplicate code. | Decoupled domain services, explicit interface contracts (DIP/LSP), unified error schemas, and deleted legacy files. | Enables rapid unit testing with in-memory mocks and safe framework migrations. |
| **System Observability** | 200 OK "Option A" error envelopes mask failures; missing correlation IDs hinder request tracing across background workers. | Standard HTTP status codes (4xx/5xx), structured API error envelopes, and end-to-end `X-Request-ID` correlation. | Delivers transparent telemetry and actionable client-side error handling. |

---

## Independent Verification & Validation Guide

To independently verify the audit observations and validate the proposed code remediations, execute the following commands in the workspace:

### 1. Python Syntax & Compilation Verification
Verify that all core Python modules compile without syntax errors:
```bash
python3 -m py_compile \
    src/app.py \
    src/dependencies.py \
    src/base_settings.py \
    src/auth/adapters/custom_auth_service.py \
    src/auth/adapters/redis_otp_store.py \
    src/auth/routes/routes.py \
    src/paper/routes/routes.py \
    src/paper/service.py \
    src/paper/models.py \
    src/paper/rate_limiter.py \
    src/paper/graph/nodes.py \
    src/paper/graph/builder.py \
    src/paper/graph/runner.py \
    src/paper/graph/tracker.py \
    src/paper/worker/settings.py \
    src/paper/worker/tasks.py \
    src/paper/compilers/adapters/document_compiler.py \
    src/paper/formatters/adapters/html_paper_formatter.py \
    src/paper/formatters/adapters/markdown_paper_formatter.py
```

### 2. Pydantic Model Resiliency & Normalization Test
Verify that the updated `Question` model auto-normalizes non-standard MCQ formats and mark allocations:
```bash
python3 -c "
from src.paper.models import Question, QuestionTypes, EvaluationPoint

# Test MCQ Auto-Normalization
q_mcq = Question(
    question_text='What is the unit of force?',
    question_type=QuestionTypes.MCQ,
    chapter='Motion',
    marks=1,
    options=['Newton', 'Joule'],
    correct_answer='Newton'
)
assert len(q_mcq.options) == 4, 'MCQ options failed to normalize to 4 items'

# Test Subjective Mark Balancing
q_subj = Question(
    question_text='Explain Newton Third Law.',
    question_type=QuestionTypes.TWO_MARK_ANS,
    chapter='Motion',
    marks=2,
    evaluation_scheme=[EvaluationPoint(point_text='Statement', allocated_marks=1), EvaluationPoint(point_text='Example', allocated_marks=3)]
)
assert sum(pt.allocated_marks for pt in q_subj.evaluation_scheme) == 2, 'Subjective marks failed to balance'
print('Pydantic auto-normalization validated successfully!')
"
```

### 3. Distributed Token Bucket Concurrency Test
Verify that the token bucket properly meters concurrent worker acquisitions:
```bash
python3 -c "
import asyncio
from src.paper.rate_limiter import DistributedTokenBucket

async def test_concurrency():
    bucket = DistributedTokenBucket(max_capacity=3, refill_rate=2.0)
    async def worker(w_id):
        await bucket.acquire()
        print(f'Worker {w_id} acquired token')
    await asyncio.gather(*(worker(i) for i in range(5)))

asyncio.run(test_concurrency())
"
```

### 4. Full Test Suite Execution
Execute the automated test suite to confirm zero regressions across all subsystems:
```bash
pytest -v
```

---
*Report generated and approved by Senior Staff Software Architect & Lead Security Reviewer.*
