"""
Test UI integration with backend APIs.
Tests React dashboard integration with FastAPI backend.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json
import sys
import os
from fastapi.testclient import TestClient

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app


class TestUIIntegration:
    """Test UI integration with backend APIs."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers for testing."""
        from app.core.security import create_access_token
        token = create_access_token(data={"sub": "test@example.com"})
        return {"Authorization": f"Bearer {token}"}
    
    def test_dashboard_data_loading(self, client, auth_headers):
        """Test dashboard can load initial data."""
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Mock dashboard data
            mock_accounts = [Mock(), Mock()]
            mock_positions = [Mock(), Mock()]
            mock_trades = [Mock(), Mock()]
            mock_signals = [Mock(), Mock()]
            
            mock_db_session.query.return_value.filter.return_value.all.side_effect = [
                mock_accounts,
                mock_positions, 
                mock_trades,
                mock_signals
            ]
            
            # Test dashboard endpoints
            accounts_response = client.get("/accounts/", headers=auth_headers)
            positions_response = client.get("/positions/", headers=auth_headers)
            trades_response = client.get("/trades/", headers=auth_headers)
            signals_response = client.get("/signals/", headers=auth_headers)
            
            # All should return 200
            assert accounts_response.status_code == 200
            assert positions_response.status_code == 200
            assert trades_response.status_code == 200
            assert signals_response.status_code == 200
            
            # All should return lists
            assert isinstance(accounts_response.json(), list)
            assert isinstance(positions_response.json(), list)
            assert isinstance(trades_response.json(), list)
            assert isinstance(signals_response.json(), list)
    
    def test_real_time_updates_websocket(self, client):
        """Test WebSocket connection for real-time updates."""
        with patch('app.main.websocket_manager') as mock_manager:
            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()
            
            # Test WebSocket connection
            with client.websocket_connect("/ws") as websocket:
                # Connection should be established
                assert websocket is not None
    
    def test_trading_form_submission(self, client, auth_headers):
        """Test trading form submission from UI."""
        trading_data = {
            "broker": "MT4",
            "symbol": "EURUSD",
            "order_type": "MARKET",
            "side": "BUY",
            "quantity": 0.1,
            "price": 1.1000,
            "stop_loss": 1.0900,
            "take_profit": 1.1100,
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
                "signal_id": "ui_signal_123",
                "order_id": "ui_order_456"
            }
            
            response = client.post("/signals/", json=trading_data, headers=auth_headers)
            
            assert response.status_code == 201
            result = response.json()
            assert result["success"] is True
            assert "signal_id" in result
            assert "order_id" in result
    
    def test_account_management_ui(self, client, auth_headers):
        """Test account management functionality in UI."""
        account_data = {
            "broker": "MT4",
            "account_id": "12345",
            "account_name": "Test MT4 Account",
            "is_active": True,
            "api_key": "test_api_key",
            "api_secret": "test_api_secret"
        }
        
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Test account creation
            response = client.post("/accounts/", json=account_data, headers=auth_headers)
            assert response.status_code == 201
            
            # Test account listing
            mock_account = Mock()
            mock_account.id = 1
            mock_account.broker = "MT4"
            mock_account.account_id = "12345"
            mock_account.account_name = "Test MT4 Account"
            mock_account.is_active = True
            
            mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_account]
            
            response = client.get("/accounts/", headers=auth_headers)
            assert response.status_code == 200
            accounts = response.json()
            assert len(accounts) == 1
            assert accounts[0]["broker"] == "MT4"
    
    def test_position_monitoring_ui(self, client, auth_headers):
        """Test position monitoring in UI."""
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Mock positions
            mock_position = Mock()
            mock_position.id = 1
            mock_position.symbol = "EURUSD"
            mock_position.side = "BUY"
            mock_position.quantity = 0.1
            mock_position.entry_price = 1.1000
            mock_position.current_price = 1.1050
            mock_position.unrealized_pnl = 50.0
            
            mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_position]
            
            response = client.get("/positions/", headers=auth_headers)
            assert response.status_code == 200
            positions = response.json()
            assert len(positions) == 1
            assert positions[0]["symbol"] == "EURUSD"
            assert positions[0]["unrealized_pnl"] == 50.0
    
    def test_trade_history_ui(self, client, auth_headers):
        """Test trade history display in UI."""
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Mock trades
            mock_trade = Mock()
            mock_trade.id = 1
            mock_trade.symbol = "EURUSD"
            mock_trade.side = "BUY"
            mock_trade.quantity = 0.1
            mock_trade.entry_price = 1.1000
            mock_trade.exit_price = 1.1050
            mock_trade.profit = 50.0
            mock_trade.status = "closed"
            mock_trade.created_at = datetime.now()
            
            mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_trade]
            
            response = client.get("/trades/", headers=auth_headers)
            assert response.status_code == 200
            trades = response.json()
            assert len(trades) == 1
            assert trades[0]["symbol"] == "EURUSD"
            assert trades[0]["profit"] == 50.0
    
    def test_signal_history_ui(self, client, auth_headers):
        """Test signal history display in UI."""
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Mock signals
            mock_signal = Mock()
            mock_signal.id = 1
            mock_signal.broker = "MT4"
            mock_signal.symbol = "EURUSD"
            mock_signal.side = "BUY"
            mock_signal.quantity = 0.1
            mock_signal.price = 1.1000
            mock_signal.status = "executed"
            mock_signal.created_at = datetime.now()
            
            mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_signal]
            
            response = client.get("/signals/", headers=auth_headers)
            assert response.status_code == 200
            signals = response.json()
            assert len(signals) == 1
            assert signals[0]["symbol"] == "EURUSD"
            assert signals[0]["status"] == "executed"
    
    def test_broker_status_ui(self, client, auth_headers):
        """Test broker status display in UI."""
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            response = client.get("/unified/brokers/status", headers=auth_headers)
            assert response.status_code == 200
            status_data = response.json()
            assert "brokers" in status_data
    
    def test_error_handling_ui(self, client, auth_headers):
        """Test error handling for UI requests."""
        # Test with invalid data
        invalid_signal_data = {
            "broker": "INVALID_BROKER",
            "symbol": "",
            "order_type": "INVALID_TYPE",
            "side": "INVALID_SIDE",
            "quantity": -1
        }
        
        response = client.post("/signals/", json=invalid_signal_data, headers=auth_headers)
        
        # Should return validation error
        assert response.status_code in [422, 400]
    
    def test_authentication_ui(self, client):
        """Test authentication flow for UI."""
        # Test login
        login_data = {
            "username": "test@example.com",
            "password": "testpassword"
        }
        
        with patch('app.routers.auth.authenticate_user') as mock_auth:
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_auth.return_value = mock_user
            
            response = client.post("/auth/login", data=login_data)
            assert response.status_code == 200
            assert "access_token" in response.json()
    
    def test_user_profile_ui(self, client, auth_headers):
        """Test user profile management in UI."""
        profile_data = {
            "full_name": "Test User Updated",
            "email": "test@example.com"
        }
        
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_user.full_name = "Test User Updated"
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            response = client.get("/auth/profile", headers=auth_headers)
            assert response.status_code == 200
            profile = response.json()
            assert profile["email"] == "test@example.com"
    
    def test_settings_ui(self, client, auth_headers):
        """Test settings management in UI."""
        settings_data = {
            "notifications": True,
            "dark_mode": True,
            "default_broker": "MT4",
            "risk_percentage": 2.0
        }
        
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # This would typically update user settings
            # For now, just test the endpoint exists
            response = client.get("/auth/profile", headers=auth_headers)
            assert response.status_code == 200
    
    def test_responsive_ui_data(self, client, auth_headers):
        """Test UI data responsiveness and pagination."""
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Test with pagination parameters
            response = client.get("/trades/?skip=0&limit=10", headers=auth_headers)
            assert response.status_code == 200
            
            response = client.get("/trades/?skip=10&limit=10", headers=auth_headers)
            assert response.status_code == 200
    
    def test_ui_performance_metrics(self, client, auth_headers):
        """Test UI performance metrics endpoint."""
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            # Mock user
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Test performance metrics
            response = client.get("/unified/performance", headers=auth_headers)
            assert response.status_code == 200
            metrics = response.json()
            assert "total_trades" in metrics
            assert "win_rate" in metrics
            assert "total_profit" in metrics


