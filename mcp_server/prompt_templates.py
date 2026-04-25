"""
MCP Server prompt templates.

The MCP server is the centralized LLM control plane. It owns prompt selection,
model routing configuration, guardrail instructions, token limits, and output
shape. It does not score candidates and it does not fetch raw candidate data.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict

from backend.auth.rbac import Role


class PromptTemplate(Enum):
    RECRUITER_EXPLAIN = "recruiter_explain"
    HIRING_MANAGER_REVIEW = "hiring_manager_review"
    AUDITOR_SUMMARY = "auditor_summary"


class RoleAwarePromptManager:
    SYSTEM_PROMPT_BASE = """You are TalentFit Assist's explanation service.
You explain deterministic JD-to-resume screening evidence for human reviewers.

Hard rules:
- Do not make hiring decisions.
- Do not rank, reject, shortlist, or recommend candidates.
- Do not infer skills, experience, seniority, intent, or potential.
- Do not mention or infer protected attributes.
- Use only the supplied deterministic score summary and retrieved evidence.
- Every factual claim must include a citation in square brackets.
- If evidence is missing, say the evidence is missing.
"""

    ROLE_TASKS = {
        Role.RECRUITER: """Task for Recruiter:
Explain candidate-to-JD alignment, evidence-backed gaps, and items a human may review.""",
        Role.HIRING_MANAGER: """Task for Hiring Manager:
Summarize evidence cards, role-alignment gaps, and interview focus areas.""",
        Role.AUDITOR: """Task for Auditor:
Summarize policy enforcement, citation status, and guardrail outcomes without exposing raw candidate data.""",
        Role.ADMIN: """Task for Admin:
Summarize model, guardrail, and token-control behavior for system operation.""",
    }

    OUTPUT_CONTRACT = """Required output JSON:
{
  "summary": "short evidence-only explanation",
  "evidence_cards": [{"claim": "...", "citation": "[Resume: chunk_id]"}],
  "gaps": [{"gap": "...", "citation": "[JD: chunk_id]"}],
  "interview_focus": [{"topic": "...", "citation": "[Evidence: chunk_id]"}],
  "guardrail_status": "passed"
}
"""

    @classmethod
    def build_prompt(
        cls,
        role: Role,
        template: PromptTemplate,
        context: Dict[str, str],
    ) -> str:
        task = cls.ROLE_TASKS.get(role, cls.ROLE_TASKS[Role.RECRUITER])
        return "\n\n".join(
            [
                cls.SYSTEM_PROMPT_BASE,
                f"Prompt template: {template.value}",
                task,
                "Deterministic score summary:\n" + context.get("score_summary", ""),
                "Retrieved evidence:\n" + context.get("retrieved_context", ""),
                "Fairness policy:\n" + context.get("policy", ""),
                cls.OUTPUT_CONTRACT,
            ]
        )

    @staticmethod
    def validate_prompt_safety(prompt: str) -> bool:
        required = [
            "do not make hiring decisions",
            "do not infer",
            "citation",
            "deterministic score",
            "retrieved evidence",
        ]
        prompt_lower = prompt.lower()
        return all(item in prompt_lower for item in required)
