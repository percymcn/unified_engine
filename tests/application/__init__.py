"""
Application Layer Tests

Tests for use cases using mock port implementations.
No real database or broker connections.
"""
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal

from app.domain.entities.signal import Signal
from app.domain.entities.trade import Trade
from app.domain.entities.order import Order
from app.domain.entities.account import Account
from app.domain.entities.position import Position
from app.domain.value_objects import (
    SignalId, AccountId, OrderId, PositionId,
    Symbol, Volume, Price, Money,
)
from app.domain.enums import (
    BrokerType, AccountType, SignalSource, SignalAction, SignalStatus,
    OrderType, OrderStatus, TradeStatus, PositionSide,
)
from app.domain.ports.repository_port import (
    SignalRepository, TradeRepository, OrderRepository,
    AccountRepository, PositionRepository,
)
from app.domain.ports.broker_port import BrokerPort
from app.domain.ports.event_port import EventPort, DomainEvent


# Reuse mock implementations from domain tests
class InMemorySignalRepository(SignalRepository):
    """In-memory signal repository for testing"""

    def __init__(self):
        self._signals: Dict[str, Signal] = {}

    async def save(self, entity: Signal) -> Signal:
        self._signals[entity.id.value] = entity
        return entity

    async def delete(self, entity: Signal) -> None:
        self._signals.pop(entity.id.value, None)

    async def get_by_id(self, signal_id: SignalId) -> Optional[Signal]:
        return self._signals.get(signal_id.value)

    async def get_pending(self, limit: int = 100) -> List[Signal]:
        return [s for s in self._signals.values() if s.status == SignalStatus.PENDING][:limit]

    async def get_by_status(self, status: SignalStatus, limit: int = 100) -> List[Signal]:
        return [s for s in self._signals.values() if s.status == status][:limit]

    async def get_by_user(self, user_id: int, limit: int = 100, offset: int = 0) -> List[Signal]:
        return list(self._signals.values())[offset:offset + limit]

    async def get_recent(self, since: datetime, limit: int = 100) -> List[Signal]:
        return [s for s in self._signals.values() if s.created_at >= since][:limit]


class InMemoryAccountRepository(AccountRepository):
    """In-memory account repository for testing"""

    def __init__(self):
        self._accounts: Dict[str, Account] = {}

    async def save(self, entity: Account) -> Account:
        self._accounts[entity.id.value] = entity
        return entity

    async def delete(self, entity: Account) -> None:
        self._accounts.pop(entity.id.value, None)

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


class InMemoryTradeRepository(TradeRepository):
    """In-memory trade repository for testing"""

    def __init__(self):
        self._trades: Dict[str, Trade] = {}

    async def save(self, entity: Trade) -> Trade:
        self._trades[entity.trade_id] = entity
        return entity

    async def delete(self, entity: Trade) -> None:
        self._trades.pop(entity.trade_id, None)

    async def get_by_id(self, trade_id: str) -> Optional[Trade]:
        return self._trades.get(trade_id)

    async def get_by_account(self, account_id: str, limit: int = 100, offset: int = 0) -> List[Trade]:
        trades = [t for t in self._trades.values() if t.account_id == account_id]
        return trades[offset:offset + limit]

    async def get_open_by_account(self, account_id: str) -> List[Trade]:
        return [t for t in self._trades.values() if t.account_id == account_id and t.status == TradeStatus.OPEN]

    async def get_by_symbol(self, account_id: str, symbol: str) -> List[Trade]:
        return [t for t in self._trades.values() if t.account_id == account_id and t.symbol.value == symbol]


class InMemoryOrderRepository(OrderRepository):
    """In-memory order repository for testing"""

    def __init__(self):
        self._orders: Dict[str, Order] = {}

    async def save(self, entity: Order) -> Order:
        self._orders[entity.id.value] = entity
        return entity

    async def delete(self, entity: Order) -> None:
        self._orders.pop(entity.id.value, None)

    async def get_by_id(self, order_id: OrderId) -> Optional[Order]:
        return self._orders.get(order_id.value)

    async def get_pending_by_account(self, account_id: str) -> List[Order]:
        return [o for o in self._orders.values() if o.account_id == account_id and o.status == OrderStatus.PENDING]

    async def get_by_status(self, account_id: str, status: OrderStatus) -> List[Order]:
        return [o for o in self._orders.values() if o.account_id == account_id and o.status == status]


