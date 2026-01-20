"""Tests for domain services using mock port implementations"""
import pytest
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.domain.entities.signal import Signal
from app.domain.entities.trade import Trade
from app.domain.entities.order import Order
from app.domain.entities.account import Account
from app.domain.entities.position import Position
from app.domain.services.signal_service import SignalService
from app.domain.ports.repository_port import SignalRepository, AccountRepository
from app.domain.ports.broker_port import BrokerPort
from app.domain.ports.event_port import EventPort, DomainEvent
from app.domain.value_objects import SignalId, Symbol, Volume, Price, AccountId, OrderId, PositionId, Money
from app.domain.enums import (
    SignalSource, SignalAction, SignalStatus, OrderType, OrderStatus,
    BrokerType, AccountType, PositionSide
)


# Mock Port Implementations

class InMemorySignalRepository(SignalRepository):
    """In-memory signal repository for testing"""
    def __init__(self):
        self._signals: Dict[str, Signal] = {}

    async def save(self, signal: Signal) -> Signal:
        self._signals[signal.id.value] = signal
        return signal

    async def delete(self, signal: Signal) -> None:
        self._signals.pop(signal.id.value, None)

    async def get_by_id(self, signal_id: SignalId) -> Optional[Signal]:
        return self._signals.get(signal_id.value)

    async def get_pending(self, limit: int = 100) -> List[Signal]:
        return [s for s in self._signals.values() if s.status == SignalStatus.PENDING][:limit]

    async def get_by_status(self, status: SignalStatus, limit: int = 100) -> List[Signal]:
        return [s for s in self._signals.values() if s.status == status][:limit]

    async def get_by_user(self, user_id: int, limit: int = 100, offset: int = 0) -> List[Signal]:
        return []

    async def get_recent(self, since: datetime, limit: int = 100) -> List[Signal]:
        return []


class InMemoryAccountRepository(AccountRepository):
    """In-memory account repository for testing"""
    def __init__(self):
        self._accounts: Dict[str, Account] = {}

    async def save(self, account: Account) -> Account:
        self._accounts[account.id.value] = account
        return account

    async def delete(self, account: Account) -> None:
        self._accounts.pop(account.id.value, None)

    async def get_by_id(self, account_id: AccountId) -> Optional[Account]:
        return self._accounts.get(account_id.value)

    async def get_by_user(self, user_id: int) -> List[Account]:
        return [a for a in self._accounts.values() if a.user_id == user_id]

    async def get_by_broker(self, broker: BrokerType) -> List[Account]:
        return [a for a in self._accounts.values() if a.broker == broker]

    async def get_active(self) -> List[Account]:
        return [a for a in self._accounts.values() if a.is_active]

    async def get_connected(self) -> List[Account]:
        return [a for a in self._accounts.values() if a.is_connected]


