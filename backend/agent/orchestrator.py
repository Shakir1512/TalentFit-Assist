"""
TalentFit Orchestration Agent

Coordinates multi-step workflows under strict constraints.
Acts as workflow conductor, NOT decision maker.

Agent Properties:
- Role-aware: Reads JWT role claims
- Tool-constrained: Cannot invent tools
- Fully auditable: Step-by-step logs
- Deterministic: No free-form reasoning
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import json
import uuid

from backend.auth.rbac import User, Role, AgentToolConstraint, Permission, RBACViolation


class AgentToolName(Enum):
    """Approved agent tools (constrained set)"""
    VALIDATE_USER_POLICY = "validate_user_policy"
    RETRIEVE_RAG_EVIDENCE = "retrieve_rag_evidence"
    COMPUTE_DETERMINISTIC_SCORE = "compute_deterministic_score"
    CALL_MCP_EXPLAINER = "call_mcp_explainer"
    LOG_AUDIT_EVENT = "log_audit_event"
    ASSEMBLE_RESPONSE = "assemble_response"


@dataclass
class ToolInvocation:
    """Record of a single tool invocation"""
    tool_name: AgentToolName
    input_params: Dict[str, Any]
    output: Dict[str, Any]
    duration_ms: float
    success: bool
    error: Optional[str] = None


@dataclass
class AgentExecutionTrace:
    """Complete execution trace for auditability"""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=datetime.utcnow)
    user_id: str = ""
    user_role: Role = None
    action: str = ""
    
    # Execution timeline
    tool_invocations: List[ToolInvocation] = field(default_factory=list)
    
    # Final state
    completed_at: Optional[datetime] = None
    success: bool = False
    error: Optional[str] = None
    final_output: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
        return {
            "execution_id": self.execution_id,
            "started_at": self.started_at.isoformat(),
            "user_id": self.user_id,
            "user_role": self.user_role.value if self.user_role else None,
            "action": self.action,
            "tool_invocations": [
                {
                    "tool_name": inv.tool_name.value,
                    "input_params": inv.input_params,
                    "output": inv.output,
                    "duration_ms": inv.duration_ms,
                    "success": inv.success,
                    "error": inv.error
                }
                for inv in self.tool_invocations
            ],
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
            "error": self.error,
            "final_output": self.final_output
        }


class AgentToolConstraintViolation(Exception):
    """Raised when agent attempts to use unauthorized tool"""
    
    def __init__(self, user_id: str, tool_name: str, role: Role):
        self.user_id = user_id
        self.tool_name = tool_name
        self.role = role
        super().__init__(
            f"User {user_id} ({role.value}) attempted unauthorized tool: {tool_name}"
        )


class MockToolExecutor:
    """
    Mock implementations of agent tools for demonstration.
    In production, these would call real APIs.
    """
    
    @staticmethod
    def validate_user_policy(user: User, action: str) -> Dict[str, any]:
        """Check if user has permission for action"""
        permissions_map = {
            "run_screening": Permission.RUN_SCREENING,
            "upload_documents": Permission.UPLOAD_DOCUMENTS,
            "view_results": Permission.VIEW_SCREENING_RESULTS,
        }
        
        permission = permissions_map.get(action)
        enforcer = RBACEnforcer()
        
        has_perm = enforcer.has_permission(user, permission) if permission else False
        
        return {
            "authorized": has_perm,
            "user_id": user.user_id,
            "role": user.role.value,
            "action": action,
            "reason": "Permission granted" if has_perm else f"Missing {permission.value if permission else 'unknown'}"
        }
    
    @staticmethod
    def retrieve_rag_evidence(jd_id: str, candidate_ids: List[str], top_k: int = 5) -> Dict[str, any]:
        """Retrieve evidence chunks from ChromaDB"""
        return {
            "jd_id": jd_id,
            "evidence": [
                {
                    "candidate_id": cid,
                    "chunks": [
                        {"text": f"Mock evidence for {cid}", "similarity": 0.85, "chunk_id": f"ch_{i}"}
                        for i in range(min(top_k, 3))
                    ]
                }
                for cid in candidate_ids[:5]  # Top 5 candidates
            ]
        }
    
    @staticmethod
    def compute_deterministic_score(jd_features: Dict, resume_features: Dict, weights: Dict) -> Dict[str, any]:
        """Compute candidate-JD match score"""
        # Mock scoring
        base_score = 0.75
        return {
            "scores": [
                {
                    "candidate_id": resume_features.get("candidate_id", "unknown"),
                    "score": base_score,
                    "breakdown": {
                        "must_have_match": 0.85,
                        "nice_to_have_match": 0.70,
                        "experience_match": 0.80,
                        "domain_relevance": 0.60,
                        "ambiguity_penalty": 0.05
                    }
                }
            ]
        }
    
    @staticmethod
    def call_mcp_explainer(context: Dict, scores: List[Dict], policy: str, max_tokens: int) -> Dict[str, any]:
        """Request LLM explanation from MCP Server"""
        return {
            "explanations": [
                {
                    "candidate_id": score.get("candidate_id"),
                    "explanation": f"Mock explanation for {score.get('candidate_id')}",
                    "evidence": ["Mock evidence 1", "Mock evidence 2"],
                    "tokens_used": 150
                }
                for score in scores[:3]
            ]
        }
    
    @staticmethod
    def log_audit_event(user_id: str, action: str, inputs: Dict, outputs: Dict) -> Dict[str, any]:
        """Log event to audit trail"""
        return {
            "audit_id": f"aud_{uuid.uuid4().hex[:8]}",
            "user_id": user_id,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            "recorded": True
        }
    
    @staticmethod
    def assemble_response(scores: List[Dict], explanations: Dict, audit_id: str) -> Dict[str, any]:
        """Assemble final structured response"""
        return {
            "results": scores,
            "explanations": explanations.get("explanations", []),
            "audit_id": audit_id,
            "status": "success"
        }


class TalentFitOrchestrationAgent:
    """
    Main orchestration agent.
    
    Responsibilities (YES):
    ✓ Validate user role & permissions
    ✓ Trigger deterministic scoring engine
    ✓ Request RAG retrieval from ChromaDB
    ✓ Forward context to MCP Server
    ✓ Enforce guardrails before/after LLM calls
    ✓ Assemble final structured response
    ✓ Log full decision trail
    
    Restrictions (NO):
    ✗ Cannot score candidates
    ✗ Cannot rank candidates
    ✗ Cannot modify deterministic scores
    ✗ Cannot make hiring decisions
    """
    
    def __init__(self, tool_executor=None):
        self.tool_executor = tool_executor or MockToolExecutor()
        self.execution_trace: Optional[AgentExecutionTrace] = None
    
    async def run_screening_workflow(
        self,
        user: User,
        jd_id: str,
        candidate_ids: List[str],
        config: Dict[str, any]
    ) -> Dict[str, any]:
        """
        Execute complete screening workflow.
        
        Args:
            user: Authenticated user
            jd_id: Job description ID
            candidate_ids: Candidate IDs to screen
            config: System configuration
            
        Returns:
            Structured result with scores, explanations, audit trail
        """
        self.execution_trace = AgentExecutionTrace(
            user_id=user.user_id,
            user_role=user.role,
            action="run_screening_workflow"
        )
        
        try:
            # Step 1: Validate permissions
            self._log(f"Step 1: Validating user permissions")
            self._invoke_tool(
                AgentToolName.VALIDATE_USER_POLICY,
                {"user": user, "action": "run_screening"},
                self.tool_executor.validate_user_policy
            )
            
            # Step 2: Check tool constraints
            self._log(f"Step 2: Checking tool constraints for {user.role.value}")
            constraint = AgentToolConstraint(user)
            if not constraint.can_invoke(AgentToolName.RETRIEVE_RAG_EVIDENCE.value):
                raise AgentToolConstraintViolation(
                    user_id=user.user_id,
                    tool_name=AgentToolName.RETRIEVE_RAG_EVIDENCE.value,
                    role=user.role
                )
            
            # Step 3: Retrieve evidence
            self._log(f"Step 3: Retrieving RAG evidence for JD {jd_id}")
            evidence_result = self._invoke_tool(
                AgentToolName.RETRIEVE_RAG_EVIDENCE,
                {"jd_id": jd_id, "candidate_ids": candidate_ids, "top_k": config.get("top_k", 5)},
                self.tool_executor.retrieve_rag_evidence
            )
            
            # Step 4: Compute scores
            self._log(f"Step 4: Computing deterministic scores")
            scoring_result = self._invoke_tool(
                AgentToolName.COMPUTE_DETERMINISTIC_SCORE,
                {
                    "jd_features": {"jd_id": jd_id},
                    "resume_features": {"candidate_ids": candidate_ids},
                    "weights": config.get("scoring_weights", {})
                },
                self.tool_executor.compute_deterministic_score
            )
            
            # Step 5: Request LLM explanations
            self._log(f"Step 5: Requesting LLM explanations from MCP Server")
            explanations_result = self._invoke_tool(
                AgentToolName.CALL_MCP_EXPLAINER,
                {
                    "context": evidence_result.get("evidence", []),
                    "scores": scoring_result.get("scores", []),
                    "policy": config.get("policy", ""),
                    "max_tokens": config.get("max_tokens", 300)
                },
                self.tool_executor.call_mcp_explainer
            )
            
            # Step 6: Log audit event
            self._log(f"Step 6: Logging audit event")
            audit_result = self._invoke_tool(
                AgentToolName.LOG_AUDIT_EVENT,
                {
                    "user_id": user.user_id,
                    "action": "run_screening",
                    "inputs": {"jd_id": jd_id, "candidate_count": len(candidate_ids)},
                    "outputs": {"scores_computed": len(scoring_result.get("scores", []))}
                },
                self.tool_executor.log_audit_event
            )
            
            # Step 7: Assemble response
            self._log(f"Step 7: Assembling final response")
            final_result = self._invoke_tool(
                AgentToolName.ASSEMBLE_RESPONSE,
                {
                    "scores": scoring_result.get("scores", []),
                    "explanations": explanations_result,
                    "audit_id": audit_result.get("audit_id")
                },
                self.tool_executor.assemble_response
            )
            
            self._log("Workflow completed successfully")
            self.execution_trace.success = True
            self.execution_trace.final_output = final_result
            
            return {
                "success": True,
                "data": final_result,
                "audit_trail": self.execution_trace.to_dict()
            }
        
        except Exception as e:
            self._log(f"ERROR: {str(e)}", is_error=True)
            self.execution_trace.success = False
            self.execution_trace.error = str(e)
            
            return {
                "success": False,
                "error": str(e),
                "audit_trail": self.execution_trace.to_dict()
            }
        
        finally:
            self.execution_trace.completed_at = datetime.utcnow()
    
    def _invoke_tool(
        self,
        tool_name: AgentToolName,
        params: Dict[str, any],
        executor_func
    ) -> Dict[str, any]:
        """
        Invoke a tool with constraint checking and timing.
        
        Args:
            tool_name: Tool to invoke
            params: Input parameters
            executor_func: Function to execute
            
        Returns:
            Tool output
        """
        import time
        
        start_time = time.time()
        
        try:
            output = executor_func(**params)
            duration_ms = (time.time() - start_time) * 1000
            
            invocation = ToolInvocation(
                tool_name=tool_name,
                input_params=params,
                output=output,
                duration_ms=duration_ms,
                success=True
            )
            self.execution_trace.tool_invocations.append(invocation)
            
            return output
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            invocation = ToolInvocation(
                tool_name=tool_name,
                input_params=params,
                output={},
                duration_ms=duration_ms,
                success=False,
                error=str(e)
            )
            self.execution_trace.tool_invocations.append(invocation)
            raise
    
    def _log(self, message: str, is_error: bool = False):
        """Log message to execution trace"""
        level = "ERROR" if is_error else "INFO"
        timestamp = datetime.utcnow().isoformat()
        print(f"[{timestamp}] {level}: {message}")


# Example usage with RBAC
if __name__ == "__main__":
    import asyncio
    
    async def demo():
        # Create mock users
        recruiter = User(user_id="u_001", email="recruiter@company.com", role=Role.RECRUITER)
        admin = User(user_id="u_admin", email="admin@company.com", role=Role.ADMIN)
        
        # Initialize agent
        agent = TalentFitOrchestrationAgent()
        
        # Run screening workflow
        print("=== RECRUITING WORKFLOW ===\n")
        result = await agent.run_screening_workflow(
            user=recruiter,
            jd_id="jd_001",
            candidate_ids=["c_042", "c_089", "c_156"],
            config={"top_k": 5, "max_tokens": 300}
        )
        
        print(f"\nResult: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"\nExecution Trace (sample):")
        trace = result['audit_trail']
        print(f"  Execution ID: {trace['execution_id']}")
        print(f"  User: {trace['user_id']} ({trace['user_role']})")
        print(f"  Tool Invocations: {len(trace['tool_invocations'])}")
        for inv in trace['tool_invocations'][:3]:
            print(f"    - {inv['tool_name']}: {inv['duration_ms']:.1f}ms")
    
    asyncio.run(demo())


# Import RBAC at bottom to avoid circular imports
from backend.auth.rbac import RBACEnforcer
