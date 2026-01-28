"""
Trial Service
Handles free trial tracking and enforcement for new users.
Trial limits: 50 trades OR 7 days (whichever comes first).
"""
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.models import User

logger = logging.getLogger(__name__)

# Trial constants
MAX_TRIAL_TRADES = 50
MAX_TRIAL_DAYS = 7


class TrialStatus(str, Enum):
    """Trial status enumeration."""
    NOT_STARTED = "not_started"  # Trial hasn't begun yet
    ACTIVE = "active"  # Trial is currently active
    EXPIRED = "expired"  # Trial has expired (trades or days exceeded)
    NOT_APPLICABLE = "not_applicable"  # User is on paid tier, no trial needed


class TrialService:
    """Service for managing user trial periods."""

    def __init__(self, db: Session):
        """Initialize trial service with database session."""
        self.db = db

    def start_trial(self, user: User) -> bool:
        """
        Start trial for a user.

        Sets trial_started_at to current time and trial_status to active.
        Only starts trial if user is on free tier and trial is pending.

        Args:
            user: The user to start trial for

        Returns:
            True if trial was started, False if trial was already started or not applicable
        """
        if user.subscription_tier != "free":
            logger.debug(f"User {user.id} is not on free tier, trial not applicable")
            return False

        if user.trial_status == "active":
            logger.debug(f"User {user.id} already has active trial")
            return False

        if user.trial_status == "expired":
            logger.debug(f"User {user.id} trial already expired")
            return False

        # Start the trial
        user.trial_started_at = datetime.utcnow()
        user.trial_status = "active"
        user.trial_trade_count = 0
        self.db.commit()

        logger.info(f"Started trial for user {user.id}")
        return True

    def increment_trade_count(self, user: User) -> int:
        """
        Increment trial trade count after successful trade.

        Args:
            user: The user whose trade count to increment

        Returns:
            New trade count
        """
        if user.subscription_tier != "free":
            return 0  # Paid users don't count trades

        if user.trial_trade_count is None:
            user.trial_trade_count = 0

        user.trial_trade_count += 1
        self.db.commit()

        logger.debug(f"User {user.id} trial trade count: {user.trial_trade_count}/{MAX_TRIAL_TRADES}")
        return user.trial_trade_count

    def check_trial_status(self, user: User) -> TrialStatus:
        """
        Check current trial status for a user.

        Returns:
            - NOT_APPLICABLE: User is on paid tier
            - NOT_STARTED: Trial pending, hasn't executed first signal yet
            - ACTIVE: Trial in progress, limits not exceeded
            - EXPIRED: Trial expired (50 trades or 7 days exceeded)
        """
        # Paid users bypass trial
        if user.subscription_tier != "free":
            return TrialStatus.NOT_APPLICABLE

        # Check current status
        status = user.trial_status or "pending"

        if status == "pending":
            return TrialStatus.NOT_STARTED

        if status == "expired":
            return TrialStatus.EXPIRED

        if status == "completed":
            return TrialStatus.NOT_APPLICABLE

        # Status is "active", check if limits exceeded
        trade_count = user.trial_trade_count or 0
        if trade_count >= MAX_TRIAL_TRADES:
            self.expire_trial(user)
            return TrialStatus.EXPIRED

        # Check days elapsed
        if user.trial_started_at:
            elapsed = datetime.utcnow() - user.trial_started_at
            if elapsed.total_seconds() > (MAX_TRIAL_DAYS * 24 * 60 * 60):
                self.expire_trial(user)
                return TrialStatus.EXPIRED

        return TrialStatus.ACTIVE

    def get_trial_info(self, user: User) -> Dict[str, Any]:
        """
        Get detailed trial information for a user.

        Returns:
            Dictionary with trial status, trades remaining, days remaining
        """
        status = self.check_trial_status(user)

        if status == TrialStatus.NOT_APPLICABLE:
            return {
                "status": status.value,
                "subscription_tier": user.subscription_tier,
                "trades_remaining": None,
                "days_remaining": None,
                "trades_used": None,
                "trial_started_at": None,
                "trial_ended_at": user.trial_ended_at.isoformat() if user.trial_ended_at else None
            }

        trade_count = user.trial_trade_count or 0
        trades_remaining = max(0, MAX_TRIAL_TRADES - trade_count)

        days_remaining = MAX_TRIAL_DAYS
        hours_remaining = 0
        if user.trial_started_at:
            elapsed = datetime.utcnow() - user.trial_started_at
            elapsed_days = elapsed.total_seconds() / (24 * 60 * 60)
            days_remaining = max(0, MAX_TRIAL_DAYS - elapsed_days)
            # Calculate hours for more precision
            hours_remaining = int((days_remaining % 1) * 24)
            days_remaining = int(days_remaining)

        return {
            "status": status.value,
            "subscription_tier": user.subscription_tier,
            "trades_remaining": trades_remaining if status != TrialStatus.EXPIRED else 0,
            "trades_used": trade_count,
            "trades_limit": MAX_TRIAL_TRADES,
            "days_remaining": days_remaining if status != TrialStatus.EXPIRED else 0,
            "hours_remaining": hours_remaining if status != TrialStatus.EXPIRED else 0,
            "days_limit": MAX_TRIAL_DAYS,
            "trial_started_at": user.trial_started_at.isoformat() if user.trial_started_at else None,
            "trial_ended_at": user.trial_ended_at.isoformat() if user.trial_ended_at else None
        }

    def expire_trial(self, user: User) -> bool:
        """
        Expire a user's trial.

        Sets trial_status to expired and records trial_ended_at.

        Args:
            user: The user whose trial to expire

        Returns:
            True if trial was expired, False if already expired or not applicable
        """
        if user.subscription_tier != "free":
            return False

        if user.trial_status == "expired":
            return False

        user.trial_status = "expired"
        user.trial_ended_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Trial expired for user {user.id}. Trade count: {user.trial_trade_count}")
        return True

    def reset_trial(self, user: User) -> bool:
        """
        Reset a user's trial (admin function).

        Clears all trial fields to allow a fresh start.

        Args:
            user: The user whose trial to reset

        Returns:
            True if trial was reset
        """
        user.trial_trade_count = 0
        user.trial_started_at = None
        user.trial_ended_at = None
        user.trial_status = "pending"
        self.db.commit()

        logger.info(f"Trial reset for user {user.id}")
        return True

    def upgrade_to_paid(self, user: User) -> bool:
        """
        Handle trial when user upgrades to paid tier.

        Sets trial_status to completed.

        Args:
            user: The user upgrading

        Returns:
            True if status was updated
        """
        if user.trial_status not in ("pending", "active", "expired"):
            return False

        user.trial_status = "completed"
        self.db.commit()

        logger.info(f"User {user.id} upgraded to paid, trial marked completed")
        return True
