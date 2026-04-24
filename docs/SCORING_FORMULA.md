# Deterministic Scoring Formula

**Candidate-JD Matching Algorithm**

---

## Overview

The scoring engine computes candidate-JD alignment as a single deterministic formula with zero randomness.

**Goal:** Explainable numerical match score [0.0 - 1.0] reflecting skill/experience alignment.

**NOT Goal:** Predict hiring success, rank candidates by value, or infer hidden skills.

---

## Formula

```
FINAL_SCORE = (
    (M × w_m) +
    (N × w_n) +
    (E × w_e) +
    (D × w_d) -
    (P × w_p)
) / 100

Where:
  M = Must-have skills match [0-100%]
  N = Nice-to-have skills match [0-100%]  
  E = Experience range alignment [0-100%]
  D = Domain relevance [0-100%]
  P = Ambiguity penalty [0-50 points]
  
  w_m = 0.4 (40%)
  w_n = 0.2 (20%)
  w_e = 0.2 (20%)
  w_d = 0.1 (10%)
  w_p = 0.1 (10%)

Result: Clamped to [0.0, 1.0]
```

---

## Component Definitions

### 1. Must-Have Skills Match (M)

**Definition:** Percentage of required skills mentioned in resume.

**Calculation:**
```
M = (skills_found / skills_required) × 100

Where:
  skills_found = count of must-have skills mentioned in resume
  skills_required = count of must-have skills in JD
```

**Skill Matching Logic:**
- **Exact Match:** "Python" == "Python" → 1.0 point
- **Partial Match:** "Python" ⊆ "Python 3.9" → 0.6 points
- **Not Found:** "Rust" not in resume → 0.0 points

**Example:**
```
JD: Must have: ["Python", "PostgreSQL", "REST APIs"]
Resume: "5 years Python programming, PostgreSQL databases, REST experience"

Found: Python (exact), PostgreSQL (exact), REST (partial)
M = (2.0 + 0.6) / 3 = 2.6/3 = 86.7% → 0.867
```

**Edge Cases:**
- No required skills → 100% (no requirements to fail)
- Resume is completely empty → 0%

---

### 2. Nice-to-Have Skills Match (N)

**Definition:** Percentage of preferred skills mentioned.

**Calculation:**
```
N = (nice_skills_found / nice_skills_required) × 100
```

**Same matching logic as must-have, but lower priority.**

**Example:**
```
JD: Nice to have: ["Kubernetes", "Terraform", "AWS"]
Resume: "Kubernetes experience, Docker as secondary"

Found: Kubernetes (exact), Docker doesn't match AWS/Terraform
N = 1.0 / 3 = 33.3% → 0.333
```

---

### 3. Experience Range Alignment (E)

**Definition:** How well resume years of experience align with JD requirements.

**Calculation:**

```
if resume_years < required_min:
    E = max(0, 100 - (shortage × 20))  # -20% per year short
    
elif resume_years <= required_max:
    E = 100  # Perfect match
    
elif resume_years > required_max + 5:
    E = max(50, 100 - ((excess - 5) × 5))  # Overqualified, floor 50%
    
else:
    E = 100  # Within acceptable overqualification
```

