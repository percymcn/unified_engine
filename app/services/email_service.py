"""
Email Service
Handles sending verification emails, welcome emails, and other notifications.
"""
import logging
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_verification_token(email: str, user_id: int) -> str:
    """
    Generate a JWT token for email verification.
    Token expires after EMAIL_VERIFICATION_EXPIRE_HOURS.
    """
    expire = datetime.utcnow() + timedelta(hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS)
    to_encode = {
        "sub": email,
        "user_id": user_id,
        "type": "email_verification",
        "exp": expire
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_email_token(token: str) -> Optional[dict]:
    """
    Verify an email verification token.
    Returns the decoded payload if valid, None if invalid.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "email_verification":
            return None
        return payload
    except Exception as e:
        logger.warning(f"Invalid verification token: {e}")
        return None


def send_email(to_email: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """
    Send an email via SMTP.
    Returns True if successful, False otherwise.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP not configured. Email not sent.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL or settings.SMTP_USER}>"
        msg["To"] = to_email

        # Add plain text version
        if text_body:
            part1 = MIMEText(text_body, "plain")
            msg.attach(part1)

        # Add HTML version
        part2 = MIMEText(html_body, "html")
        msg.attach(part2)

        # Connect and send
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(
                settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
                to_email,
                msg.as_string()
            )

        logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_verification_email(to_email: str, username: str, token: str) -> bool:
    """
    Send email verification link to new user.
    """
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #6366f1; margin: 0;">Tradeflow</h1>
            <p style="color: #6b7280; margin-top: 5px;">Automated Trading Signal Router</p>
        </div>

        <div style="background: #f9fafb; border-radius: 12px; padding: 30px; margin-bottom: 20px;">
            <h2 style="margin-top: 0;">Verify Your Email</h2>
            <p>Hi {username},</p>
            <p>Welcome to Tradeflow! Please verify your email address to activate your account and start trading.</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" style="background: #6366f1; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                    Verify Email Address
                </a>
            </div>

            <p style="font-size: 14px; color: #6b7280;">
                This link expires in {settings.EMAIL_VERIFICATION_EXPIRE_HOURS} hours. If you didn't create an account, you can ignore this email.
            </p>
        </div>

        <div style="text-align: center; font-size: 12px; color: #9ca3af;">
            <p>Tradeflow - Route trading signals to your broker accounts</p>
            <p>If you have questions, reply to this email for support.</p>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Verify Your Email - Tradeflow

    Hi {username},

    Welcome to Tradeflow! Please verify your email address to activate your account.

    Click this link to verify: {verification_url}

    This link expires in {settings.EMAIL_VERIFICATION_EXPIRE_HOURS} hours.

    If you didn't create an account, you can ignore this email.

    - The Tradeflow Team
    """

    return send_email(
        to_email=to_email,
        subject="Verify your Tradeflow account",
        html_body=html_body,
        text_body=text_body
    )


def send_welcome_email(to_email: str, username: str) -> bool:
    """
    Send welcome email after successful verification.
    """
    dashboard_url = f"{settings.FRONTEND_URL}/dashboard"
    docs_url = f"{settings.FRONTEND_URL}/docs"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #6366f1; margin: 0;">Tradeflow</h1>
            <p style="color: #6b7280; margin-top: 5px;">Automated Trading Signal Router</p>
        </div>

        <div style="background: #f9fafb; border-radius: 12px; padding: 30px; margin-bottom: 20px;">
            <h2 style="margin-top: 0; color: #10b981;">Welcome to Tradeflow!</h2>
            <p>Hi {username},</p>
            <p>Your email has been verified and your account is now active. You're ready to start automating your trades!</p>

            <h3 style="color: #374151;">Quick Start Guide</h3>
            <ol style="padding-left: 20px;">
                <li><strong>Generate a Webhook Key</strong> - This connects your signals to your account</li>
                <li><strong>Connect Your Broker</strong> - Add your MT4, MT5, TradeLocker, or other broker</li>
                <li><strong>Set Up TradingView Alerts</strong> - Point your alerts to your webhook URL</li>
                <li><strong>Start Trading</strong> - Signals will execute automatically!</li>
            </ol>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{dashboard_url}" style="background: #6366f1; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                    Go to Dashboard
                </a>
            </div>

            <div style="background: #ecfdf5; border-radius: 8px; padding: 15px; border-left: 4px solid #10b981;">
                <p style="margin: 0; font-size: 14px;">
                    <strong>Free Trial:</strong> You get 50 free trades or 7 days (whichever comes first) to test the platform. No credit card required!
                </p>
            </div>
        </div>

        <div style="text-align: center; font-size: 12px; color: #9ca3af;">
            <p>Need help? Reply to this email or visit our support page.</p>
            <p>Tradeflow - Route trading signals to your broker accounts</p>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Welcome to Tradeflow!

    Hi {username},

    Your email has been verified and your account is now active.

    Quick Start Guide:
    1. Generate a Webhook Key
    2. Connect Your Broker
    3. Set Up TradingView Alerts
    4. Start Trading!

    Go to Dashboard: {dashboard_url}

    Free Trial: 50 trades or 7 days free (whichever comes first).

    Need help? Reply to this email.

    - The Tradeflow Team
    """

    return send_email(
        to_email=to_email,
        subject="Welcome to Tradeflow - Your account is ready!",
        html_body=html_body,
        text_body=text_body
    )


def send_password_reset_email(to_email: str, username: str, reset_token: str) -> bool:
    """
    Send password reset email.
    """
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #6366f1; margin: 0;">Tradeflow</h1>
        </div>

        <div style="background: #f9fafb; border-radius: 12px; padding: 30px; margin-bottom: 20px;">
            <h2 style="margin-top: 0;">Reset Your Password</h2>
            <p>Hi {username},</p>
            <p>We received a request to reset your password. Click the button below to create a new password.</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" style="background: #6366f1; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                    Reset Password
                </a>
            </div>

            <p style="font-size: 14px; color: #6b7280;">
                This link expires in 1 hour. If you didn't request a password reset, you can ignore this email.
            </p>
        </div>

        <div style="text-align: center; font-size: 12px; color: #9ca3af;">
            <p>Tradeflow - Automated Trading Signal Router</p>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Reset Your Password - Tradeflow

    Hi {username},

    We received a request to reset your password.

    Click this link to reset: {reset_url}

    This link expires in 1 hour.

    If you didn't request this, ignore this email.

    - The Tradeflow Team
    """

    return send_email(
        to_email=to_email,
        subject="Reset your Tradeflow password",
        html_body=html_body,
        text_body=text_body
    )
