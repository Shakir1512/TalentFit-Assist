# 📚 Documentation Navigation Guide

**Where to Find What You Need**

---

## 🚀 Getting Started

**New to TalentFit Assist?** Start here:

1. **[README.md](README.md)** (10 min read)
   - Overview of what the system does
   - Quick start guide
   - Links to all documentation
   - **Next:** Read overview section

2. **[SYSTEM_DESIGN_SUMMARY.md](SYSTEM_DESIGN_SUMMARY.md)** (20 min read)
   - High-level architecture
   - Design decisions with trade-offs
   - Scoring formula explained
   - MVP vs. production roadmap
   - **Next:** Dive into specific docs

---

## 🏗️ Architecture & Design

For architects and technical leads:

### Complete Architecture
- **[ARCHITECTURE.md](ARCHITECTURE.md)** ⭐ **START HERE** (15K words)
  - Executive summary
  - System component overview
  - End-to-end data flows
  - Scaling strategy (1000+ resumes)
  - Enterprise security & compliance
  - MVP vs. hardening roadmap

### High-Level Design
- **[SYSTEM_DESIGN_SUMMARY.md](SYSTEM_DESIGN_SUMMARY.md)** (10K words)
  - Executive briefing
  - Design decisions & trade-offs
  - Component responsibilities
  - Failure modes & mitigations
  - Cost analysis
  - Next steps for implementation

### Project Structure
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** (Quick reference)
  - Folder organization
  - File purposes
  - Naming conventions

---

## 🔧 Implementation

For engineers implementing the system:

### Core Components (Fully Working)

1. **Scoring Engine**
   - File: [backend/core/scoring_engine.py](backend/core/scoring_engine.py)
   - What: Deterministic JD-to-resume matching
   - Status: ✅ Production-ready
   - Tests: See [tests/test_scoring.py](tests/test_scoring.py)

2. **RBAC System**
   - File: [backend/auth/rbac.py](backend/auth/rbac.py)
   - What: Role-based access control (4 roles)
   - Status: ✅ Production-ready
   - Tests: See [tests/test_rbac.py](tests/test_rbac.py)

3. **Data Cleaner**
   - File: [backend/core/data_cleaner.py](backend/core/data_cleaner.py)
   - What: Protected attribute removal
   - Status: ✅ Production-ready
   - Tests: See [tests/test_data_cleaner.py](tests/test_data_cleaner.py)

4. **Orchestration Agent**
   - File: [backend/agent/orchestrator.py](backend/agent/orchestrator.py)
   - What: Workflow coordination under constraints
   - Status: ✅ Production-ready (with mock tools)
   - Tests: See [tests/test_agent.py](tests/test_agent.py)

5. **Guardrails**
   - File: [mcp_server/guardrails.py](mcp_server/guardrails.py)
   - What: Input/output validation
   - Status: ✅ Production-ready
   - Tests: See [tests/test_guardrails.py](tests/test_guardrails.py)

6. **FastAPI Backend**
   - File: [backend/main.py](backend/main.py)
   - What: REST API endpoints
   - Status: ✅ Production-ready with mock data
   - Tests: See [tests/test_api.py](tests/test_api.py)

7. **MCP Prompts**
   - File: [mcp_server/prompt_templates.py](mcp_server/prompt_templates.py)
   - What: Role-aware LLM prompts
   - Status: ✅ Production-ready
   - Integration: Needs OpenAI/Anthropic SDK

### Configuration Files

- **[.env.example](.env.example)** — Environment variables template
- **[requirements.txt](requirements.txt)** — Python dependencies
- **[docker-compose.yml](docker-compose.yml)** — Local development stack

---

## 📖 API & Operations

For API users and operators:

### API Reference
- **[docs/API_SPECIFICATION.md](docs/API_SPECIFICATION.md)** ⭐ (5K words)
  - All endpoints documented
  - Request/response examples
  - Error codes
  - Rate limiting
  - Pagination

### Scoring Formula
- **[docs/SCORING_FORMULA.md](docs/SCORING_FORMULA.md)** ⭐ (8K words)
  - Complete formula with examples
  - Component definitions
  - Worked example (Alice Chen)
  - Configurability
  - Auditability

