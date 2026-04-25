"""
TalentFit Orchestration Agent.

The agent is a deterministic workflow conductor. It validates role and policy,
invokes approved tools in a fixed order, and records an auditable trace. It does
not score, rank, infer skills, or modify deterministic scoring outputs.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from backend.auth.rbac import AgentToolConstraint, Permission, RBACEnforcer, Role, User
from backend.core.repository import InMemoryTalentRepository, score_to_dict
from backend.core.scoring_engine import DeterministicScoringEngine, ScoringWeights


class AgentToolName(Enum):
    VALIDATE_USER_POLICY = "validate_user_policy"
    COMPUTE_DETERMINISTIC_SCORE = "compute_deterministic_score"
    RETRIEVE_RAG_EVIDENCE = "retrieve_rag_evidence"
    CALL_MCP_EXPLAINER = "call_mcp_explainer"
    LOG_AUDIT_EVENT = "log_audit_event"
    ASSEMBLE_RESPONSE = "assemble_response"


@dataclass
class ToolInvocation:
    tool_name: AgentToolName
    input_params: Dict[str, Any]
    output: Dict[str, Any]
    duration_ms: float
    success: bool
    error: Optional[str] = None


@dataclass
class AgentExecutionTrace:
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=datetime.utcnow)
    user_id: str = ""
    user_role: Optional[Role] = None
    action: str = ""
    tool_invocations: List[ToolInvocation] = field(default_factory=list)
    completed_at: Optional[datetime] = None
    success: bool = False
    error: Optional[str] = None
    final_output: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "started_at": self.started_at.isoformat(),
            "user_id": self.user_id,
            "user_role": self.user_role.value if self.user_role else None,
            "action": self.action,
            "tool_invocations": [
                {
                    "tool_name": item.tool_name.value,
                    "input_params": _safe_params(item.input_params),
                    "output": item.output,
                    "duration_ms": round(item.duration_ms, 2),
                    "success": item.success,
                    "error": item.error,
                }
                for item in self.tool_invocations
            ],
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
            "error": self.error,
            "final_output": self.final_output,
        }


def _safe_params(params: Dict[str, Any]) -> Dict[str, Any]:
    safe: Dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, User):
            safe[key] = {"user_id": value.user_id, "role": value.role.value}
        else:
            safe[key] = value
    return safe


class AgentToolConstraintViolation(Exception):
    def __init__(self, user_id: str, tool_name: str, role: Role):
        super().__init__(f"User {user_id} ({role.value}) cannot invoke agent tool {tool_name}")


class TalentFitToolExecutor:
    def __init__(self, repository: InMemoryTalentRepository):
        self.repository = repository
        self.rbac = RBACEnforcer()

    def validate_user_policy(self, user: User, action: str) -> Dict[str, Any]:
        required = {"run_screening": Permission.RUN_SCREENING}.get(action)
        authorized = bool(required and self.rbac.has_permission(user, required))
        return {
            "authorized": authorized,
            "role": user.role.value,
            "required_permission": required.value if required else None,
        }

    def compute_deterministic_score(
        self,
        jd_id: str,
        candidate_ids: List[str],
        weights: Dict[str, float],
    ) -> Dict[str, Any]:
        scoring_weights = ScoringWeights(
            weight_must_have=float(weights.get("must_have", 0.4)),
            weight_nice_to_have=float(weights.get("nice_to_have", 0.2)),
            weight_experience=float(weights.get("experience", 0.2)),
            weight_domain=float(weights.get("domain", 0.1)),
            weight_ambiguity_penalty=float(weights.get("ambiguity", 0.1)),
        )
        engine = DeterministicScoringEngine(scoring_weights)
        jd = self.repository.jd_features(jd_id)
        scores = []
        for candidate_id in candidate_ids:
            resume = self.repository.resume_features(candidate_id)
            scores.append(score_to_dict(candidate_id, engine.compute_score(jd, resume)))
        scores.sort(key=lambda item: item["score"], reverse=True)
        return {"scores": scores}

    def retrieve_rag_evidence(self, jd_id: str, candidate_ids: List[str], top_k: int) -> Dict[str, Any]:
        return {
            "jd_id": jd_id,
            "top_k": top_k,
            "evidence": self.repository.retrieve_evidence(jd_id, candidate_ids, top_k),
        }

    def call_mcp_explainer(
        self,
        user: User,
        context: List[Dict[str, Any]],
        scores: List[Dict[str, Any]],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        from mcp_server.main import MCPExplainRequest, explain

        request = MCPExplainRequest(
            role=user.role,
            model=config.get("llm_model", "gpt-4o-mini"),
            provider=config.get("provider", "openai"),
            temperature=float(config.get("temperature", 0.2)),
            max_tokens=int(config.get("max_tokens", 500)),
            guardrail_strictness=config.get("guardrail_strictness", "HIGH"),
            score_summary=scores,
            retrieved_context=context,
            policy=self.repository.active_policy_text(),
        )

        import asyncio

        response = asyncio.run(explain(request)) if not _inside_event_loop() else None
        if response is None:
            raise RuntimeError("MCP explain must be invoked through async path")
        payload = response.model_dump()
        self.repository.log_usage(user.user_id, user.role.value, request.model, payload["token_usage"])
        return payload

    async def call_mcp_explainer_async(
        self,
        user: User,
        context: List[Dict[str, Any]],
        scores: List[Dict[str, Any]],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        from mcp_server.main import MCPExplainRequest, explain

        request = MCPExplainRequest(
            role=user.role,
            model=config.get("llm_model", "gpt-4o-mini"),
            provider=config.get("provider", "openai"),
            temperature=float(config.get("temperature", 0.2)),
            max_tokens=int(config.get("max_tokens", 500)),
            guardrail_strictness=config.get("guardrail_strictness", "HIGH"),
            score_summary=scores,
            retrieved_context=context,
            policy=self.repository.active_policy_text(),
        )
        response = await explain(request)
        payload = response.model_dump()
        self.repository.log_usage(user.user_id, user.role.value, request.model, payload["token_usage"])
        return payload

    def log_audit_event(self, user_id: str, action: str, details: Dict[str, Any]) -> Dict[str, Any]:
        return self.repository.log_audit(user_id, action, details)

    def assemble_response(
        self,
        scores: List[Dict[str, Any]],
        explanations: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        audit_id: str,
    ) -> Dict[str, Any]:
        explanations_by_candidate = {
            item["candidate_id"]: item for item in explanations.get("output", [])
        }
        evidence_by_candidate = {item["candidate_id"]: item.get("chunks", []) for item in evidence}
        results = []
        for score in scores:
            candidate_id = score["candidate_id"]
            results.append(
                {
                    **score,
                    "explanation": explanations_by_candidate.get(candidate_id, {}),
                    "evidence_chunks": evidence_by_candidate.get(candidate_id, []),
                    "policy_compliance_badge": "passed"
                    if explanations.get("status") == "success"
                    else "blocked",
                    "audit_id": audit_id,
                }
            )
        return {
            "results": results,
            "mcp_status": explanations.get("status"),
            "token_usage": explanations.get("token_usage", {}),
            "audit_id": audit_id,
            "label": "Screening Aid - Not a Hiring Decision Tool",
        }


def _inside_event_loop() -> bool:
    try:
        import asyncio

        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


class TalentFitOrchestrationAgent:
    def __init__(self, repository: InMemoryTalentRepository, tool_executor: Optional[TalentFitToolExecutor] = None):
        self.repository = repository
        self.tool_executor = tool_executor or TalentFitToolExecutor(repository)
        self.execution_trace: Optional[AgentExecutionTrace] = None

    async def run_screening_workflow(
        self,
        user: User,
        jd_id: str,
        candidate_ids: List[str],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        self.execution_trace = AgentExecutionTrace(
            user_id=user.user_id,
            user_role=user.role,
            action="run_screening_workflow",
        )

        try:
            validation = self._invoke_tool(
                AgentToolName.VALIDATE_USER_POLICY,
                {"user": user, "action": "run_screening"},
                self.tool_executor.validate_user_policy,
            )
            if not validation.get("authorized"):
                raise PermissionError("User is not authorized to run screening")

            for tool in [
                AgentToolName.COMPUTE_DETERMINISTIC_SCORE,
                AgentToolName.RETRIEVE_RAG_EVIDENCE,
                AgentToolName.CALL_MCP_EXPLAINER,
                AgentToolName.LOG_AUDIT_EVENT,
                AgentToolName.ASSEMBLE_RESPONSE,
            ]:
                self._ensure_tool_allowed(user, tool)

            scoring = self._invoke_tool(
                AgentToolName.COMPUTE_DETERMINISTIC_SCORE,
                {
                    "jd_id": jd_id,
                    "candidate_ids": candidate_ids,
                    "weights": config.get("scoring_weights", {}),
                },
                self.tool_executor.compute_deterministic_score,
            )
            evidence = self._invoke_tool(
                AgentToolName.RETRIEVE_RAG_EVIDENCE,
                {"jd_id": jd_id, "candidate_ids": candidate_ids, "top_k": int(config.get("top_k", 5))},
                self.tool_executor.retrieve_rag_evidence,
            )

            explanations = await self._invoke_tool_async(
                AgentToolName.CALL_MCP_EXPLAINER,
                {
                    "user": user,
                    "context": evidence["evidence"],
                    "scores": scoring["scores"],
                    "config": config,
                },
                self.tool_executor.call_mcp_explainer_async,
            )
            audit = self._invoke_tool(
                AgentToolName.LOG_AUDIT_EVENT,
                {
                    "user_id": user.user_id,
                    "action": "screening_completed",
                    "details": {
                        "jd_id": jd_id,
                        "candidate_count": len(candidate_ids),
                        "mcp_status": explanations.get("status"),
                    },
                },
                self.tool_executor.log_audit_event,
            )
            final = self._invoke_tool(
                AgentToolName.ASSEMBLE_RESPONSE,
                {
                    "scores": scoring["scores"],
                    "explanations": explanations,
                    "evidence": evidence["evidence"],
                    "audit_id": audit["audit_id"],
                },
                self.tool_executor.assemble_response,
            )

            self.execution_trace.success = True
            self.execution_trace.final_output = final
            return {"success": True, "data": final, "audit_trail": self.execution_trace.to_dict()}
        except Exception as exc:
            self.execution_trace.success = False
            self.execution_trace.error = str(exc)
            return {"success": False, "error": str(exc), "audit_trail": self.execution_trace.to_dict()}
        finally:
            self.execution_trace.completed_at = datetime.utcnow()

    def _ensure_tool_allowed(self, user: User, tool: AgentToolName) -> None:
        constraint = AgentToolConstraint(user)
        if not constraint.can_invoke(tool.value):
            raise AgentToolConstraintViolation(user.user_id, tool.value, user.role)

    def _invoke_tool(self, tool_name: AgentToolName, params: Dict[str, Any], executor_func) -> Dict[str, Any]:
        started = time.time()
        try:
            output = executor_func(**params)
            self.execution_trace.tool_invocations.append(
                ToolInvocation(tool_name, params, output, (time.time() - started) * 1000, True)
            )
            return output
        except Exception as exc:
            self.execution_trace.tool_invocations.append(
                ToolInvocation(tool_name, params, {}, (time.time() - started) * 1000, False, str(exc))
            )
            raise

    async def _invoke_tool_async(self, tool_name: AgentToolName, params: Dict[str, Any], executor_func) -> Dict[str, Any]:
        started = time.time()
        try:
            output = await executor_func(**params)
            self.execution_trace.tool_invocations.append(
                ToolInvocation(tool_name, params, output, (time.time() - started) * 1000, True)
            )
            return output
        except Exception as exc:
            self.execution_trace.tool_invocations.append(
                ToolInvocation(tool_name, params, {}, (time.time() - started) * 1000, False, str(exc))
            )
            raise
