# TalentFit Assist: Enterprise Architecture Design

**Version:** 1.0  
**Date:** April 2026  
**Classification:** Enterprise-Grade AI System  
**Audience:** Principal Architects, Engineering Leads, Responsible AI Reviewers

---

## EXECUTIVE SUMMARY

**TalentFit Assist** is a deterministic, explainable JD-to-Resume screening copilot designed for large retail technology organizations. It provides evidence-based candidate evaluation without making hiring decisions.

**Core Design Principle:** *AI assists humans; humans decide.*

### Key Guarantees
- ✅ **Deterministic Scoring:** No randomness in matching logic
- ✅ **Fully Auditable:** Every decision traceable with evidence
- ✅ **Fair & Unbiased:** Protected attributes stripped at ingestion
- ✅ **Explainable:** LLM explains *why* only, not *who*
- ✅ **Human-in-the-Loop:** All outputs require human review
- ✅ **Configurable:** Admin controls all model behavior
- ✅ **Secure:** RBAC, JWT, encrypted storage

---

## ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │Recruiter UI  │  │Admin Config  │  │Auditor View  │       │
│  │(Streamlit)   │  │(Streamlit)   │  │(Streamlit)   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└────────────────────────────────────────────────────────────┘
                              ▲
                              │ HTTPS/JWT
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API GATEWAY & AUTH LAYER                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  FastAPI RBAC Middleware  (JWT Validation)            │  │
│  │  - Role extraction                                    │  │
│  │  - Permission enforcement                            │  │
│  │  - Audit logging                                     │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                              ▲
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              ORCHESTRATION & WORKFLOW LAYER                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  TalentFit Orchestration Agent                       │  │
│  │  - Validates user role & permissions                │  │
│  │  - Enforces execution order                         │  │
│  │  - Invokes constrained tools only                   │  │
│  │  - Assembles final structured response              │  │
│  │  - Fully auditable step-by-step logs                │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
     ▲                ▲                    ▲                ▲
     │                │                    │                │
     ▼                ▼                    ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Config     │ │  Deterministic
System      │ │  RAG         │ │     MCP      │
│  Engine      │ │ Scoring      │ │  Retrieval   │ │   Server     │
│              │ │   Engine     │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
     ▲                ▲                    ▲                ▲
     │                │                    │                │
     └───────────────────────────────────────────────────────┘
                       │
                       ▼
          ┌─────────────────────────────┐
          │   PERSISTENT DATA LAYER      │
          │  ┌─────────────────────────┐ │
          │  │ ChromaDB Vector Store   │ │
          │  │ (JDs, Resumes, Policies)│ │
          │  └─────────────────────────┘ │
          │  ┌─────────────────────────┐ │
          │  │ PostgreSQL              │ │
          │  │ (RBAC, Audit Logs, Conf)│ │
          │  └─────────────────────────┘ │
          │  ┌─────────────────────────┐ │
          │  │ S3 / Encrypted Storage  │ │
          │  │ (Original Documents)    │ │
          │  └─────────────────────────┘ │
          └─────────────────────────────┘
```

---

## COMPONENT RESPONSIBILITIES

### 1. **FastAPI Backend** (Control Plane)
**Responsibility:** REST API gateway, RBAC enforcement, workflow orchestration

**Core Responsibilities:**
- ✅ HTTP request validation
- ✅ JWT token extraction and validation
- ✅ Role-based access control at middleware level
- ✅ Stateless request routing
- ✅ Error handling with audit trails
- ✅ Structured response assembly

**Cannot Do:**
- ❌ Scoring
- ❌ Embedding
- ❌ LLM calls (delegated to MCP)
- ❌ Direct database modifications (triggers agent only)

---

### 2. **TalentFit Orchestration Agent** (Workflow Conductor)
**Responsibility:** Coordinate multi-step workflows under strict constraints

**Allowed Tools:**
1. `validate_user_policy()` — Check role and permissions
2. `retrieve_rag_evidence()` — Query ChromaDB (no scoring)
3. `compute_deterministic_score()` — Invoke scoring engine
4. `call_mcp_explainer()` — Request LLM explanation
5. `log_audit_event()` — Record decision trail
6. `assemble_response()` — Structure final output

**Forbidden Operations:**
- ❌ Cannot score candidates
- ❌ Cannot rank candidates
- ❌ Cannot infer skills or experience
- ❌ Cannot modify deterministic scores
- ❌ Cannot make hiring decisions
- ❌ Cannot access raw candidate data

**Example Workflow:**
```
1. Agent receives screening request from FastAPI
2. Agent: validate_user_policy(user_id, role, action="screen")
   → Confirm recruiter can run screening
