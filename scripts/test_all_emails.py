"""
Test script to send all email types to a test address.
Run with: python3 scripts/test_all_emails.py
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.resend_email_service import (
    send_verification_email,
    send_welcome_email,
    send_password_reset_email,
    send_tier_upgrade_email,
    send_trade_notification_email,
    send_payment_success_email,
    send_payment_failed_email,
    send_subscription_canceled_email,
    send_subscription_expiring_email,
    send_support_ticket_confirmation,
    send_support_response_notification,
    send_account_alert_email,
)

TEST_EMAIL = "fluxio484@gmail.com"
TEST_USERNAME = "TestUser"
DELAY = 1.5  # Resend free tier: 2 requests/sec


async def test_all_emails():
    print(f"\n{'='*60}")
    print(f"Sending all email types to: {TEST_EMAIL}")
    print(f"(with {DELAY}s delay between emails for rate limiting)")
    print(f"{'='*60}\n")

    results = []

    # 1. Verification Email
    print("1. Sending Verification Email...")
    result = await send_verification_email(
        to_email=TEST_EMAIL,
        username=TEST_USERNAME,
        token="test-verification-token-12345"
    )
    results.append(("Verification Email", result))
    print(f"   {'✓ Sent' if result else '✗ Failed'}")
    await asyncio.sleep(DELAY)

    # 2. Welcome Email
    print("2. Sending Welcome Email...")
    result = await send_welcome_email(
        to_email=TEST_EMAIL,
        username=TEST_USERNAME
    )
    results.append(("Welcome Email", result))
    print(f"   {'✓ Sent' if result else '✗ Failed'}")
    await asyncio.sleep(DELAY)

    # 3. Password Reset Email
    print("3. Sending Password Reset Email...")
    result = await send_password_reset_email(
        to_email=TEST_EMAIL,
        username=TEST_USERNAME,
        reset_token="test-reset-token-67890"
    )
    results.append(("Password Reset Email", result))
    print(f"   {'✓ Sent' if result else '✗ Failed'}")
    await asyncio.sleep(DELAY)

    # 4. Tier Upgrade Email
    print("4. Sending Tier Upgrade Email...")
    result = await send_tier_upgrade_email(
        to_email=TEST_EMAIL,
        username=TEST_USERNAME,
        new_tier="Pro Trader",
        features=[
            "Unlimited signals per month",
            "Up to 10 broker connections",
            "Priority support (12h response)",
            "Advanced risk management",
            "Custom webhook configurations"
        ]
    )
    results.append(("Tier Upgrade Email", result))
    print(f"   {'✓ Sent' if result else '✗ Failed'}")
    await asyncio.sleep(DELAY)

    # 5. Trade Notification Email
    print("5. Sending Trade Notification Email...")
    result = await send_trade_notification_email(
        to_email=TEST_EMAIL,
        username=TEST_USERNAME,
        trade_action="buy",
        symbol="EURUSD",
        quantity=0.5,
        price=1.0875,
        status="executed"
    )
    results.append(("Trade Notification Email", result))
    print(f"   {'✓ Sent' if result else '✗ Failed'}")
    await asyncio.sleep(DELAY)

    # 6. Payment Success Email
    print("6. Sending Payment Success Email...")
    result = await send_payment_success_email(
        to_email=TEST_EMAIL,
        username=TEST_USERNAME,
        tier_name="Pro Trader",
        amount=49.00,
        next_billing_date="February 28, 2026"
    )
    results.append(("Payment Success Email", result))
    print(f"   {'✓ Sent' if result else '✗ Failed'}")
    await asyncio.sleep(DELAY)

    # 7. Payment Failed Email
    print("7. Sending Payment Failed Email...")
    result = await send_payment_failed_email(
        to_email=TEST_EMAIL,
        username=TEST_USERNAME,
        tier_name="Pro Trader",
        amount=49.00,
        retry_date="February 5, 2026"
    )
    results.append(("Payment Failed Email", result))
    print(f"   {'✓ Sent' if result else '✗ Failed'}")
    await asyncio.sleep(DELAY)

    # 8. Subscription Canceled Email
    print("8. Sending Subscription Canceled Email...")
    result = await send_subscription_canceled_email(
        to_email=TEST_EMAIL,
        username=TEST_USERNAME,
        tier_name="Pro Trader",
        end_date="March 1, 2026"
    )
    results.append(("Subscription Canceled Email", result))
    print(f"   {'✓ Sent' if result else '✗ Failed'}")
    await asyncio.sleep(DELAY)

    # 9. Subscription Expiring Email
    print("9. Sending Subscription Expiring Email...")
    result = await send_subscription_expiring_email(
        to_email=TEST_EMAIL,
        username=TEST_USERNAME,
        tier_name="Pro Trader",
        days_remaining=3
    )
    results.append(("Subscription Expiring Email", result))
    print(f"   {'✓ Sent' if result else '✗ Failed'}")
    await asyncio.sleep(DELAY)

    # 10. Support Ticket Confirmation
    print("10. Sending Support Ticket Confirmation...")
    result = await send_support_ticket_confirmation(
        to_email=TEST_EMAIL,
        username=TEST_USERNAME,
        ticket_id="TKT-2026-0001",
        subject="Connection issue with TradeLocker",
        message_preview="Hi, I'm having trouble connecting my TradeLocker account. When I try to authenticate, I get an error saying 'Invalid credentials' but I'm sure my username and password are correct..."
    )
    results.append(("Support Ticket Confirmation", result))
    print(f"   {'✓ Sent' if result else '✗ Failed'}")
    await asyncio.sleep(DELAY)

    # 11. Support Response Notification
    print("11. Sending Support Response Notification...")
    result = await send_support_response_notification(
        to_email=TEST_EMAIL,
        username=TEST_USERNAME,
        ticket_id="TKT-2026-0001",
        subject="Connection issue with TradeLocker",
        response_preview="Hi TestUser, thank you for reaching out! This issue usually occurs when your TradeLocker account has 2FA enabled. Please make sure you're using an API key instead of your password..."
    )
    results.append(("Support Response Notification", result))
    print(f"   {'✓ Sent' if result else '✗ Failed'}")
    await asyncio.sleep(DELAY)

    # 12. Account Alert - Warning
    print("12. Sending Account Alert (Warning)...")
    result = await send_account_alert_email(
        to_email=TEST_EMAIL,
        username=TEST_USERNAME,
        alert_type="warning",
        alert_title="Daily Loss Limit Reached",
        alert_message="Your account has reached the daily loss limit of $500. Trading has been paused for today to protect your capital.",
        action_url="https://mytradeflow.app/dashboard/settings/risk",
        action_text="Review Risk Settings"
    )
    results.append(("Account Alert (Warning)", result))
    print(f"   {'✓ Sent' if result else '✗ Failed'}")
    await asyncio.sleep(DELAY)

    # 13. Account Alert - Error
    print("13. Sending Account Alert (Error)...")
    result = await send_account_alert_email(
        to_email=TEST_EMAIL,
        username=TEST_USERNAME,
        alert_type="error",
        alert_title="Broker Connection Lost",
        alert_message="Your MetaTrader 5 connection has been disconnected. Signals cannot be executed until the connection is restored.",
        action_url="https://mytradeflow.app/dashboard/settings/accounts",
        action_text="Reconnect Broker"
    )
    results.append(("Account Alert (Error)", result))
    print(f"   {'✓ Sent' if result else '✗ Failed'}")
    await asyncio.sleep(DELAY)

    # 14. Account Alert - Info
    print("14. Sending Account Alert (Info)...")
    result = await send_account_alert_email(
        to_email=TEST_EMAIL,
        username=TEST_USERNAME,
        alert_type="info",
        alert_title="New Feature Available",
        alert_message="We've added AI-powered strategy analysis to your account! Get intelligent feedback on your Pine Script strategies.",
        action_url="https://mytradeflow.app/ai-suite",
        action_text="Try AI Strategy Suite"
    )
    results.append(("Account Alert (Info)", result))
    print(f"   {'✓ Sent' if result else '✗ Failed'}")
    await asyncio.sleep(DELAY)

    # 15. Account Alert - Success
    print("15. Sending Account Alert (Success)...")
    result = await send_account_alert_email(
        to_email=TEST_EMAIL,
        username=TEST_USERNAME,
        alert_type="success",
        alert_title="Broker Connected Successfully",
        alert_message="Your TradeLocker account 'Main Trading' has been connected successfully. Signals will now be routed to this account.",
        action_url="https://mytradeflow.app/dashboard/settings/accounts",
        action_text="View Connected Accounts"
    )
    results.append(("Account Alert (Success)", result))
    print(f"   {'✓ Sent' if result else '✗ Failed'}")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    success = sum(1 for _, r in results if r)
    failed = sum(1 for _, r in results if not r)

    for name, result in results:
        status = "✓" if result else "✗"
        print(f"  {status} {name}")

    print(f"\nTotal: {success} sent, {failed} failed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(test_all_emails())
