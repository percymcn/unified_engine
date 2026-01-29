"""
Resend Email Service
Primary email service using Resend API for transactional emails.
Includes branded templates with logo for all email types.
"""
import logging
import httpx
from typing import Optional, List
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

# Logo URL for emails (hosted publicly)
LOGO_URL = "https://mytradeflow.app/logo.png"

# Brand colors
BRAND_PRIMARY = "#6366f1"  # Indigo
BRAND_SUCCESS = "#10b981"  # Emerald
BRAND_WARNING = "#f59e0b"  # Amber


def get_email_header() -> str:
    """Standard email header with logo"""
    return f"""
    <div style="text-align: center; margin-bottom: 30px; padding: 20px 0; border-bottom: 1px solid #e5e7eb;">
        <img src="{LOGO_URL}" alt="MyTradeFlow" style="height: 40px; width: auto;" onerror="this.style.display='none'">
        <h1 style="color: {BRAND_PRIMARY}; margin: 10px 0 0 0; font-size: 24px;">MyTradeFlow</h1>
        <p style="color: #6b7280; margin: 5px 0 0 0; font-size: 14px;">Automated Trading Signal Router</p>
    </div>
    """


def get_email_footer() -> str:
    """Standard email footer"""
    return f"""
    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; text-align: center; font-size: 12px; color: #9ca3af;">
        <p style="margin: 0;">MyTradeFlow - Route trading signals to your broker accounts</p>
        <p style="margin: 5px 0 0 0;">
            <a href="{settings.FRONTEND_URL}" style="color: {BRAND_PRIMARY}; text-decoration: none;">mytradeflow.app</a> |
            <a href="mailto:support@mytradeflow.app" style="color: {BRAND_PRIMARY}; text-decoration: none;">support@mytradeflow.app</a>
        </p>
        <p style="margin: 10px 0 0 0; font-size: 11px;">
            You're receiving this because you have an account with MyTradeFlow.
        </p>
    </div>
    """


def get_base_template(content: str) -> str:
    """Wrap content in base email template"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9fafb;">
        <div style="background: white; border-radius: 12px; padding: 30px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            {get_email_header()}
            {content}
            {get_email_footer()}
        </div>
    </body>
    </html>
    """