3. Agent: retrieve_rag_evidence(jd_id, resume_ids, top_k=5)
   → Get matching chunks from ChromaDB
4. Agent: compute_deterministic_score(jd_features, resume_features, weights)
   → Get deterministic match scores
5. Agent: call_mcp_explainer(context, scores, policy)
   → Request LLM to explain top 3 candidates
6. Agent: log_audit_event(user, action, inputs, outputs)
   → Record full decision trail
7. Agent: assemble_response(scores, explanations, audit_id)
   → Return structured result to FastAPI
8. FastAPI: Return to UI with audit trail
```

---

### 3. **MCP Server** (LLM Control Plane)
**Responsibility:** Centralized LLM management with guardrails

**MCP Responsibilities:**
- ✅ Centralized prompt management
- ✅ Model selection and routing
- ✅ Guardrail enforcement (input + output)
- ✅ Token usage tracking and cost estimation
- ✅ Provider abstraction (Claude, OpenAI, Azure)
- ✅ Output validation

**MCP Guardrail Enforcement:**

| Guardrail | Implementation | Enforcement |
|-----------|-----------------|------------|
| **Input Sanitization** | Strip protected attributes | Before LLM call |
| **Prompt Injection Protection** | Use role-aware system prompts | Template-based only |
| **Citation Requirement** | Require evidence references | Output validation |
| **Protected Attribute Detection** | Scan output for age, gender, etc. | Post-generation filter |
| **Hallucination Check** | Enforce evidence grounding | Output validator |
| **Token Limits** | Max tokens configurable per role | Pre-call enforcement |
| **Output Length** | Explainability conciseness | Post-call validation |

---

### 4. **Deterministic Scoring Engine**
**Responsibility:** Compute candidate-JD match scores with 100% reproducibility

**Scoring Formula:**

```
FINAL_SCORE = (
    (must_have_match_score * weight_must_have) +
    (nice_to_have_match_score * weight_nice_to_have) +
    (experience_range_score * weight_experience) +
    (domain_relevance_score * weight_domain) -
    (ambiguity_penalty * weight_ambiguity_penalty)
) / 100

Where:
  must_have_match_score = % of must-have skills matched [0-100]
  nice_to_have_match_score = % of nice-to-have skills matched [0-100]
  experience_range_score = alignment with required years [0-100]
  domain_relevance_score = industry experience match [0-100]
  ambiguity_penalty = penalty for unclear/missing info [0-50]
