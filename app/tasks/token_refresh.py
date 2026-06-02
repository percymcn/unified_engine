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
from app.models.enhanced_models import NotificationType, NotificationChannel
from app.services.tradovate_token_service import TradovateTokenService
from app.services.notification_service import NotificationService

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
                    await _notify_token_expired(db, account)
            except Exception as e:
                failure_count += 1
                logger.error(f"Error refreshing account {account.id}: {e}")

        if success_count > 0 or failure_count > 0:
            logger.info(
                f"Token refresh complete: {success_count} succeeded, {failure_count} failed"
            )

    finally:
        db.close()


async def _notify_token_expired(db: Session, account: TradingAccount) -> None:
    """
    Notify a user that their Tradovate token could not be refreshed.

    Best-effort: any failure to deliver the notification is logged but does not
    interrupt the token refresh task. The notification prompts the user to
    re-authenticate the affected account.
    """
    account_label = account.account_name or account.account_number or f"#{account.id}"
    try:
        await NotificationService.create_notification(
            user_id=account.user_id,
            notification_type=NotificationType.ALERT,
            title="Tradovate re-authentication required",
            message=(
                f"We couldn't refresh the access token for your Tradovate account "
                f"{account_label}. Please reconnect the account to resume trading."
            ),
            channel=NotificationChannel.IN_APP,
            action_url="/settings/accounts",
            priority="high",
            metadata={"account_id": account.id, "broker": BrokerType.TRADOVATE.value},
            db=db,
        )
    except Exception as e:
        logger.error(
            f"Failed to send token-expiry notification for account {account.id} "
            f"(user_id={account.user_id}): {e}"
        )


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
