"""
Role-Based Access Control (RBAC) System

Enforces permission checks at API and agent levels.
All unauthorized actions are blocked server-side with audit logging.
"""

from enum import Enum
from typing import Set, List, Optional
from dataclasses import dataclass
from datetime import datetime


class Role(Enum):
    """System roles with strict boundaries"""
    
    ADMIN = "admin"           # System configuration, user management
    RECRUITER = "recruiter"   # Upload docs, run screenings
    HIRING_MANAGER = "hiring_manager"  # Review results, suggest interviews
    AUDITOR = "auditor"       # Read-only access, compliance review


@dataclass
class User:
    """User model with role claims"""
    user_id: str
    email: str
    role: Role
    is_active: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class Permission(Enum):
    """Granular permissions mapped to API actions"""
    
    # Upload & Data Management
    UPLOAD_DOCUMENTS = "upload:documents"      # Upload JDs/resumes
    DELETE_DOCUMENTS = "delete:documents"      # Remove documents
    
    # Configuration
    VIEW_CONFIG = "config:view"                # View system config
    EDIT_CONFIG = "config:edit"                # Modify LLM/scoring settings
    
    # Screening
    RUN_SCREENING = "screening:run"            # Execute screening
    VIEW_SCREENING_RESULTS = "screening:view"  # View results
    DELETE_SCREENING = "screening:delete"      # Remove screening
    
    # Audit & Compliance
    VIEW_AUDIT_LOGS = "audit:view"             # View audit trail
    VIEW_TOKEN_USAGE = "usage:view"            # View cost dashboard
    
    # User Management (Admin only)
    MANAGE_USERS = "users:manage"              # Invite/remove users
    CHANGE_ROLE = "users:change_role"          # Promote/demote users


# Role → Permissions Mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        Permission.UPLOAD_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.VIEW_CONFIG,
        Permission.EDIT_CONFIG,
        Permission.RUN_SCREENING,
        Permission.VIEW_SCREENING_RESULTS,
        Permission.DELETE_SCREENING,
        Permission.VIEW_AUDIT_LOGS,
        Permission.VIEW_TOKEN_USAGE,
        Permission.MANAGE_USERS,
        Permission.CHANGE_ROLE,
    },
    Role.RECRUITER: {
        Permission.UPLOAD_DOCUMENTS,
        Permission.RUN_SCREENING,
        Permission.VIEW_SCREENING_RESULTS,
    },
    Role.HIRING_MANAGER: {
        Permission.VIEW_SCREENING_RESULTS,
    },
    Role.AUDITOR: {
        Permission.VIEW_AUDIT_LOGS,
        Permission.VIEW_TOKEN_USAGE,
    },
}


class RBACEnforcer:
    """
    Central RBAC enforcement engine.
    
    Used at three levels:
    1. FastAPI middleware - HTTP request filtering
    2. API route decorators - Endpoint permission checks
    3. Agent tools - Tool invocation constraints
    """
    
    def __init__(self):
        self.role_permissions = ROLE_PERMISSIONS
    
    def has_permission(self, user: User, permission: Permission) -> bool:
        """
        Check if user has specific permission.
        
        Args:
            user: User object with role
            permission: Required permission
            
        Returns:
            True if permitted, False otherwise
        """
        if not user.is_active:
            return False
        
        user_permissions = self.role_permissions.get(user.role, set())
        return permission in user_permissions
    
    def has_any_permission(self, user: User, permissions: List[Permission]) -> bool:
        """
        Check if user has ANY of the permissions (OR logic).
        
        Args:
            user: User object
            permissions: List of acceptable permissions
            
        Returns:
            True if user has at least one permission
        """
        return any(self.has_permission(user, perm) for perm in permissions)
    
    def has_all_permissions(self, user: User, permissions: List[Permission]) -> bool:
        """
        Check if user has ALL permissions (AND logic).
        
        Args:
            user: User object
            permissions: List of required permissions
            
        Returns:
            True if user has all permissions
        """
        return all(self.has_permission(user, perm) for perm in permissions)
    
    def get_user_capabilities(self, user: User) -> dict[str, bool]:
        """
        Get all capabilities for a user (for UI rendering).
        
        Args:
            user: User object
            
        Returns:
            Dict mapping action → capability
        """
        permissions = self.role_permissions.get(user.role, set())
        
        return {
            "can_upload": Permission.UPLOAD_DOCUMENTS in permissions,
            "can_delete_docs": Permission.DELETE_DOCUMENTS in permissions,
            "can_edit_config": Permission.EDIT_CONFIG in permissions,
            "can_run_screening": Permission.RUN_SCREENING in permissions,
            "can_view_results": Permission.VIEW_SCREENING_RESULTS in permissions,
            "can_delete_screening": Permission.DELETE_SCREENING in permissions,
            "can_view_audit": Permission.VIEW_AUDIT_LOGS in permissions,
            "can_view_usage": Permission.VIEW_TOKEN_USAGE in permissions,
            "can_manage_users": Permission.MANAGE_USERS in permissions,
        }


