"""
Trade Use Case Tests

Tests PlaceOrderUseCase, ClosePositionUseCase, etc.
using mock port implementations.
"""
import pytest
from decimal import Decimal

from app.domain.enums import OrderType, OrderStatus, BrokerType, TradeStatus
from app.application.dto.trade_dto import (
    PlaceOrderRequest, ClosePositionRequest, TradeListRequest,
)
from app.application.use_cases.place_order import PlaceOrderUseCase
from app.application.use_cases.manage_positions import (
    ClosePositionUseCase, GetPositionsUseCase, GetTradesUseCase,
)

from tests.application import (
    InMemoryTradeRepository,
    InMemoryOrderRepository,
    InMemoryPositionRepository,
    InMemoryAccountRepository,
    MockBrokerPort,
    InMemoryEventPort,
    create_test_account,
)


@pytest.fixture
def trade_repo():
    return InMemoryTradeRepository()


@pytest.fixture
def order_repo():
    return InMemoryOrderRepository()


@pytest.fixture
def position_repo():
    return InMemoryPositionRepository()


@pytest.fixture
def account_repo():
    return InMemoryAccountRepository()


@pytest.fixture
def broker_port():
    return MockBrokerPort()


@pytest.fixture
def event_port():
    return InMemoryEventPort()


class TestPlaceOrderUseCase:
    """Tests for PlaceOrderUseCase"""

    @pytest.mark.asyncio
    async def test_place_market_order_success(
        self, trade_repo, order_repo, position_repo, account_repo, broker_port, event_port
    ):
        # Setup
        account = create_test_account()
        await account_repo.save(account)
        await broker_port.connect()

        use_case = PlaceOrderUseCase(
            trade_repository=trade_repo,
            order_repository=order_repo,
            position_repository=position_repo,
            account_repository=account_repo,
            brokers={BrokerType.MT5: broker_port},
            event_port=event_port,
        )

        request = PlaceOrderRequest(
            account_id="test-account",
            symbol="EURUSD",
            order_type=OrderType.BUY,
            volume=Decimal("1.0"),
        )
        response = await use_case.execute(request)

        assert response.order_id != ""
        assert response.status == OrderStatus.EXECUTED
        assert response.error is None

    @pytest.mark.asyncio
    async def test_place_order_account_not_found(
        self, trade_repo, order_repo, position_repo, account_repo, broker_port, event_port
    ):
        use_case = PlaceOrderUseCase(
            trade_repository=trade_repo,
            order_repository=order_repo,
            position_repository=position_repo,
            account_repository=account_repo,
            brokers={BrokerType.MT5: broker_port},
            event_port=event_port,
        )

        request = PlaceOrderRequest(
            account_id="nonexistent",
            symbol="EURUSD",
            order_type=OrderType.BUY,
            volume=Decimal("1.0"),
        )
        response = await use_case.execute(request)

        assert response.status == OrderStatus.REJECTED
        assert "not found" in response.error.lower()

    @pytest.mark.asyncio
    async def test_place_order_account_disconnected(
        self, trade_repo, order_repo, position_repo, account_repo, broker_port, event_port
    ):
        # Account exists but is disconnected
        account = create_test_account(is_connected=False)
        await account_repo.save(account)

        use_case = PlaceOrderUseCase(
            trade_repository=trade_repo,
            order_repository=order_repo,
            position_repository=position_repo,
            account_repository=account_repo,
            brokers={BrokerType.MT5: broker_port},
            event_port=event_port,
        )

        request = PlaceOrderRequest(
            account_id="test-account",
            symbol="EURUSD",
            order_type=OrderType.BUY,
            volume=Decimal("1.0"),
        )
        response = await use_case.execute(request)

        assert response.status == OrderStatus.REJECTED
        assert "disabled" in response.error.lower()

    @pytest.mark.asyncio
    async def test_place_limit_order_requires_price(self):
        # Validation at DTO level
        with pytest.raises(ValueError, match="requires price"):
            PlaceOrderRequest(
                account_id="test-account",
                symbol="EURUSD",
                order_type=OrderType.BUY_LIMIT,
                volume=Decimal("1.0"),
                price=None,  # Missing price for limit order
            )


class TestClosePositionUseCase:
    """Tests for ClosePositionUseCase"""

    @pytest.mark.asyncio
    async def test_close_position_success(
        self, trade_repo, order_repo, position_repo, account_repo, broker_port, event_port
    ):
        from app.domain.entities.position import Position
        from app.domain.value_objects import PositionId, Symbol, Volume, Price
        from app.domain.enums import PositionSide
        from datetime import datetime

        account = create_test_account()
        await account_repo.save(account)
        await broker_port.connect()

        # Create a position in the repository
        position = Position(
            id=PositionId("pos-1"),
            broker_position_id="broker-pos-1",
            account_id="test-account",
            symbol=Symbol("EURUSD"),
            side=PositionSide.LONG,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            current_price=Price(Decimal("1.1050")),
            open_time=datetime.utcnow(),
        )
        await position_repo.save(position)

        use_case = ClosePositionUseCase(
            trade_repository=trade_repo,
            order_repository=order_repo,
            position_repository=position_repo,
            account_repository=account_repo,
            brokers={BrokerType.MT5: broker_port},
            event_port=event_port,
        )

        request = ClosePositionRequest(
            account_id="test-account",
            position_id="pos-1",
        )
        response = await use_case.execute(request)

        assert response.trade_id != ""
        assert response.status == TradeStatus.CLOSED


class TestGetTradesUseCase:
    """Tests for GetTradesUseCase"""

    @pytest.mark.asyncio
    async def test_get_trades_empty(self, trade_repo):
        use_case = GetTradesUseCase(trade_repository=trade_repo)
        request = TradeListRequest(account_id="test-account")
        response = await use_case.execute(request)

        assert response.total == 0
        assert len(response.trades) == 0
