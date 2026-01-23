"""
Admin Router for Owner-Only Admin Dashboard
Protected by email allowlist and authentication
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import os

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User
from app.core.config import settings
from app.services.stripe_service import PRICING_TIERS, get_all_tiers

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def redact_secret(value: Optional[str]) -> str:
    """Redact secret value (show first 6 + last 4 chars)"""
    if not value:
        return "(empty)"
    if len(value) <= 10:
        return "***REDACTED***"
    return f"{value[:6]}...{value[-4:]}"


def check_broker_config(broker_name: str, required_vars: List[str]) -> Dict[str, Any]:
    """Check broker configuration status"""
    missing = []
    present = []
    values = {}
    
    for var in required_vars:
        value = getattr(settings, var, None) or os.getenv(var)
        if not value or value in ("", "None", f"your-{var.lower()}"):
            missing.append(var)
        else:
            present.append(var)
            values[var] = redact_secret(str(value))
    
    if len(missing) == len(required_vars):
        status = "DISABLED"
    elif len(missing) == 0:
        status = "CONFIGURED"
    else:
        status = "PARTIAL"
    
    return {
        "status": status,
        "missing_vars": missing,
        "present_vars": present,
        "values": values
    }

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/overview")
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get admin dashboard overview (owner-only)"""
    check_owner_access(current_user)
    
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    verified_users = db.query(User).filter(User.is_verified == True).count()
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "verified": verified_users,
        },
        "plans_configured": len(PRICING_TIERS),
        "stripe_configured": bool(settings.STRIPE_SECRET_KEY),
    }


def check_owner_access(current_user: User) -> None:
    """Check if user is in owner admin allowlist"""
    owner_emails = settings.OWNER_ADMIN_EMAILS
    if not owner_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access not configured"
        )
    
    allowed_emails = [email.strip().lower() for email in owner_emails.split(",") if email.strip()]
    if current_user.email.lower() not in allowed_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Owner-only area."
        )


class UserInfo(BaseModel):
    id: int
    email: str
    username: str
    full_name: str | None
    role: str
    subscription_tier: str
    subscription_status: str | None
    is_active: bool
    is_verified: bool
    created_at: str
    last_login: str | None


class PlanConfig(BaseModel):
    tier_id: str
    name: str
    monthly_price: int
    price_display: str
    brokers: int
    stripe_price_id: str | None
    features: List[str]


