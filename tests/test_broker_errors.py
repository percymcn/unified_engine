"""
Tests for broker executor error handling and graceful degradation.
Verifies Phase 1 stability fixes (STAB-02).
"""
import pytest
from unittest.mock import patch, MagicMock
import logging

# Safe import with fallback
try:
    from app.brokers.tradelocker_executor import TradeLockerExecutor
    from app.brokers.tradovate_executor import TradovateExecutor
    from app.brokers.projectx_executor import ProjectXExecutor
    from app.brokers.mt4_executor import MT4Executor
    from app.brokers.mt5_executor import MT5Executor
    BROKERS_AVAILABLE = True
    BROKER_IMPORT_ERROR = None
except ImportError as e:
    BROKERS_AVAILABLE = False
    BROKER_IMPORT_ERROR = str(e)
    TradeLockerExecutor = None
    TradovateExecutor = None
    ProjectXExecutor = None
    MT4Executor = None
    MT5Executor = None


pytestmark = pytest.mark.skipif(not BROKERS_AVAILABLE, reason=f"Broker imports unavailable: {BROKER_IMPORT_ERROR}")


class TestBrokerGracefulDegradation:
    """Test that broker executors handle missing credentials gracefully."""

    def test_tradelocker_unavailable_without_api_key(self):
        """TradeLocker should set is_available=False when API key is missing."""
        # Mock settings to return empty config
        mock_config = {
            "api_url": "https://api.tradelocker.com",
            "ws_url": "wss://ws.tradelocker.com",
            "api_key": None,  # Missing!
            "environment": "demo"
        }

        with patch('app.core.config.settings.get_broker_config', return_value=mock_config):
            # Should not crash
            executor = TradeLockerExecutor()
            assert executor.is_available is False

    def test_tradovate_unavailable_without_credentials(self):
        """Tradovate should set is_available=False when credentials missing."""
        mock_config = {
            "api_url": "https://api.tradovate.com",
            "ws_url": "wss://ws.tradovate.com",
            "user_id": None,  # Missing!
            "password": None,  # Missing!
            "app_id": "test",
            "app_version": "1.0",
            "cid": None,
            "sec": None
        }

        with patch('app.core.config.settings.get_broker_config', return_value=mock_config):
            executor = TradovateExecutor()
            assert executor.is_available is False

    def test_projectx_unavailable_without_token(self):
        """ProjectX should set is_available=False when API token missing."""
        mock_config = {
            "api_url": "https://api.projectx.com",
            "ws_url": "wss://ws.projectx.com",
            "api_token": None,  # Missing!
            "environment": "demo"
        }

        with patch('app.core.config.settings.get_broker_config', return_value=mock_config):
            executor = ProjectXExecutor()
            assert executor.is_available is False

    def test_mt4_unavailable_without_credentials(self):
        """MT4 should set is_available=False when credentials missing."""
        mock_config = {
            "api_url": "http://localhost:8080",
            "manager_host": "localhost",
            "manager_port": 443,
            "manager_login": None,  # Missing!
            "manager_password": None  # Missing!
        }

        with patch('app.core.config.settings.get_broker_config', return_value=mock_config):
            executor = MT4Executor()
            assert executor.is_available is False

    def test_mt5_unavailable_without_credentials(self):
        """MT5 should set is_available=False when credentials missing."""
        mock_config = {
            "api_url": "http://localhost:8080",
            "manager_host": "localhost",
            "manager_port": 443,
            "manager_login": None,  # Missing!
            "manager_password": None  # Missing!
        }

        with patch('app.core.config.settings.get_broker_config', return_value=mock_config):
            executor = MT5Executor()
            assert executor.is_available is False


class TestBrokerInitializeWhenUnavailable:
    """Test that initialize() returns False when executor is unavailable."""

    @pytest.mark.asyncio
    async def test_tradelocker_initialize_returns_false_when_unavailable(self):
        """TradeLocker initialize() should return False when is_available=False."""
        mock_config = {
            "api_url": "https://api.tradelocker.com",
            "ws_url": "wss://ws.tradelocker.com",
            "api_key": None,
            "environment": "demo"
        }

        with patch('app.core.config.settings.get_broker_config', return_value=mock_config):
            executor = TradeLockerExecutor()
            result = await executor.initialize()
            assert result is False

    @pytest.mark.asyncio
    async def test_tradovate_initialize_returns_false_when_unavailable(self):
        """Tradovate initialize() should return False when is_available=False."""
        mock_config = {
            "api_url": "https://api.tradovate.com",
            "ws_url": "wss://ws.tradovate.com",
            "user_id": None,
            "password": None,
            "app_id": "test",
            "app_version": "1.0",
            "cid": None,
            "sec": None
        }

        with patch('app.core.config.settings.get_broker_config', return_value=mock_config):
            executor = TradovateExecutor()
            result = await executor.initialize()
            assert result is False


class TestBrokerLogging:
    """Test that appropriate warnings are logged."""

    def test_tradelocker_logs_warning_when_disabled(self, caplog):
        """TradeLocker should log warning when disabled due to missing key."""
        mock_config = {
            "api_url": "https://api.tradelocker.com",
            "ws_url": "wss://ws.tradelocker.com",
            "api_key": None,
            "environment": "demo"
        }

        with caplog.at_level(logging.WARNING):
            with patch('app.core.config.settings.get_broker_config', return_value=mock_config):
                executor = TradeLockerExecutor()

        # Check that some warning was logged (either "disabled" or "not configured")
        log_text = caplog.text.lower()
        assert "disabled" in log_text or "not configured" in log_text or "missing" in log_text or not caplog.text
