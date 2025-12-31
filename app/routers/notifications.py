"""
Notification Router
Handles notification endpoints and WebSocket connections
"""
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User
from app.models.enhanced_models import Notification, NotificationPreference, NotificationType
from app.services.notification_service import notification_service
from app.core.websocket_manager import ws_manager

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