```

**Weights Configurable from UI:**
- `weight_must_have`: [0.0 - 1.0] (default: 0.4)
- `weight_nice_to_have`: [0.0 - 1.0] (default: 0.2)
- `weight_experience`: [0.0 - 1.0] (default: 0.2)
- `weight_domain`: [0.0 - 1.0] (default: 0.1)
- `weight_ambiguity_penalty`: [0.0 - 1.0] (default: 0.1)

**Scoring Properties:**
- ✅ Fully deterministic: Same inputs → Same outputs
- ✅ Fully auditable: Score breakdown shown
- ✅ Human-readable: Clear why score is X
- ✅ No ML randomness: No neural networks involved

---

### 5. **ChromaDB Vector Store**
**Responsibility:** Persistent vector storage for RAG evidence retrieval

**Storage Structure:**

| Collection | Documents | Metadata | Purpose |
|------------|-----------|----------|---------|
| `jd_chunks` | JD text chunks | jd_id, section_type, sequence | Evidence for requirements |
| `resume_chunks` | Resume text chunks | candidate_id, section_type, jd_id_association | Evidence for capabilities |
| `policy_chunks` | Policy text chunks | policy_id, version | Fairness guardrails retrieval |

**Metadata-Aware Retrieval:**
```python
# Retrieve top-5 resume chunks most similar to JD
results = chromadb.query(
    query_embedding=jd_embedding,
    n_results=5,
    where={"candidate_id": candidate_id}  # Metadata filter
)
# Returns chunks with candidate_id, section, text, similarity score
```

---

### 6. **RBAC Enforcement Strategy**

**Role Definition:**

| Role | Upload | Config | Screen | Review | Audit |
|------|--------|--------|--------|--------|-------|
| **Admin** | ✅ | ✅ | ❌ | ❌ | ✅ |
| **Recruiter** | ✅ | ❌ | ✅ | ✅ | ❌ |
| **Hiring Manager** | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Auditor** | ❌ | ❌ | ❌ | ❌ | ✅ |

**Enforcement Points:**

```
Request flows:
1. FastAPI receives HTTP request
2. Middleware extracts JWT token
3. JWT decoded and role extracted
4. Route handler checks @require_role decorator
5. If unauthorized: return 403 with audit log
6. If authorized: proceed to orchestration agent
7. Agent receives user role from request context
8. Agent enforces tool-level permissions
9. Audit log records: user, action, role, timestamp, outcome
```

---

## CHUNKING & EMBEDDING STRATEGY

### Chunking Configuration (UI-Configurable)

| Document Type | Default Chunk Size | Default Overlap | Rationale |
|----------------|-------------------|-----------------|-----------|
| Job Description | 256 tokens | 50 tokens | Preserve requirement context |
| Resume | 128 tokens | 30 tokens | Keep work experience units together |
| Policy | 512 tokens | 100 tokens | Full guideline context |

### Embedding Strategy
- **Embedding Model:** Configurable from UI (default: `text-embedding-3-small`)
- **Chunking Engine:** Token-aware chunking with metadata preservation
- **Storage:** ChromaDB with cosine similarity search
- **Retrieval:** Top-K configurable (default: 5)

---

## END-TO-END DATA FLOW (DETAILED)

### Phase 1: Admin Configuration
```
Admin User logs in → Authenticated with JWT (role=admin)
  ↓
FastAPI /config/update endpoint
  ├─ Set embedding model: text-embedding-3-small
  ├─ Set chunk size: 256 tokens
  ├─ Set scoring weights: must_have=0.4, nice_to_have=0.2, ...
  ├─ Set LLM: Claude-3-sonnet
  ├─ Set temperature: 0.3
  ├─ Set max_tokens: 300
  ├─ Set guardrail strictness: HIGH
  └─ Set monthly token budget: $500
  
  Config stored in PostgreSQL (encrypted, versioned)
  Audit log: user_id, timestamp, changes
```

### Phase 2: Document Ingestion
```
Recruiter uploads JDs and Resumes as JSONL
  ↓
FastAPI /upload/jd and /upload/resume endpoints
  ├─ Validate JSONL format
  ├─ Data cleaning: remove protected attributes (age, gender, etc.)
  ├─ Chunk documents with configured chunk size
  ├─ Compute embeddings using configured model
  ├─ Store in ChromaDB with metadata:
  │   {
  │     "jd_id": "jd_001",
  │     "candidate_id": "c_042",
  │     "section_type": "skills",
  │     "document_type": "resume",
  │     "chunk_sequence": 3
  │   }
  └─ Store original documents in encrypted S3
  
Audit log: uploader, document count, cleaning actions
```

### Phase 3: Screening Execution
```
Recruiter clicks "Run Screening" for JD_001
  ↓
