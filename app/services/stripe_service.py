"""
Stripe Service for Tradeflow
Handles all Stripe API interactions with 4-tier pricing structure
"""
import stripe
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Stripe with API key
stripe.api_key = settings.STRIPE_SECRET_KEY

# 4-tier pricing structure
# Each tier has: name, price (cents), broker limit, stripe_price_id, and features
PRICING_TIERS = {
    "tier_1": {
        "name": "Starter",
        "price": 1999,  # $19.99/month
        "brokers": 1,
        "stripe_price_id": "price_tier1_monthly",
        "features": [
            "1 broker connection",
            "Basic signal routing",
            "Email support",
            "Dashboard analytics",
        ],
    },
    "tier_2": {
        "name": "Growth",
        "price": 3999,  # $39.99/month
        "brokers": 2,
        "stripe_price_id": "price_tier2_monthly",
        "features": [
            "2 broker connections",
            "Advanced signal routing",
            "Priority email support",
            "Dashboard analytics",
            "Symbol mapping",
        ],
    },
    "tier_3": {
        "name": "Pro",
        "price": 6999,  # $69.99/month
        "brokers": 3,
        "stripe_price_id": "price_tier3_monthly",
        "features": [
            "3 broker connections",
            "Advanced signal routing",
            "Priority support",
            "Dashboard analytics",
            "Symbol mapping",
            "Risk management",
            "Position sizing",
        ],
    },
    "tier_4": {
        "name": "Enterprise",
        "price": 12999,  # $129.99/month
        "brokers": 4,
        "stripe_price_id": "price_tier4_monthly",
        "features": [
            "4 broker connections",
            "Advanced signal routing",
            "Priority phone support",
            "Dashboard analytics",
            "Symbol mapping",
            "Risk management",
            "Position sizing",
            "Multi-account routing",
            "Custom integrations",
        ],
    },
}

# Free tier configuration (not in PRICING_TIERS as it's not purchasable)
FREE_TIER = {
    "name": "Free",
    "price": 0,
    "brokers": 1,
    "stripe_price_id": None,
    "features": [
        "1 broker connection",
        "Basic signal routing",
        "Community support",
    ],
}

# Legacy product/price configuration (for backward compatibility)
STRIPE_PRICES = {
    "pro_monthly": settings.STRIPE_PRO_PRICE_ID,  # Legacy $29/mo
}


def get_tier_by_broker_count(broker_count: int) -> Optional[str]:
    """
    Get the minimum tier required for a given broker count.

    Args:
        broker_count: Number of brokers needed

    Returns:
        tier_id (e.g., 'tier_1', 'tier_2') or None if no tier supports that many brokers
    """
    for tier_id in ["tier_1", "tier_2", "tier_3", "tier_4"]:
        if PRICING_TIERS[tier_id]["brokers"] >= broker_count:
            return tier_id
    return None  # More than 4 brokers not supported


def get_broker_limit(tier: str) -> int:
    """
    Get the maximum number of brokers allowed for a tier.

    Args:
        tier: Tier ID ('free', 'tier_1', 'tier_2', 'tier_3', 'tier_4')

    Returns:
        Maximum brokers allowed (1-4)
    """
    if tier == "free":
        return FREE_TIER["brokers"]
    if tier in PRICING_TIERS:
        return PRICING_TIERS[tier]["brokers"]
    # Legacy "pro" tier maps to tier_4 (unlimited-ish, 4 brokers)
    if tier == "pro":
        return PRICING_TIERS["tier_4"]["brokers"]
    # Default to free tier limit
    return FREE_TIER["brokers"]


def get_tier_info(tier: str) -> Dict[str, Any]:
    """
    Get full tier information including name, price, and features.

    Args:
        tier: Tier ID ('free', 'tier_1', 'tier_2', 'tier_3', 'tier_4')

    Returns:
        Dict with tier details
    """
    if tier == "free":
        return FREE_TIER.copy()
    if tier in PRICING_TIERS:
        return PRICING_TIERS[tier].copy()
    # Legacy "pro" tier maps to tier_3
    if tier == "pro":
        return PRICING_TIERS["tier_3"].copy()
    return FREE_TIER.copy()