class MockBrokerPort(BrokerPort):
    """Mock broker port for testing"""
    def __init__(self, broker_type: BrokerType = BrokerType.MT5):
        self._broker_type = broker_type
        self._connected = True
        self._orders: List[Order] = []
        self._positions: List[Position] = []

    @property
    def broker_type(self) -> BrokerType:
        return self._broker_type

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def is_connected(self) -> bool:
        return self._connected

    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        return True

    async def get_account_info(self) -> Dict[str, Any]:
        return {"balance": 10000, "equity": 10000, "margin": 0}

    async def get_positions(self) -> List[Position]:
        return self._positions

    async def get_orders(self) -> List[Order]:
        return self._orders

    async def place_order(
        self, symbol: Symbol, order_type: OrderType, volume: Volume,
        price: Optional[Price] = None, stop_loss: Optional[Price] = None,
        take_profit: Optional[Price] = None, comment: Optional[str] = None,
    ) -> Order:
        order = Order(
            id=OrderId(f"order-{len(self._orders) + 1}"),
            broker_order_id=f"broker-order-{len(self._orders) + 1}",
            account_id="test-account",
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        self._orders.append(order)
        return order

    async def modify_order(self, order_id: OrderId, price: Optional[Price] = None,
                          stop_loss: Optional[Price] = None, take_profit: Optional[Price] = None) -> Order:
        return self._orders[0] if self._orders else None

    async def cancel_order(self, order_id: OrderId) -> None:
        pass

    async def close_position(self, position_id: PositionId, volume: Optional[Volume] = None) -> Trade:
        return Trade(
            trade_id=f"trade-{position_id.value}",
            broker_trade_id=None,
            account_id="test-account",
            symbol=Symbol("EURUSD"),
            order_type=OrderType.SELL,
            volume=volume or Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            open_time=datetime.utcnow(),
        )

    async def modify_position(self, position_id: PositionId, stop_loss: Optional[Price] = None,
                              take_profit: Optional[Price] = None) -> Position:
        return self._positions[0] if self._positions else None

    async def get_quote(self, symbol: Symbol) -> Dict[str, Any]:
        return {"symbol": symbol.value, "bid": 1.1000, "ask": 1.1002}


class InMemoryEventPort(EventPort):
    """In-memory event port for testing"""
    def __init__(self):
        self.events: List[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.events.append(event)

    async def publish_batch(self, events: list[DomainEvent]) -> None:
        self.events.extend(events)


# Fixtures

@pytest.fixture
def signal_repo():
    return InMemorySignalRepository()

@pytest.fixture
def account_repo():
    return InMemoryAccountRepository()

@pytest.fixture
def broker_port():
    return MockBrokerPort()

@pytest.fixture
def event_port():
    return InMemoryEventPort()

@pytest.fixture
def signal_service(signal_repo, account_repo, broker_port, event_port):
    return SignalService(
        signal_repository=signal_repo,
        account_repository=account_repo,
        brokers={BrokerType.MT5: broker_port},
        event_port=event_port,
    )


# Signal Service Tests

class TestSignalService:
    @pytest.mark.asyncio
    async def test_process_signal_success(self, signal_service, account_repo, event_port):
        # Setup: Create a connected account
        account = Account(
            id=AccountId("acc-1"),
            user_id=1,
            broker=BrokerType.MT5,
            account_type=AccountType.DEMO,
            balance=Money(Decimal("10000")),
            equity=Money(Decimal("10000")),
            is_active=True,
            is_connected=True,
        )
        await account_repo.save(account)

        # Create signal
        signal = Signal(
            id=SignalId("sig-1"),
            source=SignalSource.TRADINGVIEW,
            symbol=Symbol("EURUSD"),
            action=SignalAction.BUY,
            volume=Volume(Decimal("1.0")),
        )

        # Process signal
        result = await signal_service.process_signal(signal)

        # Verify
        assert result.status == SignalStatus.PROCESSED
        assert len(event_port.events) >= 2  # received + processed

    @pytest.mark.asyncio
    async def test_process_signal_no_accounts_skips(self, signal_service, event_port):
        # No accounts setup
        signal = Signal(
            id=SignalId("sig-1"),
            source=SignalSource.TRADINGVIEW,
            symbol=Symbol("EURUSD"),
            action=SignalAction.BUY,
            volume=Volume(Decimal("1.0")),
        )

        result = await signal_service.process_signal(signal)

        assert result.status == SignalStatus.SKIPPED
        assert "No active accounts" in result.error_message

    @pytest.mark.asyncio
    async def test_process_signal_with_target_accounts(self, signal_service, account_repo):
        # Setup specific target account
        account = Account(
            id=AccountId("acc-target"),
            user_id=1,
            broker=BrokerType.MT5,
            account_type=AccountType.DEMO,
            balance=Money(Decimal("10000")),
            equity=Money(Decimal("10000")),
            is_active=True,
            is_connected=True,
        )
        await account_repo.save(account)

        # Create signal with target
        signal = Signal(
            id=SignalId("sig-1"),
            source=SignalSource.API,
            symbol=Symbol("EURUSD"),
            action=SignalAction.BUY,
            volume=Volume(Decimal("1.0")),
        )
        signal.add_target_account(AccountId("acc-target"))

        result = await signal_service.process_signal(signal)
        assert result.status == SignalStatus.PROCESSED

    @pytest.mark.asyncio
    async def test_process_close_signal(self, signal_service, account_repo, broker_port):
        # Setup account
        account = Account(
            id=AccountId("acc-1"),
            user_id=1,
            broker=BrokerType.MT5,
            account_type=AccountType.DEMO,
            balance=Money(Decimal("10000")),
            equity=Money(Decimal("10000")),
            is_active=True,
            is_connected=True,
        )
        await account_repo.save(account)

        # Add position to broker
        position = Position(
            id=PositionId("pos-1"),
            broker_position_id="broker-pos-1",
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            side=PositionSide.LONG,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            current_price=Price(Decimal("1.1050")),
            open_time=datetime.utcnow(),
        )
        broker_port._positions.append(position)

        # Create CLOSE signal
        signal = Signal(
            id=SignalId("sig-close"),
            source=SignalSource.TRADINGVIEW,
            symbol=Symbol("EURUSD"),
            action=SignalAction.CLOSE,
        )

        result = await signal_service.process_signal(signal)
        assert result.status == SignalStatus.PROCESSED

    @pytest.mark.asyncio
    async def test_get_pending_signals(self, signal_service, signal_repo):
        # Create pending signals
        for i in range(3):
            signal = Signal(
                id=SignalId(f"sig-{i}"),
                source=SignalSource.API,
                symbol=Symbol("EURUSD"),
                action=SignalAction.CLOSE,
            )
            await signal_repo.save(signal)

        pending = await signal_service.get_pending_signals()
        assert len(pending) == 3

    @pytest.mark.asyncio
    async def test_get_signal_by_id(self, signal_service, signal_repo):
        signal = Signal(
            id=SignalId("sig-123"),
            source=SignalSource.API,
            symbol=Symbol("EURUSD"),
            action=SignalAction.CLOSE,
        )
        await signal_repo.save(signal)

        retrieved = await signal_service.get_signal(SignalId("sig-123"))
        assert retrieved is not None
        assert retrieved.id.value == "sig-123"

    @pytest.mark.asyncio
    async def test_process_sell_signal(self, signal_service, account_repo, broker_port):
        # Setup account
        account = Account(
            id=AccountId("acc-1"),
            user_id=1,
            broker=BrokerType.MT5,
            account_type=AccountType.DEMO,
            balance=Money(Decimal("10000")),
            equity=Money(Decimal("10000")),
            is_active=True,
            is_connected=True,
        )
        await account_repo.save(account)

        # Create SELL signal
        signal = Signal(
            id=SignalId("sig-sell"),
            source=SignalSource.TRADINGVIEW,
            symbol=Symbol("GBPUSD"),
            action=SignalAction.SELL,
            volume=Volume(Decimal("0.5")),
        )

        result = await signal_service.process_signal(signal)
        assert result.status == SignalStatus.PROCESSED
        # Verify order was placed
        assert len(broker_port._orders) == 1
        assert broker_port._orders[0].order_type == OrderType.SELL


class TestMockPorts:
    """Verify mock implementations behave correctly"""

    @pytest.mark.asyncio
    async def test_in_memory_signal_repository(self):
        repo = InMemorySignalRepository()
        signal = Signal(
            id=SignalId("sig-test"),
            source=SignalSource.API,
            symbol=Symbol("EURUSD"),
            action=SignalAction.CLOSE,
        )

        # Save
        saved = await repo.save(signal)
        assert saved.id.value == "sig-test"

        # Get by ID
        retrieved = await repo.get_by_id(SignalId("sig-test"))
        assert retrieved is not None
        assert retrieved.id.value == "sig-test"

        # Get pending
        pending = await repo.get_pending()
        assert len(pending) == 1

        # Delete
        await repo.delete(signal)
        deleted = await repo.get_by_id(SignalId("sig-test"))
        assert deleted is None

    @pytest.mark.asyncio
    async def test_in_memory_account_repository(self):
        repo = InMemoryAccountRepository()
        account = Account(
            id=AccountId("acc-test"),
            user_id=1,
            broker=BrokerType.MT5,
            account_type=AccountType.DEMO,
            balance=Money(Decimal("10000")),
            equity=Money(Decimal("10000")),
            is_active=True,
            is_connected=True,
        )

        # Save
        saved = await repo.save(account)
        assert saved.id.value == "acc-test"

        # Get by ID
        retrieved = await repo.get_by_id(AccountId("acc-test"))
        assert retrieved is not None

        # Get connected
        connected = await repo.get_connected()
        assert len(connected) == 1

        # Get active
        active = await repo.get_active()
        assert len(active) == 1

    @pytest.mark.asyncio
    async def test_mock_broker_port(self):
        broker = MockBrokerPort(BrokerType.MT5)

        # Connection
        assert await broker.is_connected()
        await broker.disconnect()
        assert not await broker.is_connected()
        await broker.connect()
        assert await broker.is_connected()

        # Place order
        order = await broker.place_order(
            symbol=Symbol("EURUSD"),
            order_type=OrderType.BUY,
            volume=Volume(Decimal("1.0")),
        )
        assert order is not None
        assert order.order_type == OrderType.BUY

        # Get quote
        quote = await broker.get_quote(Symbol("EURUSD"))
        assert "bid" in quote
        assert "ask" in quote

    @pytest.mark.asyncio
    async def test_in_memory_event_port(self):
        port = InMemoryEventPort()
        assert len(port.events) == 0

        # Publish single event
        event = DomainEvent.create(
            event_type="test.event",
            payload={"key": "value"}
        )
        await port.publish(event)
        assert len(port.events) == 1

        # Publish batch
        events = [
            DomainEvent.create("test.event1", {}),
            DomainEvent.create("test.event2", {}),
        ]
        await port.publish_batch(events)
        assert len(port.events) == 3