FastAPI /screen/run endpoint
  ├─ Extract JWT: user_id, role=recruiter
  ├─ RBAC check: role can perform screening? YES
  ├─ Invoke TalentFit Orchestration Agent
  │
  └─→ Agent Step 1: Validate Permissions
      ├─ Agent calls validate_user_policy(recruiter, action=screen)
      └─ Result: ✅ Authorized
      
  └─→ Agent Step 2: Retrieve Context
      ├─ Agent calls retrieve_rag_evidence(jd_id=jd_001, top_k=5)
      ├─ ChromaDB returns top-5 chunks similar to JD requirements
      └─ Result: 
          [
            {text: "5+ years Python experience", chunk_id: ch_1},
            {text: "PostgreSQL database design", chunk_id: ch_2},
            ...
          ]
  
  └─→ Agent Step 3: Compute Deterministic Scores
      ├─ Agent calls compute_deterministic_score()
      ├─ For each candidate in pool:
      │   ├─ Extract JD features: must_have_skills, experience_range
      │   ├─ Extract resume features: mentioned_skills, years_at_role
      │   ├─ Compute match scores using deterministic formula
      │   └─ Output: {candidate_id, score: 0.78, breakdown: {...}}
      └─ Result: Ranked list [candidate_A: 0.82, candidate_B: 0.78, ...]
  
  └─→ Agent Step 4: Request LLM Explanations
      ├─ Agent calls call_mcp_explainer() with:
      │   {
      │     "context": <retrieved JD chunks>,
      │     "candidates": <top-3 ranked>,
      │     "scores": <{candidate_id, score}>,
      │     "policy": <fairness guidelines>,
      │     "user_role": recruiter,
      │     "max_tokens": 300
      │   }
      ├─ MCP Server applies guardrails:
      │   ├─ Input: Strip any protected attributes
      │   ├─ Prompt: Use recruiter-specific template
      │   ├─ Call: Claude with cold-start (temp=0.3)
      │   ├─ Output: Parse and validate citations present
      │   └─ Scan: Check for protected attributes in output
      └─ Result: LLM-generated explanation for each candidate
  
  └─→ Agent Step 5: Log and Assemble
      ├─ Agent calls log_audit_event()
      ├─ Records: screening_id, user, timestamp, candidates, scores, explanation_tokens
      └─ Result: audit_entry_id
  
  └─→ Agent Step 6: Return to FastAPI
      └─ Returns: {
           "screening_id": "scr_xyz",
           "jd_id": "jd_001",
           "results": [
             {
               "candidate_id": "c_042",
               "score": 0.82,
               "breakdown": {
                 "must_have_match": 0.90,
                 "experience_match": 0.75,
                 ...
               },
               "explanation": "This candidate has 7 years of Python...",
               "evidence": [ch_1, ch_3, ch_7],
               "audit_id": "aud_123"
             },
             ...
           ],
           "tokens_used": 487,
           "estimated_cost": 0.02
         }

FastAPI returns to UI
  ↓
Streamlit renders candidate cards with scores, breakdowns, and explanations
```

---

## GUARDRAIL ENFORCEMENT ARCHITECTURE

### Input Guardrails
**Enforced:** Data ingestion phase (FastAPI upload endpoints)
```python
def clean_document(doc):
    """Strip protected attributes"""
    protected_patterns = {
        'age': r'\b(\d{1,3})\s*(year|yo|y\.o\.)\b',
        'gender': r'\b(male|female|he|she|his|her)\b',  # Only pronouns
        'nationality': r'\b(Indian|American|British|Chinese)\b',
        'graduation_year': r'\b(Class of |Graduated |2020|2021|202\d)\b'
    }
    
    for attr, pattern in protected_patterns.items():
        doc = re.sub(pattern, '[REDACTED]', doc, flags=re.IGNORECASE)
    
    return doc
```

### Prompt Guardrails
**Enforced:** MCP Server (role-aware system prompts)
```
SYSTEM_PROMPT_RECRUITER = """
You are a screening assistant. Your role:
- Explain why each candidate matches job requirements
- Cite specific resume sections as evidence
- Do NOT make hiring recommendations
- Do NOT infer missing information
- Do NOT mention age, gender, or protected attributes
- Do NOT rank candidates as better/worse

Format:
1. Evidence: [Resume section #X]
2. Explanation: [How this aligns with requirement]
3. Gaps: [What's unclear or missing]
"""
```

### Output Guardrails
**Enforced:** MCP Server (post-generation validators)
```python
def validate_output(llm_response):
    """Check for guardrail violations"""
    
    # Check 1: Citations present?
    if len(re.findall(r'\[Resume.*?\]', llm_response)) == 0:
        raise GuardrailViolation("No citations found")
    
    # Check 2: Protected attributes mentioned?
    protected_patterns = ['age', 'gender', 'nationality', 'graduation', 'born']
    for pattern in protected_patterns:
        if re.search(pattern, llm_response, re.IGNORECASE):
            raise GuardrailViolation(f"Protected attribute detected: {pattern}")
    
    # Check 3: Hiring decision language?
    if re.search(r'should (hire|reject|select)', llm_response, re.IGNORECASE):
        raise GuardrailViolation("Hiring decision language detected")
    
    # Check 4: Length reasonable?
    if len(llm_response) > 1000:
        raise GuardrailViolation("Explanation too long; may contain hallucinations")
    
    return True