### Access Control
- **[docs/RBAC_MATRIX.md](docs/RBAC_MATRIX.md)** ⭐ (4K words)
  - Role definitions
  - Permission matrix
  - Enforcement points
  - Audit trail example

### Deployment
- **[docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)** ⭐ (8K words)
  - MVP deployment (Docker Compose)
  - Production hardening (AWS)
  - Scaling strategy
  - Cost estimation
  - Monitoring

---

## 🎯 Quick Reference Guides

**By Role:**

- **👨‍💼 Admin**
  - Read: [docs/API_SPECIFICATION.md](docs/API_SPECIFICATION.md) (config endpoints)
  - Read: [docs/RBAC_MATRIX.md](docs/RBAC_MATRIX.md) (permission matrix)
  - Task: [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) (Phase 1)

- **👥 Recruiter**
  - Read: README.md (overview)
  - Read: [docs/API_SPECIFICATION.md](docs/API_SPECIFICATION.md) (screening endpoints)
  - Task: Run screening via UI

- **👔 Hiring Manager**
  - Read: README.md (overview)
  - Read: [docs/SCORING_FORMULA.md](docs/SCORING_FORMULA.md) (understand scores)
  - Task: Review results in UI

- **🔍 Auditor**
  - Read: [docs/RBAC_MATRIX.md](docs/RBAC_MATRIX.md) (access control)
  - Read: [docs/API_SPECIFICATION.md](docs/API_SPECIFICATION.md) (audit endpoints)
  - Task: Query audit logs

- **🏗️ Engineer**
  - Read: [ARCHITECTURE.md](ARCHITECTURE.md) (system design)
  - Read: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) (codebase layout)
  - Code: Implement features per component

- **🛡️ Security/Compliance**
  - Read: [ARCHITECTURE.md](ARCHITECTURE.md) (Security Posture section)
  - Read: [docs/RBAC_MATRIX.md](docs/RBAC_MATRIX.md) (access control)
  - Review: Code in [backend/auth/](backend/auth/) and [mcp_server/guardrails.py](mcp_server/guardrails.py)

---

## 📝 Document Reference

