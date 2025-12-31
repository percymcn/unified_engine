"""
Tests for Notification Router
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.models import User
from app.models.enhanced_models import Notification, NotificationType, NotificationChannel

client = TestClient(app)

@pytest.fixture
def test_user(db: Session):
    """Create test user"""
    user = User(
        email="test@test.com",
        username="testuser",
        hashed_password="hashed",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user):
    """Get auth headers"""
    return {"Authorization": f"Bearer test-token-{test_user.id}"}

def test_get_notifications(auth_headers, test_user, db: Session):
    """Test get notifications endpoint"""
    # Create test notification
    notification = Notification(
        user_id=test_user.id,
        type=NotificationType.SYSTEM,
        channel=NotificationChannel.IN_APP,
        title="Test",
        message="Test message"
    )
    db.add(notification)
    db.commit()
    
    response = client.get("/api/v1/notifications", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_unread_count(auth_headers, test_user, db: Session):
    """Test unread count endpoint"""
    response = client.get("/api/v1/notifications/unread/count", headers=auth_headers)
    assert response.status_code == 200
    assert "count" in response.json()

def test_mark_notification_read(auth_headers, test_user, db: Session):
    """Test mark notification as read"""
    notification = Notification(
        user_id=test_user.id,
        type=NotificationType.SYSTEM,
        channel=NotificationChannel.IN_APP,
        title="Test",
        message="Test message"
    )
    db.add(notification)
    db.commit()
    
    response = client.post(f"/api/v1/notifications/{notification.id}/read", headers=auth_headers)
    assert response.status_code == 200
    
    # Verify notification is marked as read
    db.refresh(notification)
    assert notification.is_read == True

def test_mark_all_read(auth_headers, test_user, db: Session):
    """Test mark all notifications as read"""
    # Create multiple notifications
    for i in range(3):
        notification = Notification(
            user_id=test_user.id,
            type=NotificationType.SYSTEM,
            channel=NotificationChannel.IN_APP,
            title=f"Test {i}",
            message="Test message"
        )
        db.add(notification)
    db.commit()
    
    response = client.post("/api/v1/notifications/read-all", headers=auth_headers)
    assert response.status_code == 200

def test_get_notification_preferences(auth_headers):
    """Test get notification preferences"""
    response = client.get("/api/v1/notifications/preferences", headers=auth_headers)
    assert response.status_code == 200
    assert "email_enabled" in response.json()

def test_update_notification_preferences(auth_headers):
    """Test update notification preferences"""
    data = {"email_enabled": False, "in_app_enabled": True}
    response = client.put("/api/v1/notifications/preferences", json=data, headers=auth_headers)
    assert response.status_code == 200
