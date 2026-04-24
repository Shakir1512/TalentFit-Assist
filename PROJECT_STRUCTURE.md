PROJECT_ROOT/
├── README.md
├── ARCHITECTURE.md                    # Enterprise architecture design (created)
├── requirements.txt                   # Python dependencies
├── .env.example                      # Environment variables template
├── docker-compose.yml                # Local development stack
│
├── backend/                          # FastAPI Backend
│   ├── __init__.py
│   ├── main.py                       # FastAPI app entry point
│   ├── config.py                     # Configuration loader
│   ├── dependencies.py               # Shared dependencies
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt_handler.py           # JWT token validation
│   │   ├── rbac.py                  # Role-based access control
│   │   └── models.py                # User & role models
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth_middleware.py       # JWT extraction + validation
│   │   ├── audit_middleware.py      # Request/response logging
│   │   └── error_handler.py         # Centralized error handling
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py                  # POST /auth endpoints
│   │   ├── config.py                # GET/POST /config endpoints
│   │   ├── upload.py                # POST /upload/* endpoints
│   │   ├── screening.py             # POST /screen/run endpoints
│   │   ├── results.py               # GET /screen/results endpoints
│   │   ├── usage.py                 # GET /usage/tokens endpoints
│   │   └── audit.py                 # GET /audit/logs endpoints
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── scoring_engine.py        # Deterministic scoring logic
│   │   ├── data_cleaner.py          # Protected attribute stripping
│   │   ├── document_chunker.py      # Token-aware chunking
│   │   └── embedding_handler.py     # Embedding computation
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── orchestrator.py          # TalentFit Orchestration Agent
│   │   ├── tools.py                 # Agent tools (constrained set)
│   │   └── tools_spec.py            # Tool definitions & constraints
│   │
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── client.py                # MCP server communication
│   │   ├── guardrails.py            # Input/output validation
│   │   └── prompt_templates.py      # Role-aware prompts
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── chromadb_client.py       # ChromaDB operations
│   │   ├── postgres_client.py       # PostgreSQL operations
│   │   ├── s3_client.py             # S3 document storage
│   │   └── models.py                # SQLAlchemy ORM models
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── document_service.py      # Upload + chunking orchestration
│   │   ├── screening_service.py     # Screening workflow orchestration
│   │   └── audit_service.py         # Audit logging
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                # Structured logging
│       ├── token_counter.py         # Token counting for cost
│       └── validators.py            # Input validation helpers
│
├── mcp_server/                       # MCP Server (separate process)
│   ├── __init__.py
│   ├── main.py                      # MCP server entry point
│   ├── models.py                    # Request/response models
│   ├── guardrails.py                # Guardrail enforcement
│   ├── prompt_manager.py            # Prompt selection + templates
│   ├── llm_provider.py              # LLM abstraction (Claude/OpenAI/Azure)
│   ├── output_validator.py          # Citation + hallucination check
│   └── config.py                    # MCP configuration
│
├── frontend/                        # Streamlit Frontend
│   ├── __init__.py
│   ├── main.py                      # Streamlit app entry
│   │
│   ├── pages/
│   │   ├── 1_Login.py              # Authentication page
│   │   ├── 2_Dashboard.py          # Role-based dashboard
│   │   ├── 3_Upload_Documents.py   # Doc upload (Recruiter/Admin)
│   │   ├── 4_Configuration.py      # Model config (Admin)
│   │   ├── 5_Run_Screening.py      # Screening runner (Recruiter)
│   │   ├── 6_Review_Results.py     # Results viewer (Recruiter/Hiring Manager)
│   │   ├── 7_Audit_Dashboard.py    # Audit logs (Auditor)
│   │   ├── 8_Cost_Dashboard.py     # Token/cost tracking (Admin)
│   │   └── 9_Help.py               # Documentation
│   │
│   ├── components/
│   │   ├── __init__.py
│   │   ├── auth_component.py       # Login form
│   │   ├── nav_component.py        # Role-based navigation
│   │   ├── candidate_card.py       # Candidate result card
│   │   ├── evidence_viewer.py      # Evidence/citation viewer
│   │   ├── config_form.py          # Configuration UI
│   │   └── cost_display.py         # Token cost display
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── api_client.py           # FastAPI client
│   │   ├── auth_handler.py         # Token storage
│   │   └── formatters.py           # Display formatting
│   │
│   └── assets/
│       ├── logo.png
│       ├── styles.css              # Custom Streamlit styling
│       └── config.toml             # Streamlit config
│
├── tests/
│   ├── conftest.py                 # Pytest fixtures
│   ├── test_auth.py                # JWT validation tests
│   ├── test_scoring.py             # Scoring engine tests
│   ├── test_chunking.py            # Document chunking tests
│   ├── test_rbac.py                # RBAC enforcement tests
│   ├── test_guardrails.py          # Guardrail validation tests
│   ├── test_api.py                 # API endpoint tests
│   └── test_agent.py               # Orchestrator tests
│
├── scripts/
│   ├── init_db.py                  # Initialize PostgreSQL
│   ├── create_admin_user.py        # Create first admin
│   ├── seed_test_data.py           # Load test JDs/resumes
│   └── migrate_data.py             # Data migration helpers
│
├── docs/
│   ├── API_SPECIFICATION.md        # OpenAPI specs
│   ├── MCP_SPECIFICATION.md        # MCP protocol specs
│   ├── SCORING_FORMULA.md          # Scoring algorithm
│   ├── RBAC_MATRIX.md              # Permission matrix
│   ├── DEPLOYMENT_GUIDE.md         # Deployment instructions
│   └── EXAMPLES.md                 # Usage examples
│
└── docker/
    ├── Dockerfile.backend          # FastAPI container
    ├── Dockerfile.mcp              # MCP server container
    ├── Dockerfile.frontend         # Streamlit container
    └── entrypoint.sh               # Container startup
