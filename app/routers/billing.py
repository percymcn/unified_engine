"""
Billing Router for Tradeflow
Stripe Checkout and Customer Portal integration with 4-tier pricing
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import logging

from app.db.database import get_db
from app.routers.auth import get_current_user, get_current_user_optional
from app.models.models import User, Account
from app.services.stripe_service import (
    stripe_service,
    PRICING_TIERS,
    FREE_TIER,
    get_broker_limit,
    get_all_tiers,
    get_stripe_price_id,
    get_tier_info,
)
from app.core.config import settings
from app.core.billing import get_subscription_info

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    """Checkout request with tier_id (tier_1, tier_2, tier_3, tier_4)"""
    tier_id: str = "tier_1"
    # Legacy support: if plan="pro" is passed, map to tier_3
    plan: Optional[str] = None


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class SubscriptionStatus(BaseModel):
    tier: str
    tier_name: str
    status: str
    broker_limit: int
    brokers_used: int
    ends_at: Optional[str] = None
    can_manage: bool


class PlanInfo(BaseModel):
    id: str
    name: str
    monthly_price: int  # cents
    price_display: str
    features: List[str]
    stripe_price_id: Optional[str]
    broker_limit: int


def _format_price(cents: int) -> str:
    """Format price in cents to display string"""
    if cents == 0:
        return "Free"
    dollars = cents / 100
    return f"${dollars:.2f}/month"


@router.get("/plans")
async def get_plans(
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get available subscription plans (4-tier pricing).

    Returns all tiers with name, price, broker_limit, features.
    Includes current user's tier for comparison (if authenticated).

    This endpoint works WITHOUT authentication for pricing page,
    but returns personalized tier info when authenticated.
    """
    tiers = get_all_tiers()
    current_tier = "free"
    if current_user:
        current_tier = current_user.subscription_tier or "free"

    plans = []
    for tier in tiers:
        tier_id = tier["tier_id"]
        plans.append(PlanInfo(
            id=tier_id,
            name=tier["name"],
            monthly_price=tier["price"],
            price_display=_format_price(tier["price"]),
            features=tier["features"],
            stripe_price_id=tier.get("stripe_price_id"),
            broker_limit=tier["brokers"],
        ).model_dump())

    return {
        "plans": plans,
        "current_tier": current_tier,
        "current_tier_name": get_tier_info(current_tier)["name"],
    }


@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's subscription status.

    Returns current_tier, broker_limit, brokers_used, and subscription details.
    """
    tier = current_user.subscription_tier or "free"
    tier_info = get_tier_info(tier)
    broker_limit = get_broker_limit(tier)

    # Count active broker accounts
    brokers_used = db.query(Account).filter(
        Account.user_id == current_user.id,
        Account.is_active == True
    ).count()

    return SubscriptionStatus(
        tier=tier,
        tier_name=tier_info["name"],
        status=current_user.subscription_status or "active",
        broker_limit=broker_limit,
        brokers_used=brokers_used,
        ends_at=current_user.subscription_ends_at.isoformat() if current_user.subscription_ends_at else None,
        can_manage=current_user.stripe_customer_id is not None
    )


@router.get("/info")
async def get_billing_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed subscription info including usage"""
    return get_subscription_info(current_user, db)


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create Stripe Checkout session for subscription.

    Accepts tier_id (tier_1, tier_2, tier_3, tier_4) to select pricing tier.
    Legacy plan="pro" is mapped to tier_3 for backward compatibility.
    """
    # Handle legacy plan parameter
    tier_id = request.tier_id
    if request.plan == "pro":
        tier_id = "tier_3"  # Legacy pro maps to tier_3

    # Validate tier_id exists in PRICING_TIERS
    valid_tiers = list(PRICING_TIERS.keys())
    if tier_id not in valid_tiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier_id. Available: {', '.join(valid_tiers)}"
        )

    # Get tier info and price ID
    tier_info = PRICING_TIERS[tier_id]
    price_id = get_stripe_price_id(tier_id)

    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe not configured for this tier. Contact support."
        )

    # Check if already subscribed to same or higher tier
    current_tier = current_user.subscription_tier or "free"
    if current_tier == tier_id and current_user.subscription_status == "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Already subscribed to {tier_info['name']}. Use the portal to manage your subscription."
        )

    # Create or get Stripe customer
    if not current_user.stripe_customer_id:
        customer_result = stripe_service.create_customer(
            email=current_user.email,
            name=current_user.full_name or current_user.username,
            metadata={"user_id": str(current_user.id)}
        )
        if not customer_result["success"]:
            logger.error(f"Failed to create Stripe customer: {customer_result['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create payment profile"
            )
        current_user.stripe_customer_id = customer_result["customer_id"]
        db.commit()
        logger.info(f"Created Stripe customer {current_user.stripe_customer_id} for user {current_user.id}")

    # Build URLs
    base_url = settings.FRONTEND_URL or "https://tradeflow.fluxeo.net"
    success_url = f"{base_url}/dashboard/settings/billing?success=true&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}/pricing?canceled=true"

    # Create checkout session with tier in metadata
    checkout_result = stripe_service.create_checkout_session(
        customer_id=current_user.stripe_customer_id,
        price_id=price_id,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": str(current_user.id),
            "tier_id": tier_id,
            "tier_name": tier_info["name"],
            # Legacy field for backward compatibility
            "plan": request.plan or tier_id,
        }
    )

    if not checkout_result["success"]:
        logger.error(f"Failed to create checkout session: {checkout_result['error']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )

    logger.info(f"Created checkout session for user {current_user.id}, tier: {tier_id}")

    return CheckoutResponse(
        checkout_url=checkout_result["url"],
        session_id=checkout_result["session_id"]
    )


@router.get("/portal")
async def create_portal_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe Customer Portal session and return URL"""
    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account. Subscribe first."
        )

    base_url = settings.FRONTEND_URL or "https://tradeflow.fluxeo.net"
    return_url = f"{base_url}/dashboard/settings/billing"

    portal_result = stripe_service.create_portal_session(
        customer_id=current_user.stripe_customer_id,
        return_url=return_url
    )

    if not portal_result["success"]:
        logger.error(f"Failed to create portal session: {portal_result['error']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to access billing portal"
        )

    return {"portal_url": portal_result["url"]}