@router.get("/users")
async def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> Dict[str, Any]:
    """List all users (owner-only)"""
    check_owner_access(current_user)
    
    users = db.query(User).offset(skip).limit(limit).all()
    total = db.query(User).count()
    
    return {
        "users": [
            UserInfo(
                id=u.id,
                email=u.email,
                username=u.username,
                full_name=u.full_name,
                role=u.role or "free_user",
                subscription_tier=u.subscription_tier.value if u.subscription_tier else "free",
                subscription_status=u.subscription_status,
                is_active=u.is_active,
                is_verified=u.is_verified,
                created_at=u.created_at.isoformat() if u.created_at else "",
                last_login=u.last_login.isoformat() if u.last_login else None,
            ).model_dump()
            for u in users
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserInfo:
    """Get user details (owner-only)"""
    check_owner_access(current_user)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserInfo(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role or "free_user",
        subscription_tier=user.subscription_tier.value if user.subscription_tier else "free",
        subscription_status=user.subscription_status,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat() if user.created_at else "",
        last_login=user.last_login.isoformat() if user.last_login else None,
    )


@router.patch("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Toggle user active status (owner-only)"""
    check_owner_access(current_user)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "message": f"User {'activated' if user.is_active else 'deactivated'}"
    }


@router.patch("/users/{user_id}/set-tier")
async def set_user_tier(
    user_id: int,
    tier: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Set user subscription tier (owner-only)"""
    check_owner_access(current_user)
    
    from app.models.enhanced_models import SubscriptionTier
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        tier_enum = SubscriptionTier(tier)
        user.subscription_tier = tier_enum
        db.commit()
        db.refresh(user)
        
        return {
            "id": user.id,
            "email": user.email,
            "subscription_tier": tier,
            "message": f"User tier set to {tier}"
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}")


@router.post("/users/{user_id}/reset-password-link")
async def generate_reset_password_link(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Generate password reset link for user (owner-only)"""
    check_owner_access(current_user)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate reset token (simplified - in production, use proper token generation)
    from app.routers.auth import create_access_token
    from datetime import timedelta
    
    reset_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "type": "password_reset"},
        expires_delta=timedelta(hours=24)
    )
    
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    
    return {
        "user_id": user.id,
        "email": user.email,
        "reset_url": reset_url,
        "message": "Password reset link generated (valid for 24 hours)"
    }


@router.get("/plans")
async def get_plan_config(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get pricing plan configuration (owner-only)"""
    check_owner_access(current_user)
    
    tiers = get_all_tiers()
    
    plans = []
    for tier in tiers:
        tier_id = tier.get("tier_id", "free")
        plans.append(PlanConfig(
            tier_id=tier_id,
            name=tier["name"],
            monthly_price=tier["price"],
            price_display=f"${tier['price']/100:.2f}/month",
            brokers=tier["brokers"],
            stripe_price_id=tier.get("stripe_price_id"),
            features=tier["features"],
        ).model_dump())
    
    return {
        "plans": plans,
        "source": "backend PRICING_TIERS",
        "stripe_configured": bool(settings.STRIPE_SECRET_KEY),
    }


@router.get("/system/env-doctor")
async def get_env_doctor(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get ENV doctor diagnostics (owner-only)"""
    check_owner_access(current_user)
    
    # Check database
    db_info = {}
    if settings.DATABASE_URL:
        if "sqlite" in settings.DATABASE_URL.lower():
            db_file = settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
            import os
            if os.path.exists(db_file):
                import os.path
                size = os.path.getsize(db_file)
                db_info = {
                    "type": "SQLite",
                    "path": db_file,
                    "size_bytes": size,
                    "exists": True
                }
            else:
                db_info = {
                    "type": "SQLite",
                    "path": db_file,
                    "exists": False
                }
        else:
            # PostgreSQL
            db_info = {
                "type": "PostgreSQL",
                "url": settings.DATABASE_URL.split("@")[-1].split("/")[0] if "@" in settings.DATABASE_URL else "unknown",
                "exists": True
            }
    
    # Check brokers
    brokers = {}
    
    # MT4/MT5 MetaAPI SDK
    brokers["mt4_sdk"] = check_broker_config("mt4_sdk", ["METAAPI_TOKEN", "METAAPI_ACCOUNT_ID"])
    brokers["mt4_manager"] = check_broker_config("mt4_manager", [
        "MT4_MANAGER_LOGIN", "MT4_MANAGER_PASSWORD", "MT4_MANAGER_HOST", "MT4_MANAGER_PORT"
    ])
    brokers["mt5_sdk"] = check_broker_config("mt5_sdk", ["METAAPI_TOKEN", "METAAPI_ACCOUNT_ID"])
    brokers["mt5_manager"] = check_broker_config("mt5_manager", [
        "MT5_MANAGER_LOGIN", "MT5_MANAGER_PASSWORD", "MT5_MANAGER_HOST", "MT5_MANAGER_PORT"
    ])
    
    # TradeLocker
    brokers["tradelocker_sdk"] = check_broker_config("tradelocker_sdk", [
        "TRADELOCKER_USERNAME", "TRADELOCKER_PASSWORD", "TRADELOCKER_SERVER"
    ])
    brokers["tradelocker_brand"] = check_broker_config("tradelocker_brand", ["TRADELOCKER_API_KEY"])
    
    # Tradovate
    brokers["tradovate_oauth"] = check_broker_config("tradovate_oauth", [
        "TRADOVATE_CLIENT_ID", "TRADOVATE_CLIENT_SECRET"
    ])
    brokers["tradovate_password"] = check_broker_config("tradovate_password", [
        "TRADOVATE_USER_ID", "TRADOVATE_PASSWORD"
    ])
    
    # ProjectX
    brokers["projectx_sdk"] = check_broker_config("projectx_sdk", [
        "PROJECT_X_USERNAME", "PROJECT_X_API_KEY"
    ])
    brokers["projectx_legacy"] = check_broker_config("projectx_legacy", ["PROJECTX_API_TOKEN"])
    
    # OAuth
    oauth_status = {
        "google": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_ID != "your-google-client-id"),
        "github": bool(settings.GITHUB_CLIENT_ID),
        "microsoft": bool(settings.MICROSOFT_CLIENT_ID)
    }
    
    return {
        "database": db_info,
        "brokers": brokers,
        "oauth": oauth_status,
        "backend_port": settings.PORT,
        "backend_host": settings.HOST
    }
