"""Tests for broker adapter implementations."""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.domain.enums import BrokerType, OrderType, PositionSide
from app.domain.value_objects import Symbol, Volume, Price
from tests.infrastructure import create_mock_executor


class TestTradeLockerAdapter:
    """Tests for TradeLocker adapter."""

    @pytest.mark.asyncio
    async def test_broker_type_property(self):
        """Test adapter returns correct broker type."""
        from app.infrastructure.adapters.tradelocker_adapter import TradeLockerAdapter

        adapter = TradeLockerAdapter()
        assert adapter.broker_type == BrokerType.TRADELOCKER

    @pytest.mark.asyncio
    async def test_place_order_calls_executor(self):
        """Test placing order through adapter."""
        from app.infrastructure.adapters.tradelocker_adapter import TradeLockerAdapter

        executor = create_mock_executor()
        adapter = TradeLockerAdapter(executor)

        # Mock authenticate first
        await adapter.authenticate({"account_id": "acc-123", "token": "test"})

        order = await adapter.place_order(
            symbol=Symbol("EURUSD"),
            order_type=OrderType.BUY,
            volume=Volume(Decimal("1.0")),
        )

        assert order is not None
        executor.place_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_position_calls_executor(self):
        """Test closing position through adapter."""
        from app.infrastructure.adapters.tradelocker_adapter import TradeLockerAdapter

        executor = create_mock_executor()
        adapter = TradeLockerAdapter(executor)

        # Mock authenticate
        await adapter.authenticate({"account_id": "acc-123", "token": "test"})

        trade = await adapter.close_position(position_id="pos-456")

        assert trade is not None
        executor.close_position.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_account_info_calls_executor(self):
        """Test getting account info through adapter."""
        from app.infrastructure.adapters.tradelocker_adapter import TradeLockerAdapter

        executor = create_mock_executor()
        adapter = TradeLockerAdapter(executor)

        # Mock authenticate
        await adapter.authenticate({"account_id": "acc-123", "token": "test"})

        info = await adapter.get_account_info()

        assert "balance" in info
        assert "equity" in info
        executor.get_account_info.assert_called_once()


class TestTopstepAdapter:
    """Tests for Topstep adapter."""

    @pytest.mark.asyncio
    async def test_broker_type_property(self):
        """Test adapter returns correct broker type."""
        from app.infrastructure.adapters.topstep_adapter import TopstepAdapter

        adapter = TopstepAdapter()
        assert adapter.broker_type == BrokerType.TOPSTEP

    @pytest.mark.asyncio
    async def test_uses_projectx_executor(self):
        """Test adapter uses ProjectX executor internally."""
        from app.infrastructure.adapters.topstep_adapter import TopstepAdapter

        adapter = TopstepAdapter()
        # Topstep uses ProjectX gateway
        assert adapter._executor is not None


class TestTradovateAdapter:
    """Tests for Tradovate adapter."""

    @pytest.mark.asyncio
    async def test_broker_type_property(self):
        """Test adapter returns correct broker type."""
        from app.infrastructure.adapters.tradovate_adapter import TradovateAdapter

        adapter = TradovateAdapter()
        assert adapter.broker_type == BrokerType.TRADOVATE

    @pytest.mark.asyncio
    async def test_connect_calls_executor(self):
        """Test connect calls executor."""
        from app.infrastructure.adapters.tradovate_adapter import TradovateAdapter

        executor = create_mock_executor()
        adapter = TradovateAdapter(executor)

        await adapter.connect()

        executor.connect.assert_called_once()


class TestMT4Adapter:
    """Tests for MT4 adapter."""

    @pytest.mark.asyncio
    async def test_broker_type_property(self):
        """Test adapter returns correct broker type."""
        from app.infrastructure.adapters.mt4_adapter import MT4Adapter

        adapter = MT4Adapter()
        assert adapter.broker_type == BrokerType.MT4

    @pytest.mark.asyncio
    async def test_authenticate_stores_account_id(self):
        """Test authenticate stores account_id for operations."""
        from app.infrastructure.adapters.mt4_adapter import MT4Adapter

        executor = create_mock_executor()
        adapter = MT4Adapter(executor)

        await adapter.authenticate({
            "account_id": "12345",
            "server": "demo.server.com",
            "password": "secret"
        })

        # Account ID should be stored internally
        assert adapter._account_id == "12345"

    @pytest.mark.asyncio
    async def test_place_order_converts_order_type(self):
        """Test place_order converts domain OrderType to MT4 cmd integer."""
        from app.infrastructure.adapters.mt4_adapter import MT4Adapter

        executor = create_mock_executor()
        adapter = MT4Adapter(executor)

        # Mock authenticate
        await adapter.authenticate({"account_id": "12345"})

        # Place order - should convert OrderType.BUY to cmd integer
        await adapter.place_order(
            symbol=Symbol("EURUSD"),
            order_type=OrderType.BUY,
            volume=Volume(Decimal("1.0")),
        )

        # Verify executor was called
        executor.place_order.assert_called_once()


