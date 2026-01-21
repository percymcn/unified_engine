"""
Stripe Webhook Handler for Tradeflow
Processes subscription lifecycle events from Stripe
"""
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
import logging
from datetime import datetime

from app.db.database import get_db
from app.models.models import User
from app.services.stripe_service import stripe_service
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


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
    """Handle successful checkout - new subscription"""
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

    # Get subscription details for end date
    if subscription_id:
        sub_result = stripe_service.get_subscription(subscription_id)
        if sub_result["success"]:
            subscription = sub_result["subscription"]
            ends_at = datetime.fromtimestamp(subscription.current_period_end)
            update_user_subscription(db, user, "pro", "active", ends_at)
            logger.info(f"User {user.id} subscribed to Pro via checkout")
            return

    # Fallback if no subscription ID
    update_user_subscription(db, user, "pro", "active")
    logger.info(f"User {user.id} subscribed to Pro via checkout (no subscription details)")


async def handle_subscription_updated(db: Session, subscription: dict):
    """Handle subscription updates (plan changes, status changes)"""
    customer_id = subscription.get("customer")
    sub_status = subscription.get("status")  # active, past_due, canceled, etc.

    if not customer_id:
        return

    user = get_user_by_stripe_customer(db, customer_id)
    if not user:
        logger.warning(f"No user found for Stripe customer {customer_id}")
        return

    # Map Stripe status to our status
    status_map = {
        "active": "active",
        "past_due": "past_due",
        "canceled": "canceled",
        "unpaid": "past_due",
        "incomplete": "incomplete",
        "incomplete_expired": "canceled",
        "trialing": "active",
    }

    new_status = status_map.get(sub_status, "active")

    # Get period end
    period_end = subscription.get("current_period_end")
    ends_at = datetime.fromtimestamp(period_end) if period_end else None

    # Check if subscription is being canceled at period end
    cancel_at_period_end = subscription.get("cancel_at_period_end", False)
    if cancel_at_period_end:
        new_status = "canceling"

    # Update user
    update_user_subscription(db, user, "pro", new_status, ends_at)
    logger.info(f"User {user.id} subscription updated: status={new_status}")


async def handle_subscription_deleted(db: Session, subscription: dict):
    """Handle subscription cancellation/deletion"""
    customer_id = subscription.get("customer")

    if not customer_id:
        return

    user = get_user_by_stripe_customer(db, customer_id)
    if not user:
        logger.warning(f"No user found for Stripe customer {customer_id}")
        return

    # Downgrade to free
    update_user_subscription(db, user, "free", "canceled")
    logger.info(f"User {user.id} subscription deleted, downgraded to free")


async def handle_payment_succeeded(db: Session, invoice: dict):
    """Handle successful payment - ensure subscription is active"""
    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")

    if not customer_id or not subscription_id:
        return

    user = get_user_by_stripe_customer(db, customer_id)
    if not user:
        return

    # Payment succeeded - ensure active status
    if user.subscription_status != "active":
        # Get subscription for period end
        sub_result = stripe_service.get_subscription(subscription_id)
        if sub_result["success"]:
            subscription = sub_result["subscription"]
            ends_at = datetime.fromtimestamp(subscription.current_period_end)
            update_user_subscription(db, user, "pro", "active", ends_at)
        else:
            update_user_subscription(db, user, "pro", "active")

        logger.info(f"User {user.id} payment succeeded, status set to active")


async def handle_payment_failed(db: Session, invoice: dict):
    """Handle failed payment - set past_due status"""
    customer_id = invoice.get("customer")

    if not customer_id:
        return

    user = get_user_by_stripe_customer(db, customer_id)
    if not user:
        return

    # Mark as past due (Stripe will retry)
    if user.subscription_tier == "pro":
        user.subscription_status = "past_due"
        db.commit()
        logger.warning(f"User {user.id} payment failed, status set to past_due")
