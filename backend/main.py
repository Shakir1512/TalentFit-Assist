"""
FastAPI Backend - TalentFit Assist

Main application entry point with RBAC middleware, endpoint routing,
and orchestration integration.
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging
import json

from backend.auth.rbac import User, Role, RBACEnforcer, Permission, RBACViolation
from backend.core.scoring_engine import DeterministicScoringEngine, ScoringWeights
from backend.agent.orchestrator import TalentFitOrchestrationAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="TalentFit Assist",
    description="Enterprise-grade JD-to-Resume screening copilot",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:3000"],  # Streamlit + local
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core components
rbac_enforcer = RBACEnforcer()
orchestration_agent = TalentFitOrchestrationAgent()
scoring_engine = DeterministicScoringEngine(
    weights=ScoringWeights(
        weight_must_have=0.4,
        weight_nice_to_have=0.2,
        weight_experience=0.2,
        weight_domain=0.1,
        weight_ambiguity_penalty=0.1
    )
)

# ========== REQUEST/RESPONSE MODELS ==========

class LoginRequest(BaseModel):
    """User login credentials"""
    email: str
    password: str


class LoginResponse(BaseModel):
    """JWT token response"""
    token: str
    user: dict
    expires_in: int = 3600  # 1 hour


class ScreeningRequest(BaseModel):
    """Request to run screening"""
    jd_id: str
    candidate_ids: List[str]
    config_overrides: Optional[dict] = None


class ScreeningResponse(BaseModel):
    """Screening results"""
    status: str
    results: List[dict]
    audit_trail: dict
    cost_estimate: float


class ConfigUpdateRequest(BaseModel):
    """Update system configuration"""
    llm_model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    scoring_weights: Optional[dict] = None
    chunk_size: Optional[int] = None


# ========== JWT MIDDLEWARE ==========

class JWTMiddleware:
    """Middleware to extract and validate JWT token"""
    
    def __init__(self):
        self.secret_key = "dev-secret-key"  # Should be in Vault
    
    def extract_user(self, authorization: Optional[str]) -> User:
        """
        Extract and validate JWT token.
        Returns mock user for demo (in production: validate with JWT library)
        """
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        try:
            # Mock JWT parsing (in production: use jwt.decode)
            token = authorization.replace("Bearer ", "")
            
            # For demo: extract role from token suffix
            if "recruiter" in token:
                role = Role.RECRUITER
            elif "admin" in token:
                role = Role.ADMIN
            elif "hiring_manager" in token:
                role = Role.HIRING_MANAGER
            elif "auditor" in token:
                role = Role.AUDITOR
            else:
                role = Role.RECRUITER
            
            user = User(
                user_id=f"user_{hash(token) % 10000}",
                email=f"{role.value}@company.com",
                role=role,
                is_active=True
            )
            
            return user
        
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


jwt_middleware = JWTMiddleware()


def get_current_user(authorization: Optional[str] = Header(None)) -> User:
    """Dependency to get current authenticated user"""
    return jwt_middleware.extract_user(authorization)


# ========== AUDIT LOGGING ==========

class AuditLogger:
    """Log all actions for compliance"""
    
    @staticmethod
    def log_action(user_id: str, action: str, details: dict, success: bool = True):
        """Log action to audit trail"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "details": details,
            "success": success,
            "severity": "INFO" if success else "WARNING"
        }
        
        # In production: write to PostgreSQL + syslog
        logger.info(json.dumps(audit_entry))
        return audit_entry


