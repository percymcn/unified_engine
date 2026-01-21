"""
Unit tests for MetaAPI SDK Service

Tests the MetaAPISDKService wrapper for metaapi-cloud-sdk.
Uses mocking since actual MetaAPI connection requires credentials.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Import SDK service
from app.services.metaapi_sdk_service import MetaAPISDKService, SDK_AVAILABLE


class TestMetaAPISDKServiceUnit:
    """Unit tests for MetaAPISDKService with mocked SDK."""

    @pytest.fixture
    def mock_metaapi(self):
        """Create mock MetaApi instance."""
        mock_api = MagicMock()
        mock_account = AsyncMock()
        mock_connection = AsyncMock()

        # Configure account mock
        mock_account.state = "DEPLOYED"
        mock_account.deploy = AsyncMock()
        mock_account.wait_connected = AsyncMock()
        mock_account.get_streaming_connection = MagicMock(return_value=mock_connection)

        # Configure connection mock
        mock_connection.connect = AsyncMock()
        mock_connection.wait_synchronized = AsyncMock()
        mock_connection.close = AsyncMock()
        mock_connection.synchronized = True

        # Configure terminal state mock
        mock_terminal_state = MagicMock()
        mock_terminal_state.account_information = {
            "broker": "TestBroker",
            "currency": "USD",
            "server": "TestServer",
            "balance": 10000.00,
            "equity": 10500.00,
            "margin": 1000.00,
            "freeMargin": 9500.00,
            "leverage": 100,
            "name": "Test Account",
            "login": "12345",
            "platform": "mt4",
        }
        mock_terminal_state.positions = [
            {
                "id": "pos-1",
                "symbol": "EURUSD",
                "type": "POSITION_TYPE_BUY",
                "volume": 0.1,
                "openPrice": 1.0850,
                "currentPrice": 1.0860,
                "profit": 10.00,
                "commission": -0.50,
                "swap": 0.0,
                "magic": 12345,
                "comment": "Test position",
            }
        ]
        mock_terminal_state.orders = [
            {
                "id": "order-1",
                "symbol": "GBPUSD",
                "type": "ORDER_TYPE_BUY_LIMIT",
                "volume": 0.1,
                "openPrice": 1.2500,
                "stopLoss": 1.2400,
                "takeProfit": 1.2600,
                "magic": 12345,
                "state": "ORDER_STATE_PLACED",
            }
        ]
        mock_terminal_state.price = MagicMock(return_value={
            "symbol": "EURUSD",
            "bid": 1.0855,
            "ask": 1.0857,
            "time": "2026-01-21T10:00:00Z",
            "brokerTime": "2026-01-21T10:00:00Z",
        })
        mock_terminal_state.specification = MagicMock(return_value={
            "symbol": "EURUSD",
            "description": "Euro vs US Dollar",
            "currency": "EUR",
            "contractSize": 100000,
            "minVolume": 0.01,
            "maxVolume": 100.0,
            "volumeStep": 0.01,
            "digits": 5,
            "point": 0.00001,
        })
        mock_terminal_state.prices = {"EURUSD": mock_terminal_state.price()}

        mock_connection.terminal_state = mock_terminal_state

        # Health monitor
        mock_health = MagicMock()
        mock_health.server_health_status = "healthy"
        mock_health.uptime = 3600
        mock_connection.health_monitor = mock_health

        # Trading methods
        mock_connection.create_market_buy_order = AsyncMock(return_value={
            "orderId": "order-123",
            "positionId": "pos-123",
            "stringCode": "TRADE_RETCODE_DONE",
        })
        mock_connection.create_market_sell_order = AsyncMock(return_value={
            "orderId": "order-124",
            "positionId": "pos-124",
            "stringCode": "TRADE_RETCODE_DONE",
        })
        mock_connection.create_limit_buy_order = AsyncMock(return_value={
            "orderId": "order-125",
            "stringCode": "TRADE_RETCODE_DONE",
        })
        mock_connection.modify_position = AsyncMock(return_value={
            "stringCode": "TRADE_RETCODE_DONE",
        })
        mock_connection.close_position = AsyncMock(return_value={
            "orderId": "order-126",
            "stringCode": "TRADE_RETCODE_DONE",
        })
        mock_connection.modify_order = AsyncMock(return_value={
            "stringCode": "TRADE_RETCODE_DONE",
        })
        mock_connection.cancel_order = AsyncMock(return_value={
            "stringCode": "TRADE_RETCODE_DONE",
        })
        mock_connection.subscribe_to_market_data = AsyncMock()
        mock_connection.unsubscribe_from_market_data = AsyncMock()

        # Configure API mock
        mock_api.metatrader_account_api = MagicMock()
        mock_api.metatrader_account_api.get_account = AsyncMock(return_value=mock_account)

        return mock_api, mock_account, mock_connection, mock_terminal_state

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return MetaAPISDKService(
            token="test-token",
            account_id="test-account-id",
            application="tradeflow-test",
        )

    def test_service_initialization(self, service):
        """Test service initializes with correct parameters."""
        assert service.token == "test-token"
        assert service.account_id == "test-account-id"
        assert service.application == "tradeflow-test"
        assert not service.is_connected
        assert service.terminal_state is None

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SDK_AVAILABLE, reason="MetaAPI SDK not installed")
    async def test_connect_success(self, service, mock_metaapi):
        """Test successful connection."""
        mock_api, mock_account, mock_connection, _ = mock_metaapi

        with patch("app.services.metaapi_sdk_service.MetaApi", return_value=mock_api):
            result = await service.connect()

            assert result is True
            assert service.is_connected
            mock_api.metatrader_account_api.get_account.assert_called_once_with("test-account-id")
            mock_connection.connect.assert_called_once()
            mock_connection.wait_synchronized.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SDK_AVAILABLE, reason="MetaAPI SDK not installed")
    async def test_connect_deploys_if_needed(self, service, mock_metaapi):
        """Test connection deploys account if not deployed."""
        mock_api, mock_account, mock_connection, _ = mock_metaapi
        mock_account.state = "UNDEPLOYED"

        with patch("app.services.metaapi_sdk_service.MetaApi", return_value=mock_api):
            result = await service.connect()

            assert result is True
            mock_account.deploy.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SDK_AVAILABLE, reason="MetaAPI SDK not installed")
    async def test_disconnect(self, service, mock_metaapi):
        """Test disconnection."""
        mock_api, mock_account, mock_connection, _ = mock_metaapi

        with patch("app.services.metaapi_sdk_service.MetaApi", return_value=mock_api):
            await service.connect()
            await service.disconnect()

            assert not service.is_connected
            mock_connection.close.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SDK_AVAILABLE, reason="MetaAPI SDK not installed")
    async def test_get_account_info(self, service, mock_metaapi):
        """Test getting account information."""
        mock_api, mock_account, mock_connection, _ = mock_metaapi

        with patch("app.services.metaapi_sdk_service.MetaApi", return_value=mock_api):
            await service.connect()
            info = await service.get_account_info()

            assert info["broker"] == "TestBroker"
            assert info["currency"] == "USD"
            assert info["balance"] == 10000.00
            assert info["equity"] == 10500.00
            assert info["leverage"] == 100

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SDK_AVAILABLE, reason="MetaAPI SDK not installed")
    async def test_get_positions(self, service, mock_metaapi):
        """Test getting positions."""
        mock_api, mock_account, mock_connection, _ = mock_metaapi

        with patch("app.services.metaapi_sdk_service.MetaApi", return_value=mock_api):
            await service.connect()
            positions = await service.get_positions()

            assert len(positions) == 1
            pos = positions[0]
            assert pos["id"] == "pos-1"
            assert pos["symbol"] == "EURUSD"
            assert pos["side"] == "buy"
            assert pos["volume"] == 0.1

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SDK_AVAILABLE, reason="MetaAPI SDK not installed")
    async def test_get_orders(self, service, mock_metaapi):
        """Test getting pending orders."""
        mock_api, mock_account, mock_connection, _ = mock_metaapi

        with patch("app.services.metaapi_sdk_service.MetaApi", return_value=mock_api):
            await service.connect()
            orders = await service.get_orders()

            assert len(orders) == 1
            order = orders[0]
            assert order["id"] == "order-1"
            assert order["symbol"] == "GBPUSD"

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SDK_AVAILABLE, reason="MetaAPI SDK not installed")
    async def test_create_market_buy_order(self, service, mock_metaapi):
        """Test placing market buy order."""
        mock_api, mock_account, mock_connection, _ = mock_metaapi

        with patch("app.services.metaapi_sdk_service.MetaApi", return_value=mock_api):
            await service.connect()
            result = await service.create_market_buy_order(
                symbol="EURUSD",
                volume=0.1,
                stop_loss=1.0800,
                take_profit=1.1000,
            )

            assert result["success"] is True
            assert result["order_id"] == "order-123"
            mock_connection.create_market_buy_order.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SDK_AVAILABLE, reason="MetaAPI SDK not installed")
    async def test_create_market_sell_order(self, service, mock_metaapi):
        """Test placing market sell order."""
        mock_api, mock_account, mock_connection, _ = mock_metaapi

        with patch("app.services.metaapi_sdk_service.MetaApi", return_value=mock_api):
            await service.connect()
            result = await service.create_market_sell_order(
                symbol="EURUSD",
                volume=0.1,
            )

            assert result["success"] is True
            mock_connection.create_market_sell_order.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SDK_AVAILABLE, reason="MetaAPI SDK not installed")
    async def test_modify_position(self, service, mock_metaapi):
        """Test modifying position SL/TP."""
        mock_api, mock_account, mock_connection, _ = mock_metaapi

        with patch("app.services.metaapi_sdk_service.MetaApi", return_value=mock_api):
            await service.connect()
            result = await service.modify_position(
                position_id="pos-1",
                stop_loss=1.0800,
                take_profit=1.1000,
            )

            assert result["success"] is True
            mock_connection.modify_position.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SDK_AVAILABLE, reason="MetaAPI SDK not installed")
    async def test_close_position(self, service, mock_metaapi):
        """Test closing position."""
        mock_api, mock_account, mock_connection, _ = mock_metaapi

        with patch("app.services.metaapi_sdk_service.MetaApi", return_value=mock_api):
            await service.connect()
            result = await service.close_position(position_id="pos-1")

            assert result["success"] is True
            mock_connection.close_position.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SDK_AVAILABLE, reason="MetaAPI SDK not installed")
    async def test_cancel_order(self, service, mock_metaapi):
        """Test cancelling pending order."""
        mock_api, mock_account, mock_connection, _ = mock_metaapi

        with patch("app.services.metaapi_sdk_service.MetaApi", return_value=mock_api):
            await service.connect()
            result = await service.cancel_order(order_id="order-1")

            assert result["success"] is True
            mock_connection.cancel_order.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SDK_AVAILABLE, reason="MetaAPI SDK not installed")
    async def test_subscribe_to_market_data(self, service, mock_metaapi):
        """Test subscribing to market data."""
        mock_api, mock_account, mock_connection, _ = mock_metaapi

        with patch("app.services.metaapi_sdk_service.MetaApi", return_value=mock_api):
            await service.connect()
            result = await service.subscribe_to_market_data("EURUSD")

            assert result is True
            mock_connection.subscribe_to_market_data.assert_called_once_with(symbol="EURUSD")

    @pytest.mark.skipif(not SDK_AVAILABLE, reason="MetaAPI SDK not installed")
    def test_get_quote(self, service, mock_metaapi):
        """Test getting quote from terminal state."""
        mock_api, mock_account, mock_connection, mock_terminal = mock_metaapi

        # Manually set up connection
        service._connection = mock_connection
        service._is_connected = True

        quote = service.get_quote("EURUSD")

        assert quote is not None
        assert quote["symbol"] == "EURUSD"
        assert quote["bid"] == 1.0855
        assert quote["ask"] == 1.0857

    @pytest.mark.skipif(not SDK_AVAILABLE, reason="MetaAPI SDK not installed")
    def test_get_symbol_specification(self, service, mock_metaapi):
        """Test getting symbol specification."""
        mock_api, mock_account, mock_connection, mock_terminal = mock_metaapi

        # Manually set up connection
        service._connection = mock_connection
        service._is_connected = True

        spec = service.get_symbol_specification("EURUSD")

        assert spec is not None
        assert spec["symbol"] == "EURUSD"
        assert spec["contract_size"] == 100000
        assert spec["digits"] == 5

    @pytest.mark.skipif(not SDK_AVAILABLE, reason="MetaAPI SDK not installed")
    def test_health_status(self, service, mock_metaapi):
        """Test health status reporting."""
        mock_api, mock_account, mock_connection, mock_terminal = mock_metaapi

        # Manually set up connection
        service._connection = mock_connection
        service._is_connected = True

        status = service.health_status

        assert status["connected"] is True
        assert status["synchronized"] is True

    def test_health_status_not_connected(self, service):
        """Test health status when not connected."""
        status = service.health_status

        assert status["connected"] is False
        assert status["synchronized"] is False


class TestMetaAPISDKServiceIntegration:
    """Integration tests requiring actual SDK (marked skip if not available)."""

    @pytest.mark.skip(reason="Requires actual MetaAPI credentials")
    @pytest.mark.asyncio
    async def test_real_connection(self):
        """
        Test actual connection to MetaAPI.

        To run this test, set:
        - METAAPI_TOKEN environment variable
        - METAAPI_ACCOUNT_ID environment variable
        """
        import os

        token = os.environ.get("METAAPI_TOKEN")
        account_id = os.environ.get("METAAPI_ACCOUNT_ID")

        if not token or not account_id:
            pytest.skip("MetaAPI credentials not configured")

        service = MetaAPISDKService(token=token, account_id=account_id)

        try:
            # Connect
            connected = await service.connect()
            assert connected is True

            # Get account info
            info = await service.get_account_info()
            assert "balance" in info
            assert "equity" in info

            # Get positions
            positions = await service.get_positions()
            assert isinstance(positions, list)

        finally:
            await service.disconnect()


class TestMetaAPISDKAvailability:
    """Tests for SDK availability checking."""

    def test_sdk_available_flag(self):
        """Test SDK_AVAILABLE flag reflects actual SDK installation."""
        try:
            from metaapi_cloud_sdk import MetaApi
            assert SDK_AVAILABLE is True
        except ImportError:
            assert SDK_AVAILABLE is False

    def test_service_creation_without_sdk(self):
        """Test service can be created even without SDK installed."""
        # Service should be creatable regardless of SDK availability
        service = MetaAPISDKService(
            token="test",
            account_id="test",
        )
        assert service.token == "test"
        assert service.account_id == "test"


class TestDualModeExecutors:
    """Test dual-mode behavior in executors."""

    @pytest.mark.asyncio
    async def test_mt4_executor_without_sdk_credentials(self):
        """Test MT4 executor falls back to httpx without SDK credentials."""
        from app.brokers.mt4_executor import MT4Executor

        # Create executor without MetaAPI credentials
        executor = MT4Executor(metaapi_token=None, metaapi_account_id=None)

        # Should not be using SDK mode
        assert not executor._use_sdk or not executor._has_metaapi_credentials()

    @pytest.mark.asyncio
    async def test_mt5_executor_without_sdk_credentials(self):
        """Test MT5 executor falls back to httpx without SDK credentials."""
        from app.brokers.mt5_executor import MT5Executor

        # Create executor without MetaAPI credentials
        executor = MT5Executor(metaapi_token=None, metaapi_account_id=None)

        # Should not be using SDK mode
        assert not executor._use_sdk or not executor._has_metaapi_credentials()

    @pytest.mark.asyncio
    async def test_mt4_executor_with_sdk_credentials(self):
        """Test MT4 executor accepts SDK credentials."""
        from app.brokers.mt4_executor import MT4Executor

        executor = MT4Executor(
            metaapi_token="test-token",
            metaapi_account_id="test-account",
        )

        # Should have SDK credentials stored
        assert executor._metaapi_token == "test-token"
        assert executor._metaapi_account_id == "test-account"

    @pytest.mark.asyncio
    async def test_mt5_executor_with_sdk_credentials(self):
        """Test MT5 executor accepts SDK credentials."""
        from app.brokers.mt5_executor import MT5Executor

        executor = MT5Executor(
            metaapi_token="test-token",
            metaapi_account_id="test-account",
        )

        # Should have SDK credentials stored
        assert executor._metaapi_token == "test-token"
        assert executor._metaapi_account_id == "test-account"