```

---

## CONFIGURATION MANAGEMENT

### Configuration Schema
```json
{
  "config_id": "cfg_prod_v3",
  "version": 3,
  "created_at": "2026-04-24T10:00:00Z",
  "updated_by": "admin@company.com",
  
  "llm_config": {
    "provider": "anthropic",
    "model": "claude-3-sonnet-20240229",
    "temperature": 0.3,
    "max_tokens": 300,
    "top_p": 0.9
  },
  
  "embedding_config": {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "embedding_dimension": 1536
  },
  
  "chunking_config": {
    "jd_chunk_size": 256,
    "jd_overlap": 50,
    "resume_chunk_size": 128,
    "resume_overlap": 30,
    "policy_chunk_size": 512,
    "policy_overlap": 100
  },
  
  "rag_config": {
    "top_k": 5,
    "similarity_threshold": 0.5,
    "max_context_tokens": 2000
  },
  
  "scoring_config": {
    "weight_must_have": 0.4,
    "weight_nice_to_have": 0.2,
    "weight_experience": 0.2,
    "weight_domain": 0.1,
    "weight_ambiguity_penalty": 0.1
  },
  
  "guardrail_config": {
    "strictness": "HIGH",
    "require_citations": true,
    "block_on_protected_attributes": true,
    "max_hallucination_score": 0.8
  },
  
  "cost_config": {
    "monthly_token_budget": 500000,
    "cost_per_1k_input_tokens": 0.003,
    "cost_per_1k_output_tokens": 0.015,
    "alert_threshold_percent": 80
  }
}
```

---

## ENTERPRISE SCALABILITY

### Scaling for 1000+ Resumes per JD

**Challenge:** Embed and retrieve context for 1000+ candidates quickly

**Solution Architecture:**

```
1. Batch Embedding Processing
   ├─ Job: Chunk all 1000 resumes (async background job)
   ├─ Pipeline: 100 documents/batch
   ├─ Embed in parallel: 4 GPU workers
   ├─ Store in ChromaDB incrementally
   └─ Time: ~2-3 minutes for 1000 documents

2. Screening Execution
   ├─ Deterministic scoring (vectorized): 
   │  ├─ NumPy operations on 1000 resume vectors
   │  ├─ Single pass through must-have/nice-to-have
   │  └─ Time: ~100ms for 1000 candidates
   │
   ├─ RAG retrieval (cached queries):
   │  ├─ ChromaDB indexed search: top-5 per candidate
   │  ├─ Parallel retrieval: 10 workers
   │  └─ Time: ~500ms for 1000 candidates
   │
   ├─ LLM explanation (top-50 only):
   │  ├─ Batch 10 explanations per request
   │  ├─ 5 parallel MCP calls
   │  └─ Time: ~5 seconds total
   │
   └─ Total end-to-end: ~6 seconds

3. Data Layer Optimization
   ├─ ChromaDB: In-memory for hot data
   ├─ PostgreSQL: Connection pooling (50 connections)
   ├─ S3: Read-only cached documents
   └─ Caching: Redis for frequent embeddings

4. Cost Control
   ├─ Token budget: $500/month = ~150M tokens
   ├─ Per screening: ~1000 tokens = $0.02
   ├─ 1000 screenings max per month
   ├─ Hard stop: Alert at 80%, block at 100%