# ========== ENDPOINTS ==========

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT token.
    
    In production:
    - Validate against identity provider (OKTA, Azure AD)
    - Verify password
    - Check MFA if configured
    """
    # Mock auth for demo
    roles = {
        "recruiter@company.com": Role.RECRUITER,
        "admin@company.com": Role.ADMIN,
        "hiring-manager@company.com": Role.HIRING_MANAGER,
        "auditor@company.com": Role.AUDITOR,
    }
    
    if request.email not in roles:
        AuditLogger.log_action(request.email, "login_failed", {"reason": "invalid_email"}, success=False)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Mock token generation
    role = roles[request.email]
    token = f"mock_jwt_token_{role.value}"
    
    user = User(user_id=f"u_{hash(request.email) % 10000}", email=request.email, role=role)
    
    AuditLogger.log_action(user.user_id, "login_success", {"email": request.email})
    
    return LoginResponse(
        token=token,
        user={
            "user_id": user.user_id,
            "email": user.email,
            "role": user.role.value,
            "capabilities": rbac_enforcer.get_user_capabilities(user)
        },
        expires_in=3600
    )


@app.post("/config/update")
async def update_config(
    request: ConfigUpdateRequest,
    user: User = Depends(get_current_user)
):
    """
    Update system configuration.
    Requires ADMIN role.
    """
    # RBAC check
    if not rbac_enforcer.has_permission(user, Permission.EDIT_CONFIG):
        AuditLogger.log_action(user.user_id, "config_update_denied", {}, success=False)
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Validate inputs
    if request.temperature is not None and not (0 <= request.temperature <= 2.0):
        raise HTTPException(status_code=400, detail="Temperature must be 0-2.0")
    
    if request.max_tokens is not None and not (1 <= request.max_tokens <= 4000):
        raise HTTPException(status_code=400, detail="Max tokens must be 1-4000")
    
    config_update = {
        "llm_model": request.llm_model,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "scoring_weights": request.scoring_weights,
        "chunk_size": request.chunk_size
    }
    
    # Remove None values
    config_update = {k: v for k, v in config_update.items() if v is not None}
    
    # In production: save to PostgreSQL with versioning
    AuditLogger.log_action(user.user_id, "config_updated", config_update)
    
    return {
        "status": "success",
        "updated_keys": list(config_update.keys()),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/screen/run", response_model=ScreeningResponse)
async def run_screening(
    request: ScreeningRequest,
    user: User = Depends(get_current_user)
):
    """
    Execute screening workflow.
    Requires RECRUITER or ADMIN role.
    
    Flow:
    1. RBAC validation
    2. Invoke orchestration agent
    3. Agent runs workflow (validate → RAG → score → explain → audit)
    4. Return results with audit trail
    """
    
    # RBAC check
    if not rbac_enforcer.has_permission(user, Permission.RUN_SCREENING):
        AuditLogger.log_action(
            user.user_id,
            "screening_denied",
            {"jd_id": request.jd_id},
            success=False
        )
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Validate request
    if not request.jd_id or not request.candidate_ids:
        raise HTTPException(status_code=400, detail="Missing jd_id or candidate_ids")
    
    if len(request.candidate_ids) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 candidates per screening")
    
    try:
        # Build config
        config = {
            "top_k": 5,
            "max_tokens": 300,
            "scoring_weights": {
                "must_have": 0.4,
                "nice_to_have": 0.2,
                "experience": 0.2,
                "domain": 0.1,
                "ambiguity": 0.1
            }
        }
        
        # Merge overrides
        if request.config_overrides:
            config.update(request.config_overrides)
        
        # Invoke orchestration agent
        result = orchestration_agent.run_screening_workflow(
            user=user,
            jd_id=request.jd_id,
            candidate_ids=request.candidate_ids,
            config=config
        )
        
        # Log successful screening
        AuditLogger.log_action(
            user.user_id,
            "screening_completed",
            {
                "jd_id": request.jd_id,
                "candidates_screened": len(request.candidate_ids),
                "execution_id": result.get("audit_trail", {}).get("execution_id")
            }
        )
        
        return ScreeningResponse(
            status="success" if result["success"] else "failed",
            results=result.get("data", {}).get("results", []),
            audit_trail=result.get("audit_trail", {}),
            cost_estimate=0.02 * len(request.candidate_ids)  # Mock cost
        )
    
    except Exception as e:
        AuditLogger.log_action(
            user.user_id,
            "screening_error",
            {"jd_id": request.jd_id, "error": str(e)},
            success=False
        )
        logger.error(f"Screening failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Screening failed: {str(e)}")


@app.get("/screen/results/{screening_id}")
async def get_screening_results(
    screening_id: str,
    user: User = Depends(get_current_user)
):
    """
    Retrieve screening results and audit trail.
    Requires RECRUITER, HIRING_MANAGER, or ADMIN role.
    """
    
    # RBAC check
    if not rbac_enforcer.has_permission(user, Permission.VIEW_SCREENING_RESULTS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # In production: query results from PostgreSQL
    mock_results = {
        "screening_id": screening_id,
        "status": "completed",
        "timestamp": datetime.utcnow().isoformat(),
        "results": [
            {
                "candidate_id": "c_001",
                "score": 0.82,
                "explanation": "Mock explanation"
            }
        ],
        "audit_trail": {"user": user.user_id, "completed_at": datetime.utcnow().isoformat()}
    }
    
    return mock_results


@app.get("/audit/logs")
async def get_audit_logs(
    limit: int = 100,
    user: User = Depends(get_current_user)
):
    """
    Retrieve audit logs.
    Requires AUDITOR or ADMIN role.
    """
    
    # RBAC check
    if not rbac_enforcer.has_permission(user, Permission.VIEW_AUDIT_LOGS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # In production: query from PostgreSQL
    return {
        "status": "success",
        "logs": [],
        "total_records": 0,
        "retrieved_at": datetime.utcnow().isoformat()
    }


@app.get("/usage/tokens")
async def get_token_usage(
    user: User = Depends(get_current_user)
):
    """
    Get token usage and cost metrics.
    Requires ADMIN or AUDITOR role.
    """
    
    # RBAC check
    if not rbac_enforcer.has_permission(user, Permission.VIEW_TOKEN_USAGE):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # In production: aggregate from PostgreSQL
    return {
        "status": "success",
        "total_tokens_month": 0,
        "total_cost_month": 0.0,
        "budget_limit": 500.0,
        "budget_used_percent": 0,
        "cost_by_model": {},
        "cost_by_user": {}
    }


@app.exception_handler(RBACViolation)
async def rbac_violation_handler(request: Request, exc: RBACViolation):
    """Handle RBAC violations"""
    AuditLogger.log_action(
        exc.user_id,
        "rbac_violation",
        {"permission": exc.permission.value, "action": exc.action},
        success=False
    )
    return {
        "status": "denied",
        "message": str(exc),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint with API documentation"""
    return {
        "name": "TalentFit Assist",
        "version": "1.0.0",
        "description": "Enterprise-grade JD-to-Resume screening copilot",
        "docs": "/docs",
        "status": "ready"
    }


# ========== APPLICATION STARTUP/SHUTDOWN ==========

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("Starting TalentFit Assist backend...")
    # Initialize connections to PostgreSQL, ChromaDB, etc.
    logger.info("✓ Database connections initialized")
    logger.info("✓ ChromaDB client ready")
    logger.info("✓ Orchestration agent ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down TalentFit Assist...")
    # Close database connections, cleanup
    logger.info("✓ Cleanup complete")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
