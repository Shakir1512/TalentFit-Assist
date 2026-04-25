# RBAC Implementation Specification

**TalentFit Assist - Role-Based Access Control**

---

## Role Definitions

### 1. Admin
**Purpose:** Configure system behavior, manage users, audit compliance

**Permissions:**
- ✅ Create/update/delete users
- ✅ Configure LLM model, temperature, max tokens
- ✅ Configure chunk size, overlap, embedding model
- ✅ Configure scoring weights
- ✅ Configure guardrail strictness
- ✅ Set monthly token budget
- ✅ Upload policy documents
- ✅ View cost dashboards
- ✅ Export audit logs
- ✅ View fairness metrics

**Denied:**
- ❌ Cannot run screenings (not recruiter's role)
- ❌ Cannot upload resumes directly
- ❌ Cannot make hiring decisions

---

### 2. Recruiter
**Purpose:** Upload documents, run screenings, review candidates

**Permissions:**
- ✅ Upload job descriptions
- ✅ Upload resumes
- ✅ Run screening workflows
- ✅ View screening results
- ✅ Export candidate lists
- ✅ View token usage (personal)
- ✅ Download evidence cards

**Denied:**
- ❌ Cannot modify configuration
- ❌ Cannot view other recruiter's screenings
- ❌ Cannot audit access logs
- ❌ Cannot view cost breakdown

---

### 3. Hiring Manager
**Purpose:** Review evidence, provide feedback on candidates

**Permissions:**
- ✅ View screening results (shared by recruiter)
- ✅ View evidence cards with citations
- ✅ View score breakdown
- ✅ Add notes/feedback

**Denied:**
- ❌ Cannot run screenings
- ❌ Cannot modify scores
- ❌ Cannot upload documents
- ❌ Cannot view audit logs

---

### 4. Auditor
**Purpose:** Compliance, fairness, and audit trail monitoring

**Permissions:**
- ✅ Read all audit logs
- ✅ View fairness metrics
- ✅ View token usage (system-wide)
- ✅ View compliance reports
- ✅ Export audit data
- ✅ View access logs

**Denied:**
- ❌ Cannot modify any data
- ❌ Cannot run screenings
- ❌ Cannot delete logs
- ❌ Cannot view confidential data (resumes)

---

## Permission Matrix

```
                           Admin  Recruiter  HiringMgr  Auditor
─────────────────────────────────────────────────────────────
Manage Users                 ✓       ✗          ✗         ✗
Configure LLM                ✓       ✗          ✗         ✗
Configure Weights            ✓       ✗          ✗         ✗
Configure Guardrails         ✓       ✗          ✗         ✗
Set Budget                   ✓       ✗          ✗         ✗
Upload Policy                ✓       ✗          ✗         ✗
─────────────────────────────────────────────────────────────
Upload JD                    ✓       ✓          ✗         ✗
Upload Resume                ✓       ✓          ✗         ✗
Run Screening                ✓       ✓          ✗         ✗
View Results                 ✓       ✓          ✓         ✗
Add Feedback                 ✓       ✓          ✓         ✗
─────────────────────────────────────────────────────────────
View Audit Logs              ✓       ✗          ✗         ✓
View Cost Breakdown          ✓       ✗          ✗         ✓
View Fairness Metrics        ✓       ✗          ✗         ✓
Export Compliance Reports    ✓       ✗          ✗         ✓
─────────────────────────────────────────────────────────────
```

---

## Implementation Strategy

### Layer 1: JWT Token Claims

**Token Format:**
```json
{
  "sub": "user_id",
  "email": "user@company.com",
  "role": "recruiter",
  "permissions": [
    "run_screening",
    "upload_resume",
    "view_results"
  ],
  "iat": 1714070400,
  "exp": 1714156800
}
```

**Token Generation (Login):**
```python
def issue_jwt_token(user: User) -> str:
    """Generate JWT with role claims"""
    payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "permissions": get_permissions(user.role),
        "iat": now(),
        "exp": now() + 24*3600
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
```

---

### Layer 2: Middleware Enforcement

**AuthMiddleware:**
```python
class AuthMiddleware:
    async def __call__(self, request: Request, call_next):
        # Extract JWT from Authorization header
        token = extract_bearer_token(request.headers.get("Authorization"))
        
        if not token:
            return JSONResponse({"error": "Missing token"}, status_code=401)
        
        # Validate JWT signature + expiry
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except JWTError:
            return JSONResponse({"error": "Invalid token"}, status_code=401)
        
        # Attach to request context
        request.state.user = User.from_token(payload)
        request.state.role = payload["role"]
        request.state.permissions = payload["permissions"]
        
        return await call_next(request)
```

---

### Layer 3: Endpoint Decorators

**Decorator Implementation:**
```python
from functools import wraps
from enum import Enum

class Permission(str, Enum):
    RUN_SCREENING = "run_screening"
    UPLOAD_RESUME = "upload_resume"
    UPLOAD_JD = "upload_jd"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    CONFIGURE_LLM = "configure_llm"
    # ... etc

def require_permission(required_permission: Permission):
    """Decorator to enforce permission at endpoint level"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user_permissions = request.state.permissions
            
            if required_permission not in user_permissions:
                # Log unauthorized attempt
                await audit_log.log_event({
                    "user_id": request.state.user.id,
                    "action": "unauthorized_access_attempt",
                    "endpoint": request.url.path,
                    "required_permission": required_permission,
                    "user_permissions": user_permissions,
                    "timestamp": now()
                })
                
                return JSONResponse(
                    {"error": f"Missing permission: {required_permission}"},
                    status_code=403
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator

# Usage:
@app.post("/api/v1/screening/run")
@require_permission(Permission.RUN_SCREENING)
async def run_screening(request: Request, body: ScreeningRequest):
    # Endpoint code
    pass
```

---

### Layer 4: Agent Tool Constraints

**Tool Access Control:**
```python
class AgentToolConstraint:
    def __init__(self, user_role: str):
        self.user_role = user_role
        self.allowed_tools = self._get_allowed_tools(user_role)
    
    def _get_allowed_tools(self, role: str) -> List[str]:
        """Return which tools this role can invoke"""
        if role == "admin":
            return [
                "validate_user_policy",
                "retrieve_rag_evidence",
                "compute_deterministic_score",
                "call_mcp_explainer",
                "log_audit_event",
                "assemble_response"
            ]
        elif role == "recruiter":
            return [
                "validate_user_policy",
                "retrieve_rag_evidence",
                "compute_deterministic_score",
                "call_mcp_explainer",
                "log_audit_event",
                "assemble_response"
            ]
        elif role == "hiring_manager":
            return [
                "validate_user_policy",
                "log_audit_event"
            ]
        elif role == "auditor":
            return []  # Read-only, no tools
        else:
            raise ValueError(f"Unknown role: {role}")
    
    def can_invoke(self, tool_name: str) -> bool:
        """Check if tool can be invoked"""
        if tool_name not in self.allowed_tools:
            log_warning(f"Role {self.user_role} attempted to invoke {tool_name}")
            return False
        return True
    
    async def invoke_tool(self, tool_name: str, *args, **kwargs):
        """Safely invoke tool with constraint check"""
        if not self.can_invoke(tool_name):
            raise PermissionError(
                f"Role {self.user_role} cannot invoke {tool_name}"
            )
        
        # Get tool and call it
        tool = getattr(AgentTools, tool_name)
        return await tool(*args, **kwargs)
```

---

### Layer 5: UI Rendering

**Streamlit Page Visibility:**
```python
# pages/3_Upload_Documents.py
import streamlit as st
from auth import get_current_user

def main():
    # Get authenticated user
    user = get_current_user(st.session_state.get("token"))
    
    if user is None:
        st.error("Not authenticated")
        st.stop()
    
    # Check permission
    if user.role not in ["admin", "recruiter"]:
        st.error("You don't have permission to access this page")
        st.stop()
    
    st.title("Upload Documents")
    
    # Admin-only: can upload policies
    if user.role == "admin":
        with st.expander("Upload Policy (Admin Only)"):
            policy_file = st.file_uploader("Select policy document")
            if st.button("Upload Policy"):
                api.upload_policy(policy_file, st.session_state.token)
    
    # Both admin and recruiter can upload JD/Resume
    st.subheader("Upload Job Descriptions or Resumes")
    doc_type = st.selectbox("Document Type", ["Job Description", "Resume"])
    files = st.file_uploader("Select files", accept_multiple_files=True)
    
    if st.button("Upload"):
        endpoint = f"upload/{doc_type.lower().replace(' ', '_')}"
        api.upload_documents(files, endpoint, st.session_state.token)
```

---

## Audit Trail

**Every permission check logged:**
```python
async def audit_permission_check(
    user_id: str,
    permission: str,
    endpoint: str,
    allowed: bool,
    timestamp: datetime
):
    await db.insert("audit_logs", {
        "user_id": user_id,
        "action": "permission_check",
        "resource": permission,
        "endpoint": endpoint,
        "allowed": allowed,
        "timestamp": timestamp,
        "ip_address": request.client.host,
        "user_agent": request.headers.get("User-Agent")
    })
```

---

## Testing

**Test Cases:**
```python
async def test_unauthorized_user_cannot_run_screening():
    """Verify recruiter cannot run screening if permission revoked"""
    token = generate_test_token(role="recruiter", permissions=[])
    response = await client.post(
        "/api/v1/screening/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"jd_id": "jd_1", "resume_ids": ["r_1"]}
    )
    assert response.status_code == 403
    assert "permission" in response.json()["error"].lower()

async def test_admin_can_configure_model():
    """Verify admin can change LLM model"""
    token = generate_test_token(role="admin")
    response = await client.post(
        "/api/v1/config/update",
        headers={"Authorization": f"Bearer {token}"},
        json={"llm_model": "gpt-4"}
    )
    assert response.status_code == 200

async def test_recruiter_cannot_configure_model():
    """Verify recruiter cannot change LLM"""
    token = generate_test_token(role="recruiter")
    response = await client.post(
        "/api/v1/config/update",
        headers={"Authorization": f"Bearer {token}"},
        json={"llm_model": "gpt-4"}
    )
    assert response.status_code == 403
```

---

## Security Considerations

### 1. Token Theft
**Mitigation:**
- Short expiry (24 hours)
- Refresh token rotation
- Token blacklist on logout
- HTTPS/TLS only

### 2. Role Escalation
**Mitigation:**
- Roles stored in database (not user-modifiable)
- JWT signed with private key
- Cannot self-issue tokens

### 3. Insider Threat
**Mitigation:**
- All actions logged with user ID
- Cannot delete/modify audit logs
- Auditor role has read-only access

### 4. Brute Force
**Mitigation:**
- Rate limiting on login endpoint
- Account lockout after N failures
- IP-based throttling

---

## Compliance

**GDPR:**
- User roles are not sensitive personal data
- Audit logs kept for 1 year (configurable)

**SOC2:**
- Role-based access with audit trail
- User provisioning/deprovisioning tracked
- Segregation of duties enforced

**HIPAA (if applicable):**
- Fine-grained role separation
- Comprehensive audit trail
- Data access controls

