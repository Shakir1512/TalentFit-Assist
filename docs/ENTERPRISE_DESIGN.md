# TalentFit Assist Enterprise Design

## 1. Architecture Diagram

```text
Streamlit multi-page UI
  - Role-aware rendering
  - Admin config, recruiter upload/run, manager review, auditor dashboards
  - "Screening Aid - Not a Hiring Decision Tool"
        |
        | HTTPS + JWT role claims
        v
FastAPI stateless API boundary
  - /auth, /config, /upload/*, /screen/*, /usage/tokens, /audit/logs
  - Server-side RBAC, validation, audit logging, budget checks
        |
        v
TalentFit Orchestration Agent
  - Fixed workflow order
  - Approved tools only
  - Auditable step trace
  - Does not score, rank, infer, or decide
        |
        +--> Deterministic Scoring Engine
        |    - Skill, experience, domain, ambiguity scoring
        |    - UI-configurable weights
        |
        +--> ChromaDB Retrieval Layer
        |    - Metadata-filtered JD/resume/policy chunks
        |    - Evidence retrieval only
        |
        +--> MCP Server
             - Prompt management, model routing, guardrails
             - Token accounting, output validation, provider abstraction
             - Explanation only, no business data persistence

Persistence in production:
  PostgreSQL: users/config/audit/results
  ChromaDB: persistent vectors and metadata
  Object storage: encrypted original documents
  Redis/queue: async screening orchestration at scale
```

## 2. FastAPI Folder Structure

```text
backend/
  main.py                    # REST API, RBAC, upload/screening endpoints
  auth/rbac.py               # roles, permissions, agent tool constraints
  agent/orchestrator.py      # TalentFit Orchestration Agent
  core/scoring_engine.py     # deterministic scoring formula
  core/data_cleaner.py       # protected attribute stripping
  core/repository.py         # local repository, chunking, evidence retrieval facade
mcp_server/
  main.py                    # MCP control plane API
  guardrails.py              # input/output guardrails and token accounting
  prompt_templates.py        # role-aware prompt templates
```

## 3. Streamlit Page Structure

```text
frontend/main.py                    # login and role capability view
frontend/pages/1_Admin_Config.py    # model, chunking, scoring, budget controls
frontend/pages/2_Uploads.py         # JD, resume, fairness policy ingestion
frontend/pages/3_Screening.py       # recruiter screening workflow
frontend/pages/4_Review.py          # hiring manager evidence review
frontend/pages/5_Audit_Usage.py     # auditor/admin logs and token dashboard
```

## 4. RBAC Strategy

JWT role claims are read by FastAPI dependencies and converted to a `User`.
Every endpoint checks a concrete permission before doing work. The Streamlit UI
uses capability flags for rendering, but backend checks are authoritative.

Roles:
- Admin: configuration, policy upload, user/config/cost governance.
- Recruiter: upload JD/resume, run screening, view results.
- Hiring Manager: view evidence, gaps, interview focus only.
- Auditor: read-only audit and token usage.

## 5. LLM Prompt Template

The MCP prompt contract says the model is an explanation service only. It
forbids hiring decisions, ranking language, inferred skills, protected attribute
mentions, and uncited claims. Output must be structured JSON with summary,
evidence cards, gaps, interview focus, and guardrail status.

## 6. Deterministic Scoring Formula

```text
final_score =
  (must_have_match * w_must_have
 + nice_to_have_match * w_nice_to_have
 + experience_match * w_experience
 + domain_relevance * w_domain
 - ambiguity_penalty * w_ambiguity_penalty) / 100
```

Weights must sum to `1.0`. The LLM never contributes to this score.

## 7. Guardrail Points

Input ingestion strips protected attributes before chunking. FastAPI blocks
unauthorized actions and token-budget breaches. The agent enforces tool order
and tool allowlists. The MCP server enforces prompt injection checks,
temperature/max-token limits, citation requirements, protected-attribute scans,
hallucination indicators, and hiring-decision language checks. Violations block
output and create audit records.

## 8. Scaling to 1000+ Resumes

Production screening should run asynchronously: upload and embedding jobs go to
a queue, ChromaDB stores persistent vectors, retrieval is batched by JD and
candidate metadata filters, deterministic scoring is parallelized across
workers, and LLM explanation calls are limited to top evidence cards or
human-selected candidates. Results and traces are stored in PostgreSQL with
pagination in the UI.

## 9. Enterprise-Grade Properties

The system separates business logic, orchestration, retrieval, and LLM control.
Scoring is reproducible, explanations are evidence-bound, protected attributes
are stripped at ingestion, RBAC is server-side, audit trails include every agent
tool invocation, and token budgets have hard-stop enforcement.

## 10. MVP vs Hardening Roadmap

MVP in this repository:
- In-memory local repository for documents, config, results, audit, and usage.
- Deterministic local retrieval facade with Chroma-compatible metadata.
- MCP server with local deterministic explanation generation.
- Demo JWT parsing for role-based workflows.

Production hardening:
- Replace demo JWT parsing with IdP-backed RS256 verification.
- Replace in-memory storage with PostgreSQL, encrypted object storage, and
  persistent ChromaDB collections.
- Route MCP calls to Claude/OpenAI/Azure with provider-specific token accounting.
- Add async workers, rate limits, tenant isolation, immutable audit storage,
  automated fairness reports, and CI load tests for 1000+ resume runs.
