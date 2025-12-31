"""
Notification Service
Handles in-app notifications, email notifications, and WebSocket delivery
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.models import User
from app.models.enhanced_models import (
    Notification, NotificationPreference, NotificationType,
    NotificationChannel
)
from app.core.config import settings
from app.core.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for managing notifications"""
    
    @staticmethod
    async def create_notification(
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        action_url: Optional[str] = None,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> Notification:
        """Create and send a notification"""
        if not db:
            logger.error("Database session required for notification creation")
            return None
        
        # Check user preferences
        pref = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id
        ).first()
        
        if pref:
            # Check if channel is enabled
            channel_enabled = {
                NotificationChannel.EMAIL: pref.email_enabled,
                NotificationChannel.SMS: pref.sms_enabled,
                NotificationChannel.PUSH: pref.push_enabled,
                NotificationChannel.IN_APP: pref.in_app_enabled,
            }.get(channel, True)
            
            if not channel_enabled:
                logger.info(f"Channel {channel} disabled for user {user_id}")
                return None
            
            # Check type preference
            type_enabled = {
                NotificationType.TRADE: pref.trade_notifications,
                NotificationType.SIGNAL: pref.signal_notifications,
                NotificationType.ALERT: pref.alert_notifications,
                NotificationType.SYSTEM: pref.system_notifications,
                NotificationType.BILLING: pref.billing_notifications,
            }.get(notification_type, True)
            
            if not type_enabled:
                logger.info(f"Type {notification_type} disabled for user {user_id}")
                return None
        
        # Create notification record
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            channel=channel,
            title=title,
            message=message,
            action_url=action_url,
            priority=priority,
            metadata=metadata or {},
            sent_at=datetime.utcnow()
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        # Send via WebSocket for in-app notifications
        if channel == NotificationChannel.IN_APP:
            await NotificationService._send_websocket_notification(user_id, notification)
        
        # Send email if requested
        if channel == NotificationChannel.EMAIL:
            await NotificationService._send_email_notification(user_id, notification, db)
        
        logger.info(f"Notification created: {notification.id} for user {user_id}")
        return notification
    
    @staticmethod
    async def _send_websocket_notification(user_id: int, notification: Notification):
        """Send notification via WebSocket"""
        try:
            await ws_manager.send_to_user(user_id, {
                "type": "notification",
                "data": {
                    "id": notification.id,
                    "type": notification.type.value,
                    "title": notification.title,
                    "message": notification.message,
                    "action_url": notification.action_url,
                    "priority": notification.priority,
                    "created_at": notification.created_at.isoformat()
                }
            })
            notification.delivered_at = datetime.utcnow()
        except Exception as e:
            logger.error(f"Failed to send WebSocket notification: {e}")
            notification.failed_at = datetime.utcnow()
            notification.failure_reason = str(e)
    
    @staticmethod
    async def _send_email_notification(
        user_id: int,
        notification: Notification,
        db: Session
    ):
        """Send notification via email"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.email:
                logger.warning(f"No email found for user {user_id}")
                return
            
            # Check if SMTP is configured
            smtp_host = getattr(settings, "SMTP_HOST", None)
            if not smtp_host:
                logger.warning("SMTP not configured, skipping email notification")
                return
            
            # Create email
            msg = MIMEMultipart("alternative")
            msg["Subject"] = notification.title
            msg["From"] = getattr(settings, "EMAIL_FROM", "noreply@trading-engine.com")
            msg["To"] = user.email
            
            # Email body
            text = f"""
{notification.title}

{notification.message}

{notification.action_url if notification.action_url else ""}
"""
            html = f"""
<html>
<body>
<h2>{notification.title}</h2>
<p>{notification.message}</p>
{f'<p><a href="{notification.action_url}">View Details</a></p>' if notification.action_url else ''}
</body>
</html>
"""
            
            part1 = MIMEText(text, "plain")
            part2 = MIMEText(html, "html")
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email
            smtp_port = getattr(settings, "SMTP_PORT", 587)
            smtp_user = getattr(settings, "SMTP_USER", None)
            smtp_password = getattr(settings, "SMTP_PASSWORD", None)
            
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if getattr(settings, "SMTP_TLS", True):
                    server.starttls()
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            notification.delivered_at = datetime.utcnow()
            db.commit()
            logger.info(f"Email notification sent to {user.email}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            notification.failed_at = datetime.utcnow()
            notification.failure_reason = str(e)
            db.commit()
    
    @staticmethod
    def get_user_notifications(
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
        db: Session = None
    ) -> List[Notification]:
        """Get user notifications"""
        if not db:
            return []
        
        query = db.query(Notification).filter(Notification.user_id == user_id)
        
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        return query.order_by(Notification.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def mark_as_read(notification_id: int, user_id: int, db: Session) -> bool:
        """Mark notification as read"""
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if notification:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            db.commit()
            return True
        
        return False
    
    @staticmethod
    def mark_all_as_read(user_id: int, db: Session) -> int:
        """Mark all user notifications as read"""
        count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update({
            Notification.is_read: True,
            Notification.read_at: datetime.utcnow()
        })
        db.commit()
        return count

notification_service = NotificationService()