```

---

## WHY THIS IS ENTERPRISE-GRADE

| Attribute | Why It Matters | Implementation |
|-----------|----------------|-----------------|
| **Auditability** | Compliance + transparency | Every decision logged with evidence trail |
| **Determinism** | Reproducibility + fairness | No randomness in scoring; same inputs → same outputs |
| **Explainability** | Human oversight + trust | LLM explains *why*, not *who*; cites evidence |
| **Fairness** | Legal + ethical compliance | Protected attributes stripped at ingestion |
| **RBAC** | Security + access control | Role-based API + UI rendering |
| **Configurability** | Flexibility for different teams | All model behavior configurable via UI |
| **Scalability** | Production load | Async jobs, batch processing, caching |
| **Cost Control** | Budget predictability | Token counting, cost dashboard, hard limits |
| **Separation of Concerns** | Maintainability | FastAPI ≠ Scoring ≠ LLM ≠ Agent |
| **Guardrails** | Risk mitigation | Input, prompt, output validation layers |

---

## MVP vs. PRODUCTION HARDENING

### MVP (Weeks 1-4)
**In MVP:**
- ✅ Single-tenant deployment
- ✅ Local PostgreSQL (not cloud-managed)
- ✅ Basic RBAC (4 roles)
- ✅ Deterministic scoring engine
- ✅ ChromaDB with basic retrieval
- ✅ Single MCP server instance
- ✅ Manual audit log inspection

**Simplified For MVP:**
```
- No caching layer (add Redis later)
- No distributed job queue (add Celery later)
- No Kubernetes (deploy on single VM)
- No multi-region (deploy in single region)
- No encryption at rest (add later)
- Single LLM provider (Claude only)
```

### PRODUCTION HARDENING (Weeks 5-12)

**Add These Components:**

| Hardening | MVP Limitation | Production Solution |
|-----------|-----------------|-------------------|
| **Caching** | None | Redis cluster for embeddings + results |
| **Async Jobs** | Synchronous upload | Celery + message queue for batch processing |
| **Load Balancing** | Single FastAPI instance | Nginx + 3 FastAPI instances behind LB |
| **Database** | Local PostgreSQL | Cloud-managed RDS with read replicas |
| **Storage** | Local disk | S3 with encryption + versioning |
| **Secrets** | Environment variables | AWS Secrets Manager or HashiCorp Vault |
| **Monitoring** | Logs only | Prometheus + Grafana + DataDog |
| **Disaster Recovery** | Manual backups | Automated daily backups + RTO/RPO SLAs |
| **Multi-tenancy** | Single tenant | Tenant isolation + data segregation |
| **Encryption** | None | TLS in transit + encryption at rest (AES-256) |
| **FedRAMP** | N/A | If required for government work |
| **Compliance** | Basic audit logs | SOC2 compliance + regular audits |

### Scaling Timeline
```
MVP (Week 1):
  └─ 10 concurrent users
  └─ 100 resumes/JD
  └─ Single VM (8 GB RAM)

Month 2 (Add caching):
  └─ 50 concurrent users
  └─ 5000 resumes/JD
  └─ Multi-instance + Redis

Month 3 (Add async):
  └─ 200 concurrent users
  └─ 20000 resumes/JD
  └─ Batch processing queue

Quarter 2 (Full production):
  └─ 500+ concurrent users
  └─ Multi-tenant
  └─ Multi-region
```

---

## SECURITY POSTURE

### Authentication & Authorization
```
Client → HTTPS → FastAPI
  ├─ Extract JWT from Authorization header
  ├─ Verify signature (HS256 or RS256)
  ├─ Extract claims: sub (user_id), role
  ├─ Check token expiry (TTL: 1 hour)
  ├─ Middleware enforces role for each route
  └─ Return 403 if unauthorized
```

### Data Protection
| Data Type | At Rest | In Transit | Access |
|-----------|---------|-----------|--------|
| Original Documents | Encrypted S3 | HTTPS | Admins only |
| Embeddings | ChromaDB encrypted | HTTPS | FastAPI only |
| Audit Logs | PostgreSQL encrypted | HTTPS | Auditors only |
| Config | PostgreSQL encrypted | HTTPS | Admins only |
| Candidates | Cleaned (attributes removed) | HTTPS | Authorized roles |

### Secrets Management
```
API Keys:
  - OpenAI key → Vault
  - Anthropic key → Vault
  - Database password → Vault
  - JWT secret → Vault

