"""
Support Ticket Router for Tradeflow
Handles support ticket creation and escalation from the chatbot
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import logging
import uuid
from datetime import datetime

from app.db.database import get_db
from app.models.models import User
from app.core.security import get_current_user
from app.services.resend_email_service import (
    send_support_ticket_confirmation,
    send_account_alert_email,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/support", tags=["support"])


class ChatMessage(BaseModel):
    role: str
    content: str


class SupportTicketCreate(BaseModel):
    subject: str
    message: str
    chat_history: Optional[List[ChatMessage]] = None
    category: Optional[str] = "general"


class SupportTicketResponse(BaseModel):
    success: bool
    ticket_id: str
    message: str


@router.post("/ticket", response_model=SupportTicketResponse)
async def create_support_ticket(
    ticket: SupportTicketCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a support ticket from the chatbot escalation

    This endpoint:
    1. Creates a unique ticket ID
    2. Sends confirmation email to user
    3. Forwards ticket to support team
    """
    try:
        # Generate unique ticket ID
        ticket_id = f"TF-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        # Format chat history for email
        chat_summary = ""
        if ticket.chat_history:
            chat_summary = "\n\n--- Chat History ---\n"
            for msg in ticket.chat_history[-10:]:  # Last 10 messages
                role = "User" if msg.role == "user" else "TradeBot"
                # Truncate long messages
                content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
                chat_summary += f"\n{role}: {content}\n"

        # Send confirmation email to user
        try:
            await send_support_ticket_confirmation(
                to_email=current_user.email,
                username=current_user.username,
                ticket_id=ticket_id,
                subject=ticket.subject,
                message_preview=ticket.message[:200] + "..." if len(ticket.message) > 200 else ticket.message,
            )
        except Exception as e:
            logger.warning(f"Failed to send ticket confirmation email: {e}")

        # Send ticket to support team via email
        support_email = getattr(settings, 'SUPPORT_EMAIL', 'support@mytradeflow.app')
        try:
            # Use the generic alert email to forward to support
            # In production, you'd use a dedicated support email service
            import resend
            resend.api_key = settings.RESEND_API_KEY

            # Build the support ticket email
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #6366f1;">New Support Ticket #{ticket_id}</h2>

                <div style="background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p><strong>From:</strong> {current_user.username} ({current_user.email})</p>
                    <p><strong>User ID:</strong> {current_user.id}</p>
                    <p><strong>Tier:</strong> {current_user.subscription_tier or 'free'}</p>
                    <p><strong>Category:</strong> {ticket.category}</p>
                    <p><strong>Subject:</strong> {ticket.subject}</p>
                </div>

                <h3>Message:</h3>
                <div style="background: #fff; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
                    <p style="white-space: pre-wrap;">{ticket.message}</p>
                </div>

                {f'''<div style="margin-top: 20px;">
                    <h3>Chat History:</h3>
                    <div style="background: #f1f5f9; padding: 15px; border-radius: 8px; font-size: 12px;">
                        <pre style="white-space: pre-wrap;">{chat_summary}</pre>
                    </div>
                </div>''' if chat_summary else ''}

                <p style="color: #64748b; font-size: 12px; margin-top: 20px;">
                    Ticket created: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
                </p>
            </div>
            """

            resend.Emails.send({
                "from": f"Tradeflow Support <support@{settings.RESEND_DOMAIN}>",
                "to": [support_email],
                "reply_to": current_user.email,
                "subject": f"[Ticket #{ticket_id}] {ticket.subject}",
                "html": html_content,
            })

            logger.info(f"Support ticket {ticket_id} created by user {current_user.id}")

        except Exception as e:
            logger.error(f"Failed to forward support ticket to team: {e}")
            # Still return success - user got confirmation

        return SupportTicketResponse(
            success=True,
            ticket_id=ticket_id,
            message="Support ticket created successfully. We'll respond within 24 hours."
        )

    except Exception as e:
        logger.error(f"Error creating support ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create support ticket. Please try again or email support@mytradeflow.app directly."
        )


@router.get("/faq")
async def get_faq():
    """
    Get frequently asked questions for the support chatbot
    Returns structured FAQ data that can be used by the frontend
    """
    return {
        "categories": [
            {
                "id": "getting-started",
                "name": "Getting Started",
                "questions": [
                    {
                        "q": "How do I get started with Tradeflow?",
                        "a": "1. Sign up and verify your email\n2. Generate a webhook key\n3. Connect your broker account\n4. Set up alerts in TradingView\n5. Test with a small trade"
                    },
                    {
                        "q": "What brokers are supported?",
                        "a": "MT4/MT5 (via MetaAPI), TradeLocker, ProjectX/TopStep, and Tradovate."
                    },
                ]
            },
            {
                "id": "webhooks",
                "name": "Webhooks",
                "questions": [
                    {
                        "q": "What is my webhook URL?",
                        "a": "Your webhook URL is: https://api.mytradeflow.app/api/v1/webhook/signal/{YOUR_KEY}"
                    },
                    {
                        "q": "What format should my webhook payload be?",
                        "a": "JSON with: action (buy/sell/close), symbol. Optional: quantity, stop_loss, take_profit."
                    },
                ]
            },
            {
                "id": "troubleshooting",
                "name": "Troubleshooting",
                "questions": [
                    {
                        "q": "Why aren't my trades executing?",
                        "a": "Check: 1) Webhook key is correct, 2) Broker is connected, 3) JSON is valid, 4) Symbol exists, 5) Sufficient margin."
                    },
                    {
                        "q": "Why was my signal rejected?",
                        "a": "Check the Rejected Signals widget - common reasons: stale signal, duplicate, drawdown limit exceeded."
                    },
                ]
            },
        ]
    }
