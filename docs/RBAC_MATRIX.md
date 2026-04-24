# RBAC - Role-Based Access Control Matrix

**Permission Assignment by Role**

---

## Role Definitions

### 1. ADMIN
**Responsibility:** System operation, configuration, user management  
**Use Case:** Platform operators, security teams, compliance leads

| Permission | Purpose |
|------------|---------|
| `config:view` | View current system configuration |
| `config:edit` | Modify LLM model, weights, thresholds |
| `upload:documents` | Upload JDs, resumes, policies |
| `delete:documents` | Remove documents from system |
| `screening:run` | Execute screening workflows |
| `screening:view` | View all screening results |
| `screening:delete` | Remove screening records |
| `audit:view` | View full audit logs |
| `usage:view` | View token usage and cost |
| `users:manage` | Invite/remove users, manage accounts |
| `users:change_role` | Promote/demote user roles |

**Restrictions:**
- Cannot view candidate PII (personal data)
- Cannot override deterministic scores
- Cannot make hiring decisions

---

### 2. RECRUITER
**Responsibility:** Day-to-day screening operations  
**Use Case:** Talent acquisition team, recruiting coordinators

| Permission | Purpose |
|------------|---------|
| `upload:documents` | Upload resumes and job descriptions |
| `screening:run` | Execute candidate screenings |
| `screening:view` | View screening results and explanations |

**Restrictions:**
- Cannot modify system configuration
- Cannot delete documents
- Cannot view audit logs
- Cannot see cost/token metrics
- Cannot manage users

**Workflow:**
```
1. Recruiter uploads JDs (20 documents)
2. Recruiter uploads resumes (500 candidates)
3. Recruiter runs screening on JD_001
4. Recruiter sees ranked candidates with explanations
5. Recruiter exports shortlist for hiring managers
6. Recruiter cannot see admin settings
```

---

### 3. HIRING_MANAGER
**Responsibility:** Review screening results, make hiring decisions  
**Use Case:** Department heads, team leads

| Permission | Purpose |
|------------|---------|
| `screening:view` | View screening results and evidence |

**Restrictions:**
- Cannot run screenings
- Cannot upload documents
- Cannot modify configurations
- Cannot see audit logs
- Cannot see costs
- Cannot manage users

**Workflow:**
```
1. Hiring Manager receives shortlist from Recruiter
2. Hiring Manager views evidence cards (resume + JD alignment)
3. Hiring Manager sees interview focus suggestions
4. Hiring Manager makes hiring recommendation
5. SYSTEM ENFORCES: Hiring Manager cannot change scores
```

---

### 4. AUDITOR
**Responsibility:** Compliance and fairness monitoring  
**Use Case:** Compliance officers, legal team, ethics reviewers

| Permission | Purpose |
|------------|---------|
| `audit:view` | View all audit logs and decision trails |
| `usage:view` | View token usage and cost metrics |

**Restrictions:**
- Read-only access
- Cannot modify anything
- Cannot see individual candidate data (only aggregates)
- Cannot see system configuration

**Workflow:**
```
1. Auditor queries screening logs for Q1 2026
2. Auditor analyzes fairness metrics:
   - Score distribution by demographics
   - Token usage by screener
   - Policy violation frequency
3. Auditor downloads compliance report
4. SYSTEM ENFORCES: Cannot access raw candidate data
```

---

## Permission Matrix

| Permission | Admin | Recruiter | Hiring Manager | Auditor |
|-----------|:-----:|:---------:|:-----------:|:-------:|
| `config:view` | ✓ | ✗ | ✗ | ✗ |
| `config:edit` | ✓ | ✗ | ✗ | ✗ |
| `upload:documents` | ✓ | ✓ | ✗ | ✗ |
| `delete:documents` | ✓ | ✗ | ✗ | ✗ |
| `screening:run` | ✓ | ✓ | ✗ | ✗ |
| `screening:view` | ✓ | ✓ | ✓ | ✗ |
| `screening:delete` | ✓ | ✗ | ✗ | ✗ |
| `audit:view` | ✓ | ✗ | ✗ | ✓ |
| `usage:view` | ✓ | ✗ | ✗ | ✓ |
| `users:manage` | ✓ | ✗ | ✗ | ✗ |
| `users:change_role` | ✓ | ✗ | ✗ | ✗ |

---

## API Endpoint Access

