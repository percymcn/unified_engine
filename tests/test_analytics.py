"""
Tests for Analytics Router
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.models import User
from app.models.enhanced_models import UserSubscription, SubscriptionTier, SubscriptionStatus

client = TestClient(app)

@pytest.fixture
def admin_user(db: Session):
    """Create admin user for testing"""
    user = User(
        email="admin@test.com",
        username="admin",
        hashed_password="hashed",
        role="admin",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def auth_headers(admin_user):
    """Get auth headers for admin user"""
    # In real implementation, get token from login endpoint
    return {"Authorization": f"Bearer test-token-{admin_user.id}"}

def test_get_dashboard_stats(auth_headers):
    """Test dashboard stats endpoint"""
    response = client.get("/api/v1/analytics/dashboard", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_users" in data
    assert "active_users" in data
    assert "total_organizations" in data

def test_get_user_signups(auth_headers):
    """Test user signups endpoint"""
    response = client.get("/api/v1/analytics/user-signups?days=30", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_subscription_distribution(auth_headers):
    """Test subscription distribution endpoint"""
    response = client.get("/api/v1/analytics/subscription-distribution", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_revenue_stats(auth_headers):
    """Test revenue stats endpoint"""
    response = client.get("/api/v1/analytics/revenue?period=month&months=6", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_api_usage(auth_headers):
    """Test API usage endpoint"""
    response = client.get("/api/v1/analytics/api-usage?days=30", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_analytics_requires_auth():
    """Test analytics endpoints require authentication"""
    response = client.get("/api/v1/analytics/dashboard")
    assert response.status_code == 401

def test_analytics_requires_admin_role():
    """Test analytics endpoints require admin role"""
    # Create regular user
    # Test that regular user cannot access analytics
    pass  # Implement with proper auth setup