async def send_email_resend(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    from_email: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> bool:
    """
    Send email via Resend API.
    Returns True if successful, False otherwise.
    """
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured. Falling back to SMTP.")
        # Import and use SMTP fallback
        from app.services.email_service import send_email
        return send_email(to_email, subject, html_body, text_body)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": from_email or f"{settings.RESEND_FROM_NAME} <{settings.RESEND_FROM_EMAIL}>",
                    "to": [to_email],
                    "subject": subject,
                    "html": html_body,
                    "text": text_body,
                    "reply_to": reply_to or "support@mytradeflow.app",
                },
                timeout=30.0,
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(f"Email sent via Resend to {to_email}, ID: {data.get('id')}")
                return True
            else:
                logger.error(f"Resend API error: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        logger.error(f"Failed to send email via Resend: {e}")
        return False


async def send_welcome_email(to_email: str, username: str) -> bool:
    """Send welcome email after successful verification"""
    content = f"""
    <div style="padding: 20px 0;">
        <h2 style="margin-top: 0; color: {BRAND_SUCCESS};">Welcome to MyTradeFlow!</h2>
        <p>Hi {username},</p>
        <p>Your email has been verified and your account is now active. You're ready to start automating your trades!</p>

        <div style="background: #f0fdf4; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid {BRAND_SUCCESS};">
            <h3 style="margin: 0 0 15px 0; color: #166534;">Quick Start Guide</h3>
            <ol style="margin: 0; padding-left: 20px;">
                <li style="margin-bottom: 8px;"><strong>Generate a Webhook Key</strong> - This connects your signals to your account</li>
                <li style="margin-bottom: 8px;"><strong>Connect Your Broker</strong> - Add MT4, MT5, TradeLocker, or ProjectX</li>
                <li style="margin-bottom: 8px;"><strong>Set Up TradingView Alerts</strong> - Point your alerts to your webhook URL</li>
                <li><strong>Start Trading</strong> - Signals will execute automatically!</li>
            </ol>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{settings.FRONTEND_URL}/dashboard" style="background: {BRAND_PRIMARY}; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                Go to Dashboard
            </a>
        </div>

        <div style="background: #fef3c7; border-radius: 8px; padding: 15px; border-left: 4px solid {BRAND_WARNING};">
            <p style="margin: 0; font-size: 14px;">
                <strong>Free Trial:</strong> You get 50 free trades or 7 days (whichever comes first) to test the platform. No credit card required!
            </p>
        </div>
    </div>
    """

    return await send_email_resend(
        to_email=to_email,
        subject="Welcome to MyTradeFlow - Your account is ready!",
        html_body=get_base_template(content),
        text_body=f"Welcome {username}! Your MyTradeFlow account is ready. Go to {settings.FRONTEND_URL}/dashboard to get started.",
    )


async def send_verification_email(to_email: str, username: str, token: str) -> bool:
    """Send email verification link"""
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    content = f"""
    <div style="padding: 20px 0;">
        <h2 style="margin-top: 0;">Verify Your Email</h2>
        <p>Hi {username},</p>
        <p>Welcome to MyTradeFlow! Please verify your email address to activate your account and start trading.</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{verification_url}" style="background: {BRAND_PRIMARY}; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                Verify Email Address
            </a>
        </div>

        <p style="font-size: 14px; color: #6b7280;">
            This link expires in {settings.EMAIL_VERIFICATION_EXPIRE_HOURS} hours. If you didn't create an account, you can safely ignore this email.
        </p>
    </div>
    """

    return await send_email_resend(
        to_email=to_email,
        subject="Verify your MyTradeFlow account",
        html_body=get_base_template(content),
        text_body=f"Hi {username}, verify your email: {verification_url}",
    )


async def send_password_reset_email(to_email: str, username: str, reset_token: str) -> bool:
    """Send password reset email"""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    content = f"""
    <div style="padding: 20px 0;">
        <h2 style="margin-top: 0;">Reset Your Password</h2>
        <p>Hi {username},</p>
        <p>We received a request to reset your password. Click the button below to create a new password.</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" style="background: {BRAND_PRIMARY}; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                Reset Password
            </a>
        </div>

        <p style="font-size: 14px; color: #6b7280;">
            This link expires in 1 hour. If you didn't request a password reset, you can ignore this email.
        </p>

        <div style="background: #fef2f2; border-radius: 8px; padding: 15px; border-left: 4px solid #ef4444; margin-top: 20px;">
            <p style="margin: 0; font-size: 13px; color: #991b1b;">
                <strong>Security tip:</strong> Never share this link with anyone. Our team will never ask for your password.
            </p>
        </div>
    </div>
    """

    return await send_email_resend(
        to_email=to_email,
        subject="Reset your MyTradeFlow password",
        html_body=get_base_template(content),
        text_body=f"Hi {username}, reset your password: {reset_url}",
    )


async def send_tier_upgrade_email(to_email: str, username: str, new_tier: str, features: List[str]) -> bool:
    """Send tier upgrade confirmation email"""
    features_html = "".join([f"<li style='margin-bottom: 8px;'>{f}</li>" for f in features])

    content = f"""
    <div style="padding: 20px 0;">
        <h2 style="margin-top: 0; color: {BRAND_SUCCESS};">Upgrade Successful!</h2>
        <p>Hi {username},</p>
        <p>Your account has been upgraded to <strong style="color: {BRAND_PRIMARY};">{new_tier}</strong>. Thank you for your trust in MyTradeFlow!</p>

        <div style="background: #f0fdf4; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid {BRAND_SUCCESS};">
            <h3 style="margin: 0 0 15px 0; color: #166534;">Your New Features</h3>
            <ul style="margin: 0; padding-left: 20px;">
                {features_html}
            </ul>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{settings.FRONTEND_URL}/dashboard" style="background: {BRAND_PRIMARY}; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                Explore Your New Features
            </a>
        </div>

        <p style="font-size: 14px; color: #6b7280;">
            Your billing will be charged automatically. You can manage your subscription at any time from your dashboard settings.
        </p>
    </div>
    """

    return await send_email_resend(
        to_email=to_email,
        subject=f"Welcome to {new_tier} - MyTradeFlow",
        html_body=get_base_template(content),
        text_body=f"Hi {username}, your MyTradeFlow account has been upgraded to {new_tier}!",
    )


async def send_broadcast_email(
    to_emails: List[str],
    subject: str,
    message: str,
    cta_text: Optional[str] = None,
    cta_url: Optional[str] = None,
) -> dict:
    """
    Send broadcast email to multiple users (admin function).
    Returns dict with success/failure counts.
    """
    cta_html = ""
    if cta_text and cta_url:
        cta_html = f"""
        <div style="text-align: center; margin: 30px 0;">
            <a href="{cta_url}" style="background: {BRAND_PRIMARY}; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                {cta_text}
            </a>
        </div>
        """

    content = f"""
    <div style="padding: 20px 0;">
        <div style="white-space: pre-wrap; line-height: 1.8;">{message}</div>
        {cta_html}
    </div>
    """

    html_body = get_base_template(content)
    results = {"sent": 0, "failed": 0, "errors": []}

    for email in to_emails:
        try:
            success = await send_email_resend(
                to_email=email,
                subject=subject,
                html_body=html_body,
                text_body=message,
            )
            if success:
                results["sent"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(email)
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{email}: {str(e)}")

    logger.info(f"Broadcast email: {results['sent']} sent, {results['failed']} failed")
    return results


async def send_trade_notification_email(
    to_email: str,
    username: str,
    trade_action: str,
    symbol: str,
    quantity: float,
    price: float,
    status: str,
) -> bool:
    """Send trade execution notification email"""
    status_color = BRAND_SUCCESS if status == "executed" else "#ef4444"
    status_bg = "#f0fdf4" if status == "executed" else "#fef2f2"

    content = f"""
    <div style="padding: 20px 0;">
        <h2 style="margin-top: 0;">Trade {status.capitalize()}</h2>
        <p>Hi {username},</p>

        <div style="background: {status_bg}; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid {status_color};">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Action:</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right;">{trade_action.upper()}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Symbol:</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right;">{symbol}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Quantity:</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right;">{quantity}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Price:</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right;">${price:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Status:</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right; color: {status_color};">{status.upper()}</td>
                </tr>
            </table>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{settings.FRONTEND_URL}/dashboard/trades" style="background: {BRAND_PRIMARY}; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                View Trade Details
            </a>
        </div>
    </div>
    """

    return await send_email_resend(
        to_email=to_email,
        subject=f"Trade {status.capitalize()}: {trade_action.upper()} {symbol}",
        html_body=get_base_template(content),
        text_body=f"Trade {status}: {trade_action.upper()} {quantity} {symbol} @ ${price}",
    )
