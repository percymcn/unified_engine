"""
Webhook Log Retention Service

Automatically cleans up old webhook logs based on user subscription tier.
Retention periods:
- Free/Starter (tier_1): 7 days
- Trader (tier_2): 14 days
- Pro (tier_3): 30 days
- Enterprise (tier_4): 90 days
"""

import logging
from datetime import datetime, timedelta
from typing import Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, delete

from app.db.database import SessionLocal
from app.models.models import WebhookLog, User
from app.models.database_models import WebhookConfig

logger = logging.getLogger(__name__)

# Retention periods in days by tier
RETENTION_DAYS = {
    "free": 7,
    "tier_1": 7,      # Starter
    "tier_2": 14,     # Trader
    "tier_3": 30,     # Pro
    "tier_4": 90,     # Enterprise
    None: 7,          # Default for users without tier
}


def get_retention_days(tier: str) -> int:
    """Get retention days for a subscription tier."""
    return RETENTION_DAYS.get(tier, RETENTION_DAYS["free"])


async def cleanup_webhook_logs_for_user(
    db: Session,
    user_id: int,
    retention_days: int
) -> int:
    """
    Delete webhook logs older than retention_days for a specific user.

    Returns the number of logs deleted.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    # Get webhook keys belonging to this user
    webhook_configs = db.query(WebhookConfig.webhook_key).filter(
        WebhookConfig.user_id == user_id
    ).all()

    webhook_keys = [wc.webhook_key for wc in webhook_configs if wc.webhook_key]

    if not webhook_keys:
        return 0

    # Delete old logs for these webhook keys
    # WebhookLog.source contains the webhook source type, but we need to match via payload
    # For now, we'll delete based on created_at for logs that contain the webhook_key
    deleted_count = 0

    for webhook_key in webhook_keys:
        # Match logs where payload contains this webhook_key
        result = db.execute(
            delete(WebhookLog).where(
                and_(
                    WebhookLog.created_at < cutoff_date,
                    WebhookLog.payload.contains(webhook_key)
                )
            )
        )
        deleted_count += result.rowcount

    return deleted_count


async def cleanup_all_webhook_logs(db: Session = None) -> Dict[str, int]:
    """
    Run webhook log cleanup for all users based on their subscription tiers.

    Returns a summary of cleanup operations.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        summary = {
            "users_processed": 0,
            "logs_deleted": 0,
            "errors": 0,
        }

        # Get all users with their subscription tiers
        users = db.query(User).all()

        for user in users:
            try:
                tier = getattr(user, 'subscription_tier', None) or getattr(user, 'tier', None) or 'free'
                retention_days = get_retention_days(tier)

                deleted = await cleanup_webhook_logs_for_user(db, user.id, retention_days)

                summary["users_processed"] += 1
                summary["logs_deleted"] += deleted

                if deleted > 0:
                    logger.info(f"Deleted {deleted} webhook logs for user {user.id} (tier: {tier}, retention: {retention_days} days)")

            except Exception as e:
                logger.error(f"Error cleaning up logs for user {user.id}: {e}")
                summary["errors"] += 1

        # Also clean up orphaned logs (no matching webhook config) older than 7 days
        orphan_cutoff = datetime.utcnow() - timedelta(days=7)

        # Get all webhook keys that exist in configs
        all_webhook_keys = db.query(WebhookConfig.webhook_key).filter(
            WebhookConfig.webhook_key.isnot(None)
        ).all()
        all_keys = {wc.webhook_key for wc in all_webhook_keys}

        # Delete old logs that don't match any webhook config
        orphan_logs = db.query(WebhookLog).filter(
            WebhookLog.created_at < orphan_cutoff
        ).all()

        orphan_deleted = 0
        for log in orphan_logs:
            # Check if this log's payload contains any known webhook key
            is_orphan = True
            for key in all_keys:
                if key and key in (log.payload or ""):
                    is_orphan = False
                    break

            if is_orphan:
                db.delete(log)
                orphan_deleted += 1

        if orphan_deleted > 0:
            logger.info(f"Deleted {orphan_deleted} orphaned webhook logs")
            summary["logs_deleted"] += orphan_deleted

        db.commit()

        logger.info(f"Webhook cleanup complete: {summary}")
        return summary

    except Exception as e:
        logger.error(f"Webhook cleanup failed: {e}")
        db.rollback()
        raise
    finally:
        if close_session:
            db.close()


async def get_retention_stats(db: Session = None) -> Dict[str, any]:
    """
    Get statistics about webhook log retention.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        from sqlalchemy import func

        # Total logs
        total_logs = db.query(func.count(WebhookLog.id)).scalar()

        # Logs by age
        now = datetime.utcnow()

        logs_7d = db.query(func.count(WebhookLog.id)).filter(
            WebhookLog.created_at >= now - timedelta(days=7)
        ).scalar()

        logs_14d = db.query(func.count(WebhookLog.id)).filter(
            WebhookLog.created_at >= now - timedelta(days=14)
        ).scalar()

        logs_30d = db.query(func.count(WebhookLog.id)).filter(
            WebhookLog.created_at >= now - timedelta(days=30)
        ).scalar()

        logs_90d = db.query(func.count(WebhookLog.id)).filter(
            WebhookLog.created_at >= now - timedelta(days=90)
        ).scalar()

        # Oldest log
        oldest = db.query(func.min(WebhookLog.created_at)).scalar()

        return {
            "total_logs": total_logs,
            "logs_last_7_days": logs_7d,
            "logs_last_14_days": logs_14d,
            "logs_last_30_days": logs_30d,
            "logs_last_90_days": logs_90d,
            "oldest_log": oldest.isoformat() if oldest else None,
            "retention_policy": RETENTION_DAYS,
        }

    finally:
        if close_session:
            db.close()
