"""
Notification Router
Handles notification endpoints and WebSocket connections
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User
from app.models.enhanced_models import Notification, NotificationPreference, NotificationType
from app.services.notification_service import notification_service
from app.core.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    message: str
    action_url: str = None
    priority: str
    is_read: bool
    created_at: str
    
    class Config:
        from_attributes = True

@router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user notifications"""
    notifications = notification_service.get_user_notifications(
        current_user.id,
        unread_only=unread_only,
        limit=limit,
        db=db
    )
    
    return [
        NotificationResponse(
            id=n.id,
            type=n.type.value,
            title=n.title,
            message=n.message,
            action_url=n.action_url,
            priority=n.priority,
            is_read=n.is_read,
            created_at=n.created_at.isoformat()
        )
        for n in notifications
    ]

@router.get("/unread/count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get count of unread notifications"""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    return {"count": count}

@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark notification as read"""
    success = notification_service.mark_as_read(notification_id, current_user.id, db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {"message": "Notification marked as read"}

@router.post("/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read"""
    count = notification_service.mark_all_as_read(current_user.id, db)
    return {"message": f"Marked {count} notifications as read"}

@router.get("/preferences")
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user notification preferences"""
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).first()
    
    if not pref:
        # Create default preferences
        pref = NotificationPreference(user_id=current_user.id)
        db.add(pref)
        db.commit()
        db.refresh(pref)
    
    return {
        "email_enabled": pref.email_enabled,
        "sms_enabled": pref.sms_enabled,
        "push_enabled": pref.push_enabled,
        "in_app_enabled": pref.in_app_enabled,
        "trade_notifications": pref.trade_notifications,
        "signal_notifications": pref.signal_notifications,
        "alert_notifications": pref.alert_notifications,
        "system_notifications": pref.system_notifications,
        "billing_notifications": pref.billing_notifications,
        "quiet_hours_enabled": pref.quiet_hours_enabled,
        "quiet_hours_start": pref.quiet_hours_start,
        "quiet_hours_end": pref.quiet_hours_end,
    }

@router.put("/preferences")
async def update_notification_preferences(
    preferences: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user notification preferences"""
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).first()
    
    if not pref:
        pref = NotificationPreference(user_id=current_user.id)
        db.add(pref)
    
    # Update preferences
    for key, value in preferences.items():
        if hasattr(pref, key):
            setattr(pref, key, value)
    
    db.commit()
    db.refresh(pref)
    
    return {"message": "Preferences updated"}

@router.websocket("/ws")
async def notification_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time notifications"""
    await websocket.accept()

    try:
        # Get user from query params or token
        token = websocket.query_params.get("token")
        # In production, verify token and get user_id
        # For now, accept connection

        while True:
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "subscribe":
                # Subscribe to notifications
                await websocket.send_json({"type": "subscribed"})

    except WebSocketDisconnect:
        logger.info("Notification WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


# ============================================================
# Messaging Handles (Telegram, Discord, Slack, WhatsApp)
# ============================================================

class MessagingHandlesRequest(BaseModel):
    """Request model for updating messaging handles"""
    telegram_enabled: Optional[bool] = None
    telegram_chat_id: Optional[str] = None
    discord_enabled: Optional[bool] = None
    discord_webhook_url: Optional[str] = None
    slack_enabled: Optional[bool] = None
    slack_webhook_url: Optional[str] = None
    whatsapp_enabled: Optional[bool] = None
    whatsapp_number: Optional[str] = None


@router.get("/messaging-handles")
async def get_messaging_handles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user messaging handles for push notifications"""
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).first()

    if not pref:
        pref = NotificationPreference(user_id=current_user.id)
        db.add(pref)
        db.commit()
        db.refresh(pref)

    return {
        "telegram": {
            "enabled": getattr(pref, "telegram_enabled", False),
            "chat_id": getattr(pref, "telegram_chat_id", None),
        },
        "discord": {
            "enabled": getattr(pref, "discord_enabled", False),
            "webhook_url": getattr(pref, "discord_webhook_url", None),
        },
        "slack": {
            "enabled": getattr(pref, "slack_enabled", False),
            "webhook_url": getattr(pref, "slack_webhook_url", None),
        },
        "whatsapp": {
            "enabled": getattr(pref, "whatsapp_enabled", False),
            "number": getattr(pref, "whatsapp_number", None),
        },
        "user_tier": current_user.subscription_tier,
    }


@router.put("/messaging-handles")
async def update_messaging_handles(
    handles: MessagingHandlesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user messaging handles for push notifications"""
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).first()

    if not pref:
        pref = NotificationPreference(user_id=current_user.id)
        db.add(pref)

    # Update Telegram
    if handles.telegram_enabled is not None:
        pref.telegram_enabled = handles.telegram_enabled
    if handles.telegram_chat_id is not None:
        pref.telegram_chat_id = handles.telegram_chat_id

    # Update Discord
    if handles.discord_enabled is not None:
        pref.discord_enabled = handles.discord_enabled
    if handles.discord_webhook_url is not None:
        pref.discord_webhook_url = handles.discord_webhook_url

    # Update Slack
    if handles.slack_enabled is not None:
        pref.slack_enabled = handles.slack_enabled
    if handles.slack_webhook_url is not None:
        pref.slack_webhook_url = handles.slack_webhook_url

    # Update WhatsApp
    if handles.whatsapp_enabled is not None:
        pref.whatsapp_enabled = handles.whatsapp_enabled
    if handles.whatsapp_number is not None:
        pref.whatsapp_number = handles.whatsapp_number

    db.commit()
    db.refresh(pref)

    logger.info(f"Updated messaging handles for user {current_user.id}")

    return {"message": "Messaging handles updated successfully"}


@router.post("/test-telegram")
async def test_telegram_notification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a test Telegram notification to verify setup"""
    from app.services.telegram_service import send_telegram_message

    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).first()

    if not pref or not getattr(pref, "telegram_chat_id", None):
        raise HTTPException(
            status_code=400,
            detail="Telegram chat ID not configured. Start a chat with the bot first."
        )

    success = await send_telegram_message(
        chat_id=pref.telegram_chat_id,
        message=f"🎉 <b>Test Notification</b>\n\nHi {current_user.username}!\n\nYour Telegram notifications are working correctly.\n\n— MyTradeFlow",
    )

    if success:
        return {"message": "Test notification sent successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test notification")
