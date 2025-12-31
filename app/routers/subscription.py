"""
Subscription Management Router
Stripe integration for Unified Trading Engine
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User
# Stripe integration - try to import from shared_modules or use mock
try:
    import sys
    sys.path.append('/home/pharma5')
    from shared_modules.stripe_service import (
        create_customer,
        create_subscription,
        cancel_subscription,
        get_subscription,
        get_customer_subscriptions,
        create_checkout_session,
        SUBSCRIPTION_TIERS
    )
except ImportError:
    # Mock Stripe service if not available
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("shared_modules.stripe_service not available, using mock implementation")
    
    SUBSCRIPTION_TIERS = {
        "unified-trading-engine": {
            "basic": {"name": "Basic", "amount": 0, "price_id": "price_basic"},
            "premium": {"name": "Premium", "amount": 2900, "price_id": "price_premium"},
            "enterprise": {"name": "Enterprise", "amount": 9900, "price_id": "price_enterprise"}
        }
    }
    
    def create_customer(email, name):
        return {"success": True, "customer_id": f"cus_mock_{email}"}
    
    def create_subscription(customer_id, price_id):
        return {"success": True, "subscription_id": f"sub_mock_{customer_id}"}
    
    def cancel_subscription(subscription_id):
        return {"success": True}
    
    def get_subscription(subscription_id):
        return {"success": True, "status": "active"}
    
    def get_customer_subscriptions(customer_id):
        return {"success": True, "subscriptions": []}
    
    def create_checkout_session(customer_id, service_id, tier, success_url, cancel_url):
        return {"success": True, "url": f"https://checkout.stripe.com/mock?tier={tier}"}

router = APIRouter(prefix="/api/subscription", tags=["subscription"])

class SubscriptionRequest(BaseModel):
    tier: str  # basic, standard, premium

class SubscriptionResponse(BaseModel):
    subscription_id: str
    status: str
    tier: str
    checkout_url: Optional[str] = None

@router.post("/create", response_model=SubscriptionResponse)
async def create_user_subscription(
    request: SubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create subscription for current user"""
    service_id = "unified-trading-engine"
    
    if request.tier not in SUBSCRIPTION_TIERS[service_id]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier. Available tiers: {list(SUBSCRIPTION_TIERS[service_id].keys())}"
        )
    
    # Create or get Stripe customer
    if not current_user.stripe_customer_id:
        customer_result = create_customer(
            email=current_user.email,
            name=current_user.username
        )
        if not customer_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create customer"
            )
        current_user.stripe_customer_id = customer_result["customer_id"]
        db.commit()
    
    # Create checkout session
    checkout_result = create_checkout_session(
        customer_id=current_user.stripe_customer_id,
        service_id=service_id,
        tier=request.tier,
        success_url=f"https://trading.secure.ai/subscription/success",
        cancel_url=f"https://trading.secure.ai/subscription/cancel"
    )
    
    if not checkout_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=checkout_result.get("error", "Failed to create checkout session")
        )
    
    return SubscriptionResponse(
        subscription_id="",
        status="pending",
        tier=request.tier,
        checkout_url=checkout_result["url"]
    )

@router.get("/status")
async def get_user_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription status"""
    if not current_user.stripe_customer_id:
        return {"status": "no_subscription", "tier": None}
    
    subscriptions_result = get_customer_subscriptions(current_user.stripe_customer_id)
    if not subscriptions_result.get("success"):
        return {"status": "error", "error": subscriptions_result.get("error")}
    
    subscriptions = subscriptions_result["subscriptions"]
    active_subscription = next(
        (s for s in subscriptions if s["status"] == "active"),
        None
    )
    
    if not active_subscription:
        return {"status": "no_active_subscription", "tier": None}
    
    return {
        "status": "active",
        "subscription_id": active_subscription["id"],
        "current_period_end": active_subscription["current_period_end"]
    }

@router.post("/cancel")
async def cancel_user_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel current user's subscription"""
    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No subscription found"
        )
    
    subscriptions_result = get_customer_subscriptions(current_user.stripe_customer_id)
    if not subscriptions_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscriptions"
        )
    
    subscriptions = subscriptions_result["subscriptions"]
    active_subscription = next(
        (s for s in subscriptions if s["status"] == "active"),
        None
    )
    
    if not active_subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription found"
        )
    
    cancel_result = cancel_subscription(active_subscription["id"])
    if not cancel_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=cancel_result.get("error", "Failed to cancel subscription")
        )
    
    return {"status": "canceled", "message": "Subscription canceled successfully"}

@router.get("/tiers")
async def get_available_tiers():
    """Get available subscription tiers"""
    service_id = "unified-trading-engine"
    tiers = SUBSCRIPTION_TIERS[service_id]
    return {
        "tiers": [
            {
                "id": tier_id,
                "name": config["name"],
                "price": config["amount"] / 100,  # Convert cents to dollars
                "price_id": config["price_id"]
            }
            for tier_id, config in tiers.items()
        ]
    }
