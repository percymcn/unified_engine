"""
Billing utilities for Tradeflow
Feature gating and subscription limit enforcement with 4-tier pricing
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import NamedTuple

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User
from app.models.database_models import TradingAccount
from app.services.stripe_service import get_broker_limit as stripe_get_broker_limit


class SubscriptionLimits(NamedTuple):
    """Subscription tier limits"""
    tier: str
    max_broker_connections: int  # Based on tier (1, 2, 3, 4)
    max_signals_per_day: int  # -1 for unlimited on paid tiers
    max_webhooks: int  # -1 for unlimited on paid tiers


# 4-tier limit definitions
# Broker limits: tier_1=1, tier_2=2, tier_3=3, tier_4=4
TIER_LIMITS = {
    "free": SubscriptionLimits(
        tier="free",
        max_broker_connections=1,
        max_signals_per_day=50,
        max_webhooks=1,
    ),
    "tier_1": SubscriptionLimits(
        tier="tier_1",
        max_broker_connections=1,
        max_signals_per_day=-1,  # unlimited
        max_webhooks=-1,  # unlimited
    ),
    "tier_2": SubscriptionLimits(
        tier="tier_2",
        max_broker_connections=2,
        max_signals_per_day=-1,  # unlimited
        max_webhooks=-1,  # unlimited
    ),
    "tier_3": SubscriptionLimits(
        tier="tier_3",
        max_broker_connections=3,
        max_signals_per_day=-1,  # unlimited
        max_webhooks=-1,  # unlimited
    ),
    "tier_4": SubscriptionLimits(
        tier="tier_4",
        max_broker_connections=4,
        max_signals_per_day=-1,  # unlimited
        max_webhooks=-1,  # unlimited
    ),
    # Legacy "pro" tier for backward compatibility (maps to tier_3 limits)
    "pro": SubscriptionLimits(
        tier="pro",
        max_broker_connections=3,
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
    current_count = db.query(TradingAccount).filter(
        TradingAccount.user_id == user.id,
        TradingAccount.is_active == True
    ).count()

    can_add = current_count < limits.max_broker_connections
    return can_add, current_count, limits.max_broker_connections


def require_broker_slot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency that ensures user can add a broker connection.
    Raises 402 (Payment Required) if broker limit exceeded for tier.
    """
    can_add, current, max_allowed = check_broker_limit(current_user, db)

    if not can_add:
        tier = current_user.subscription_tier or "free"
        tier_name = _get_tier_display_name(tier)

        # Build upgrade message based on current tier
        if tier == "free":
            upgrade_message = "Upgrade to a paid plan for more broker connections."
        elif tier == "tier_4":
            upgrade_message = "You've reached the maximum broker limit for Enterprise tier."
        else:
            # Suggest next tier
            next_tier_limit = max_allowed + 1
            upgrade_message = f"Upgrade to add up to {next_tier_limit} broker connections."

        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "broker_limit_exceeded",
                "message": f"{tier_name} plan allows {max_allowed} broker connection(s). {upgrade_message}",
                "current": current,
                "limit": max_allowed,
                "tier": tier,
                "upgrade_url": "/pricing"
            }
        )

    return current_user


def _get_tier_display_name(tier: str) -> str:
    """Get display name for a tier"""
    names = {
        "free": "Free",
        "tier_1": "Starter",
        "tier_2": "Growth",
        "tier_3": "Pro",
        "tier_4": "Enterprise",
        "pro": "Pro",  # Legacy
    }
    return names.get(tier, "Free")


def get_subscription_info(user: User, db: Session) -> dict:
    """Get user's subscription info for display"""
    tier = user.subscription_tier or "free"
    limits = get_user_limits(user)
    _, broker_count, broker_limit = check_broker_limit(user, db)

    return {
        "tier": tier,
        "tier_name": _get_tier_display_name(tier),
        "status": user.subscription_status or "active",
        "limits": {
            "broker_connections": {
                "current": broker_count,
                "limit": broker_limit,
                "unlimited": False  # No tier has unlimited brokers in 4-tier model
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
        "can_add_broker": broker_count < broker_limit,
        "at_broker_limit": broker_count >= broker_limit,
    }
