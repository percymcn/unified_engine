"""
Stripe Webhook Handler for Tradeflow
Processes subscription lifecycle events from Stripe with 4-tier support
"""
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
import logging
from datetime import datetime

from app.db.database import get_db
from app.models.models import User
from app.services.stripe_service import stripe_service, PRICING_TIERS, get_tier_from_price_id
from app.services.resend_email_service import (
    send_payment_success_email,
    send_payment_failed_email,
    send_subscription_canceled_email,
    send_tier_upgrade_email,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

# Also create an alias router for the /api/v1/stripe/webhook path that Stripe may be configured to use
alias_router = APIRouter(prefix="/api/v1/stripe", tags=["webhooks"])


def get_user_by_stripe_customer(db: Session, customer_id: str) -> User | None:
    """Find user by Stripe customer ID"""
    return db.query(User).filter(User.stripe_customer_id == customer_id).first()


def update_user_subscription(
    db: Session,
    user: User,
    tier: str,
    subscription_status: str,
    ends_at: datetime | None = None
):
    """Update user subscription fields"""
    user.subscription_tier = tier
    user.subscription_status = subscription_status
    if ends_at:
        user.subscription_ends_at = ends_at
    db.commit()
    logger.info(f"Updated user {user.id} subscription: tier={tier}, status={subscription_status}")


@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Stripe webhook events

    Stripe sends events for subscription lifecycle:
    - checkout.session.completed: New subscription created
    - customer.subscription.updated: Subscription changed
    - customer.subscription.deleted: Subscription canceled
    - invoice.payment_succeeded: Payment successful
    - invoice.payment_failed: Payment failed
    """

    # Get raw body for signature verification
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        logger.warning("Stripe webhook missing signature header")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing signature"
        )

    # Verify signature and construct event
    result = stripe_service.construct_webhook_event(payload, sig_header)
    if not result["success"]:
        logger.warning(f"Stripe webhook signature verification failed: {result['error']}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )

    event = result["event"]
    event_type = event["type"]
    data = event["data"]["object"]

    logger.info(f"Stripe webhook received: {event_type}")

    try:
        # Handle different event types
        if event_type == "checkout.session.completed":
            await handle_checkout_completed(db, data)

        elif event_type == "customer.subscription.updated":
            await handle_subscription_updated(db, data)

        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(db, data)

        elif event_type == "invoice.payment_succeeded":
            await handle_payment_succeeded(db, data)

        elif event_type == "invoice.payment_failed":
            await handle_payment_failed(db, data)

        else:
            logger.debug(f"Unhandled Stripe event type: {event_type}")

    except Exception as e:
        logger.error(f"Error processing Stripe webhook {event_type}: {e}")
        # Return 200 anyway - Stripe will retry on 4xx/5xx
        # We don't want retries for our processing errors

    # Always return 200 to acknowledge receipt
    return {"received": True}


async def handle_checkout_completed(db: Session, session: dict):
    """Handle successful checkout - new subscription with tier from metadata"""
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    metadata = session.get("metadata", {})

    if not customer_id:
        logger.warning("Checkout session missing customer ID")
        return

    user = get_user_by_stripe_customer(db, customer_id)
    if not user:
        # Try to find by metadata user_id
        user_id = metadata.get("user_id")
        if user_id:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user:
                user.stripe_customer_id = customer_id

        if not user:
            logger.warning(f"No user found for Stripe customer {customer_id}")
            return

    # Get tier from metadata (4-tier pricing)
    # Fallback to "tier_1" if not specified, or "tier_3" if legacy "pro" plan
    tier_id = metadata.get("tier_id")
    if not tier_id:
        # Legacy support: plan="pro" maps to tier_3
        plan = metadata.get("plan")
        if plan == "pro":
            tier_id = "tier_3"
        else:
            tier_id = "tier_1"  # Default to lowest paid tier

    # Validate tier_id
    if tier_id not in PRICING_TIERS:
        logger.warning(f"Invalid tier_id in checkout metadata: {tier_id}, defaulting to tier_1")
        tier_id = "tier_1"

    tier_name = PRICING_TIERS[tier_id]["name"]
    tier_features = PRICING_TIERS[tier_id].get("features", [])

    # Get subscription details for end date
    if subscription_id:
        sub_result = stripe_service.get_subscription(subscription_id)
        if sub_result["success"]:
            subscription = sub_result["subscription"]
            ends_at = datetime.fromtimestamp(subscription.current_period_end)
            update_user_subscription(db, user, tier_id, "active", ends_at)
            logger.info(f"User {user.id} subscribed to {tier_name} ({tier_id}) via checkout")

            # Send tier upgrade email
            try:
                await send_tier_upgrade_email(
                    to_email=user.email,
                    username=user.username,
                    new_tier=tier_name,
                    features=tier_features[:6],  # Top 6 features
                )
            except Exception as e:
                logger.warning(f"Failed to send tier upgrade email: {e}")
            return

    # Fallback if no subscription ID
    update_user_subscription(db, user, tier_id, "active")
    logger.info(f"User {user.id} subscribed to {tier_name} ({tier_id}) via checkout (no subscription details)")

    # Send tier upgrade email
    try:
        await send_tier_upgrade_email(
            to_email=user.email,
            username=user.username,
            new_tier=tier_name,
            features=tier_features[:6],
        )
    except Exception as e:
        logger.warning(f"Failed to send tier upgrade email: {e}")


async def handle_subscription_updated(db: Session, subscription: dict):
    """Handle subscription updates (plan changes, status changes)"""
    customer_id = subscription.get("customer")
    sub_status = subscription.get("status")  # active, past_due, canceled, etc.
    metadata = subscription.get("metadata", {})

    if not customer_id:
        return

    user = get_user_by_stripe_customer(db, customer_id)
    if not user:
        logger.warning(f"No user found for Stripe customer {customer_id}")
        return

    # Get tier from subscription metadata
    tier_id = metadata.get("tier_id")

    # If no tier in metadata, try to detect from price_id
    if not tier_id:
        items = subscription.get("items", {}).get("data", [])
        if items:
            price_id = items[0].get("price", {}).get("id")
            if price_id:
                tier_id = get_tier_from_price_id(price_id)
                logger.info(f"Detected tier {tier_id} from price_id {price_id}")

    # Final fallback to user's current tier
    if not tier_id:
        tier_id = user.subscription_tier or "tier_1"
        logger.warning(f"No tier detected, using current: {tier_id}")

    # Map Stripe status to our status
    status_map = {
        "active": "active",
        "past_due": "past_due",
        "canceled": "canceled",
        "unpaid": "past_due",
        "incomplete": "incomplete",
        "incomplete_expired": "canceled",
        "trialing": "trialing",
    }

    new_status = status_map.get(sub_status, "active")

    # Get period end
    period_end = subscription.get("current_period_end")
    ends_at = datetime.fromtimestamp(period_end) if period_end else None

    # Check if subscription is being canceled at period end
    cancel_at_period_end = subscription.get("cancel_at_period_end", False)
    if cancel_at_period_end:
        new_status = "canceling"

    # Update user with their current tier
    update_user_subscription(db, user, tier_id, new_status, ends_at)
    logger.info(f"User {user.id} subscription updated: tier={tier_id}, status={new_status}")


async def handle_subscription_deleted(db: Session, subscription: dict):
    """Handle subscription cancellation/deletion"""
    customer_id = subscription.get("customer")

    if not customer_id:
        return

    user = get_user_by_stripe_customer(db, customer_id)
    if not user:
        logger.warning(f"No user found for Stripe customer {customer_id}")
        return

    # Get previous tier for email
    previous_tier = user.subscription_tier or "free"
    tier_name = PRICING_TIERS.get(previous_tier, {}).get("name", "your plan")

    # Get end date for email
    period_end = subscription.get("current_period_end")
    end_date = datetime.fromtimestamp(period_end).strftime("%B %d, %Y") if period_end else "immediately"

    # Downgrade to free
    update_user_subscription(db, user, "free", "canceled")
    logger.info(f"User {user.id} subscription deleted, downgraded to free")

    # Send cancellation email
    try:
        await send_subscription_canceled_email(
            to_email=user.email,
            username=user.username,
            tier_name=tier_name,
            end_date=end_date,
        )
    except Exception as e:
        logger.warning(f"Failed to send subscription canceled email: {e}")


async def handle_payment_succeeded(db: Session, invoice: dict):
    """Handle successful payment - ensure subscription is active"""
    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")
    amount_paid = invoice.get("amount_paid", 0) / 100  # Convert cents to dollars

    if not customer_id or not subscription_id:
        return

    user = get_user_by_stripe_customer(db, customer_id)
    if not user:
        return

    # Get current tier (preserve it on payment success)
    tier_id = user.subscription_tier or "tier_1"
    tier_name = PRICING_TIERS.get(tier_id, {}).get("name", "Subscription")

    # Payment succeeded - ensure active status
    next_billing_date = "N/A"
    if user.subscription_status != "active":
        # Get subscription for period end
        sub_result = stripe_service.get_subscription(subscription_id)
        if sub_result["success"]:
            subscription = sub_result["subscription"]
            ends_at = datetime.fromtimestamp(subscription.current_period_end)
            next_billing_date = ends_at.strftime("%B %d, %Y")
            # Check if subscription metadata has updated tier
            metadata = subscription.get("metadata", {})
            if metadata.get("tier_id"):
                tier_id = metadata["tier_id"]
                tier_name = PRICING_TIERS.get(tier_id, {}).get("name", "Subscription")
            update_user_subscription(db, user, tier_id, "active", ends_at)
        else:
            update_user_subscription(db, user, tier_id, "active")

        logger.info(f"User {user.id} payment succeeded, tier={tier_id}, status set to active")

    # Send payment success email (for all successful payments)
    try:
        await send_payment_success_email(
            to_email=user.email,
            username=user.username,
            tier_name=tier_name,
            amount=amount_paid,
            next_billing_date=next_billing_date,
        )
    except Exception as e:
        logger.warning(f"Failed to send payment success email: {e}")


async def handle_payment_failed(db: Session, invoice: dict):
    """Handle failed payment - set past_due status and notify user"""
    customer_id = invoice.get("customer")
    amount_due = invoice.get("amount_due", 0) / 100  # Convert cents to dollars

    if not customer_id:
        return

    user = get_user_by_stripe_customer(db, customer_id)
    if not user:
        return

    # Mark as past due (Stripe will retry) - applies to any paid tier
    if user.subscription_tier and user.subscription_tier.startswith("tier_"):
        user.subscription_status = "past_due"
        db.commit()
        logger.warning(f"User {user.id} payment failed, tier={user.subscription_tier}, status set to past_due")

        # Get tier name for email
        tier_name = PRICING_TIERS.get(user.subscription_tier, {}).get("name", "your subscription")

        # Calculate retry date (Stripe typically retries in 3-5 days)
        next_attempt = invoice.get("next_payment_attempt")
        retry_date = None
        if next_attempt:
            retry_date = datetime.fromtimestamp(next_attempt).strftime("%B %d, %Y")

        # Send payment failed email
        try:
            await send_payment_failed_email(
                to_email=user.email,
                username=user.username,
                tier_name=tier_name,
                amount=amount_due,
                retry_date=retry_date,
            )
        except Exception as e:
            logger.warning(f"Failed to send payment failed email: {e}")


# Alias endpoint for /api/v1/stripe/webhook (what Stripe may be configured to use)
@alias_router.post("/webhook")
async def stripe_webhook_alias(request: Request, db: Session = Depends(get_db)):
    """Alias for Stripe webhook - redirects to main handler"""
    return await stripe_webhook(request, db)