class RBACViolation(Exception):
    """Raised when RBAC check fails"""
    
    def __init__(self, user_id: str, permission: Permission, action: str):
        self.user_id = user_id
        self.permission = permission
        self.action = action
        super().__init__(
            f"User {user_id} denied access: requires {permission.value} for {action}"
        )


# API Route Protection Decorator
def require_permission(permission: Permission):
    """
    Decorator for FastAPI routes requiring specific permission.
    
    Usage:
        @app.post("/screen/run")
        @require_permission(Permission.RUN_SCREENING)
        async def run_screening(request: ScreeningRequest, user: User):
            ...
    """
    def decorator(func):
        async def wrapper(*args, user: User = None, **kwargs):
            enforcer = RBACEnforcer()
            if not enforcer.has_permission(user, permission):
                raise RBACViolation(
                    user_id=user.user_id,
                    permission=permission,
                    action=func.__name__
                )
            return await func(*args, user=user, **kwargs)
        return wrapper
    return decorator


# Agent Tool Constraint Example
class AgentToolConstraint:
    """
    Defines which tools an agent tool can invoke based on user role.
    
    Example:
        tool_constraint = AgentToolConstraint(recruiter_user)
        if tool_constraint.can_invoke("compute_score"):
            # Invoke scoring tool
    """
    
    # Tool → Required Permissions Mapping
    TOOL_PERMISSIONS = {
        "validate_user_policy": {Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER, Role.AUDITOR},
        "retrieve_rag_evidence": {Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER},
        "compute_deterministic_score": {Role.ADMIN, Role.RECRUITER},
        "call_mcp_explainer": {Role.ADMIN, Role.RECRUITER},
        "log_audit_event": {Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER, Role.AUDITOR},
        "assemble_response": {Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER},
    }
    
    def __init__(self, user: User):
        self.user = user
    
    def can_invoke(self, tool_name: str) -> bool:
        """
        Check if user can invoke specific agent tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if permitted
        """
        allowed_roles = self.TOOL_PERMISSIONS.get(tool_name, set())
        return self.user.role in allowed_roles
    
    def get_allowed_tools(self) -> List[str]:
        """Get all tools available to user"""
        return [
            tool for tool, allowed_roles in self.TOOL_PERMISSIONS.items()
            if self.user.role in allowed_roles
        ]


# Example usage
if __name__ == "__main__":
    enforcer = RBACEnforcer()
    
    # Create users
    recruiter = User(user_id="u_001", email="alice@company.com", role=Role.RECRUITER)
    admin = User(user_id="u_admin", email="admin@company.com", role=Role.ADMIN)
    auditor = User(user_id="u_audit", email="auditor@company.com", role=Role.AUDITOR)
    
    # Test permissions
    print("Recruiter can upload:", enforcer.has_permission(recruiter, Permission.UPLOAD_DOCUMENTS))
    print("Recruiter can edit config:", enforcer.has_permission(recruiter, Permission.EDIT_CONFIG))
    print("Admin can edit config:", enforcer.has_permission(admin, Permission.EDIT_CONFIG))
    print("Auditor can run screening:", enforcer.has_permission(auditor, Permission.RUN_SCREENING))
    
    # Get capabilities for UI
    print("\nRecruiter capabilities:")
    for action, capability in enforcer.get_user_capabilities(recruiter).items():
        if capability:
            print(f"  ✓ {action}")
    
    # Agent tool constraints
    tool_constraint = AgentToolConstraint(recruiter)
    print("\nAgent tools available to recruiter:", tool_constraint.get_allowed_tools())
