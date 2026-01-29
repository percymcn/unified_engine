"""
Telegram Notification Service
Handles push notifications via Telegram Bot API with tier-based gating.

Tier Gating:
- Free: No Telegram notifications
- Starter (tier_1): Price alerts only
- Trader (tier_2): Price alerts + daily summary
- Pro (tier_3): All trade notifications + signals
- Enterprise (tier_4): Real-time everything + custom alerts
"""
import logging
import httpx
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


class TelegramNotificationType(str, Enum):
    """Types of Telegram notifications with tier requirements"""
    PRICE_ALERT = "price_alert"  # tier_1+
    DAILY_SUMMARY = "daily_summary"  # tier_2+
    TRADE_EXECUTED = "trade_executed"  # tier_3+
    TRADE_FAILED = "trade_failed"  # tier_3+
    SIGNAL_RECEIVED = "signal_received"  # tier_3+
    SIGNAL_REJECTED = "signal_rejected"  # tier_3+
    REAL_TIME_UPDATE = "real_time_update"  # tier_4+
    CUSTOM_ALERT = "custom_alert"  # tier_4+
    SYSTEM_ALERT = "system_alert"  # All tiers (critical only)
    TIER_UPGRADE = "tier_upgrade"  # All tiers


# Tier requirements for notification types
TIER_REQUIREMENTS: Dict[TelegramNotificationType, str] = {
    TelegramNotificationType.PRICE_ALERT: "starter",  # tier_1
    TelegramNotificationType.DAILY_SUMMARY: "trader",  # tier_2
    TelegramNotificationType.TRADE_EXECUTED: "pro",  # tier_3
    TelegramNotificationType.TRADE_FAILED: "pro",  # tier_3
    TelegramNotificationType.SIGNAL_RECEIVED: "pro",  # tier_3
    TelegramNotificationType.SIGNAL_REJECTED: "pro",  # tier_3
    TelegramNotificationType.REAL_TIME_UPDATE: "enterprise",  # tier_4
    TelegramNotificationType.CUSTOM_ALERT: "enterprise",  # tier_4
    TelegramNotificationType.SYSTEM_ALERT: "free",  # All tiers
    TelegramNotificationType.TIER_UPGRADE: "free",  # All tiers
}

# Tier hierarchy for comparison
TIER_HIERARCHY = {
    "free": 0,
    "starter": 1,
    "trader": 2,
    "pro": 3,
    "enterprise": 4,
}


def user_has_tier_access(user_tier: str, required_tier: str) -> bool:
    """Check if user's tier meets the required tier for a notification type"""
    user_level = TIER_HIERARCHY.get(user_tier.lower(), 0)
    required_level = TIER_HIERARCHY.get(required_tier.lower(), 0)
    return user_level >= required_level


async def send_telegram_message(
    chat_id: str,
    message: str,
    parse_mode: str = "HTML",
    disable_notification: bool = False,
) -> bool:
    """
    Send message via Telegram Bot API.
    Returns True if successful.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not configured")
        return False

    if not chat_id:
        logger.warning("No Telegram chat_id provided")
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": parse_mode,
                    "disable_notification": disable_notification,
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                logger.info(f"Telegram message sent to {chat_id}")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


async def send_trade_notification(
    chat_id: str,
    user_tier: str,
    trade_action: str,
    symbol: str,
    quantity: float,
    price: float,
    status: str,
    broker: Optional[str] = None,
) -> bool:
    """Send trade execution notification via Telegram (tier_3+)"""
    notification_type = (
        TelegramNotificationType.TRADE_EXECUTED
        if status == "executed"
        else TelegramNotificationType.TRADE_FAILED
    )

    if not user_has_tier_access(user_tier, TIER_REQUIREMENTS[notification_type]):
        logger.debug(f"User tier {user_tier} doesn't have access to {notification_type}")
        return False

    status_emoji = "✅" if status == "executed" else "❌"
    action_emoji = "📈" if trade_action.lower() == "buy" else "📉"

    message = f"""
{status_emoji} <b>Trade {status.upper()}</b>

{action_emoji} <b>{trade_action.upper()}</b> {symbol}
📊 Quantity: <code>{quantity}</code>
💰 Price: <code>${price:,.2f}</code>
{f"🏦 Broker: {broker}" if broker else ""}
🕐 Time: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC
"""

    return await send_telegram_message(chat_id, message.strip())


async def send_signal_notification(
    chat_id: str,
    user_tier: str,
    signal_action: str,
    symbol: str,
    source: Optional[str] = None,
    status: str = "received",
) -> bool:
    """Send signal notification via Telegram (tier_3+)"""
    notification_type = (
        TelegramNotificationType.SIGNAL_RECEIVED
        if status == "received"
        else TelegramNotificationType.SIGNAL_REJECTED
    )

    if not user_has_tier_access(user_tier, TIER_REQUIREMENTS[notification_type]):
        return False

    status_emoji = "📨" if status == "received" else "🚫"
    action_emoji = "📈" if signal_action.lower() == "buy" else "📉"

    message = f"""
{status_emoji} <b>Signal {status.upper()}</b>

