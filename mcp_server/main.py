"""
TalentFit MCP Server.

This FastAPI service models the MCP control plane responsibilities locally:
prompt management, model/provider selection, generation controls, token usage,
guardrail checks, and structured output validation. The local implementation
generates citation-preserving explanations deterministically so the repository
can run without external provider credentials.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.auth.rbac import Role
from mcp_server.guardrails import GuardrailConfig, InputGuardrails, OutputGuardrails, TokenCounter
from mcp_server.prompt_templates import PromptTemplate, RoleAwarePromptManager


app = FastAPI(
    title="TalentFit MCP Server",
    description="Centralized LLM control plane for TalentFit Assist",
    version="1.0.0",
)


class MCPExplainRequest(BaseModel):
    role: Role
    model: str = "gpt-4o-mini"
    provider: str = "openai"
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=500, ge=64, le=4000)
    guardrail_strictness: str = "HIGH"
    score_summary: List[Dict[str, Any]]
    retrieved_context: List[Dict[str, Any]]
    policy: str


class MCPExplainResponse(BaseModel):
    status: str
    provider: str
    model: str
    prompt_template: str
    output: List[Dict[str, Any]]
    guardrail_results: Dict[str, Any]
    token_usage: Dict[str, Any]


def _context_to_text(context: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for item in context:
        candidate_id = item.get("candidate_id", "unknown")
        for chunk in item.get("chunks", []):
            metadata = chunk.get("metadata", {})
            chunk_id = chunk.get("chunk_id") or metadata.get("chunk_id") or "chunk"
            source = metadata.get("section_type", "Evidence")
            text = str(chunk.get("text", "")).replace("\n", " ")[:500]
            lines.append(f"[{source.title()}: {chunk_id}] candidate={candidate_id} {text}")
    return "\n".join(lines)


def _score_to_text(scores: List[Dict[str, Any]]) -> str:
    return "\n".join(
        f"candidate={score.get('candidate_id')} score={score.get('score')} breakdown={score.get('breakdown')}"
        for score in scores
    )


def _deterministic_explanation(
    scores: List[Dict[str, Any]],
    context: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    chunks_by_candidate = {item.get("candidate_id"): item.get("chunks", []) for item in context}
    explanations: List[Dict[str, Any]] = []
    for score in scores:
        candidate_id = score.get("candidate_id")
        chunks = chunks_by_candidate.get(candidate_id, [])
        first_chunk = chunks[0] if chunks else {}
        citation = f"[Resume: {first_chunk.get('chunk_id', 'no_chunk')}]"
        jd_citation = "[JD: deterministic-score-summary]"
        breakdown = score.get("breakdown", {})
        explanations.append(
            {
                "candidate_id": candidate_id,
                "summary": (
                    f"Deterministic score is {score.get('score', 0):.2f}. "
                    f"Must-have match is {breakdown.get('must_have_match', 0):.1f}% "
                    f"and experience alignment is {breakdown.get('experience_match', 0):.1f}% {citation}."
                ),
                "evidence_cards": [
                    {
                        "claim": "Resume evidence was retrieved for human review.",
                        "citation": citation,
                    }
                ],
                "gaps": [
                    {
                        "gap": "Review any low-scoring score components before deciding next steps.",
                        "citation": jd_citation,
                    }
                ],
                "interview_focus": [
                    {
                        "topic": "Validate skills or experience areas with weaker deterministic evidence.",
                        "citation": citation,
                    }
                ],
                "guardrail_status": "passed",
            }
        )
    return explanations


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "healthy", "component": "mcp_server"}


@app.post("/mcp/explain", response_model=MCPExplainResponse)
async def explain(request: MCPExplainRequest) -> MCPExplainResponse:
    config = GuardrailConfig(strictness=request.guardrail_strictness)
    input_guardrails = InputGuardrails(config)
    output_guardrails = OutputGuardrails(config)

    context_text = _context_to_text(request.retrieved_context)
    score_text = _score_to_text(request.score_summary)
    prompt = RoleAwarePromptManager.build_prompt(
        role=request.role,
        template=PromptTemplate.RECRUITER_EXPLAIN,
        context={
            "score_summary": score_text,
            "retrieved_context": context_text,
            "policy": request.policy,
        },
    )
    if not RoleAwarePromptManager.validate_prompt_safety(prompt):
        raise HTTPException(status_code=500, detail="Prompt safety contract failed")

    input_results = [
        input_guardrails.validate_prompt_injection(context_text),
        input_guardrails.validate_protected_attributes(context_text),
        input_guardrails.validate_input_length(prompt, max_tokens=request.max_tokens),
    ]
    input_ok = all(result.passed for result in input_results)
    if not input_ok:
        return MCPExplainResponse(
            status="blocked",
            provider=request.provider,
            model=request.model,
            prompt_template=PromptTemplate.RECRUITER_EXPLAIN.value,
            output=[],
            guardrail_results={
                "input": [result.__dict__ for result in input_results],
                "output": [],
            },
            token_usage=TokenCounter.estimate_cost(prompt, "", request.model),
        )

    output = _deterministic_explanation(request.score_summary, request.retrieved_context)
    output_text = json.dumps(output)
    output_ok, output_results = output_guardrails.validate_all(output_text)
    status = "success" if output_ok else "blocked"
    final_output = output if output_ok else []

    return MCPExplainResponse(
        status=status,
        provider=request.provider,
        model=request.model,
        prompt_template=PromptTemplate.RECRUITER_EXPLAIN.value,
        output=final_output,
        guardrail_results={
            "input": [result.__dict__ for result in input_results],
            "output": [result.__dict__ for result in output_results],
        },
        token_usage=TokenCounter.estimate_cost(prompt, output_text if output_ok else "", request.model),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8888)
