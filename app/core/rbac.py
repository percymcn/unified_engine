"""
Role-Based Access Control (RBAC) System
Provides permission checking and role management
"""
from functools import wraps
from typing import List, Optional
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import User
from app.models.enhanced_models import Role, Permission
from app.routers.auth import get_current_user

# Permission constants
PERMISSIONS = {
    # Account permissions
    "accounts:read": "Read accounts",
    "accounts:write": "Create/update accounts",
    "accounts:delete": "Delete accounts",
    "accounts:manage": "Full account management",
    
    # User permissions
    "users:read": "Read users",
    "users:write": "Create/update users",
    "users:delete": "Delete users",
    "users:manage": "Full user management",
    
    # Signal permissions
    "signals:read": "Read signals",
    "signals:write": "Create signals",
    "signals:execute": "Execute signals",
    "signals:manage": "Full signal management",
    
    # Trade permissions
    "trades:read": "Read trades",
    "trades:write": "Create trades",
    "trades:manage": "Full trade management",
    
    # Position permissions
    "positions:read": "Read positions",
    "positions:write": "Create/update positions",
    "positions:close": "Close positions",
    
    # Strategy permissions
    "strategies:read": "Read strategies",
    "strategies:write": "Create/update strategies",
    "strategies:execute": "Execute strategies",
    "strategies:manage": "Full strategy management",
    
    # Admin permissions
    "admin:read": "Read admin data",
    "admin:write": "Write admin data",
    "admin:manage": "Full admin access",
    
    # Organization permissions
    "org:read": "Read organization data",
    "org:write": "Update organization",
    "org:manage": "Full organization management",
    "org:billing": "Manage organization billing",
}

# Role definitions with permissions
ROLE_PERMISSIONS = {
    "super_admin": [
        "*"  # All permissions
    ],
    "admin": [
        "accounts:*",
        "users:read",
        "users:write",
        "signals:*",
        "trades:*",
        "positions:*",
        "strategies:*",
        "org:read",
        "org:write",
    ],
    "premium_user": [
        "accounts:read",
        "accounts:write",
        "signals:read",
        "signals:write",
        "signals:execute",
        "trades:read",
        "trades:write",
        "positions:read",
        "positions:write",
        "positions:close",
        "strategies:read",
        "strategies:write",
        "strategies:execute",
        "org:read",
    ],
    "free_user": [
        "accounts:read",
        "accounts:write",  # Limited to 1 account
        "signals:read",
        "signals:write",  # Limited
        "trades:read",
        "positions:read",
        "strategies:read",
    ],
}

def check_permission(permission: str):
    """
    Decorator to check if user has required permission
    Usage:
        @router.get("/accounts")
        @check_permission("accounts:read")
        async def get_accounts(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current_user from kwargs or dependencies
            current_user = None
            db = None
            
            # Try to get from kwargs
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            elif 'db' in kwargs:
                db = kwargs['db']
            
            # If not found, try to get from dependencies
            if not current_user:
                # This will be resolved by FastAPI's dependency injection
                pass
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not has_permission(current_user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def has_permission(user: User, permission: str) -> bool:
    """Check if user has a specific permission"""
    if not user or not user.is_active:
        return False
    
    # Super admin has all permissions
    if user.role == "super_admin":
        return True
    
    # Get role permissions
    role_perms = ROLE_PERMISSIONS.get(user.role, [])
    
    # Check for wildcard permission
    if "*" in role_perms:
        return True
    
    # Check exact permission
    if permission in role_perms:
        return True
    
    # Check wildcard permissions (e.g., "accounts:*" matches "accounts:read")
    resource, action = permission.split(":", 1) if ":" in permission else (permission, "")
    wildcard_permission = f"{resource}:*"
    if wildcard_permission in role_perms:
        return True
    
    return False

def require_role(*roles: str):
    """
    Dependency to require specific role(s)
    Usage:
        @router.get("/admin")
        async def admin_endpoint(current_user: User = Depends(require_role("admin", "super_admin"))):
            ...
    """
    def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {', '.join(roles)}"
            )
        
        return current_user
    
    return role_checker

def require_permission(permission: str):
    """
    Dependency to require specific permission
    Usage:
        @router.get("/accounts")
        async def get_accounts(current_user: User = Depends(require_permission("accounts:read"))):
            ...
    """
    def permission_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}"
            )
        return current_user
    
    return permission_checker

def get_user_permissions(user: User) -> List[str]:
    """Get all permissions for a user"""
    if not user or not user.is_active:
        return []
    
    if user.role == "super_admin":
        return list(PERMISSIONS.keys())
    
    return ROLE_PERMISSIONS.get(user.role, [])

async def initialize_default_roles(db: Session):
    """Initialize default roles and permissions in database"""
    # Create permissions
    for perm_name, perm_desc in PERMISSIONS.items():
        existing = db.query(Permission).filter(Permission.name == perm_name).first()
        if not existing:
            resource, action = perm_name.split(":", 1) if ":" in perm_name else (perm_name, "")
            perm = Permission(
                name=perm_name,
                resource=resource,
                action=action,
                description=perm_desc
            )
            db.add(perm)
    
    db.commit()
    
    # Create roles
    for role_name, permissions in ROLE_PERMISSIONS.items():
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            role = Role(
                name=role_name,
                description=f"Default {role_name} role",
                is_system_role=True
            )
            db.add(role)
            db.flush()
        
        # Assign permissions to role
        if "*" in permissions:
            # Super admin gets all permissions
            all_perms = db.query(Permission).all()
            role.permissions = all_perms
        else:
            role_perms = []
            for perm_name in permissions:
                if perm_name.endswith("*"):
                    # Wildcard permission
                    resource = perm_name.split(":")[0]
                    perms = db.query(Permission).filter(Permission.resource == resource).all()
                    role_perms.extend(perms)
                else:
                    perm = db.query(Permission).filter(Permission.name == perm_name).first()
                    if perm:
                        role_perms.append(perm)
            
            role.permissions = list(set(role_perms))
    
    db.commit()
