# Prompt Engineering Guide

**TalentFit Assist - LLM Prompt Templates and Orchestration**

---

## Overview

The MCP Server uses **role-aware, hardcoded system prompts** (never user-provided). Every LLM call is **deterministic, citation-enforced, and guardrailed**.

---

## System Prompt Template

### Role: Explainer (Used for All Screening Explanations)

```
You are a screening evidence explainer for TalentFit Assist.

Your role:
- Explain WHY candidates align or misalign with a job description
- Ground every statement in provided evidence chunks
- Never make hiring recommendations
- Never mention or infer protected attributes (age, gender, nationality)
- Never rate candidates as "good" or "bad"

Instructions:
1. Read the evidence chunks (from resume and JD)
2. Compare specific skills, experience, and qualifications
3. Cite every claim with [Source: resume/JD, section, line]
4. Keep explanation under 300 tokens
5. Use neutral language ("aligns" not "fits perfectly")

Example citation format:
"[Resume: Experience] The candidate has 7 years Python experience [JD: Requirements] which exceeds the 5-year requirement."

Forbidden patterns (block these):
- "This candidate should be hired"
- "I recommend hiring"
- "They are a good fit"
- "Age 28, Indian national"
- "Graduated from IIT Bombay in 2018"

Stop if you cannot cite your statement. Better to be silent than hallucinate.
```

---

## Prompt Construction

### Input Structure

```python
@dataclass
class ExplanationRequest:
    """Request sent to MCP Server"""
    user_role: str               # "recruiter", "hiring_manager", "admin"
    evidence_chunks: List[str]   # Retrieved from ChromaDB
    candidate_id: str            # For audit trail
    score: float                 # Deterministic score (0.0-1.0)
    jd_id: str                   # For context
    policy: str                  # Fairness policy text
    max_tokens: int              # Default: 300
```

### Output Structure

```python
@dataclass
class ExplanationResult:
    """Response from MCP Server"""
    explanation: str                    # Cited explanation
    citations: List[Citation]           # All citations in output
    token_usage: Dict[str, int]        # input_tokens, output_tokens
    guardrail_checks: List[GuardrailResult]  # All checks passed
    cost_usd: float                     # Estimated cost
    model_used: str                     # "claude-3-sonnet"
```

---

## Role-Specific Prompts

### For Recruiter

```
System Prompt (Recruiter-Specific):

You are helping a recruiter understand candidate alignment.

Your job:
- Explain how the candidate matches the job requirements
- Highlight both strengths and gaps
- Provide actionable insights for further screening

Evidence provided:
{evidence_chunks}

Candidate score: {score} / 100

Keep explanation focused on:
1. Must-have skills match
2. Experience gaps or excess
3. Domain relevance
4. Specific evidence from resume and JD

Example:
"[Resume: Experience] Alice has 7 years Python [JD: Requirements] which meets the 5-10 year requirement. However, [Resume] she has not worked with Docker, which is listed as a [JD: Requirements] must-have skill."

User Role: RECRUITER
Constraints:
- Do not make recommendations
- Do not judge candidate value
- Do not mention protected attributes
- Must cite every claim
```

### For Hiring Manager

```
System Prompt (Hiring Manager-Specific):

You are helping a hiring manager review candidate evidence.

Your job:
- Provide a clear summary of candidate qualifications
- Flag any concerns or standout strengths
- Frame in terms of job fit, not candidate value

Evidence provided:
{evidence_chunks}

Candidate score: {score} / 100

Keep explanation objective and evidence-based.

User Role: HIRING_MANAGER
Constraints:
- Read-only summary
- No recommendations
- No bias language
- Evidence citations required
```

### For Auditor (Compliance Review)

```
System Prompt (Auditor-Specific):

You are auditing a screening for compliance with fairness policy.

Your job:
- Verify explanation does not mention protected attributes
- Check that scoring is aligned with deterministic formula
- Confirm all claims are properly cited

Evidence provided:
{evidence_chunks}

Policy:
{fairness_policy}

If you find any violations, flag them:
- Protected attributes mentioned: ["age", "gender", "nationality"]
- Uncited claims: ["...text..."]
- Suspicious language: ["...phrase..."]

User Role: AUDITOR
Constraints:
- Strict compliance checking
- Block unsafe output
- No exceptions
```

---

## Citation Enforcement

### Citation Patterns (Allowed)

```
✓ [Resume: Experience] Candidate has Python
✓ [Resume: line 42] Text verbatim from resume
✓ [JD: Requirements] Job description requirement
✓ [Evidence: chunk_3] Retrieved evidence chunk
✓ [Policy: section 2] Fairness policy reference
```

### Citation Validation

```python
class CitationValidator:
    CITATION_PATTERN = r'\[([^:]+):\s*([^\]]+)\]'
    
    ALLOWED_SOURCES = [
        "Resume",
        "JD",
        "Evidence",
        "Policy",
        "Score Breakdown"
    ]
    
    def validate_citations(text: str) -> CitationValidationResult:
        """Check that all citations are valid"""
        citations = re.findall(CITATION_PATTERN, text)
        
        violations = []
        for source, reference in citations:
            if source not in ALLOWED_SOURCES:
                violations.append(f"Invalid source: {source}")
            
            if not reference.strip():
                violations.append(f"Empty reference: {source}")
        
        # Check for uncited claims
        sentences = text.split(".")
        for sentence in sentences:
            if len(sentence) > 50:  # Long claim
                if not any(s in sentence for s in ["[", "]"]):
                    violations.append(f"Uncited claim: {sentence[:50]}...")
        
        return CitationValidationResult(
            passed=len(violations) == 0,
            violations=violations,
            citation_count=len(citations)
        )
```