**Rationale:**
- Below minimum: Candidate lacks depth → penalty
- Within range: No penalty
- Slightly overqualified: Acceptable (doesn't hurt)
- Far overqualified: Slight penalty (risk of quick departure)

**Example 1: Junior candidate**
```
JD: 5-10 years required
Resume: 3 years experience

shortage = 5 - 3 = 2 years
E = max(0, 100 - (2 × 20)) = max(0, 60) = 60%
```

**Example 2: Perfect fit**
```
JD: 5-10 years
Resume: 7 years

E = 100%
```

**Example 3: Very overqualified**
```
JD: 5-10 years
Resume: 20 years

excess = 20 - 10 - 5 = 5 years
E = max(50, 100 - (5 × 5)) = max(50, 75) = 75%
```

---

### 4. Domain Relevance (D)

**Definition:** Industry/domain alignment.

**Calculation:**

```
if resume_has_exact_domain:
    D = 100
    
elif resume_has_related_domain:
    D = 70
    
elif resume_has_any_experience:
    D = 30
    
else:
    D = 0
```

**Related Domains Mapping:**
```
"retail" ← → ["retail technology", "e-commerce", "omnichannel"]
"technology" ← → ["fintech", "tech", "software"]
"finance" ← → ["fintech", "financial"]
```

**Example:**
```
JD required domain: "retail technology"
Resume domain experience: {
  "retail technology": 4 years,
  "fintech": 2 years,
  "consulting": 1 year
}

Has exact domain → D = 100%
```

---

### 5. Ambiguity Penalty (P)

**Definition:** Deductions for data quality/clarity issues.

**Calculation:**
```
P = sum([
  10 if "missing_years_of_experience" else 0,
   5 if "resume_gaps" else 0,
   5 if "unclear_skill_names" else 0,
   5 if "no_education_listed" else 0,
   ...
])

Max penalty: 50 points
```

**Flags (examples):**
| Flag | Points | Meaning |
|------|--------|---------|
| `missing_years` | 10 | Can't determine experience duration |
| `resume_gaps` | 5 | Employment gaps not explained |
| `unclear_skills` | 5 | Skills named ambiguously |
| `no_education` | 5 | No education section |
| `date_mismatch` | 5 | Inconsistent job dates |

**Example:**
```
Resume issues found:
  - Missing end year for current role
  - Unclear if "data" refers to analytics or engineering
  
Penalties: 10 + 5 = 15 points
P = 15
```

---

## Complete Worked Example

**Job Description:**
```
Title: Senior Backend Engineer, Retail Tech

Must-have:
  - 5+ years backend development
  - Python or Go
  - PostgreSQL
  
Nice-to-have:
  - Kubernetes
  - React (for breadth)
  
Required experience: 5-10 years
Domain: Retail Technology
```

**Resume:**
```
Alice Chen
Summary: 7 years of backend engineering
  
Experience:
  - 4 years: Python backend at RetailCo
  - 3 years: Go backend at FinTech startup
  
Skills: Python, Go, PostgreSQL, Docker, some React exposure
Education: B.S. Computer Science 2019
```

**Scoring:**

1. **Must-have Skills (M):**
   - Required: [5+ years backend, Python or Go, PostgreSQL]
   - Found: [7 years backend ✓, Python ✓, Go (alternative) ✓, PostgreSQL ✓]
   - M = 3/3 = 100%

2. **Nice-to-have Skills (N):**
   - Required: [Kubernetes, React]
   - Found: [Docker (similar to K8s) = 0.6, React (mentioned) = 1.0]
   - N = (0.6 + 1.0) / 2 = 80%

3. **Experience Range (E):**
   - Resume: 7 years
   - Required: 5-10 years
   - 5 ≤ 7 ≤ 10 → E = 100%

4. **Domain Relevance (D):**
   - Required: "Retail Technology"
   - Resume experience:
     - RetailCo (4 years) = exact match!
     - FinTech (3 years) = related domain
   - D = 100%

5. **Ambiguity Penalty (P):**
   - Education dates old but OK
   - All roles dated clearly
   - No gaps
   - P = 0

**Final Calculation:**
```
FINAL_SCORE = (
    (100 × 0.4) +       # Must-have
    (80 × 0.2) +        # Nice-to-have
    (100 × 0.2) +       # Experience
    (100 × 0.1) -       # Domain
    (0 × 0.1)           # Penalty
) / 100

= (40 + 16 + 20 + 10 - 0) / 100
= 86 / 100
= 0.86 (86%)
```

**Interpretation:**
```
Score: 0.86 / 1.0 (86%)
Audit Trail:
  - Must-have match: 100% (3/3 skills found)
  - Nice-to-have match: 80% (1.6/2 skills found)
  - Experience alignment: 100% (7 years within 5-10 range)
  - Domain relevance: 100% (4 years retail technology)
  - Ambiguity penalty: 0 (clean data)

Explanation:
  Candidate has directly matched required skills (Python, PostgreSQL),
  sufficient backend experience (7 years vs 5 required), and relevant
  retail technology domain background. Minor gap in Kubernetes but
  compensated by Docker experience. Ready for next review stage.
```

---

## Configurability

All weights and thresholds are UI-configurable:

```json
{
  "weights": {
    "must_have": 0.4,
    "nice_to_have": 0.2,
    "experience": 0.2,
    "domain": 0.1,
    "ambiguity_penalty": 0.1
  },
  "experience_penalties": {
    "years_short_penalty": 20,
    "years_excess_limit": 5,
    "years_excess_penalty": 5,
    "overqualified_floor": 50
  },
  "skill_matching": {
    "exact_match_weight": 1.0,
    "partial_match_weight": 0.6,
    "not_found_weight": 0.0
  }
}
```

---

## Non-Configurability (Locked)

These cannot change without code review:
- ✓ Formula structure (deterministic, no ML)
- ✓ Clamping range [0.0, 1.0]
- ✓ Component definitions (must-have, experience, etc.)
- ✓ Direction of penalties (always penalize ambiguity)

---

## Auditability

Every score includes breakdown:

```json
{
  "candidate_id": "c_042",
  "final_score": 0.86,
  "breakdown": {
    "must_have_match": 1.0,
    "nice_to_have_match": 0.8,
    "experience_match": 1.0,
    "domain_relevance": 1.0,
    "ambiguity_penalty": 0.0
  },
  "audit_trail": {
    "must_have_match": "100% (3/3 skills matched: Python, PostgreSQL, backend)",
    "nice_to_have_match": "80% (1.6/2 skills: Kubernetes=0.6, React=1.0)",
    "experience_match": "100% (Resume: 7 years, Required: 5-10)",
    "domain_relevance": "100% (4 years retail technology)",
    "ambiguity_penalty": "0 points (no quality issues)"
  },
  "formula": {
    "calculation": "(100×0.4) + (80×0.2) + (100×0.2) + (100×0.1) - (0×0.1) = 86/100"
  }
}
```

Every number traceable to evidence.

---

## Limitations & Design Choices

### What It CANNOT Do
- ❌ Predict job performance
- ❌ Infer missing skills
- ❌ Rank by "cultural fit"
- ❌ Account for soft skills
- ❌ Apply ML learned weights

### Why These Limitations?
- **Transparency:** Every point is explainable
- **Fairness:** No learned biases from training data
- **Auditability:** Regulatory compliance
- **Reproducibility:** Same inputs → Same outputs, always

### Future Enhancements
In production hardening:
- Custom skill equivalency mappings (user-provided)
- Contextual weighting by role (e.g., leadership roles weight domain higher)
- Historical validation: track score vs. hire success rate
