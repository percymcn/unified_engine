"""
Billing utilities for Tradeflow
Feature gating and subscription limit enforcement
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import NamedTuple

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User, Account


class SubscriptionLimits(NamedTuple):
    """Subscription tier limits"""
    tier: str
    max_broker_connections: int  # -1 for unlimited
    max_signals_per_day: int  # -1 for unlimited
    max_webhooks: int  # -1 for unlimited


# Tier limit definitions
TIER_LIMITS = {
    "free": SubscriptionLimits(
        tier="free",
        max_broker_connections=1,
        max_signals_per_day=50,
        max_webhooks=1,
    ),
    "pro": SubscriptionLimits(
        tier="pro",
        max_broker_connections=-1,  # unlimited
        max_signals_per_day=-1,  # unlimited
        max_webhooks=-1,  # unlimited
    ),
}


def get_tier_limits(tier: str) -> SubscriptionLimits:
    """Get limits for a subscription tier"""
    return TIER_LIMITS.get(tier, TIER_LIMITS["free"])


def get_user_limits(user: User) -> SubscriptionLimits:
    """Get current user's subscription limits"""
    tier = user.subscription_tier or "free"

    # If subscription is not active, use free limits
    if user.subscription_status not in ["active", "trialing", "canceling"]:
        tier = "free"

    return get_tier_limits(tier)


def check_broker_limit(
    user: User,
    db: Session
) -> tuple[bool, int, int]:
    """
    Check if user can add more broker connections.

    Returns:
        (can_add, current_count, max_allowed)
    """
    limits = get_user_limits(user)

    # Unlimited
    if limits.max_broker_connections == -1:
        return True, 0, -1

    # Count current broker connections
    current_count = db.query(Account).filter(
        Account.user_id == user.id,
        Account.is_active == True
    ).count()

    can_add = current_count < limits.max_broker_connections
    return can_add, current_count, limits.max_broker_connections


def require_broker_slot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency that ensures user can add a broker connection.
    Raises 403 if limit exceeded.
    """
    can_add, current, max_allowed = check_broker_limit(current_user, db)

    if not can_add:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "broker_limit_exceeded",
                "message": f"Free plan allows {max_allowed} broker connection. Upgrade to Pro for unlimited.",
                "current": current,
                "limit": max_allowed,
                "upgrade_url": "/pricing"
            }
        )

    return current_user


def get_subscription_info(user: User, db: Session) -> dict:
    """Get user's subscription info for display"""
    limits = get_user_limits(user)
    _, broker_count, broker_limit = check_broker_limit(user, db)

    return {
        "tier": user.subscription_tier or "free",
        "status": user.subscription_status or "active",
        "limits": {
            "broker_connections": {
                "current": broker_count,
                "limit": broker_limit,
                "unlimited": broker_limit == -1
            },
            "signals_per_day": {
                "limit": limits.max_signals_per_day,
                "unlimited": limits.max_signals_per_day == -1
            },
            "webhooks": {
                "limit": limits.max_webhooks,
                "unlimited": limits.max_webhooks == -1
            }
        },
        "can_add_broker": broker_limit == -1 or broker_count < broker_limit
    }
