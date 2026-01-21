"""
Stripe Service for Tradeflow
Handles all Stripe API interactions
"""
import stripe
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Stripe with API key
stripe.api_key = settings.STRIPE_SECRET_KEY

# Product/Price configuration
STRIPE_PRICES = {
    "pro_monthly": settings.STRIPE_PRO_PRICE_ID,  # $29/mo
}


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
