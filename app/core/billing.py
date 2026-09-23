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
# Tier aliases: starter=tier_1, trader=tier_2, pro=tier_3, enterprise=tier_4
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
    # Tier aliases (display names used in UI)
    "starter": SubscriptionLimits(
        tier="starter",
        max_broker_connections=1,
        max_signals_per_day=-1,  # unlimited
        max_webhooks=-1,  # unlimited
    ),
    "trader": SubscriptionLimits(
        tier="trader",
        max_broker_connections=2,
        max_signals_per_day=-1,  # unlimited
        max_webhooks=-1,  # unlimited
    ),
    "pro": SubscriptionLimits(
        tier="pro",
        max_broker_connections=3,
        max_signals_per_day=-1,  # unlimited
        max_webhooks=-1,  # unlimited
    ),
    "enterprise": SubscriptionLimits(
        tier="enterprise",
        max_broker_connections=-1,  # unlimited for enterprise
        max_signals_per_day=-1,  # unlimited
        max_webhooks=-1,  # unlimited
    ),
}


# Canonical ids used by feature gates. Display aliases and tier_N ids compare equal.
_TIER_CANONICAL = {
    "free": "free",
    "free_user": "free",
    "basic": "free",
    "starter": "tier_1",
    "tier_1": "tier_1",
    "tier1": "tier_1",
    "trader": "tier_2",
    "tier_2": "tier_2",
    "tier2": "tier_2",
    "pro": "tier_3",
    "tier_3": "tier_3",
    "tier3": "tier_3",
    "enterprise": "tier_4",
    "tier_4": "tier_4",
    "tier4": "tier_4",
}

_TIER_LEVELS = {
    "free": 0,
    "tier_1": 1,
    "tier_2": 2,
    "tier_3": 3,
    "tier_4": 4,
}


def normalize_tier_id(tier: str | None) -> str:
    """Fold enterprise/tier_4 (and the other aliases) onto free|tier_1..tier_4.

    Unknown, blank, and mixed-case values become ``free`` so the free gate
    stays closed. ``enterprise`` and ``tier_4`` both become ``tier_4``.
    """
    if tier is None:
        return "free"
    key = str(tier).strip().lower().replace("-", "_").replace(" ", "_")
    return _TIER_CANONICAL.get(key, "free")


def tier_level(tier: str | None) -> int:
    """Numeric rank for gate comparisons. Free is 0, Enterprise/tier_4 is 4."""
    return _TIER_LEVELS.get(normalize_tier_id(tier), 0)


def is_free_tier(tier: str | None) -> bool:
    return normalize_tier_id(tier) == "free"


def is_enterprise_tier(tier: str | None) -> bool:
    return normalize_tier_id(tier) == "tier_4"


def get_tier_limits(tier: str) -> SubscriptionLimits:
    """Get limits for a subscription tier.

    Case and aliases are accepted. Broker caps stay on the stored row when
    that row exists (``enterprise`` is unlimited, ``tier_4`` is 4) so this
    does not change a plan's connection count. Unknown ids use free limits.
    """
    if not tier:
        return TIER_LIMITS["free"]
    direct = TIER_LIMITS.get(str(tier).strip().lower())
    if direct is not None:
        return direct
    canonical = normalize_tier_id(tier)
    return TIER_LIMITS.get(canonical, TIER_LIMITS["free"])


def get_user_limits(user: User) -> SubscriptionLimits:
    """Get current user's subscription limits"""
    tier = user.subscription_tier or "free"

    # If subscription is not active, use free limits
    if user.subscription_status not in ["active", "trialing", "canceling"]:
        tier = "free"

    # Case-fold and alias lookup happen in get_tier_limits. Pass the stored
    # id through so "enterprise" keeps its row and "tier_4" keeps its row.
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
        tier = normalize_tier_id(current_user.subscription_tier)
        tier_name = _get_tier_display_name(tier)

        # Build upgrade message based on current tier
        if is_free_tier(tier):
            upgrade_message = "Upgrade to a paid plan for more broker connections."
        elif is_enterprise_tier(tier):
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
    """Get display name for a tier. enterprise and tier_4 are both Enterprise."""
    names = {
        "free": "Free",
        "tier_1": "Starter",
        "tier_2": "Growth",
        "tier_3": "Pro",
        "tier_4": "Enterprise",
    }
    return names.get(normalize_tier_id(tier), "Free")


def get_subscription_info(user: User, db: Session) -> dict:
    """Get user's subscription info for display"""
    tier = normalize_tier_id(user.subscription_tier)
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
