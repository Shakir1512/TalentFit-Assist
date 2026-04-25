"""
FastAPI backend for TalentFit Assist.

The backend is the policy-enforcing API boundary. It validates JWT role claims,
owns business data access, invokes the constrained orchestration agent, and
prevents UI-only enforcement mistakes.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.agent.orchestrator import TalentFitOrchestrationAgent
from backend.auth.rbac import Permission, RBACEnforcer, RBACViolation, Role, User
from backend.core.repository import InMemoryTalentRepository


app = FastAPI(
    title="TalentFit Assist",
    description="Enterprise-ready JD-to-resume screening copilot",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

repository = InMemoryTalentRepository()
rbac = RBACEnforcer()
orchestration_agent = TalentFitOrchestrationAgent(repository)


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: Dict[str, Any]
    expires_in: int = 3600


class ConfigUpdateRequest(BaseModel):
    llm_model: Optional[str] = None
    provider: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=64, le=4000)
    embedding_model: Optional[str] = None
    top_k: Optional[int] = Field(default=None, ge=1, le=50)
    chunk_size: Optional[int] = Field(default=None, ge=128, le=4000)
    chunk_overlap: Optional[int] = Field(default=None, ge=0, le=1000)
    scoring_weights: Optional[Dict[str, float]] = None
    guardrail_strictness: Optional[str] = None
    monthly_token_budget: Optional[int] = Field(default=None, ge=1)


class DocumentUploadRequest(BaseModel):
    documents: List[Dict[str, Any]]


class PolicyUploadRequest(BaseModel):
    policy_id: str = "policy_default"
    content: str


class ScreeningRequest(BaseModel):
    jd_id: str
    candidate_ids: List[str]
    config_overrides: Optional[Dict[str, Any]] = None


class ScreeningResponse(BaseModel):
    status: str
    screening_id: Optional[str] = None
    results: List[Dict[str, Any]] = []
    audit_trail: Dict[str, Any]
    token_usage: Dict[str, Any] = {}
    cost_estimate: float = 0.0


class JWTMiddleware:
    """
    Local JWT-like parser for development.

    Production hardening:
    - Validate RS256 JWTs against enterprise IdP JWKS
    - Enforce exp/iat/aud/iss
    - Use tenant and data-access claims
    """

    def extract_user(self, authorization: Optional[str]) -> User:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        token = authorization.removeprefix("Bearer ").strip()
        role = Role.RECRUITER
        if "admin" in token:
            role = Role.ADMIN
        elif "hiring_manager" in token or "hiring-manager" in token:
            role = Role.HIRING_MANAGER
        elif "auditor" in token:
            role = Role.AUDITOR
        elif "recruiter" in token:
            role = Role.RECRUITER
        return User(user_id=f"user_{role.value}", email=f"{role.value}@company.com", role=role)


jwt_middleware = JWTMiddleware()


def current_user(authorization: Optional[str] = Header(None)) -> User:
    return jwt_middleware.extract_user(authorization)


def require(user: User, permission: Permission) -> None:
    if not rbac.has_permission(user, permission):
        audit = repository.log_audit(
            user.user_id,
            "rbac_denied",
            {"permission": permission.value, "role": user.role.value},
            success=False,
        )
        raise HTTPException(
            status_code=403,
            detail={"message": "Insufficient permissions", "audit_id": audit["audit_id"]},
        )


def _public_config() -> Dict[str, Any]:
    return json.loads(json.dumps(repository.config))


@app.get("/")
async def root() -> Dict[str, str]:
    return {
        "name": "TalentFit Assist",
        "status": "ready",
        "label": "Screening Aid - Not a Hiring Decision Tool",
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    roles = {
        "admin@company.com": Role.ADMIN,
        "recruiter@company.com": Role.RECRUITER,
        "hiring-manager@company.com": Role.HIRING_MANAGER,
        "auditor@company.com": Role.AUDITOR,
    }
    role = roles.get(request.email)
    if not role:
        repository.log_audit(request.email, "login_failed", {"reason": "unknown_email"}, success=False)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user = User(user_id=f"user_{role.value}", email=request.email, role=role)
    repository.log_audit(user.user_id, "login_success", {"email": request.email})
    return LoginResponse(
        token=f"mock_jwt_token_{role.value}",
        user={
            "user_id": user.user_id,
            "email": user.email,
            "role": user.role.value,
            "capabilities": rbac.get_user_capabilities(user),
        },
    )


@app.get("/config")
async def get_config(user: User = Depends(current_user)) -> Dict[str, Any]:
    require(user, Permission.VIEW_CONFIG)
    return {"status": "success", "config": _public_config()}


@app.post("/config/update")
async def update_config(request: ConfigUpdateRequest, user: User = Depends(current_user)) -> Dict[str, Any]:
    require(user, Permission.EDIT_CONFIG)
    patch = request.model_dump(exclude_none=True)
    weights = patch.get("scoring_weights")
    if weights is not None and not 0.99 <= sum(float(v) for v in weights.values()) <= 1.01:
        raise HTTPException(status_code=400, detail="Scoring weights must sum to 1.0")
    config = repository.update_config(patch)
    repository.log_audit(user.user_id, "config_updated", {"updated_keys": list(patch.keys())})
    return {"status": "success", "updated_keys": list(patch.keys()), "config": config}


@app.post("/upload/jd")
async def upload_jd(
    request: DocumentUploadRequest,
    user: User = Depends(current_user),
) -> Dict[str, Any]:
    require(user, Permission.UPLOAD_DOCUMENTS)
    processed = repository.ingest_records("jd", request.documents)
    repository.log_audit(user.user_id, "jd_uploaded", {"count": len(processed)})
    return {"status": "success", "uploaded": len(processed), "processed": processed}


@app.post("/upload/resume")
async def upload_resume(
    request: DocumentUploadRequest,
    user: User = Depends(current_user),
) -> Dict[str, Any]:
    require(user, Permission.UPLOAD_DOCUMENTS)
    processed = repository.ingest_records("resume", request.documents)
    repository.log_audit(user.user_id, "resume_uploaded", {"count": len(processed)})
    return {"status": "success", "uploaded": len(processed), "processed": processed}


@app.post("/upload/policy")
async def upload_policy(request: PolicyUploadRequest, user: User = Depends(current_user)) -> Dict[str, Any]:
    require(user, Permission.EDIT_CONFIG)
    processed = repository.ingest_policy_markdown(request.content, request.policy_id)
    repository.log_audit(user.user_id, "policy_uploaded", {"policy_id": request.policy_id})
    return {"status": "success", "processed": processed}


@app.post("/screen/run", response_model=ScreeningResponse)
async def run_screening(request: ScreeningRequest, user: User = Depends(current_user)) -> ScreeningResponse:
    require(user, Permission.RUN_SCREENING)
    if len(request.candidate_ids) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 candidates per screening")
    if repository.monthly_tokens() >= int(repository.config["monthly_token_budget"]):
        audit = repository.log_audit(user.user_id, "budget_blocked", {"jd_id": request.jd_id}, success=False)
        raise HTTPException(status_code=429, detail={"message": "Monthly token budget exceeded", "audit_id": audit["audit_id"]})

    config = _public_config()
    if request.config_overrides:
        config.update(request.config_overrides)

    result = await orchestration_agent.run_screening_workflow(
        user=user,
        jd_id=request.jd_id,
        candidate_ids=request.candidate_ids,
        config=config,
    )
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    payload = result["data"]
    screening_id = repository.record_screening(
        {
            "jd_id": request.jd_id,
            "candidate_ids": request.candidate_ids,
            "results": payload["results"],
            "audit_trail": result["audit_trail"],
        }
    )
    usage = payload.get("token_usage", {})
    return ScreeningResponse(
        status="success",
        screening_id=screening_id,
        results=payload["results"],
        audit_trail=result["audit_trail"],
        token_usage=usage,
        cost_estimate=float(usage.get("total_cost", 0.0)),
    )


@app.get("/screen/results/{screening_id}")
async def get_screening_results(screening_id: str, user: User = Depends(current_user)) -> Dict[str, Any]:
    require(user, Permission.VIEW_SCREENING_RESULTS)
    result = repository.screenings.get(screening_id)
    if not result:
        raise HTTPException(status_code=404, detail="Screening not found")
    return result


@app.get("/usage/tokens")
async def token_usage(user: User = Depends(current_user)) -> Dict[str, Any]:
    require(user, Permission.VIEW_TOKEN_USAGE)
    return {"status": "success", **repository.usage_summary()}


@app.get("/audit/logs")
async def audit_logs(limit: int = 100, user: User = Depends(current_user)) -> Dict[str, Any]:
    require(user, Permission.VIEW_AUDIT_LOGS)
    bounded_limit = max(1, min(limit, 1000))
    return {
        "status": "success",
        "records": repository.audit_logs[-bounded_limit:],
        "total": len(repository.audit_logs),
        "retrieved_at": datetime.utcnow().isoformat(),
    }


@app.exception_handler(RBACViolation)
async def rbac_violation_handler(request: Request, exc: RBACViolation) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={
            "status": "denied",
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})