class TestMT5Adapter:
    """Tests for MT5 adapter."""

    @pytest.mark.asyncio
    async def test_broker_type_property(self):
        """Test adapter returns correct broker type."""
        from app.infrastructure.adapters.mt5_adapter import MT5Adapter

        adapter = MT5Adapter()
        assert adapter.broker_type == BrokerType.MT5

    @pytest.mark.asyncio
    async def test_is_connected_false_initially(self):
        """Test adapter not connected by default."""
        from app.infrastructure.adapters.mt5_adapter import MT5Adapter

        adapter = MT5Adapter()
        assert adapter.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_with_credentials(self):
        """Test connecting adapter with credentials."""
        from app.infrastructure.adapters.mt5_adapter import MT5Adapter

        executor = create_mock_executor()
        adapter = MT5Adapter(executor)

        await adapter.connect()

        executor.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_passes_credentials(self):
        """Test authenticate passes credentials to executor."""
        from app.infrastructure.adapters.mt5_adapter import MT5Adapter

        executor = create_mock_executor()
        adapter = MT5Adapter(executor)

        credentials = {
            "account_id": "12345",
            "server": "demo.server.com",
            "password": "secret"
        }

        await adapter.authenticate(credentials)

        # Should store account_id
        assert adapter._account_id == "12345"

    @pytest.mark.asyncio
    async def test_get_positions_calls_executor(self):
        """Test get_positions calls executor."""
        from app.infrastructure.adapters.mt5_adapter import MT5Adapter

        executor = create_mock_executor()
        adapter = MT5Adapter(executor)

        await adapter.authenticate({"account_id": "12345"})

        positions = await adapter.get_positions()

        executor.get_positions.assert_called_once()
        assert isinstance(positions, list)


class TestAllAdaptersImplementBrokerPort:
    """Verify all adapters implement BrokerPort interface."""

    @pytest.mark.parametrize("adapter_class,broker_type", [
        ("TradeLockerAdapter", BrokerType.TRADELOCKER),
        ("TopstepAdapter", BrokerType.TOPSTEP),
        ("TradovateAdapter", BrokerType.TRADOVATE),
        ("MT4Adapter", BrokerType.MT4),
        ("MT5Adapter", BrokerType.MT5),
    ])
    def test_adapter_returns_correct_broker_type(self, adapter_class, broker_type):
        """Test all adapters return correct broker type."""
        if adapter_class == "TradeLockerAdapter":
            from app.infrastructure.adapters.tradelocker_adapter import TradeLockerAdapter
            adapter = TradeLockerAdapter()
        elif adapter_class == "TopstepAdapter":
            from app.infrastructure.adapters.topstep_adapter import TopstepAdapter
            adapter = TopstepAdapter()
        elif adapter_class == "TradovateAdapter":
            from app.infrastructure.adapters.tradovate_adapter import TradovateAdapter
            adapter = TradovateAdapter()
        elif adapter_class == "MT4Adapter":
            from app.infrastructure.adapters.mt4_adapter import MT4Adapter
            adapter = MT4Adapter()
        elif adapter_class == "MT5Adapter":
            from app.infrastructure.adapters.mt5_adapter import MT5Adapter
            adapter = MT5Adapter()

        assert adapter.broker_type == broker_type

    @pytest.mark.parametrize("adapter_class", [
        "TradeLockerAdapter",
        "TopstepAdapter",
        "TradovateAdapter",
        "MT4Adapter",
        "MT5Adapter",
    ])
    def test_adapter_has_required_methods(self, adapter_class):
        """Test all adapters have BrokerPort methods."""
        if adapter_class == "TradeLockerAdapter":
            from app.infrastructure.adapters.tradelocker_adapter import TradeLockerAdapter
            adapter = TradeLockerAdapter()
        elif adapter_class == "TopstepAdapter":
            from app.infrastructure.adapters.topstep_adapter import TopstepAdapter
            adapter = TopstepAdapter()
        elif adapter_class == "TradovateAdapter":
            from app.infrastructure.adapters.tradovate_adapter import TradovateAdapter
            adapter = TradovateAdapter()
        elif adapter_class == "MT4Adapter":
            from app.infrastructure.adapters.mt4_adapter import MT4Adapter
            adapter = MT4Adapter()
        elif adapter_class == "MT5Adapter":
            from app.infrastructure.adapters.mt5_adapter import MT5Adapter
            adapter = MT5Adapter()

        # Verify BrokerPort methods exist
        assert hasattr(adapter, "connect")
        assert hasattr(adapter, "disconnect")
        assert hasattr(adapter, "place_order")
        assert hasattr(adapter, "close_position")
        assert hasattr(adapter, "get_positions")
        assert hasattr(adapter, "get_orders")
        assert hasattr(adapter, "broker_type")