class InMemoryPositionRepository(PositionRepository):
    """In-memory position repository for testing"""

    def __init__(self):
        self._positions: Dict[str, Position] = {}

    async def save(self, entity: Position) -> Position:
        self._positions[entity.id.value] = entity
        return entity

    async def delete(self, entity: Position) -> None:
        self._positions.pop(entity.id.value, None)

    async def get_by_id(self, position_id: PositionId) -> Optional[Position]:
        return self._positions.get(position_id.value)

    async def get_open_by_account(self, account_id: str) -> List[Position]:
        return [p for p in self._positions.values() if p.account_id == account_id and p.is_active]

    async def get_by_symbol(self, account_id: str, symbol: str) -> List[Position]:
        return [p for p in self._positions.values() if p.account_id == account_id and p.symbol.value == symbol]


class MockBrokerPort(BrokerPort):
    """Mock broker port for testing"""

    def __init__(self, broker_type: BrokerType = BrokerType.MT5):
        self._broker_type = broker_type
        self._connected = False
        self._positions: List[Position] = []
        self._orders: List[Order] = []
        self._order_counter = 0

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

    async def authenticate(self, credentials: Dict) -> bool:
        return True

    async def get_account_info(self) -> Dict:
        return {
            "balance": 10000.0,
            "equity": 10000.0,
            "margin": 0.0,
            "free_margin": 10000.0,
            "leverage": 100,
            "currency": "USD",
        }

    async def get_positions(self) -> List[Position]:
        return self._positions

    async def get_orders(self) -> List[Order]:
        return self._orders

    async def place_order(
        self,
        symbol: Symbol,
        order_type: OrderType,
        volume: Volume,
        price: Optional[Price] = None,
        stop_loss: Optional[Price] = None,
        take_profit: Optional[Price] = None,
        comment: Optional[str] = None,
    ) -> Order:
        self._order_counter += 1
        order = Order(
            id=OrderId(f"order-{self._order_counter}"),
            broker_order_id=f"broker-{self._order_counter}",
            account_id="test-account",
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            status=OrderStatus.EXECUTED,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            comment=comment,
        )
        return order

    async def modify_order(
        self, order_id: OrderId, price: Optional[Price] = None,
        stop_loss: Optional[Price] = None, take_profit: Optional[Price] = None,
    ) -> Order:
        raise NotImplementedError

    async def cancel_order(self, order_id: OrderId) -> None:
        pass

    async def close_position(
        self, position_id: PositionId, volume: Optional[Volume] = None,
    ) -> Trade:
        return Trade(
            trade_id="trade-1",
            broker_trade_id="broker-trade-1",
            account_id="test-account",
            symbol=Symbol("EURUSD"),
            order_type=OrderType.BUY,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            open_time=datetime.utcnow(),
            close_price=Price(Decimal("1.1050")),
            close_time=datetime.utcnow(),
            status=TradeStatus.CLOSED,
        )

    async def modify_position(
        self, position_id: PositionId,
        stop_loss: Optional[Price] = None, take_profit: Optional[Price] = None,
    ) -> Position:
        return Position(
            id=position_id,
            broker_position_id="broker-pos-1",
            account_id="test-account",
            symbol=Symbol("EURUSD"),
            side=PositionSide.LONG,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            current_price=Price(Decimal("1.1050")),
            open_time=datetime.utcnow(),
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

    async def get_quote(self, symbol: Symbol) -> Dict:
        return {"symbol": symbol.value, "bid": 1.1000, "ask": 1.1002, "timestamp": datetime.utcnow()}


class InMemoryEventPort(EventPort):
    """In-memory event port for testing"""

    def __init__(self):
        self.events: List[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.events.append(event)

    async def publish_batch(self, events: List[DomainEvent]) -> None:
        self.events.extend(events)


def create_test_account(
    account_id: str = "test-account",
    user_id: int = 1,
    broker: BrokerType = BrokerType.MT5,
    is_active: bool = True,
    is_connected: bool = True,
) -> Account:
    """Factory for test accounts"""
    return Account(
        id=AccountId(account_id),
        user_id=user_id,
        broker=broker,
        account_type=AccountType.DEMO,
        balance=Money(Decimal("10000")),
        equity=Money(Decimal("10000")),
        is_active=is_active,
        is_connected=is_connected,
    )
