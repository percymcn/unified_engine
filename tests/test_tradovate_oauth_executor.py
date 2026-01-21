"""
Tests for TradovateExecutor OAuth Support

Tests OAuth initialization, token refresh integration, and dual-mode authentication.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
import httpx
import sys

from app.brokers.tradovate_executor import TradovateExecutor
from app.infrastructure.adapters.tradovate_adapter import TradovateAdapter
from app.models.pydantic_schemas import ExecutorOrderResponse, ExecutorTradeResponse


class TestTradovateExecutorOAuth:
    """Test suite for TradovateExecutor OAuth mode."""

    @patch("app.brokers.tradovate_executor.settings")
    def test_executor_initializes_with_oauth_token(self, mock_settings):
        """Test that executor initializes in OAuth mode when token provided."""
        mock_settings.get_broker_config.return_value = {
            "api_url": "https://demo.tradovate.com/v1",
            "ws_url": "wss://demo.tradovate.com/v1/websocket",
        }

        executor = TradovateExecutor(
            account_id=1,
            access_token="test_oauth_token",
            environment="demo",
        )

        assert executor._use_oauth is True
        assert executor._oauth_token == "test_oauth_token"
        assert executor._account_id == 1
        assert executor._oauth_environment == "demo"
        assert executor.api_url == "https://demo.tradovate.com/v1"
        assert executor.is_available is True

    @patch("app.brokers.tradovate_executor.settings")
    def test_executor_uses_live_url_for_live_environment(self, mock_settings):
        """Test that executor uses live API URL for live environment."""
        mock_settings.get_broker_config.return_value = {
            "api_url": "https://demo.tradovate.com/v1",
            "ws_url": "wss://demo.tradovate.com/v1/websocket",
        }

        executor = TradovateExecutor(
            account_id=1,
            access_token="test_oauth_token",
            environment="live",
        )

        assert executor.api_url == "https://live.tradovate.com/v1"

    @patch("app.brokers.tradovate_executor.settings")
    def test_executor_falls_back_to_password_without_oauth(self, mock_settings):
        """Test that executor uses password mode without OAuth token."""
        mock_settings.get_broker_config.return_value = {
            "api_url": "https://demo.tradovate.com/v1",
            "ws_url": "wss://demo.tradovate.com/v1/websocket",
            "user_id": "test_user",
            "password": "test_password",
        }

        executor = TradovateExecutor()

        assert executor._use_oauth is False
        assert executor.user_id == "test_user"
        assert executor.password == "test_password"
        assert executor.is_available is True

    @patch("app.brokers.tradovate_executor.settings")
    def test_executor_not_available_without_credentials(self, mock_settings):
        """Test that executor is not available without any credentials."""
        mock_settings.get_broker_config.return_value = {
            "api_url": "https://demo.tradovate.com/v1",
            "ws_url": "wss://demo.tradovate.com/v1/websocket",
        }

        executor = TradovateExecutor()

        assert executor._use_oauth is False
        assert executor.is_available is False


class TestTradovateExecutorOAuthInitialize:
    """Test OAuth initialization flow."""

    @pytest.mark.asyncio
    @patch("app.brokers.tradovate_executor.settings")
    @patch("httpx.AsyncClient")
    async def test_initialize_oauth_success(self, mock_client_class, mock_settings):
        """Test successful OAuth initialization."""
        mock_settings.get_broker_config.return_value = {
            "api_url": "https://demo.tradovate.com/v1",
            "ws_url": "wss://demo.tradovate.com/v1/websocket",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"accountId": 123}]

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        mock_session.headers = {}
        mock_session.is_closed = False

        mock_client_class.return_value = mock_session

        executor = TradovateExecutor(
            account_id=1,
            access_token="valid_token",
            environment="demo",
        )

        result = await executor.initialize()

        assert result is True
        assert executor._is_connected is True
        assert executor.access_token == "valid_token"

    @pytest.mark.asyncio
    @patch("app.brokers.tradovate_executor.settings")
    @patch("httpx.AsyncClient")
    async def test_initialize_oauth_invalid_token(self, mock_client_class, mock_settings):
        """Test OAuth initialization with invalid token."""
        mock_settings.get_broker_config.return_value = {
            "api_url": "https://demo.tradovate.com/v1",
            "ws_url": "wss://demo.tradovate.com/v1/websocket",
        }

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        mock_session.headers = {}

        mock_client_class.return_value = mock_session

        executor = TradovateExecutor(
            account_id=1,
            access_token="invalid_token",
            environment="demo",
        )

        result = await executor.initialize()

        assert result is False
        assert executor._is_connected is False


class TestTradovateExecutorTokenRefresh:
    """Test token refresh integration."""

    @pytest.mark.asyncio
    @patch("app.brokers.tradovate_executor.settings")
    async def test_ensure_valid_token_password_mode(self, mock_settings):
        """Test that password mode always returns True for token validation."""
        mock_settings.get_broker_config.return_value = {
            "api_url": "https://demo.tradovate.com/v1",
            "ws_url": "wss://demo.tradovate.com/v1/websocket",
            "user_id": "test",
            "password": "test",
        }

        executor = TradovateExecutor()
        executor.session = MagicMock()
        executor.session.headers = {}

        result = await executor._ensure_valid_token()

        assert result is True

    @pytest.mark.asyncio
    @patch("app.brokers.tradovate_executor.settings")
    async def test_ensure_valid_token_oauth_no_account_id(self, mock_settings):
        """Test token validation returns True when OAuth mode but no account ID."""
        mock_settings.get_broker_config.return_value = {
            "api_url": "https://demo.tradovate.com/v1",
            "ws_url": "wss://demo.tradovate.com/v1/websocket",
        }

        executor = TradovateExecutor(
            access_token="test_token",
            environment="demo",
        )
        executor.session = MagicMock()
        executor.session.headers = {}

        # No account_id means can't refresh, but still valid
        result = await executor._ensure_valid_token()

        assert result is True

    @pytest.mark.asyncio
    @patch("app.brokers.tradovate_executor.settings")
    async def test_ensure_valid_token_oauth_refresh_success(self, mock_settings):
        """Test successful OAuth token refresh."""
        mock_settings.get_broker_config.return_value = {
            "api_url": "https://demo.tradovate.com/v1",
            "ws_url": "wss://demo.tradovate.com/v1/websocket",
        }

        # Mock database and token service
        mock_db = MagicMock()
        mock_account = MagicMock()
        mock_account.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_account

        mock_service = MagicMock()
        mock_service.get_access_token.return_value = "refreshed_token"

        executor = TradovateExecutor(
            account_id=1,
            access_token="old_token",
            environment="demo",
        )
        executor.session = MagicMock()
        executor.session.headers = {}

        with patch("app.db.database.SessionLocal", return_value=mock_db), \
             patch("app.services.tradovate_token_service.TradovateTokenService", return_value=mock_service):
            result = await executor._ensure_valid_token()

        assert result is True
        assert executor._oauth_token == "refreshed_token"
        assert executor.access_token == "refreshed_token"
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.brokers.tradovate_executor.settings")
    async def test_ensure_valid_token_oauth_refresh_failure(self, mock_settings):
        """Test OAuth token refresh failure."""
        mock_settings.get_broker_config.return_value = {
            "api_url": "https://demo.tradovate.com/v1",
            "ws_url": "wss://demo.tradovate.com/v1/websocket",
        }

        # Mock database
        mock_db = MagicMock()
        mock_account = MagicMock()
        mock_account.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_account

        # Mock token service returning None (refresh failed)
        mock_service = MagicMock()
        mock_service.get_access_token.return_value = None

        executor = TradovateExecutor(
            account_id=1,
            access_token="old_token",
            environment="demo",
        )
        executor.session = MagicMock()
        executor.session.headers = {}

        with patch("app.db.database.SessionLocal", return_value=mock_db), \
             patch("app.services.tradovate_token_service.TradovateTokenService", return_value=mock_service):
            result = await executor._ensure_valid_token()

        assert result is False
        mock_db.close.assert_called_once()


class TestTradovateExecutorAPIWithTokenRefresh:
    """Test API methods with token refresh integration."""

    @pytest.mark.asyncio
    @patch("app.brokers.tradovate_executor.settings")
    async def test_place_order_returns_error_on_token_failure(self, mock_settings):
        """Test that place_order returns error when token refresh fails."""
        mock_settings.get_broker_config.return_value = {
            "api_url": "https://demo.tradovate.com/v1",
            "ws_url": "wss://demo.tradovate.com/v1/websocket",
        }

        executor = TradovateExecutor(
            account_id=1,
            access_token="test_token",
            environment="demo",
        )
        executor.session = MagicMock()
        executor.session.headers = {}

        # Mock _ensure_valid_token to return False
        executor._ensure_valid_token = AsyncMock(return_value=False)

        from app.models.pydantic_schemas import OrderRequest
        order = OrderRequest(
            account_id="123",
            symbol="ES",
            order_type="market_buy",
            quantity=1.0,
        )

        response = await executor.place_order(order)

        assert response.success is False
        assert "Token expired and refresh failed" in response.error

    @pytest.mark.asyncio
    @patch("app.brokers.tradovate_executor.settings")
    async def test_get_positions_returns_empty_on_token_failure(self, mock_settings):
        """Test that get_positions returns empty list when token refresh fails."""
        mock_settings.get_broker_config.return_value = {
            "api_url": "https://demo.tradovate.com/v1",
            "ws_url": "wss://demo.tradovate.com/v1/websocket",
        }

        executor = TradovateExecutor(
            account_id=1,
            access_token="test_token",
            environment="demo",
        )
        executor.session = MagicMock()
        executor.session.headers = {}

        # Mock _ensure_valid_token to return False
        executor._ensure_valid_token = AsyncMock(return_value=False)

        positions = await executor.get_positions()

        assert positions == []

    @pytest.mark.asyncio
    @patch("app.brokers.tradovate_executor.settings")
    async def test_close_position_returns_error_on_token_failure(self, mock_settings):
        """Test that close_position returns error when token refresh fails."""
        mock_settings.get_broker_config.return_value = {
            "api_url": "https://demo.tradovate.com/v1",
            "ws_url": "wss://demo.tradovate.com/v1/websocket",
        }

        executor = TradovateExecutor(
            account_id=1,
            access_token="test_token",
            environment="demo",
        )
        executor.session = MagicMock()
        executor.session.headers = {}

        # Mock _ensure_valid_token to return False
        executor._ensure_valid_token = AsyncMock(return_value=False)

        response = await executor.close_position("123")

        assert response.success is False
        assert "Token expired and refresh failed" in response.error


class TestTradovateAdapter:
    """Test TradovateAdapter OAuth support."""

    @patch("app.infrastructure.adapters.tradovate_adapter.TradovateExecutor")
    def test_adapter_passes_oauth_config_to_executor(self, mock_executor_class):
        """Test that adapter passes OAuth config to executor."""
        mock_executor = MagicMock()
        mock_executor._use_oauth = True
        mock_executor_class.return_value = mock_executor

        adapter = TradovateAdapter(
            account_id=1,
            access_token="test_token",
            environment="demo",
        )

        mock_executor_class.assert_called_once_with(
            account_id=1,
            access_token="test_token",
            environment="demo",
        )
        assert adapter.is_using_oauth is True

    @patch("app.infrastructure.adapters.tradovate_adapter.TradovateExecutor")
    def test_adapter_is_using_oauth_property(self, mock_executor_class):
        """Test is_using_oauth property reflects executor state."""
        mock_executor = MagicMock()
        mock_executor._use_oauth = False
        mock_executor_class.return_value = mock_executor

        adapter = TradovateAdapter()

        assert adapter.is_using_oauth is False

    def test_adapter_accepts_pre_configured_executor(self):
        """Test that adapter accepts a pre-configured executor."""
        mock_executor = MagicMock()
        mock_executor._use_oauth = True

        adapter = TradovateAdapter(executor=mock_executor)

        assert adapter._executor is mock_executor
        assert adapter.is_using_oauth is True
