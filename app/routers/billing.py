"""
Billing Router for Tradeflow
Stripe Checkout and Customer Portal integration
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User
from app.services.stripe_service import stripe_service
from app.core.config import settings
from app.core.billing import get_subscription_info

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan: str = "pro"


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class SubscriptionStatus(BaseModel):
    tier: str
    status: str
    ends_at: Optional[str] = None
    can_manage: bool


class PlanInfo(BaseModel):
    id: str
    name: str
    price: int
    price_display: str
    features: list[str]
    broker_limit: int


PLANS = {
    "free": PlanInfo(
        id="free",
        name="Free",
        price=0,
        price_display="$0/month",
        features=[
            "1 broker connection",
            "Basic signal routing",
            "Community support",
        ],
        broker_limit=1
    ),
    "pro": PlanInfo(
        id="pro",
        name="Pro",
        price=2900,
        price_display="$29/month",
        features=[
            "Unlimited broker connections",
            "Priority signal execution",
            "Advanced routing rules",
            "Email support",
            "Webhook analytics",
        ],
        broker_limit=-1
    )
}


@router.get("/plans")
async def get_plans():
    """Get available subscription plans"""
    return {"plans": [plan.model_dump() for plan in PLANS.values()]}


@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription status"""
    return SubscriptionStatus(
        tier=current_user.subscription_tier or "free",
        status=current_user.subscription_status or "active",
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
    """Create Stripe Checkout session for subscription"""
    if request.plan not in ["pro"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid plan. Available: pro"
        )

    if current_user.subscription_tier == "pro" and current_user.subscription_status == "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already subscribed to Pro. Use the portal to manage your subscription."
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

    # Get price ID from settings
    price_id = settings.STRIPE_PRO_PRICE_ID
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe not configured. Contact support."
        )

    # Build URLs
    base_url = settings.FRONTEND_URL or "https://tradeflow.fluxeo.net"
    success_url = f"{base_url}/dashboard/settings/billing?success=true&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}/pricing?canceled=true"

    # Create checkout session
    checkout_result = stripe_service.create_checkout_session(
        customer_id=current_user.stripe_customer_id,
        price_id=price_id,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": str(current_user.id), "plan": request.plan}
    )

    if not checkout_result["success"]:
        logger.error(f"Failed to create checkout session: {checkout_result['error']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )

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
