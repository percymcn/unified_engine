"""
Background task to refresh expiring Tradovate tokens.

This module provides an async task that should be scheduled to run periodically
(recommended: every 5 minutes) to proactively refresh OAuth tokens before they expire.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.database_models import TradingAccount, BrokerType
from app.services.tradovate_token_service import TradovateTokenService

logger = logging.getLogger(__name__)

# Refresh tokens expiring within this window
REFRESH_WINDOW_MINUTES = 10


async def refresh_expiring_tokens() -> None:
    """
    Find and refresh Tradovate tokens expiring soon.

    Called periodically by the scheduler. This function:
    1. Queries for Tradovate accounts with tokens expiring within REFRESH_WINDOW_MINUTES
    2. Attempts to refresh each token using the refresh token
    3. Logs warnings for any failures (user may need to re-authenticate)

    Note: This is a best-effort background task. If refresh fails, the user
    will need to re-authenticate when they next try to use the account.
    """
    db: Session = SessionLocal()
    try:
        threshold = datetime.utcnow() + timedelta(minutes=REFRESH_WINDOW_MINUTES)

        # Find Tradovate accounts with tokens expiring soon
        accounts = db.query(TradingAccount).filter(
            TradingAccount.broker == BrokerType.TRADOVATE,
            TradingAccount.is_active == True,
            TradingAccount.token_expires_at != None,
            TradingAccount.token_expires_at <= threshold,
            TradingAccount.refresh_token != None,
        ).all()

        if not accounts:
            logger.debug("No Tradovate tokens need refreshing")
            return

        logger.info(f"Refreshing tokens for {len(accounts)} Tradovate account(s)")

        service = TradovateTokenService(db)
        success_count = 0
        failure_count = 0

        for account in accounts:
            try:
                success = await service.refresh_token_async(account)
                if success:
                    success_count += 1
                else:
                    failure_count += 1
                    logger.warning(
                        f"Failed to refresh token for account {account.id} "
                        f"(user_id={account.user_id}), user may need to re-authenticate"
                    )
                    # TODO: Send notification to user about expired token
            except Exception as e:
                failure_count += 1
                logger.error(f"Error refreshing account {account.id}: {e}")

        if success_count > 0 or failure_count > 0:
            logger.info(
                f"Token refresh complete: {success_count} succeeded, {failure_count} failed"
            )

    finally:
        db.close()


async def check_token_health() -> dict:
    """
    Check the health of all Tradovate tokens.

    Returns:
        dict: Summary of token health including:
            - total: Total Tradovate accounts
            - healthy: Accounts with valid tokens
            - expiring_soon: Accounts with tokens expiring within 1 hour
            - expired: Accounts with expired tokens
            - no_token: Accounts without tokens
    """
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        one_hour = now + timedelta(hours=1)

        # Query all active Tradovate accounts
        accounts = db.query(TradingAccount).filter(
            TradingAccount.broker == BrokerType.TRADOVATE,
            TradingAccount.is_active == True,
        ).all()

        health = {
            "total": len(accounts),
            "healthy": 0,
            "expiring_soon": 0,
            "expired": 0,
            "no_token": 0,
        }

        for account in accounts:
            if not account.access_token:
                health["no_token"] += 1
            elif not account.token_expires_at:
                # Has token but no expiry tracked - assume healthy
                health["healthy"] += 1
            elif account.token_expires_at <= now:
                health["expired"] += 1
            elif account.token_expires_at <= one_hour:
                health["expiring_soon"] += 1
            else:
                health["healthy"] += 1

        return health

    finally:
        db.close()