| Endpoint | Get | Admin | Recruiter | Hiring Mgr | Auditor |
|----------|:---:|:----:|:---------:|:----------:|:-------:|
| POST `/auth/login` | ✓ | ✓ | ✓ | ✓ | ✓ |
| GET `/config` | `config:view` | ✓ | ✗ | ✗ | ✗ |
| POST `/config/update` | `config:edit` | ✓ | ✗ | ✗ | ✗ |
| POST `/upload/jd` | `upload:documents` | ✓ | ✓ | ✗ | ✗ |
| POST `/upload/resume` | `upload:documents` | ✓ | ✓ | ✗ | ✗ |
| POST `/upload/policy` | `upload:documents` | ✓ | ✗ | ✗ | ✗ |
| POST `/screen/run` | `screening:run` | ✓ | ✓ | ✗ | ✗ |
| GET `/screen/results/{id}` | `screening:view` | ✓ | ✓ | ✓ | ✗ |
| GET `/audit/logs` | `audit:view` | ✓ | ✗ | ✗ | ✓ |
| GET `/usage/tokens` | `usage:view` | ✓ | ✗ | ✗ | ✓ |

---

## Enforcement Points

### 1. JWT Middleware
Every request flow:
```
1. Client sends HTTP request with JWT token
2. FastAPI middleware extracts JWT
3. JWT decoded: extract role claim
4. Role mapped to User object
5. User injected into handler via Depends()
6. Handler checks specific permission
7. If denied: 403 + audit log
```

### 2. Handler Decorator
```python
from backend.auth.rbac import require_permission, Permission

@app.post("/config/update")
@require_permission(Permission.EDIT_CONFIG)
async def update_config(user: User = Depends(get_current_user)):
    # Only Admin reaches here
```

### 3. Agent Tool Constraints
```python
from backend.agent.orchestrator import AgentToolConstraint

# During agent execution:
constraint = AgentToolConstraint(user)
if not constraint.can_invoke("compute_deterministic_score"):
    raise AgentToolConstraintViolation(...)
```

### 4. UI Role-Based Rendering
```python
# Streamlit frontend
if user_capabilities["can_edit_config"]:
    st.markdown("# Configuration Panel")
    # Show config UI
else:
    st.info("Configuration requires Admin role")
```

---

## Audit Trail Example

**Incident:** Recruiter attempts to modify configuration

**Flow:**
```
1. Recruiter logs in → role=recruiter
2. PUT /config/update {"max_tokens": 500}
3. Middleware extracts role: RECRUITER
4. Handler checks @require_permission(EDIT_CONFIG)
5. RBAC check: recruiter has EDIT_CONFIG? NO
6. HTTP 403 Forbidden
7. AuditLogger.log_action():
   {
     "timestamp": "2026-04-24T10:47:00Z",
     "user_id": "u_001",
     "user_email": "recruiter@company.com",
     "action": "config_update_denied",
     "permission_required": "config:edit",
     "user_role": "recruiter",
     "details": {},
     "severity": "WARNING"
   }
8. Log stored in PostgreSQL + syslog
```

---

## Cross-Tenant Isolation (Future)

In multi-tenant deployment:

```
# Each tenant has isolated data
GET /screen/results/{screening_id}
  └─ Check: screening_id belongs to user's tenant
  └─ If not: 403 Forbidden + audit log
```

---

## Session Management

| Property | Value | Notes |
|----------|-------|-------|
| Token TTL | 1 hour | Can be configured |
| Refresh Window | 15 min before expiry | Automatic refresh |
| Inactivity Timeout | 30 min | Optional |
| Concurrent Sessions | 1 per user | Device confirmation if > 1 |

---

## OAuth2 Integration (Future)

```python
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.get("/protected")
async def protected_route(token: str = Depends(oauth2_scheme)):
    # Validate with identity provider
    # Extract role from token
```

---

## Permission Escalation Prevention

### What Cannot Happen
- ❌ Recruiter cannot self-promote to ADMIN
- ❌ User cannot request elevated permissions dynamically
- ❌ Front-end cannot override back-end RBAC
- ❌ Audit logs cannot be deleted by anyone
- ❌ User cannot see other user's audits

### Enforcement
- **Back-end first:** All RBAC checks server-side
- **Never trust UI:** UI renders based on capabilities, but server validates
- **Immutable audit:** Audit log entries cannot be modified
- **Role changes:** Only by another ADMIN via audit trail

---

## Testing RBAC

```bash
# Test 1: Recruiter cannot access config
curl -H "Authorization: Bearer recruiter_token" \
     http://localhost:8000/config/update \
     -X POST -d '{"max_tokens": 500}'
# Expected: 403 Forbidden

# Test 2: Admin can access config
curl -H "Authorization: Bearer admin_token" \
     http://localhost:8000/config/update \
     -X POST -d '{"max_tokens": 500}'
# Expected: 200 OK

# Test 3: Auditor can see logs
curl -H "Authorization: Bearer auditor_token" \
     http://localhost:8000/audit/logs
# Expected: 200 OK (with logs)

# Test 4: Recruiter cannot see logs
curl -H "Authorization: Bearer recruiter_token" \
     http://localhost:8000/audit/logs
# Expected: 403 Forbidden
```
