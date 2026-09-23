"""Canonical subscription tier ids shared by billing and feature gates."""

from typing import Any, Optional

# Stored product ids and legacy labels that mean the same plan.
_CANONICAL_TIERS = {
    "free": "free",
    "basic": "free",
    "tier_1": "tier_1",
    "starter": "tier_1",
    "tier_2": "tier_2",
    "growth": "tier_2",
    "standard": "tier_2",
    "tier_3": "tier_3",
    "pro": "tier_3",
    "premium": "tier_3",
    "tier_4": "tier_4",
    "enterprise": "tier_4",
}


def canonical_tier_id(raw: Optional[Any]) -> str:
    """
    Normalize a tier id to free, tier_1, tier_2, tier_3, or tier_4.

    enterprise and tier_4 are the same plan. basic and free are the same plan.
    Unknown values are treated as free so a missing plan cannot unlock paid limits.
    """
    if raw is None:
        return "free"
    value = getattr(raw, "value", raw)
    key = str(value).strip().lower()
    return _CANONICAL_TIERS.get(key, "free")


def legacy_subscription_tier(raw: Optional[Any]) -> str:
    """
    Map a canonical tier onto the older FREE / PREMIUM / ENTERPRISE feature enum.

    tier_4 and enterprise unlock enterprise features. free and basic stay free.
    Other paid tiers use the premium feature set.
    """
    canonical = canonical_tier_id(raw)
    if canonical == "tier_4":
        return "enterprise"
    if canonical == "free":
        return "free"
    return "premium"