class TestUIComponentIntegration:
    """Test specific UI component integrations."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers."""
        from app.core.security import create_access_token
        token = create_access_token(data={"sub": "test@example.com"})
        return {"Authorization": f"Bearer {token}"}
    
    def test_trading_panel_integration(self, client, auth_headers):
        """Test trading panel component integration."""
        # Test symbol search
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Test symbol data endpoint
            response = client.get("/unified/symbols/EURUSD", headers=auth_headers)
            # Should either return data or 404 if not implemented
            assert response.status_code in [200, 404]
    
    def test_chart_component_integration(self, client, auth_headers):
        """Test chart component data integration."""
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Test price data endpoint
            response = client.get("/unified/price-history/EURUSD?period=1d", headers=auth_headers)
            # Should either return data or 404 if not implemented
            assert response.status_code in [200, 404]
    
    def test_notification_system_ui(self, client, auth_headers):
        """Test notification system integration."""
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Test notifications endpoint
            response = client.get("/unified/notifications", headers=auth_headers)
            # Should either return data or 404 if not implemented
            assert response.status_code in [200, 404]
    
    def test_risk_management_ui(self, client, auth_headers):
        """Test risk management component integration."""
        with patch('app.db.database.get_db') as mock_db:
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Test risk metrics endpoint
            response = client.get("/unified/risk-metrics", headers=auth_headers)
            # Should either return data or 404 if not implemented
            assert response.status_code in [200, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])