# API Specification

**TalentFit Assist REST API**  
**Version:** 1.0.0  
**Base URL:** `http://localhost:8000/api/v1`

---

## Authentication

All endpoints require JWT bearer token in `Authorization` header:

```
Authorization: Bearer <jwt_token>
```

Token format:
```json
{
  "sub": "user_id",
  "email": "user@company.com",
  "role": "recruiter",
  "iat": 1234567890,
  "exp": 1234571490
}
```

---

## Endpoints

### Authentication

#### POST /auth/login
Authenticate user and receive JWT token.

**Request:**
```json
{
  "email": "recruiter@company.com",
  "password": "secure_password"
}
```

**Response (200):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "user_id": "u_001",
    "email": "recruiter@company.com",
    "role": "recruiter",
    "capabilities": {
      "can_upload": true,
      "can_edit_config": false,
      "can_run_screening": true
    }
  },
  "expires_in": 3600
}
```

**Response (401):**
```json
{
  "status": "error",
  "message": "Invalid credentials"
}
```

---

### Configuration

#### GET /config
Get current system configuration.

**Required Permission:** `config:view`

**Response (200):**
```json
{
  "llm_config": {
    "provider": "anthropic",
    "model": "claude-3-sonnet-20240229",
    "temperature": 0.3,
    "max_tokens": 300
  },
  "embedding_config": {
    "model": "text-embedding-3-small",
    "dimension": 1536
  },
  "chunking_config": {
    "jd_chunk_size": 256,
    "resume_chunk_size": 128
  },
  "scoring_config": {
    "weight_must_have": 0.4,
    "weight_nice_to_have": 0.2,
    "weight_experience": 0.2,
    "weight_domain": 0.1,
    "weight_ambiguity_penalty": 0.1
  },
  "cost_config": {
    "monthly_token_budget": 500000,
    "budget_used": 150000,
    "budget_used_percent": 30
  }
}
```

#### POST /config/update
Update system configuration.

**Required Permission:** `config:edit` (ADMIN only)

**Request:**
```json
{
  "llm_model": "claude-3-sonnet-20240229",
  "temperature": 0.3,
  "max_tokens": 300,
  "scoring_weights": {
    "must_have": 0.4,
    "nice_to_have": 0.2
  }
}
```

**Response (200):**
```json
{
  "status": "success",
  "updated_keys": ["llm_model", "temperature", "scoring_weights"],
  "timestamp": "2026-04-24T10:30:00Z"
}
```

**Response (403):**
```json
{
  "status": "error",
  "message": "Insufficient permissions: requires config:edit"
}
```

---

### Document Upload

#### POST /upload/jd
Upload job descriptions.

**Required Permission:** `upload:documents` (RECRUITER, ADMIN)

**Request:**
```json
{
  "documents": [
    {
      "jd_id": "jd_001",
      "title": "Senior Backend Engineer",
      "content": "Job description text...",
      "metadata": {
        "department": "Engineering",
        "location": "Remote"
      }
    }
  ]
}
```

**Response (200):**
```json
{
  "status": "success",
  "uploaded": 1,
  "processed": {
    "jd_001": {
      "chunks": 12,
      "embedded": true,
      "cleaning_actions": [
        {
          "type": "graduation_year",
          "count": 2,
          "description": "Graduation year"
        }
      ]
    }
  },
  "timestamp": "2026-04-24T10:30:00Z"
}
```

#### POST /upload/resume
Upload resumes.

**Required Permission:** `upload:documents` (RECRUITER, ADMIN)

**Request:**
```json
{
  "documents": [
    {
      "candidate_id": "c_042",
      "name": "Alice Chen",
      "content": "Resume text...",
      "metadata": {
        "source": "LinkedIn",
        "applied_date": "2026-04-20"
      }
    }
  ]
}
```

**Response (200):**
```json
{
  "status": "success",
  "uploaded": 1,
  "processed": {
    "c_042": {
      "chunks": 8,
      "embedded": true,
      "quality_score": 0.92,
      "quality_issues": []
    }
  }
}
```

#### POST /upload/policy
Upload fairness policy guidelines.

**Required Permission:** `upload:documents` (ADMIN only)

**Request:**
```json
{
  "policy_id": "policy_v3",
  "version": "3.0",
  "content": "Fairness guidelines...",
  "effective_date": "2026-04-24"
}
```

**Response (200):**
```json
{
  "status": "success",
  "policy_id": "policy_v3",
  "chunks": 4,
  "embedded": true
}
```

---

### Screening

#### POST /screen/run
Execute screening workflow.

**Required Permission:** `screening:run` (RECRUITER, ADMIN)

**Request:**
```json
{
  "jd_id": "jd_001",
  "candidate_ids": ["c_042", "c_089", "c_156"],
  "config_overrides": {
    "top_k": 5,
    "max_tokens": 300
  }
}
```

**Response (200):**
```json
{
  "status": "success",
  "screening_id": "scr_xyz123",
  "results": [
    {
      "candidate_id": "c_042",
      "name": "Alice Chen",
      "score": 0.82,
      "breakdown": {
        "must_have_match": 0.85,
        "nice_to_have_match": 0.70,
        "experience_match": 0.80,
        "domain_relevance": 0.60,
        "ambiguity_penalty": 0.05
      },
      "explanation": "[Resume: Experience] 7 years Python experience...",
      "evidence_chunks": ["ch_1", "ch_3", "ch_7"],
      "audit_id": "aud_001"
    }
  ],
  "ranked": [
    {"candidate_id": "c_042", "score": 0.82},
    {"candidate_id": "c_089", "score": 0.78}
  ],
  "tokens_used": 487,
  "cost_estimate": 0.02,
  "completed_at": "2026-04-24T10:35:00Z",
  "audit_trail": {
    "execution_id": "exe_xyz",
    "steps": [
      {"step": "validate_policy", "duration_ms": 5},
      {"step": "retrieve_evidence", "duration_ms": 142},
      {"step": "compute_scores", "duration_ms": 23},
      {"step": "llm_explanation", "duration_ms": 312}
    ]
  }
}
```

**Response (400):**
```json
{
  "status": "error",
  "message": "Maximum 1000 candidates per screening",
  "error_code": "VALIDATION_ERROR"
}
```

**Response (403):**
```json
{
  "status": "denied",
  "message": "User denied access: requires screening:run",
  "audit_id": "aud_denied_001"
}
```

#### GET /screen/results/{screening_id}
Retrieve screening results.

**Required Permission:** `screening:view` (RECRUITER, HIRING_MANAGER, ADMIN)

**Response (200):**
```json
{
  "screening_id": "scr_xyz123",
  "jd_id": "jd_001",
  "status": "completed",
  "results": [
    {
      "candidate_id": "c_042",
      "score": 0.82,
      "explanation": "..."
    }
  ],
  "created_at": "2026-04-24T10:30:00Z",
  "completed_at": "2026-04-24T10:35:00Z"
}
```

---

### Usage & Costs

#### GET /usage/tokens
Get token usage and cost metrics.

**Required Permission:** `usage:view` (ADMIN, AUDITOR)

**Query Parameters:**
- `start_date`: ISO date (default: 30 days ago)
- `end_date`: ISO date (default: today)
- `group_by`: "user" | "model" | "day" (default: "day")

**Response (200):**
```json
{
  "period": {
    "start_date": "2026-03-25",
    "end_date": "2026-04-24"
  },
  "summary": {
    "total_tokens": 2500000,
    "total_cost": 45.50,
    "by_model": {
      "claude-3-sonnet": {
        "input_tokens": 2000000,
        "output_tokens": 500000,
        "cost": 45.50
      }
    }
  },
  "budget": {
    "monthly_limit": 500000,
    "tokens_used": 300000,
    "budget_used_percent": 60,
    "days_until_reset": 6
  },
  "top_users": [
    {"user": "recruiter@company.com", "tokens": 500000, "cost": 9.00}
  ]
}
```

---

### Audit Logs

#### GET /audit/logs
Retrieve audit logs.

**Required Permission:** `audit:view` (AUDITOR, ADMIN)

**Query Parameters:**
- `limit`: Max records (default: 100, max: 10000)
- `offset`: Pagination offset (default: 0)
- `user_id`: Filter by user
- `action`: Filter by action type
- `start_date`: ISO date
- `end_date`: ISO date
- `severity`: "ALL" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

**Response (200):**
```json
{
  "records": [
    {
      "audit_id": "aud_001",
      "timestamp": "2026-04-24T10:35:00Z",
      "user_id": "u_001",
      "user_email": "recruiter@company.com",
      "action": "screening_completed",
      "details": {
        "jd_id": "jd_001",
        "candidates_screened": 3
      },
      "success": true,
      "severity": "INFO"
    }
  ],
  "total": 1250,
  "limit": 100,
  "offset": 0
}
```

#### GET /audit/logs/{audit_id}
Get specific audit entry with full trace.

**Response (200):**
```json
{
  "audit_id": "aud_001",
  "execution_trace": {
    "execution_id": "exe_xyz",
    "user_id": "u_001",
    "user_role": "recruiter",
    "action": "run_screening_workflow",
    "tool_invocations": [
      {
        "step": 1,
        "tool": "validate_user_policy",
        "duration_ms": 5,
        "success": true
      },
      {
        "step": 2,
        "tool": "retrieve_rag_evidence",
        "duration_ms": 142,
        "success": true
      }
    ],
    "total_duration_ms": 482,
    "success": true
  }
}
```

---

## Error Codes

| Code | Message | HTTP | Meaning |
|------|---------|------|---------|
| `UNAUTHORIZED` | Invalid or missing JWT | 401 | Authentication failed |
| `FORBIDDEN` | Insufficient permissions | 403 | RBAC denied |
| `INVALID_REQUEST` | Bad request format | 400 | Validation error |
| `RESOURCE_NOT_FOUND` | Resource doesn't exist | 404 | Not found |
| `QUOTA_EXCEEDED` | Token budget exceeded | 429 | Rate limit |
| `INTERNAL_ERROR` | Server error | 500 | Unexpected error |

---

## Rate Limiting

All endpoints are rate-limited:
- **Authenticated users:** 100 req/min
- **Bulk operations** (like screening): Counted as 10 req due to cost

When limit exceeded:
```
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

---

## Pagination

List endpoints support pagination:

```
GET /audit/logs?limit=50&offset=100
```

Response includes:
```json
{
  "records": [...],
  "total": 1250,
  "limit": 50,
  "offset": 100,
  "has_next": true,
  "has_prev": true
}
```

---

## Webhooks (Future)

For async operations, webhook support planned:
```json
{
  "event": "screening.completed",
  "screening_id": "scr_xyz",
  "timestamp": "2026-04-24T10:35:00Z"
}
```
