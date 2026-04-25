# TalentFit Assist: Complete Enterprise Architecture

**Version:** 2.0 — Production-Ready  
**Date:** April 2026  
**Classification:** Enterprise-Grade AI System  
**Audience:** Principal Architects, Engineering Leads, CISOs, Responsible AI Reviewers

---

## TABLE OF CONTENTS

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Component Specifications](#component-specifications)
4. [Data Flow Diagrams](#data-flow-diagrams)
5. [Security Architecture](#security-architecture)
6. [Scaling Strategy](#scaling-strategy)
7. [Production Considerations](#production-considerations)
8. [Trade-offs & Design Decisions](#trade-offs--design-decisions)
9. [MVP vs. Production Hardening](#mvp-vs-production-hardening)

---

## EXECUTIVE SUMMARY

**TalentFit Assist** is a deterministic, explainable JD-to-Resume screening copilot built for large retail technology organizations with 500+ hiring teams.

### Core Principle
**"AI assists humans; humans decide."**

The system is engineered to prevent three classes of harm:
1. **Hiring Bias**: Protected attributes stripped at ingestion (not inference)
2. **False Authority**: LLM explains evidence, never makes decisions
3. **Unaccountable Black Box**: Every decision traceable with full audit trail

### Non-Functional Requirements Met
| Requirement | Target | Implementation |
|-------------|--------|-----------------|
| **Determinism** | 100% reproducibility | Pure Python scoring, no ML |
| **Auditability** | Zero-trust logging | Every operation immutable log entry |
| **Fairness** | Protected attribute stripping | At upload, before embedding |
| **Scalability** | 1000 candidates in <10s | ChromaDB + batch processing |
| **Security** | SOC2 compliance ready | Encryption, RBAC, secrets management |
| **Configurability** | No code changes required | Admin UI controls all behavior |

### Key Guarantees
- ✅ **Deterministic Scoring:** Same inputs → same outputs, 100% reproducible
- ✅ **Fully Auditable:** Every decision has traceable evidence chain
- ✅ **Fair & Unbiased:** Protected attributes stripped at source (age, gender, nationality, graduation year)
- ✅ **Explainable:** LLM explains *why* (citation-based), never *who* to hire
- ✅ **Human-in-the-Loop:** All screening results require human review
- ✅ **Configurable:** Weights, thresholds, models controllable from UI
- ✅ **Secure:** JWT-based auth, role-based access control, encrypted storage

---

## ARCHITECTURE OVERVIEW

### High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                       PRESENTATION LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │   Recruiter  │  │    Admin     │  │   Auditor    │               │
│  │   Screening  │  │ Configuration│  │  Compliance  │               │
│  │   UI         │  │   UI         │  │   View       │               │
│  │(Streamlit)   │  │(Streamlit)   │  │ (Streamlit)  │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
└────────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS/TLS 1.3
                              │ JWT Bearer Token
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  API GATEWAY & AUTH LAYER                           │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ FastAPI RBAC Middleware                                       │ │
│  │ ✓ JWT extraction & validation                                │ │
│  │ ✓ Role extraction from token claims                          │ │
│  │ ✓ Permission check at endpoint level                         │ │
│  │ ✓ Request/response audit logging                             │ │
│  │ ✓ Error handling with compliance formatting                  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ API Routes (/api/v1/*)                                         │ │
│  │ - /auth/login, /auth/refresh, /auth/logout                   │ │
│  │ - /config/{model, weights, guardrails, budget}              │ │
│  │ - /upload/{jd, resume, policy}                               │ │
│  │ - /screening/{run, results, status}                          │ │
│  │ - /usage/{tokens, costs, limits}                             │ │
│  │ - /audit/{logs, events, compliance-report}                   │ │
│  └────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              ORCHESTRATION & WORKFLOW LAYER                         │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ TalentFit Orchestration Agent                                 │ │
│  │                                                                │ │
│  │ Responsibilities:                                            │ │
│  │ ✓ Validates user role & permissions (RBAC gate)             │ │
│  │ ✓ Retrieves evidence from ChromaDB (deterministic RAG)       │ │
│  │ ✓ Invokes deterministic scoring engine                       │ │
│  │ ✓ Forwards context to MCP Server for LLM calls              │ │
│  │ ✓ Enforces guardrails before/after LLM                       │ │
│  │ ✓ Logs every step for full auditability                      │ │
│  │ ✓ Assembles structured response                              │ │
│  │                                                                │ │
│  │ Constraints (Agent CANNOT):                                  │ │
│  │ ✗ Score candidates                                           │ │
│  │ ✗ Rank candidates by preference                              │ │
│  │ ✗ Infer skills from other attributes                         │ │
│  │ ✗ Make any hiring recommendations                            │ │
│  │ ✗ Modify deterministic scores                                │ │
│  └────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
     ▲              ▲                ▲                  ▲
     │              │                │                  │
     │              │                │                  │
┌────┴──────────────┴────────────────┴──────────────────┴────────────┐
│                     BUSINESS LOGIC LAYER                            │
├──────────────┬──────────────────┬──────────────────┬────────────────┤
│  Config      │  Deterministic   │  RAG Data        │  MCP Server    │
│  Engine      │  Scoring Engine  │  Retrieval       │  (LLM API)     │
│              │                  │                  │                │
│ • Model sel. │ • Feature extract│ • ChromaDB query │ • Guardrails   │
│ • Weight cfg │ • Match algorithm│ • Metadata filter│ • Prompts      │
│ • LLM params │ • Score assembly │ • Similarity calc│ • Routing      │
│ • Budget set │ • Auditing       │ • Evidence link  │ • Cost track   │
└──────────────┴──────────────────┴──────────────────┴────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   PERSISTENT DATA LAYER                             │
├──────────────────────────────────────────────────────────────────── │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ChromaDB Vector Store (Semantic Search)                     │   │
│  │                                                              │   │
│  │ Collections:                                                │   │
│  │ • jd_chunks: Job descriptions → vectors + metadata          │   │
│  │ • resume_chunks: Resumes → vectors + metadata               │   │
│  │ • policy_chunks: Fairness policies → vectors                │   │
│  │                                                              │   │
│  │ Storage: Persistent (.chroma/ directory or remote)          │   │
│  │ Retrieval: Cosine similarity + metadata filtering           │   │
│  │ Updates: Incremental (new docs added, old not deleted)      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ PostgreSQL Database                                          │   │
│  │                                                              │   │
│  │ Tables:                                                      │   │
│  │ • users: User profiles (id, email, role, created_at)        │   │
│  │ • roles: Role definitions (name, permissions)               │   │
│  │ • jds: Job descriptions (id, title, content, meta)          │   │
│  │ • resumes: Resume metadata (id, candidate, status)          │   │
│  │ • screening_results: Results (id, jd_id, resume_ids)        │   │
│  │ • audit_logs: Every action (user, action, args, result)     │   │
│  │ • config: Current system config (model, weights, budget)    │   │
│  │ • tokens_usage: Per-user token tracking (daily, monthly)    │   │
│  │ • policies: Fairness policies (id, version, content)        │   │
│  │                                                              │   │
│  │ Features: ACID compliance, full audit trail, encryption     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ AWS S3 / Cloud Storage (Original Documents)                 │   │
│  │                                                              │   │
│  │ Buckets:                                                     │   │
│  │ • /original-documents: Encrypted originals (backups)        │   │
│  │ • /cleaned-documents: Protected-attr stripped versions       │   │
│  │ • /audit-exports: Compliance audit reports                  │   │
│  │                                                              │   │
│  │ Security: Server-side encryption, versioning, MFA delete    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## COMPONENT SPECIFICATIONS

### 1. FastAPI Backend (`backend/main.py`)

**Role:** REST API gateway, request validation, RBAC enforcement

**Key Features:**
- Stateless REST API (horizontally scalable)
- JWT-based authentication with role claims
- Middleware for audit logging
- Structured error responses with correlation IDs
- OpenAPI/Swagger documentation

**Middleware Stack:**
```python
app.add_middleware(CORSMiddleware, ...)          # CORS config
app.add_middleware(TrustedHostMiddleware, ...)   # Host validation
app.add_middleware(AuthMiddleware)               # JWT extraction
app.add_middleware(AuditMiddleware)              # Logging
app.add_middleware(ErrorHandlerMiddleware)       # Error formatting
```

**Example Endpoint:**
```python
@app.post("/api/v1/screening/run")
@require_permission(Permission.RUN_SCREENING)  # RBAC decorator
async def run_screening(
    request: ScreeningRequest,
    user: AuthToken = Depends(get_current_user)
) -> ScreeningResponse:
    """
    Trigger deterministic screening workflow.
    
    RBAC: Requires role=admin OR role=recruiter
    Audit: Full event logged with inputs/outputs
    """
    # Orchestration agent handles all business logic
    result = await orchestrator.run_screening(
        user_id=user.sub,
        jd_id=request.jd_id,
        resume_ids=request.resume_ids,
        user_role=user.role
    )
    return result
```

---

### 2. TalentFit Orchestration Agent (`backend/agent/orchestrator.py`)

**Role:** Workflow orchestration under strict tool constraints

**Allowed Tools:**

```python
class AgentTools:
    
    async def validate_user_policy(
        self, user_id: str, action: str
    ) -> PolicyValidationResult:
        """
        Check if user has permission to perform action.
        Returns: allowed (bool), reason (str), user_role (str)
        """
    
    async def retrieve_rag_evidence(
        self, jd_id: str, resume_ids: List[str], top_k: int = 5
    ) -> List[EvidenceChunk]:
        """
        Query ChromaDB for relevant evidence chunks.
        Does NOT filter or score - just retrieves.
        """
    
    async def compute_deterministic_score(
        self, jd_features: Dict, resume_features: Dict, weights: Dict
    ) -> ScoringResult:
        """
        Call scoring engine (pure Python, no ML).
        Returns: score (0.0-1.0), breakdown, audit_trail
        """
    
    async def call_mcp_explainer(
        self, context: ExplainerContext, scores: List[float], policy: str
    ) -> ExplanationResult:
        """
        Request LLM explanation via MCP Server.
        Input: ranked scores + evidence
        Output: Cited explanation (citations required)
        """
    
    async def log_audit_event(
        self, event: AuditEvent
    ) -> str:
        """Log action with full context. Returns audit_id."""
    
    async def assemble_response(
        self, scores: Dict, explanations: Dict, audit_id: str
    ) -> ScreeningResponse:
        """Assemble final structured response."""
```

**Forbidden Operations:**
```python
# Agent CANNOT do any of these:
# ❌ score_candidate(resume, jd) - scoring is deterministic engine's job
# ❌ rank_candidates(scores) - ranking is hiring decision
# ❌ infer_skill(resume_text, jd_skill) - inference forbidden
# ❌ modify_score(score, adjustment) - scores immutable
# ❌ filter_candidates(candidates, criteria) - filtering is ranking
```

**Example Workflow:**
```
User: "Screen 500 resumes against Senior Python Backend JD"

Agent executes:
┌─ Step 1: validate_user_policy("recruiter_001", "run_screening")
│  └─ ✓ Allowed (role=recruiter, has permission)
│
├─ Step 2: retrieve_rag_evidence(
│    jd_id="jd_003", 
│    resume_ids=[...500 IDs...],
│    top_k=5
│  )
│  └─ Returns ~2500 evidence chunks (5 per resume)
│
├─ Step 3: compute_deterministic_score(
│    jd_features={"must_have": [...], "experience": "5-10"},
│    resume_features=[...500 extracted features...],
│    weights={"must_have": 0.4, "nice": 0.2, ...}
│  )
│  └─ Returns scores [0.87, 0.65, 0.92, ...] with breakdowns
│
├─ Step 4: call_mcp_explainer(
│    context={
│      "top_candidates": [top 5 by score],
│      "evidence_chunks": [...],
│      "policy": "fairness_policy.md"
│    },
│    scores=[0.92, 0.87, 0.85, 0.82, 0.81]
│  )
│  └─ Returns explanation with citations: 
│     "[Resume: Experience] candidate has 8 years, [JD: Req] needs 5-10"
│
├─ Step 5: log_audit_event({
│    user_id: "recruiter_001",
│    action: "screening_run",
│    input: {jd_id, resume_ids_count},
│    output: {result_count, top_scores},
│    timestamp: now
│  })
│  └─ Audit ID: "audit_8f3c42b1"
│
└─ Step 6: assemble_response(...)
   └─ Returns JSON to FastAPI → UI
```

---

### 3. Deterministic Scoring Engine (`backend/core/scoring_engine.py`)

**Role:** Pure Python scoring (no ML, 100% deterministic)

**Formula:**
```
FINAL_SCORE = (
    (must_have_match × weight_must_have) +
    (nice_to_have_match × weight_nice_to_have) +
    (experience_alignment × weight_experience) +
    (domain_relevance × weight_domain) -
    (ambiguity_penalty × weight_ambiguity)
) / 100
```

**Inputs:** Extracted features from JD and resume (keyword matches)
**Output:** Score 0.0-1.0 with full breakdown

**Features:**
- Pure determinism: Same input → Same output, always
- Fully auditable: Every point tied to extraction logic
- No randomness: No random seeds, weights, or shuffle
- Human-readable: Every score breakdown is understandable

---

### 4. MCP Server (`mcp_server/main.py`)

**Role:** Centralized LLM control plane with guardrails

**Responsibilities:**
- Centralized prompt management (role-aware templates)
- Model selection and routing (Claude, OpenAI, Azure)
- Guardrail enforcement (input validation, output checks)
- Token usage tracking and cost estimation
- Provider abstraction (swap LLM provider without changing FastAPI)

**Guardrail Layers:**

| Layer | Enforcement | Purpose |
|-------|-------------|---------|
| **Input Sanitization** | Strip protected attributes | Prevent bias injection |
| **Prompt Injection** | Block malicious keywords | Prevent prompt hacking |
| **Citation Requirement** | Scan for evidence markers | Enforce grounding in facts |
| **Protected Attribute Detection** | Regex scan output | Prevent age/gender leakage |
| **Hiring Decision Ban** | Block decision language | Prevent "hire" or "reject" |
| **Output Length** | 50-500 tokens | Prevent hallucination via length |

---

### 5. ChromaDB Vector Store (`backend/storage/chromadb_client.py`)

**Role:** Semantic search and evidence retrieval

**Collections:**

```python
# jd_chunks collection
{
  "id": "ch_jd_003_001",
  "embedding": [0.12, 0.45, ...],  # Auto-embedded
  "metadata": {
    "jd_id": "jd_003",
    "jd_title": "Senior Backend Engineer",
    "section_type": "requirements",
    "sequence": 1,
    "created_at": "2026-04-25T10:30:00Z"
  },
  "document": "Must-have: Python, PostgreSQL, REST API. Experience with high-scale systems."
}

# resume_chunks collection
{
  "id": "ch_resume_042_001",
  "embedding": [...],
  "metadata": {
    "candidate_id": "cand_042",
    "section_type": "experience",
    "sequence": 1,
    "years_of_experience": 7,
    "industries": ["retail", "fintech"]
  },
  "document": "Senior Python Backend Engineer at RetailCorp (2021-2026). Led team of 5..."
}

# policy_chunks collection
{
  "id": "ch_policy_001_001",
  "embedding": [...],
  "metadata": {
    "policy_id": "policy_fairness_v2",
    "version": 2,
    "policy_type": "fairness_guidelines"
  },
  "document": "Do not consider age, graduation year, or nationality in any evaluation."
}
```

**Query Example:**
```python
# Retrieve top 5 resume chunks most similar to JD requirements
results = chromadb_client.query(
    query_embedding=embed("Python PostgreSQL REST API"),
    collection_name="resume_chunks",
    n_results=5,
    where={"candidate_id": "cand_042"}  # Filter by metadata
)

# Returns: [
#   {id, document, metadata, distance},
#   ...
# ]
```

---

### 6. RBAC Enforcement (`backend/auth/rbac.py`)

**Role Matrix:**

```
                  Admin  Recruiter  Hiring Manager  Auditor
─────────────────────────────────────────────────────────
Upload JD          ✓        ✓           ✗             ✗
Upload Resume      ✓        ✓           ✗             ✗
Upload Policy      ✓        ✗           ✗             ✗
Modify Config      ✓        ✗           ✗             ✗
Run Screening      ✓        ✓           ✗             ✗
View Results       ✓        ✓           ✓             ✗
View Audit Logs    ✓        ✗           ✗             ✓
View Costs         ✓        ✗           ✗             ✓
Manage Users       ✓        ✗           ✗             ✗
```

**Enforcement Points:**
1. **Middleware**: Extract role from JWT token
2. **Endpoint**: Decorator `@require_permission(Permission.RUN_SCREENING)`
3. **Agent Tools**: `AgentToolConstraint(user_role).can_invoke(tool_name)`
4. **UI Rendering**: Streamlit hides pages based on role

---

## DATA FLOW DIAGRAMS

### Flow 1: Admin Configuration

```
Admin User
   │
   ├─ Login (email/password)
   ├─ JWT token issued (role=admin)
   │
   ├─ POST /api/v1/config/update
   │   {
   │     "llm_model": "claude-3-sonnet",
   │     "temperature": 0.3,
   │     "max_tokens": 300,
   │     "chunk_size": 256,
   │     "embedding_model": "text-embedding-3-small",
   │     "weights": {
   │       "must_have": 0.4,
   │       "nice_to_have": 0.2,
   │       "experience": 0.2,
   │       "domain": 0.1,
   │       "ambiguity": 0.1
   │     },
   │     "guardrail_strictness": "HIGH"
   │   }
   │
   ├─ FastAPI validates RBAC (admin? ✓)
   ├─ Config Engine updates in-memory config
   ├─ PostgreSQL persists config (with version)
   │
   └─ Response: {success: true, config_id: "cfg_123"}
```

### Flow 2: Document Upload & Embedding

```
Recruiter uploads: resumes.jsonl (500 resumes)
   │
   ├─ POST /api/v1/upload/resume
   ├─ FastAPI validates file format (JSONL)
   │
   ├─ Document Service:
   │   ├─ Read each resume: {id, text, candidate_name, email}
   │   ├─ Data Cleaner strips protected attributes
   │   │   (Remove: age, gender, graduation year, nationality)
   │   ├─ Tokenize document
   │   ├─ Token-Aware Chunker splits by chunk_size=256, overlap=50
   │   ├─ Embedding Handler embeds each chunk
   │   ├─ Store in ChromaDB with metadata
   │   │   (candidate_id, section_type, sequence_number)
   │   └─ Backup original to S3 (encrypted)
   │
   └─ Response: {uploaded: 500, chunks_created: 2847, audit_id}
```

### Flow 3: Screening Execution

```
Recruiter triggers: "Screen 500 candidates against JD_003"
   │
   ├─ POST /api/v1/screening/run
   │   {
   │     "jd_id": "jd_003",
   │     "resume_ids": ["cand_001", ..., "cand_500"]
   │   }
   │
   ├─ FastAPI validates JWT (role=recruiter? ✓)
   │
   ├─ Orchestration Agent:
   │   │
   │   ├─ Step 1: Validate RBAC
   │   │  validate_user_policy("recruiter_042", "run_screening")
   │   │
   │   ├─ Step 2: Retrieve RAG Evidence
   │   │  for each resume in [500]:
   │   │    retrieve_rag_evidence(
   │   │      jd_embedding,
   │   │      resume_id,
   │   │      top_k=5
   │   │    ) → [5 chunks]
   │   │  Total: 2500 evidence chunks
   │   │
   │   ├─ Step 3: Compute Deterministic Scores
   │   │  for each resume:
   │   │    score = scoring_engine.compute(
   │   │      jd_features,
   │   │      resume_features,
   │   │      weights
   │   │    )
   │   │  Scores: [0.87, 0.65, 0.92, 0.54, ...] (500 scores)
   │   │
   │   ├─ Step 4: LLM Explanations (Top 5 only)
   │   │  for top_5_candidates:
   │   │    explanation = mcp_server.explain(
   │   │      evidence_chunks,
   │   │      score,
   │   │      policy
   │   │    )
   │   │    ✓ Citations required
   │   │    ✓ No hiring decisions
   │   │    ✓ Guardrails checked
   │   │
   │   ├─ Step 5: Audit Logging
   │   │  log_audit_event({
   │   │    user: "recruiter_042",
   │   │    action: "screening_run",
   │   │    inputs: {jd_id, resume_count},
   │   │    outputs: {scores, explanations},
   │   │    timestamp: now,
   │   │    costs: {tokens_used, estimated_cost}
   │   │  })
   │   │
   │   └─ Step 6: Assemble Response
   │      Return to FastAPI:
   │      {
   │        "screening_id": "scr_42",
   │        "timestamp": "2026-04-25T15:30:00Z",
   │        "results": [
   │          {
   │            "candidate_id": "cand_003",
   │            "score": 0.92,
   │            "score_breakdown": {
   │              "must_have": 0.95,
   │              "nice_to_have": 0.70,
   │              "experience": 1.0,
   │              "domain": 1.0,
   │              "ambiguity_penalty": 0
   │            },
   │            "explanation": "[Resume: line 3] Python experience...",
   │            "evidence_count": 5
   │          },
   │          ...
   │        ],
   │        "audit_id": "audit_42",
   │        "cost_usd": 0.23
   │      }
   │
   └─ UI renders ranked list with evidence cards
```

---

## SECURITY ARCHITECTURE

### Authentication & Authorization

**JWT Token Structure:**
```json
{
  "sub": "user_42",
  "email": "recruiter@company.com",
  "role": "recruiter",
  "permissions": ["run_screening", "view_results", "upload_resume"],
  "iat": 1714070400,
  "exp": 1714156800,
  "iss": "talentfit-auth"
}
```

**Token Lifecycle:**
- **Issued:** Login endpoint, 24-hour expiry
- **Validated:** Every request by AuthMiddleware
- **Refreshed:** Optional refresh endpoint
- **Revoked:** Logout adds to blacklist (Redis)

### Data Protection

| Data | At Rest | In Transit | In Use |
|------|---------|-----------|--------|
| **Passwords** | Bcrypt + salt | N/A (hashed before send) | Never in memory |
| **JWT Tokens** | Redis (blacklist only) | HTTPS/TLS 1.3 | Memory (short-lived) |
| **Resumes** | AES-256 encryption | HTTPS/TLS 1.3 | Streaming (not all in memory) |
| **Audit Logs** | PostgreSQL + immutable | HTTPS/TLS 1.3 | Read-only access |
| **API Keys** | Vault / SecretsManager | Injected via env | Never in code |

### Guardrails Enforcement

**Input Validation:**
```python
class InputGuardrails:
    def validate_all(text: str) -> bool:
        checks = [
            validate_prompt_injection(text),
            validate_protected_attributes(text),
            validate_input_length(text)
        ]
        return all(c.passed for c in checks)
```

**Output Validation:**
```python
class OutputGuardrails:
    def validate_all(text: str) -> bool:
        checks = [
            validate_citations_present(text),
            validate_no_protected_attributes(text),
            validate_no_hiring_decisions(text),
            validate_output_length(text),
            validate_no_hallucination_indicators(text)
        ]
        return all(c.passed for c in checks)
```

---

## SCALING STRATEGY

### Horizontal Scalability

**Stateless Design:**
- FastAPI instances: Run behind load balancer
- Agent instances: Run as separate worker processes
- MCP Server: Can be replicated across multiple instances

**Database Scaling:**
- PostgreSQL: Read replicas for audit log queries
- ChromaDB: Persistent storage (local SSD or network attached)
- Redis: Session store, token blacklist (optional clustering)

**Batch Processing:**
- 500 resumes screened in ~10 seconds (with 5 API calls):
  1. Retrieve evidence (2s): 500 × 5 chunks = 2500 chunks queried
  2. Score (3s): Pure Python, vectorized operations
  3. Explain (4s): 5 parallel LLM API calls
  4. Log + respond (1s): Database writes

**Typical Deployment:**
```
Load Balancer (AWS ALB)
├─ FastAPI Instance 1 (t3.medium)
├─ FastAPI Instance 2 (t3.medium)
└─ FastAPI Instance 3 (t3.medium)

MCP Server
├─ Claude API (async client)
└─ Cost tracking service

PostgreSQL
├─ Primary (t3.large) - configs, audit
└─ Read Replica (t3.large) - audit queries

ChromaDB
├─ Persistent (.chroma/ on EBS)
└─ Auto-scaling vector searches

Redis
└─ Session + token blacklist (cache-2xlarge)

S3
└─ Encrypted document backups
```

---

## PRODUCTION CONSIDERATIONS

### Monitoring & Observability

**Metrics to Track:**
- Request latency (p50, p95, p99)
- Token usage per user/day
- Cost per screening
- Guardrail violation rate
- Cache hit rate (ChromaDB)
- Database query latency

**Logging:**
- Structured logs (JSON format)
- Correlation IDs on every request
- Full audit trail for compliance

### Disaster Recovery

**RPO (Recovery Point Objective):** <1 hour
**RTO (Recovery Time Objective):** <1 hour

**Backup Strategy:**
- PostgreSQL: Daily snapshots to S3
- ChromaDB: Periodic exports to S3
- Original documents: Versioned in S3 with MFA delete

---

## TRADE-OFFS & DESIGN DECISIONS

### Decision 1: Deterministic Scoring vs. ML Models

**Choice:** Deterministic (no neural networks)

**Rationale:**
- ✅ 100% Reproducibility: Same input always gives same output
- ✅ Explainability: Every point traceable to business logic
- ✅ Fairness: No learned biases from training data
- ✅ Auditability: Clear evidence for each component

**Trade-off:**
- ❌ Less accurate than ML (but fairness > precision in hiring)
- ❌ Requires manual feature engineering
- ❌ Cannot discover non-obvious patterns

**Why Fair > Accurate:** A hiring system can be wrong, but it cannot be unfair.

---

### Decision 2: LLM for Explanation Only

**Choice:** Never let LLM score or rank

**Rationale:**
- ✅ Legal liability: AI doesn't make decisions
- ✅ Human oversight: Human must read explanation
- ✅ Accountability: Clear who's responsible (human recruiter)
- ✅ Audit trail: Every explanation cited with evidence

**Trade-off:**
- ❌ More API calls: 5 explanations × 500 screenings
- ❌ Higher cost: ~$0.02 per explanation
- ❌ Higher latency: Waits for LLM responses

**Why Explanation-Only:** "The system suggested this, but I'm responsible for this hiring decision."

---

### Decision 3: Orchestration Agent vs. Monolithic

**Choice:** Agent as conductor, not decision-maker

**Rationale:**
- ✅ Clear separation: Each tool has one responsibility
- ✅ Testability: Can test each tool independently
- ✅ Auditability: Each step logged separately
- ✅ Maintainability: Adding features doesn't require core rewrites

**Trade-off:**
- ❌ More complex orchestration code
- ❌ More function calls = slight latency overhead
- ❌ Requires stricter tool contracts

**Why Orchestration:** Clear audit trail requires clear steps.

---

### Decision 4: Protected Attribute Stripping at Ingestion

**Choice:** Remove at upload, not per-query

**Rationale:**
- ✅ Defense in depth: Prevents accidental leakage
- ✅ Performance: One-time cleanup, not per-request
- ✅ Consistency: Admin cannot change stripped data
- ✅ Audit clarity: Clear point where fairness enforced

**Trade-off:**
- ❌ Information loss: Cannot use age for "graduate program"
- ❌ Cannot retroactively change policy
- ❌ Requires careful feature extraction logic

**Why Early Stripping:** Once it's gone, it cannot leak.

---

## MVP VS. PRODUCTION HARDENING

### MVP (v1.0) - Ready for Launch

**What's Included:**
- ✅ Single-threaded LLM calls (synchronous)
- ✅ Local ChromaDB (persistent .chroma directory)
- ✅ Basic RBAC (4 roles, no fine-grained permissions)
- ✅ In-memory config cache (reloaded on restart)
- ✅ JSON audit logs (local filesystem)
- ✅ Basic guardrails (regex-based)

**Time to Deploy:** ~2 weeks on AWS EC2
**Cost to Run:** ~$500/month (compute + LLM API)

---

### Hardening Roadmap (v1.1-v2.0)

#### Phase 1: Enterprise Reliability (Month 2)

**Improvements:**
- [ ] Async/await for LLM calls (5x throughput)
- [ ] Elasticsearch for audit log search (compliance requirement)
- [ ] Database connection pooling (higher concurrency)
- [ ] Caching layer (Redis) for frequent queries
- [ ] Circuit breaker for LLM API failures

**Effort:** 1 week  
**Impact:** Can handle 10x load

---

#### Phase 2: Advanced Security (Month 3)

**Improvements:**
- [ ] Field-level encryption in PostgreSQL (sensitive fields)
- [ ] Kubernetes deployment (auto-scaling, multi-region)
- [ ] Multi-factor authentication (MFA) for admin
- [ ] API rate limiting (prevent abuse)
- [ ] IP whitelisting (restrict access)

**Effort:** 2 weeks  
**Impact:** SOC2 Type II compliance

---

#### Phase 3: Intelligence & Insights (Month 4)

**Improvements:**
- [ ] Fairness metrics dashboard (bias detection)
- [ ] ML-based bias detection (flag suspicious patterns)
- [ ] Candidate experience feedback (feedback loop)
- [ ] Comparative analytics (how teams screen)
- [ ] Predictive offer-acceptance modeling

**Effort:** 3 weeks  
**Impact:** Strategic insights into hiring patterns

---

#### Phase 4: Global Scaling (Month 6)

**Improvements:**
- [ ] Multi-region deployment (EU, APAC)
- [ ] 24/7 support SLAs
- [ ] Localization (multi-language prompts)
- [ ] GDPR compliance (data residency)
- [ ] Enterprise SSO (SAML/OIDC)

**Effort:** 4 weeks  
**Impact:** Enterprise sales unlock

---

### Feature Parity: MVP vs. Production

| Feature | MVP | v1.1 | v1.5 | v2.0 |
|---------|-----|------|------|------|
| Basic Screening | ✅ | ✅ | ✅ | ✅ |
| RBAC (4 roles) | ✅ | ✅ | ✅ | ✅ |
| Deterministic Scoring | ✅ | ✅ | ✅ | ✅ |
| Guardrails | ✅ | ✅ | ✅ | ✅ |
| Async LLM | ❌ | ✅ | ✅ | ✅ |
| Elasticsearch Audit | ❌ | ✅ | ✅ | ✅ |
| Kubernetes | ❌ | ❌ | ✅ | ✅ |
| Multi-region | ❌ | ❌ | ❌ | ✅ |
| Fairness Dashboard | ❌ | ❌ | ✅ | ✅ |
| SSO Integration | ❌ | ❌ | ❌ | ✅ |

---

## Conclusion

**TalentFit Assist** is designed as an enterprise system from day one, not a toy demo. Every architectural decision prioritizes:

1. **Fairness**: Bias detection and prevention
2. **Explainability**: Evidence-based decisions
3. **Auditability**: Full trace for compliance
4. **Security**: Enterprise-grade controls
5. **Scalability**: 1000s of candidates, 100s of teams

The MVP is production-ready and can be deployed to a Fortune 500 company's infrastructure with confidence.

---

**Document Version:** 2.0 | **Date:** April 25, 2026 | **Classification:** Enterprise Architecture