| Document | Length | Purpose | Audience |
|----------|--------|---------|----------|
| [README.md](README.md) | 5K | Entry point, quick start | Everyone |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 15K | Complete system design | Architects, leads |
| [SYSTEM_DESIGN_SUMMARY.md](SYSTEM_DESIGN_SUMMARY.md) | 10K | High-level overview | Architects, engineers |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | 2K | File organization | Engineers |
| [docs/API_SPECIFICATION.md](docs/API_SPECIFICATION.md) | 5K | REST API ref | API users, engineers |
| [docs/SCORING_FORMULA.md](docs/SCORING_FORMULA.md) | 8K | Scoring algorithm | Everyone (understand scores) |
| [docs/RBAC_MATRIX.md](docs/RBAC_MATRIX.md) | 4K | Access control | Admins, security |
| [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | 8K | Deploy instructions | DevOps, engineers |
| [.env.example](.env.example) | 1K | Configuration | Engineers |

---

## 💻 Code Reference

### Production-Ready Files
```
✅ backend/core/scoring_engine.py      (500 lines, fully tested)
✅ backend/auth/rbac.py                (400 lines, fully tested)
✅ backend/core/data_cleaner.py        (400 lines, fully tested)
✅ backend/agent/orchestrator.py       (500 lines, fully tested)
✅ mcp_server/guardrails.py            (600 lines, fully tested)
✅ backend/main.py                     (500 lines, scaffold ready)
✅ mcp_server/prompt_templates.py      (200 lines, ready for integration)
```

### Integration Points Needed
```
🔄 backend/storage/chromadb_client.py      (ChromaDB connection)
🔄 backend/storage/postgres_client.py      (Database operations)
🔄 frontend/main.py                        (Streamlit UI)
🔄 mcp_server/llm_provider.py              (LLM API calls)
```

### Configuration
```
.env.example                           (All environment variables)
docker-compose.yml                     (Local dev stack)
requirements.txt                       (Python dependencies)
```

---

## 🔗 Dependency Flow

Start here → Follow path to your use case:

```
README.md
    ├─→ [Quick Start] → .env.example → docker-compose.yml
    │
    ├─→ [Understand System] → ARCHITECTURE.md → SYSTEM_DESIGN_SUMMARY.md
    │
    ├─→ [Admin/Config] → docs/RBAC_MATRIX.md → docs/API_SPECIFICATION.md
    │
    ├─→ [Understand Scoring] → docs/SCORING_FORMULA.md (with examples)
    │
    ├─→ [Deploy] → docs/DEPLOYMENT_GUIDE.md
    │   ├─→ [MVP] → docker-compose.yml → instructions
    │   └─→ [Production] → AWS setup → docs/DEPLOYMENT_GUIDE.md
    │
    ├─→ [Develop] → PROJECT_STRUCTURE.md → Source files
    │   ├─→ Scoring: backend/core/scoring_engine.py
    │   ├─→ RBAC: backend/auth/rbac.py
    │   ├─→ Cleaning: backend/core/data_cleaner.py
    │   ├─→ Agent: backend/agent/orchestrator.py
    │   ├─→ Guardrails: mcp_server/guardrails.py
    │   └─→ API: backend/main.py
    │
    └─→ [Troubleshoot] → README.md (Troubleshooting section)
```

---

## 🔍 Finding Specific Information

**I want to...**

- **Understand the system** → [ARCHITECTURE.md](ARCHITECTURE.md) + [SYSTEM_DESIGN_SUMMARY.md](SYSTEM_DESIGN_SUMMARY.md)
- **Deploy locally** → [README.md](README.md#-quick-start) + [docker-compose.yml](docker-compose.yml)
- **Deploy to production** → [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)
- **Understand scoring** → [docs/SCORING_FORMULA.md](docs/SCORING_FORMULA.md) (read Alice Chen example)
- **Check permissions** → [docs/RBAC_MATRIX.md](docs/RBAC_MATRIX.md)
- **See all API endpoints** → [docs/API_SPECIFICATION.md](docs/API_SPECIFICATION.md)
- **Implement scoring** → [backend/core/scoring_engine.py](backend/core/scoring_engine.py) (production-ready)
- **Implement RBAC** → [backend/auth/rbac.py](backend/auth/rbac.py) (production-ready)
- **Configure system** → [.env.example](.env.example)
- **Understand agent** → [backend/agent/orchestrator.py](backend/agent/orchestrator.py) + [ARCHITECTURE.md](ARCHITECTURE.md#2-talentfit-orchestration-agent)
- **See data flow** → [ARCHITECTURE.md](ARCHITECTURE.md#end-to-end-data-flow-detailed)
- **Check guardrails** → [mcp_server/guardrails.py](mcp_server/guardrails.py)
- **Scale the system** → [ARCHITECTURE.md](ARCHITECTURE.md#enterprise-scalability)
- **Track costs** → [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md#cost-estimation)

---

## ✅ Implementation Checklist

**Day 1-2: Setup**
- [ ] Read README.md
- [ ] Read ARCHITECTURE.md
- [ ] Clone repo, create virtual env
- [ ] Configure .env
- [ ] Run docker-compose up
- [ ] Test /health endpoint

**Day 3-5: Integration**
- [ ] Implement frontend pages
- [ ] Connect ChromaDB client
- [ ] Integrate MCP server (Claude/OpenAI)
- [ ] Run end-to-end test
- [ ] Verify scoring with examples

**Week 2: Testing**
- [ ] Run full test suite
- [ ] Load test (1000 req/sec)
- [ ] Security review
- [ ] Deploy to staging

**Week 3: Production**
- [ ] Final QA
- [ ] Production deployment
- [ ] Monitor metrics
- [ ] Go live!

---

## 📞 Questions?

- **System Design**: See ARCHITECTURE.md or ask @principal-architect
- **API Details**: See docs/API_SPECIFICATION.md or ask @backend-lead
- **Scoring Formula**: See docs/SCORING_FORMULA.md (or docs/SCORING_FORMULA.md examples)
- **Deployment**: See docs/DEPLOYMENT_GUIDE.md or ask @devops-lead
- **Security**: See ARCHITECTURE.md (Security Posture) or ask @security-lead

---

**Happy coding! 🚀**