Rotation:
  - Every 90 days
  - Automated rotation for service accounts
  - Manual approval for privilege escalation
```

---

## KEY DECISIONS & TRADE-OFFS

### Decision 1: Deterministic Scoring vs. ML Ranking
**Decision:** Deterministic scoring (no neural networks)
**Rationale:**
- Fully auditable: Can explain every point
- Fair: No learned biases from training data
- Reproducible: Same inputs → same outputs always
**Trade-off:** Less precise than ML, but explainability > precision for hiring

### Decision 2: LLM for Explanation Only
**Decision:** LLM explains *why*, never scores or ranks
**Rationale:**
- Prevents liability: AI cannot make hiring decisions
- Human oversight: Always human review before hire
- Compliance: Meets fairness regulations
**Trade-off:** Requires LLM guardrails; more complex architecture

### Decision 3: Agent as Orchestrator, Not Decision-Maker
**Decision:** Agent coordinates tools; cannot modify scores
**Rationale:**
- Transparent workflow: Each step auditable
- Tool-constrained: Cannot invent capabilities
- Clear boundaries: Not autonomous hiring system
**Trade-off:** More API calls; slightly higher latency

### Decision 4: Protected Attribute Stripping at Ingestion
**Decision:** Remove age, gender, nationality at upload time
**Rationale:**
- Prevents lookup attacks: Even admin cannot access
- Compliance: Proactive fairness enforcement
- Simplicity: One-time cleanup, not per-query
**Trade-off:** Information loss, but acceptable for hiring

### Decision 5: ChromaDB Over Elasticsearch
**Decision:** Vector search (ChromaDB) for semantic retrieval
**Rationale:**
- Native embedding support
- Simpler than Elasticsearch setup
- Metadata filtering for candidate isolation
**Trade-off:** Less powerful full-text search; acceptable for this use case

---

## MONITORING & OBSERVABILITY

### Dashboards Required

**Admin Dashboard:**
- LLM model performance
- Token usage by user and role
- Cost tracking vs. budget
- Search latency percentiles

**Auditor Dashboard:**
- Fairness metrics: score distribution by protected attributes
- Policy violation frequency
- Guardrail trigger events
- Screening volume by team

**Operations Dashboard:**
- API response times (p50, p95, p99)
- Database connection pool usage
- ChromaDB query latency
- Error rates by endpoint

### Metrics to Track
```
- Requests per second
- Token usage per screening
- Latency: embedding vs. RAG vs. LLM
- Guardrail violations per day
- Cost per screening
- Candidate pool size per JD
- Screening duration
```

---

## DEPLOYMENT & ROLLOUT STRATEGY

### Environment Structure
```
Development:
  └─ Localhost, SQLite for demo
  
Staging:
  ├─ CloudFormation automation
  ├─ Prod-like data volume (10% scale)
  ├─ Integration tests
  ├─ Manual QA
  
Production:
  ├─ AWS (or GCP/Azure)
  ├─ RDS PostgreSQL
  ├─ S3 for storage
  ├─ CloudFront CDN (if UI heavy)
  ├─ Kubernetes (for scaling)
  ├─ Blue-green deployments
```

### Rollout Plan
```
Week 1: Deploy to 1 internal team (10 users)
Week 2: Expand to 3 teams (50 users)
Week 3: Expand to all recruiting (200 users)
Week 4: Open to hiring managers (500+ users)

Rollback strategy:
  - If >1% error rate: Rollback to previous version
  - If hallucination detected: Rollback + retrain MCP guardrails
  - If fairness regression: Rollback + audit scoring weights
```

---

## CONCLUSION

**TalentFit Assist** is designed as an enterprise-grade, deterministic, explainable screening copilot. Its architecture enforces:

1. **Responsibility:** AI assists; humans decide
2. **Auditability:** Every decision traceable
3. **Fairness:** Protected attributes removed
4. **Scalability:** Handles 1000+ resumes per JD
5. **Configurability:** All behavior tunable by admins
6. **Security:** RBAC, encryption, secrets management

The system prioritizes **transparency and human oversight** over automation autonomy—reflecting responsible AI principles suitable for consequential hiring decisions.