def get_all_tiers() -> List[Dict[str, Any]]:
    """
    Get all available tiers for display in pricing UI.

    Returns:
        List of tier info dicts with tier_id included
    """
    tiers = []

    # Add free tier
    free = FREE_TIER.copy()
    free["tier_id"] = "free"
    tiers.append(free)

    # Add paid tiers
    for tier_id, tier_info in PRICING_TIERS.items():
        tier = tier_info.copy()
        tier["tier_id"] = tier_id
        tiers.append(tier)

    return tiers


def sync_prices_from_stripe() -> Dict[str, str]:
    """
    Sync Stripe price IDs from Stripe API (optional, for production).
    Falls back to hardcoded price IDs if Stripe is not configured or sync fails.
    
    Returns:
        Dict mapping tier_id -> stripe_price_id
    """
    if not settings.STRIPE_SECRET_KEY:
        logger.warning("Stripe not configured, using fallback price IDs")
        return {tier_id: tier_info["stripe_price_id"] for tier_id, tier_info in PRICING_TIERS.items()}
    
    try:
        # Fetch prices from Stripe
        prices = stripe.Price.list(active=True, limit=100)
        tier_to_price_id = {}
        
        # Map Stripe prices to tiers by metadata or lookup
        for price in prices.data:
            # Check if price has tier metadata
            tier_id = price.metadata.get("tier_id")
            if tier_id and tier_id in PRICING_TIERS:
                tier_to_price_id[tier_id] = price.id
            # Also check by amount (cents) and recurring interval
            elif price.recurring and price.recurring.interval == "month":
                amount = price.unit_amount
                if amount:
                    # Match by price amount
                    for tid, tinfo in PRICING_TIERS.items():
                        if tinfo["price"] == amount:
                            tier_to_price_id[tid] = price.id
                            break
        
        # Update PRICING_TIERS with synced prices (but keep fallback)
        for tier_id, price_id in tier_to_price_id.items():
            if tier_id in PRICING_TIERS:
                PRICING_TIERS[tier_id]["stripe_price_id"] = price_id
                logger.info(f"Synced Stripe price {price_id} for tier {tier_id}")
        
        # Return synced prices, fallback to hardcoded if missing
        result = {}
        for tier_id in PRICING_TIERS.keys():
            result[tier_id] = tier_to_price_id.get(tier_id) or PRICING_TIERS[tier_id]["stripe_price_id"]
        
        return result
    except Exception as e:
        logger.warning(f"Failed to sync Stripe prices, using fallback: {e}")
        # Fallback to hardcoded price IDs
        return {tier_id: tier_info["stripe_price_id"] for tier_id, tier_info in PRICING_TIERS.items()}


def get_stripe_price_id(tier_id: str) -> Optional[str]:
    """
    Get the Stripe price ID for a given tier.

    Args:
        tier_id: Tier ID ('tier_1', 'tier_2', 'tier_3', 'tier_4')

    Returns:
        Stripe price ID or None if invalid tier
    """
    if tier_id in PRICING_TIERS:
        return PRICING_TIERS[tier_id]["stripe_price_id"]
    return None


class StripeService:
    """Service for Stripe operations"""

    @staticmethod
    def create_customer(email: str, name: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            return {"success": True, "customer_id": customer.id, "customer": customer}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer creation failed: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def create_checkout_session(
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout session"""
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata or {},
                subscription_data={
                    "metadata": metadata or {}
                }
            )
            return {"success": True, "session_id": session.id, "url": session.url}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe checkout session creation failed: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def create_portal_session(customer_id: str, return_url: str) -> Dict[str, Any]:
        """Create a Stripe Customer Portal session"""
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return {"success": True, "url": session.url}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe portal session creation failed: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_subscription(subscription_id: str) -> Dict[str, Any]:
        """Get subscription details"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {"success": True, "subscription": subscription}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription retrieval failed: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def cancel_subscription(subscription_id: str, at_period_end: bool = True) -> Dict[str, Any]:
        """Cancel a subscription"""
        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)
            return {"success": True, "subscription": subscription}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription cancellation failed: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def construct_webhook_event(payload: bytes, signature: str) -> Dict[str, Any]:
        """Construct and verify a webhook event"""
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                settings.STRIPE_WEBHOOK_SECRET
            )
            return {"success": True, "event": event}
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Stripe webhook signature verification failed: {e}")
            return {"success": False, "error": "Invalid signature"}
        except Exception as e:
            logger.error(f"Stripe webhook construction failed: {e}")
            return {"success": False, "error": str(e)}


stripe_service = StripeService()
