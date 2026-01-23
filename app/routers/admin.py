"""
Admin Router for Owner-Only Admin Dashboard
Protected by email allowlist and authentication
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User
from app.core.config import settings
from app.services.stripe_service import PRICING_TIERS, get_all_tiers

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