---

## Guardrail Orchestration

### Pre-LLM Call

```python
async def prepare_mcp_request(request: ExplanationRequest) -> Dict:
    """Prepare request with guardrails"""
    
    # 1. Input sanitization
    cleaned_chunks = strip_protected_attributes(request.evidence_chunks)
    
    # 2. Validate input
    input_guards = InputGuardrails(config)
    passed, results = input_guards.validate_all(str(cleaned_chunks))
    if not passed:
        raise GuardrailViolation("Input failed guardrail checks")
    
    # 3. Build prompt
    system_prompt = get_system_prompt(request.user_role)
    user_prompt = f"""
    Explain this candidate's alignment with the job:
    
    Evidence:
    {cleaned_chunks}
    
    Candidate Score: {request.score:.1%}
    
    Keep explanation under {request.max_tokens} tokens.
    Cite every claim.
    """
    
    # 4. Log pre-call
    log_audit_event({
        "stage": "pre_llm_call",
        "user_role": request.user_role,
        "candidate_id": request.candidate_id,
        "evidence_chunks_count": len(cleaned_chunks)
    })
    
    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "temperature": 0.3,  # Low randomness
        "max_tokens": request.max_tokens,
        "top_p": 0.9
    }
```

### Post-LLM Call

```python
async def validate_mcp_response(response: str, config: GuardrailConfig) -> Dict:
    """Validate output with guardrails"""
    
    output_guards = OutputGuardrails(config)
    passed, results = output_guards.validate_all(response)
    
    # Check each guardrail
    for result in results:
        if not result.passed and result.severity == "CRITICAL":
            log_guardrail_violation({
                "guardrail": result.__class__.__name__,
                "severity": result.severity,
                "violations": result.violations
            })
            raise GuardrailViolation(f"Output failed: {result.violations}")
    
    # Extract citations
    citations = extract_citations(response)
    
    # Calculate cost
    cost = TokenCounter.estimate_cost(
        input_text=system_prompt + user_prompt,
        output_text=response,
        model="claude-3-sonnet"
    )
    
    return {
        "explanation": response,
        "citations": citations,
        "passed_guardrails": all(r.passed for r in results),
        "cost_usd": cost["total_cost"],
        "token_usage": {
            "input": cost["input_tokens"],
            "output": cost["output_tokens"]
        }
    }
```

---

## Temperature & Sampling

### Why Low Temperature?

**Goal:** Reproducible, consistent explanations

```
Temperature: 0.3  (low randomness)
Top-p: 0.9        (focus on likely tokens)
```

**Effect:**
- Same input → Same output (mostly)
- Consistent explanation style
- Reduced hallucination risk

**Not 0.0 because:**
- Some variation is natural
- Complete determinism not achievable with LLMs
- Low variance ≈ deterministic for our purposes

---

## Cost Estimation

### Per-Call Cost

```python
def estimate_explanation_cost(user_role: str) -> float:
    """Estimate cost per explanation"""
    
    # Average token counts
    avg_input_tokens = 800    # System + evidence + user prompt
    avg_output_tokens = 150   # Typical explanation
    
    # Claude-3-Sonnet pricing
    input_price = 0.003   # $0.003 per 1K input tokens
    output_price = 0.015  # $0.015 per 1K output tokens
    
    input_cost = (avg_input_tokens / 1000) * input_price
    output_cost = (avg_output_tokens / 1000) * output_price
    total_cost = input_cost + output_cost
    
    return total_cost  # ~$0.004 per explanation
```

### Batch Cost

```
500 resumes screened against 1 JD
Top 5 candidates explained

Costs:
- 5 explanations × $0.004 = $0.02
- 500 scores (0 cost - deterministic) = $0.00
- Audit logging = $0.00
Total: ~$0.02 per 500-candidate screening
```

---

## Testing Prompts

### Test Case: Check Citation Enforcement

```python
async def test_citation_enforcement():
    """Verify explanation requires citations"""
    
    evidence = "[Resume] Python experience"
    
    # Call with weak guardrails should fail
    config = GuardrailConfig(strictness="HIGH")
    guard = OutputGuardrails(config)
    
    # Output without citations
    bad_output = "The candidate is great and should be considered."
    result = guard.validate_citations_present(bad_output)
    assert not result.passed, "Should reject uncited output"
    
    # Output with citations
    good_output = "[Resume: Experience] The candidate has Python experience."
    result = guard.validate_citations_present(good_output)
    assert result.passed, "Should accept cited output"
```

### Test Case: Check Protected Attribute Blocking

```python
async def test_protected_attribute_blocking():
    """Verify age/gender cannot leak through"""
    
    config = GuardrailConfig(strictness="HIGH")
    guard = OutputGuardrails(config)
    
    # Output mentioning age
    bad_output = "The candidate is 28 years old and well-fit."
    result = guard.validate_protected_attributes_absence(bad_output)
    assert not result.passed, "Should block age mention"
```

---

## Conclusion

**Key Principles:**
1. **Hardcoded prompts** (no user injection)
2. **Role-aware** (recruiter ≠ auditor)
3. **Citation enforced** (every claim cited)
4. **Guardrailed** (input + output validation)
5. **Low temperature** (reproducible)
6. **Cost tracked** (per-call, per-user)

Result: **Transparent, auditable, fair explanations** that assist humans without making decisions.
