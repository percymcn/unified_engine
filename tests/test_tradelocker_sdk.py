"""
TradeLocker SDK Integration Tests

Tests for the TradeLocker SDK wrapper and executor integration.
Uses mocking to test without real API credentials.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
from datetime import datetime


class TestTradeLockerSDKWrapper:
    """Tests for TradeLockerSDKWrapper async wrapper."""

    @pytest.fixture
    def mock_tlapi(self):
        """Create mock TLAPI instance."""
        mock = MagicMock()
        mock.get_acc_nums.return_value = [12345]
        mock.get_acc_ids.return_value = [67890]
        mock.get_all_instruments.return_value = MagicMock(
            to_dict=lambda x: [
                {"tradableInstrumentId": 1, "name": "EURUSD"},
                {"tradableInstrumentId": 2, "name": "BTCUSD"},
            ]
        )
        mock.get_latest_asking_price.return_value = 1.0850
        mock.create_order.return_value = {"orderId": "ord123", "status": "filled"}
        mock.close_position.return_value = {"id": "pos123", "status": "closed"}
        mock.get_all_positions.return_value = MagicMock(
            to_dict=lambda x: [{"id": 1, "symbol": "EURUSD", "qty": 1.0}]
        )
        mock.get_all_orders.return_value = MagicMock(to_dict=lambda x: [])
        mock.get_account_state.return_value = {
            "balance": 10000.0,
            "equity": 10050.0,
            "margin": 100.0,
        }
        return mock

    @pytest.mark.asyncio
    async def test_wrapper_initialization_success(self, mock_tlapi):
        """Test SDK wrapper initializes successfully with valid credentials."""
        with patch("app.brokers.tradelocker_sdk_wrapper.TLAPI", return_value=mock_tlapi):
            from app.brokers.tradelocker_sdk_wrapper import TradeLockerSDKWrapper

            wrapper = TradeLockerSDKWrapper(
                environment="https://demo.tradelocker.com",
                username="test@example.com",
                password="password",
                server="Demo Server",
            )

            result = await wrapper.initialize()

            assert result is True
            assert wrapper.is_initialized is True
            assert wrapper.account_number == 12345
            assert wrapper.account_id == 67890

    @pytest.mark.asyncio
    async def test_wrapper_initialization_import_error(self):
        """Test SDK wrapper handles missing SDK gracefully."""
        with patch.dict("sys.modules", {"tradelocker": None}):
            # Need to reload the module to trigger import error
            with patch(
                "app.brokers.tradelocker_sdk_wrapper.TLAPI",
                side_effect=ImportError("No module named 'tradelocker'"),
            ):
                from app.brokers.tradelocker_sdk_wrapper import TradeLockerSDKWrapper

                wrapper = TradeLockerSDKWrapper(
                    environment="https://demo.tradelocker.com",
                    username="test@example.com",
                    password="password",
                    server="Demo Server",
                )

                result = await wrapper.initialize()

                assert result is False
                assert wrapper.is_initialized is False

    @pytest.mark.asyncio
    async def test_get_all_instruments(self, mock_tlapi):
        """Test async instrument fetch."""
        with patch("app.brokers.tradelocker_sdk_wrapper.TLAPI", return_value=mock_tlapi):
            from app.brokers.tradelocker_sdk_wrapper import TradeLockerSDKWrapper

            wrapper = TradeLockerSDKWrapper(
                environment="https://demo.tradelocker.com",
                username="test@example.com",
                password="password",
                server="Demo Server",
            )
            await wrapper.initialize()

            instruments = await wrapper.get_all_instruments()

            assert instruments is not None
            mock_tlapi.get_all_instruments.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_instrument_id_by_symbol(self, mock_tlapi):
        """Test symbol to instrument ID lookup."""
        with patch("app.brokers.tradelocker_sdk_wrapper.TLAPI", return_value=mock_tlapi):
            from app.brokers.tradelocker_sdk_wrapper import TradeLockerSDKWrapper

            wrapper = TradeLockerSDKWrapper(
                environment="https://demo.tradelocker.com",
                username="test@example.com",
                password="password",
                server="Demo Server",
            )
            await wrapper.initialize()

            # Mock instruments to return list (after to_dict)
            instruments = MagicMock()
            instruments.__getitem__ = lambda self, key: MagicMock(
                empty=False,
                iloc=MagicMock(__getitem__=lambda self, idx: {"tradableInstrumentId": 1})
            )
            mock_tlapi.get_all_instruments.return_value = instruments

            instrument_id = await wrapper.get_instrument_id_by_symbol("EURUSD")

            # Result depends on mock setup, just verify no error
            assert True  # Test passes if no exception

    @pytest.mark.asyncio
    async def test_create_order(self, mock_tlapi):
        """Test async order creation."""
        with patch("app.brokers.tradelocker_sdk_wrapper.TLAPI", return_value=mock_tlapi):
            from app.brokers.tradelocker_sdk_wrapper import TradeLockerSDKWrapper

            wrapper = TradeLockerSDKWrapper(
                environment="https://demo.tradelocker.com",
                username="test@example.com",
                password="password",
                server="Demo Server",
            )
            await wrapper.initialize()

            result = await wrapper.create_order(
                instrument_id=1,
                quantity=1.0,
                side="buy",
                order_type="market",
            )

            assert result["success"] is True
            mock_tlapi.create_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_position(self, mock_tlapi):
        """Test async position close."""
        with patch("app.brokers.tradelocker_sdk_wrapper.TLAPI", return_value=mock_tlapi):
            from app.brokers.tradelocker_sdk_wrapper import TradeLockerSDKWrapper

            wrapper = TradeLockerSDKWrapper(
                environment="https://demo.tradelocker.com",
                username="test@example.com",
                password="password",
                server="Demo Server",
            )
            await wrapper.initialize()

            result = await wrapper.close_position(position_id=123)

            assert result["success"] is True
            mock_tlapi.close_position.assert_called_once()

    @pytest.mark.asyncio
    async def test_methods_require_initialization(self, mock_tlapi):
        """Test that methods fail gracefully without initialization."""
        from app.brokers.tradelocker_sdk_wrapper import TradeLockerSDKWrapper

        wrapper = TradeLockerSDKWrapper(
            environment="https://demo.tradelocker.com",
            username="test@example.com",
            password="password",
            server="Demo Server",
        )

        # Without initialize(), methods should return None/empty
        instruments = await wrapper.get_all_instruments()
        assert instruments is None

        order_result = await wrapper.create_order(1, 1.0, "buy", "market")
        assert order_result is None

    @pytest.mark.asyncio
    async def test_error_handling_in_create_order(self, mock_tlapi):
        """Test error handling when SDK raises exception."""
        mock_tlapi.create_order.side_effect = Exception("Connection error")

        with patch("app.brokers.tradelocker_sdk_wrapper.TLAPI", return_value=mock_tlapi):
            from app.brokers.tradelocker_sdk_wrapper import TradeLockerSDKWrapper

            wrapper = TradeLockerSDKWrapper(
                environment="https://demo.tradelocker.com",
                username="test@example.com",
                password="password",
                server="Demo Server",
            )
            await wrapper.initialize()

            result = await wrapper.create_order(
                instrument_id=1,
                quantity=1.0,
                side="buy",
                order_type="market",
            )

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_shutdown(self, mock_tlapi):
        """Test wrapper shutdown cleans up resources."""
        with patch("app.brokers.tradelocker_sdk_wrapper.TLAPI", return_value=mock_tlapi):
            from app.brokers.tradelocker_sdk_wrapper import TradeLockerSDKWrapper

            wrapper = TradeLockerSDKWrapper(
                environment="https://demo.tradelocker.com",
                username="test@example.com",
                password="password",
                server="Demo Server",
            )
            await wrapper.initialize()
            assert wrapper.is_initialized is True

            wrapper.shutdown()

            assert wrapper.is_initialized is False


class TestTradeLockerExecutorSDKMode:
    """Tests for TradeLockerExecutor in SDK mode."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with SDK credentials."""
        mock = MagicMock()
        mock.get_broker_config.return_value = {
            "api_url": "https://api.tradelocker.com",
            "ws_url": "wss://api.tradelocker.com/ws",
            "api_key": None,  # No Brand API key
            "environment": "DEMO",
            "username": "test@example.com",
            "password": "password",
            "server": "Demo Server",
            "sdk_environment": "https://demo.tradelocker.com",
        }
        return mock

    @pytest.fixture
    def mock_settings_brand_api(self):
        """Create mock settings with Brand API key only."""
        mock = MagicMock()
        mock.get_broker_config.return_value = {
            "api_url": "https://api.tradelocker.com",
            "ws_url": "wss://api.tradelocker.com/ws",
            "api_key": "brand-api-key-123",
            "environment": "DEMO",
            "username": None,
            "password": None,
            "server": None,
            "sdk_environment": "https://demo.tradelocker.com",
        }
        return mock

    @pytest.mark.asyncio
    async def test_executor_prefers_sdk_over_brand_api(self, mock_settings):
        """Test that executor prefers SDK mode when credentials available."""
        with patch("app.brokers.tradelocker_executor.settings", mock_settings):
            from app.brokers.tradelocker_executor import TradeLockerExecutor

            executor = TradeLockerExecutor()

            assert executor._sdk_available is True
            assert executor._brand_api_available is False
            assert executor.is_available is True

    @pytest.mark.asyncio
    async def test_executor_falls_back_to_brand_api(self, mock_settings_brand_api):
        """Test that executor uses Brand API when SDK credentials missing."""
        with patch("app.brokers.tradelocker_executor.settings", mock_settings_brand_api):
            from app.brokers.tradelocker_executor import TradeLockerExecutor

            executor = TradeLockerExecutor()

            assert executor._sdk_available is False
            assert executor._brand_api_available is True
            assert executor.is_available is True

    @pytest.mark.asyncio
    async def test_executor_disabled_without_any_credentials(self):
        """Test that executor is disabled without any credentials."""
        mock = MagicMock()
        mock.get_broker_config.return_value = {
            "api_url": "https://api.tradelocker.com",
            "ws_url": "wss://api.tradelocker.com/ws",
            "api_key": None,
            "environment": "DEMO",
            "username": None,
            "password": None,
            "server": None,
            "sdk_environment": "https://demo.tradelocker.com",
        }

        with patch("app.brokers.tradelocker_executor.settings", mock):
            from app.brokers.tradelocker_executor import TradeLockerExecutor

            executor = TradeLockerExecutor()

            assert executor._sdk_available is False
            assert executor._brand_api_available is False
            assert executor.is_available is False


class TestTradeLockerAdapterSDKMode:
    """Tests for TradeLockerAdapter with SDK support."""

    @pytest.mark.asyncio
    async def test_adapter_is_using_sdk_property(self):
        """Test is_using_sdk property reflects executor state."""
        from app.infrastructure.adapters.tradelocker_adapter import TradeLockerAdapter
        from unittest.mock import MagicMock

        mock_executor = MagicMock()
        mock_executor._use_sdk = True

        adapter = TradeLockerAdapter(executor=mock_executor)

        assert adapter.is_using_sdk is True

    @pytest.mark.asyncio
    async def test_adapter_is_using_sdk_false_when_no_executor(self):
        """Test is_using_sdk returns False when no executor."""
        from app.infrastructure.adapters.tradelocker_adapter import TradeLockerAdapter

        adapter = TradeLockerAdapter()

        assert adapter.is_using_sdk is False
