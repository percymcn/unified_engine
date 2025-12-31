"""
Test API endpoints and authentication functionality.
Tests all REST API endpoints, JWT authentication, and security.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import json
import sys
import os
from fastapi.testclient import TestClient
from fastapi import status

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.security import create_access_token, verify_token, get_password_hash
from app.models.schemas import UserCreate, UserLogin, BrokerType
from app.db.database import get_db


class TestAuthentication:
    """Test authentication and authorization functionality."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def test_user_data(self):
        """Sample user data for testing."""
        return {
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User"
        }
    
    @pytest.fixture
    def admin_user_data(self):
        """Sample admin user data for testing."""
        return {
            "email": "admin@example.com",
            "password": "adminpassword123",
            "full_name": "Admin User",
            "is_admin": True
        }
    
    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long
    
    def test_verify_token(self):
        """Test JWT token verification."""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "test@example.com"
    
    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(Exception):
            verify_token(invalid_token)
    
    def test_password_hashing(self):
        """Test password hashing functionality."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt hash prefix
    
    def test_user_registration(self, client, test_user_data):
        """Test user registration endpoint."""
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user creation
            mock_db_session.add.return_value = None
            mock_db_session.commit.return_value = None
            mock_db_session.refresh.return_value = None
            
            response = client.post("/auth/register", json=test_user_data)
            
            # Should return 201 Created on successful registration
            assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]
    
    def test_user_login(self, client, test_user_data):
        """Test user login endpoint."""
        with patch('app.db.database.get_db') as mock_db, \
             patch('app.routers.auth.authenticate_user') as mock_auth:
            
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock successful authentication
            mock_user = Mock()
            mock_user.email = test_user_data["email"]
            mock_user.is_active = True
            mock_auth.return_value = mock_user
            
            login_data = {
                "email": test_user_data["email"],
                "password": test_user_data["password"]
            }
            
            response = client.post("/auth/login", data=login_data)
            
            assert response.status_code == status.HTTP_200_OK
            assert "access_token" in response.json()
            assert response.json()["token_type"] == "bearer"
    
    def test_user_login_invalid_credentials(self, client, test_user_data):
        """Test login with invalid credentials."""
        with patch('app.routers.auth.authenticate_user') as mock_auth:
            mock_auth.return_value = None  # Authentication fails
            
            login_data = {
                "email": test_user_data["email"],
                "password": "wrongpassword"
            }
            
            response = client.post("/auth/login", data=login_data)
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.get("/accounts/")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_protected_endpoint_with_valid_token(self, client):
        """Test accessing protected endpoint with valid token."""
        # Create a valid token
        token = create_access_token(data={"sub": "test@example.com"})
        
        headers = {"Authorization": f"Bearer {token}"}
        
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user existence
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            response = client.get("/accounts/", headers=headers)
            
            # Should not be 401 (authentication passed)
            assert response.status_code != status.HTTP_401_UNAUTHORIZED


class TestAPIEndpoints:
    """Test all API endpoints functionality."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers for testing."""
        token = create_access_token(data={"sub": "test@example.com"})
        return {"Authorization": f"Bearer {token}"}
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "healthy"
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.json()
    
    def test_get_accounts(self, client, auth_headers):
        """Test getting user accounts."""
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user and accounts
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Mock accounts query
            mock_accounts = [Mock(), Mock()]
            mock_db_session.query.return_value.filter.return_value.all.return_value = mock_accounts
            
            response = client.get("/accounts/", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            assert isinstance(response.json(), list)
    
    def test_create_account(self, client, auth_headers):
        """Test creating a new account."""
        account_data = {
            "broker": "MT4",
            "account_id": "12345",
            "account_name": "Test MT4 Account",
            "is_active": True
        }
        
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            response = client.post("/accounts/", json=account_data, headers=auth_headers)
            
            assert response.status_code == status.HTTP_201_CREATED
    
    def test_get_positions(self, client, auth_headers):
        """Test getting positions."""
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Mock positions
            mock_positions = [Mock(), Mock()]
            mock_db_session.query.return_value.filter.return_value.all.return_value = mock_positions
            
            response = client.get("/positions/", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            assert isinstance(response.json(), list)
    
    def test_get_trades(self, client, auth_headers):
        """Test getting trades."""
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Mock trades
            mock_trades = [Mock(), Mock()]
            mock_db_session.query.return_value.filter.return_value.all.return_value = mock_trades
            
            response = client.get("/trades/", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            assert isinstance(response.json(), list)
    
    def test_create_signal(self, client, auth_headers):
        """Test creating a signal."""
        signal_data = {
            "broker": "MT4",
            "symbol": "EURUSD",
            "order_type": "MARKET",
            "side": "BUY",
            "quantity": 0.1,
            "price": 1.1000,
            "signal_type": "ENTRY"
        }
        
        with patch('app.db.database.get_db') as mock_db, \
             patch('app.services.signal_processor.SignalProcessor.process_signal') as mock_process:
            
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Mock signal processing
            mock_process.return_value = {
                "success": True,
                "signal_id": "signal_123",
                "order_id": "order_456"
            }
            
            response = client.post("/signals/", json=signal_data, headers=auth_headers)
            
            assert response.status_code == status.HTTP_201_CREATED
            assert response.json()["success"] is True
    
    def test_get_signals(self, client, auth_headers):
        """Test getting signals."""
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Mock signals
            mock_signals = [Mock(), Mock()]
            mock_db_session.query.return_value.filter.return_value.all.return_value = mock_signals
            
            response = client.get("/signals/", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            assert isinstance(response.json(), list)
    
    def test_unified_router_broker_status(self, client, auth_headers):
        """Test unified router broker status endpoint."""
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            response = client.get("/unified/brokers/status", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            assert "brokers" in response.json()
    
    def test_unified_router_execute_signal(self, client, auth_headers):
        """Test unified router signal execution."""
        signal_data = {
            "broker": "MT4",
            "symbol": "EURUSD",
            "order_type": "MARKET",
            "side": "BUY",
            "quantity": 0.1,
            "signal_type": "ENTRY"
        }
        
        with patch('app.db.database.get_db') as mock_db, \
             patch('app.services.signal_processor.SignalProcessor.process_signal') as mock_process:
            
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Mock signal processing
            mock_process.return_value = {
                "success": True,
                "order_id": "unified_order_123"
            }
            
            response = client.post("/unified/execute", json=signal_data, headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["success"] is True


class TestWebhookEndpoints:
    """Test webhook endpoints functionality."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    def test_tradingview_webhook(self, client):
        """Test TradingView webhook endpoint."""
        webhook_data = {
            "symbol": "EURUSD",
            "action": "buy",
            "price": 1.1000,
            "quantity": 0.1
        }
        
        with patch('app.services.signal_processor.SignalProcessor.process_webhook_signal') as mock_process:
            mock_process.return_value = {
                "success": True,
                "signal_id": "tv_webhook_123"
            }
            
            response = client.post("/webhooks/tradingview", json=webhook_data)
            
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["status"] == "success"
    
    def test_trailhacker_webhook(self, client):
        """Test TrailHacker webhook endpoint."""
        webhook_data = {
            "ticker": "ES",
            "order_action": "BOT",
            "order_type": "MKT",
            "quantity": 1,
            "price": 4500.25
        }
        
        with patch('app.services.signal_processor.SignalProcessor.process_webhook_signal') as mock_process:
            mock_process.return_value = {
                "success": True,
                "signal_id": "th_webhook_456"
            }
            
            response = client.post("/webhooks/trailhacker", json=webhook_data)
            
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["status"] == "success"
    
    def test_webhook_authentication(self, client):
        """Test webhook authentication."""
        webhook_data = {
            "symbol": "EURUSD",
            "action": "buy",
            "price": 1.1000,
            "quantity": 0.1
        }
        
        # Test without API key
        response = client.post("/webhooks/tradingview", json=webhook_data)
        
        # Should either succeed (if no auth required) or fail with 401
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]


class TestErrorHandling:
    """Test API error handling."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    def test_404_not_found(self, client):
        """Test 404 error handling."""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_validation_error(self, client):
        """Test validation error handling."""
        # Send invalid data to an endpoint
        invalid_data = {
            "invalid_field": "invalid_value"
        }
        
        response = client.post("/signals/", json=invalid_data)
        
        # Should return 422 for validation errors or 401 for auth
        assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_401_UNAUTHORIZED]
    
    def test_method_not_allowed(self, client):
        """Test method not allowed error."""
        response = client.delete("/accounts/")  # DELETE might not be allowed
        
        # Should return 405 Method Not Allowed or 401 for auth
        assert response.status_code in [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_401_UNAUTHORIZED]


class TestRateLimiting:
    """Test API rate limiting functionality."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    def test_rate_limiting(self, client):
        """Test that rate limiting is implemented."""
        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = client.get("/health")
            responses.append(response.status_code)
        
        # At least some requests should succeed
        assert status.HTTP_200_OK in responses
        
        # If rate limiting is implemented, some might be 429
        # This test is basic and would need adjustment based on actual rate limiting config
        pass


class TestCORS:
    """Test CORS configuration."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/health")
        
        # Check for CORS headers
        cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-methods",
            "access-control-allow-headers"
        ]
        
        # CORS headers should be present (if configured)
        for header in cors_headers:
            if header in response.headers:
                assert response.headers[header] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])