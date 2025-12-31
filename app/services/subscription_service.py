"""
Enhanced Subscription Service
Handles subscription management, tier enforcement, and usage tracking
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import User
from app.models.enhanced_models import (
    UserSubscription, SubscriptionTier, SubscriptionStatus,
    Organization, UsageMetric
)
from app.core.config import settings

logger = logging.getLogger(__name__)

# Subscription tier limits
TIER_LIMITS = {
    SubscriptionTier.FREE: {
        "max_accounts": 1,
        "max_api_calls_per_month": 1000,
        "max_signals_per_month": 100,
        "max_users": 1,
        "features": ["basic_trading", "basic_analytics"]
    },
    SubscriptionTier.PREMIUM: {
        "max_accounts": 10,
        "max_api_calls_per_month": 100000,
        "max_signals_per_month": 10000,
        "max_users": 5,
        "features": ["advanced_trading", "advanced_analytics", "priority_support", "custom_strategies"]
    },
    SubscriptionTier.ENTERPRISE: {
        "max_accounts": -1,  # Unlimited
        "max_api_calls_per_month": -1,  # Unlimited
        "max_signals_per_month": -1,  # Unlimited
        "max_users": -1,  # Unlimited
        "features": ["all_features", "multi_tenancy", "dedicated_support", "custom_integrations", "sla"]
    }
}

class SubscriptionService:
    """Service for managing user subscriptions"""
    
    @staticmethod
    def get_user_tier(user: User, db: Session) -> SubscriptionTier:
        """Get user's subscription tier"""
        if user.subscription_tier:
            return user.subscription_tier
        
        # Check subscription record
        subscription = db.query(UserSubscription).filter(
            UserSubscription.user_id == user.id,
            UserSubscription.status == SubscriptionStatus.ACTIVE
        ).first()
        
        if subscription:
            return subscription.tier
        
        return SubscriptionTier.FREE
    
    @staticmethod
    def get_tier_limits(tier: SubscriptionTier) -> Dict[str, Any]:
        """Get limits for a subscription tier"""
        return TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTier.FREE])
    
    @staticmethod
    def check_account_limit(user: User, db: Session) -> bool:
        """Check if user can create more accounts"""
        tier = SubscriptionService.get_user_tier(user, db)
        limits = SubscriptionService.get_tier_limits(tier)
        max_accounts = limits["max_accounts"]
        
        if max_accounts == -1:  # Unlimited
            return True
        
        # Count current accounts
        from app.models.models import Account
        current_count = db.query(Account).filter(Account.user_id == user.id).count()
        
        return current_count < max_accounts
    
    @staticmethod
    def check_api_limit(user: User, db: Session) -> bool:
        """Check if user has API calls remaining this month"""
        tier = SubscriptionService.get_user_tier(user, db)
        limits = SubscriptionService.get_tier_limits(tier)
        max_calls = limits["max_api_calls_per_month"]
        
        if max_calls == -1:  # Unlimited
            return True
        
        # Count API calls this month
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_count = db.query(UsageMetric).filter(
            UsageMetric.user_id == user.id,
            UsageMetric.metric_type == "api_call",
            UsageMetric.date >= start_of_month
        ).count()
        
        return current_count < max_calls
    
    @staticmethod
    def check_signal_limit(user: User, db: Session) -> bool:
        """Check if user can create more signals this month"""
        tier = SubscriptionService.get_user_tier(user, db)
        limits = SubscriptionService.get_tier_limits(tier)
        max_signals = limits["max_signals_per_month"]
        
        if max_signals == -1:  # Unlimited
            return True
        
        # Count signals this month
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        from app.models.models import Signal
        current_count = db.query(Signal).filter(
            Signal.user_id == user.id,
            Signal.created_at >= start_of_month
        ).count()
        
        return current_count < max_signals
    
    @staticmethod
    def track_usage(
        user: User,
        metric_type: str,
        value: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        db: Session = None
    ):
        """Track usage metric"""
        if not db:
            return
        
        usage = UsageMetric(
            user_id=user.id,
            organization_id=user.primary_organization_id,
            metric_type=metric_type,
            metric_value=value,
            date=datetime.utcnow(),
            hour=datetime.utcnow().hour,
            metadata=metadata or {}
        )
        db.add(usage)
        db.commit()
    
    @staticmethod
    def has_feature(user: User, feature: str, db: Session) -> bool:
        """Check if user has access to a feature"""
        tier = SubscriptionService.get_user_tier(user, db)
        limits = SubscriptionService.get_tier_limits(tier)
        features = limits.get("features", [])
        
        return feature in features or "all_features" in features
    
    @staticmethod
    def require_feature(feature: str):
        """Dependency to require a feature"""
        def feature_checker(
            current_user: User = None,
            db: Session = None
        ):
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not SubscriptionService.has_feature(current_user, feature, db):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Feature '{feature}' requires a premium subscription"
                )
            
            return current_user
        
        return feature_checker
    
    @staticmethod
    def update_subscription(
        user: User,
        tier: SubscriptionTier,
        status: SubscriptionStatus,
        stripe_subscription_id: Optional[str] = None,
        stripe_customer_id: Optional[str] = None,
        db: Session = None
    ):
        """Update user subscription"""
        if not db:
            return
        
        # Update user tier
        user.subscription_tier = tier
        if stripe_customer_id:
            user.stripe_customer_id = stripe_customer_id
        
        # Update or create subscription record
        subscription = db.query(UserSubscription).filter(
            UserSubscription.user_id == user.id
        ).first()
        
        if not subscription:
            subscription = UserSubscription(
                user_id=user.id,
                tier=tier,
                status=status,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
                start_date=datetime.utcnow()
            )
            db.add(subscription)
        else:
            subscription.tier = tier
            subscription.status = status
            if stripe_subscription_id:
                subscription.stripe_subscription_id = stripe_subscription_id
            if stripe_customer_id:
                subscription.stripe_customer_id = stripe_customer_id
            subscription.updated_at = datetime.utcnow()
        
        # Set limits
        limits = SubscriptionService.get_tier_limits(tier)
        subscription.max_accounts = limits["max_accounts"]
        subscription.max_api_calls_per_month = limits["max_api_calls_per_month"]
        subscription.max_signals_per_month = limits["max_signals_per_month"]
        
        db.commit()
        return subscription

subscription_service = SubscriptionService()