{action_emoji} <b>{signal_action.upper()}</b> {symbol}
{f"📡 Source: {source}" if source else ""}
🕐 Time: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC
"""

    return await send_telegram_message(chat_id, message.strip())


async def send_price_alert(
    chat_id: str,
    user_tier: str,
    symbol: str,
    alert_type: str,
    price: float,
    threshold: float,
) -> bool:
    """Send price alert notification via Telegram (tier_1+)"""
    if not user_has_tier_access(user_tier, TIER_REQUIREMENTS[TelegramNotificationType.PRICE_ALERT]):
        return False

    alert_emoji = "🔔" if alert_type == "above" else "🔻"

    message = f"""
{alert_emoji} <b>Price Alert</b>

📊 {symbol} is now <b>{alert_type}</b> your target
💰 Current: <code>${price:,.2f}</code>
🎯 Threshold: <code>${threshold:,.2f}</code>
🕐 Time: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC
"""

    return await send_telegram_message(chat_id, message.strip())


async def send_daily_summary(
    chat_id: str,
    user_tier: str,
    total_trades: int,
    winning_trades: int,
    losing_trades: int,
    total_pnl: float,
    top_symbol: Optional[str] = None,
) -> bool:
    """Send daily trading summary via Telegram (tier_2+)"""
    if not user_has_tier_access(user_tier, TIER_REQUIREMENTS[TelegramNotificationType.DAILY_SUMMARY]):
        return False

    pnl_emoji = "📈" if total_pnl >= 0 else "📉"
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    message = f"""
📊 <b>Daily Trading Summary</b>

📋 Total Trades: <code>{total_trades}</code>
✅ Winning: <code>{winning_trades}</code>
❌ Losing: <code>{losing_trades}</code>
📈 Win Rate: <code>{win_rate:.1f}%</code>

{pnl_emoji} <b>P&L: ${total_pnl:+,.2f}</b>

{f"⭐ Top Symbol: {top_symbol}" if top_symbol else ""}
📅 Date: {datetime.utcnow().strftime("%Y-%m-%d")}
"""

    return await send_telegram_message(chat_id, message.strip())


async def send_real_time_update(
    chat_id: str,
    user_tier: str,
    update_type: str,
    data: Dict[str, Any],
) -> bool:
    """Send real-time update via Telegram (tier_4 only)"""
    if not user_has_tier_access(user_tier, TIER_REQUIREMENTS[TelegramNotificationType.REAL_TIME_UPDATE]):
        return False

    message = f"""
⚡ <b>Real-Time Update</b>

📌 Type: {update_type}
📦 Data: <code>{str(data)[:200]}</code>
🕐 Time: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC
"""

    return await send_telegram_message(chat_id, message.strip(), disable_notification=True)


async def send_system_alert(
    chat_id: str,
    user_tier: str,
    alert_type: str,
    message_text: str,
) -> bool:
    """Send system alert via Telegram (all tiers - critical only)"""
    # System alerts go to all tiers
    message = f"""
⚠️ <b>System Alert</b>

🔔 {alert_type.upper()}

{message_text}

🕐 Time: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC
"""

    return await send_telegram_message(chat_id, message.strip())


async def send_tier_upgrade_notification(
    chat_id: str,
    new_tier: str,
    features: list,
) -> bool:
    """Send tier upgrade notification via Telegram (all tiers)"""
    features_text = "\n".join([f"  • {f}" for f in features[:5]])

    message = f"""
🎉 <b>Account Upgraded!</b>

🚀 You're now on <b>{new_tier}</b>

<b>New Features:</b>
{features_text}

Thanks for trusting MyTradeFlow!
"""

    return await send_telegram_message(chat_id, message.strip())


async def broadcast_telegram_message(
    chat_ids: list,
    message: str,
    min_tier: str = "free",
    user_tiers: Optional[Dict[str, str]] = None,
) -> Dict[str, int]:
    """
    Broadcast message to multiple Telegram users.
    Respects tier gating if user_tiers dict is provided.
    """
    results = {"sent": 0, "failed": 0, "skipped": 0}

    for chat_id in chat_ids:
        # Check tier if user_tiers provided
        if user_tiers and chat_id in user_tiers:
            if not user_has_tier_access(user_tiers[chat_id], min_tier):
                results["skipped"] += 1
                continue

        success = await send_telegram_message(chat_id, message)
        if success:
            results["sent"] += 1
        else:
            results["failed"] += 1

    logger.info(f"Telegram broadcast: {results}")
    return results
