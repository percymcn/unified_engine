"""
Infrastructure layer tests.

Provides:
- Mock executors for broker adapters
- In-memory SQLite for repository tests
- Test data factories
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4

from app.domain.entities import Signal, Trade, Order, Account, Position
from app.domain.enums import (
    SignalSource, SignalAction, SignalStatus,
    BrokerType, OrderType, OrderStatus, PositionSide,
)
from app.domain.value_objects import Symbol, Volume, Price, Money, SignalId, AccountId


# Mock executor factory
def create_mock_executor():
    """Create a mock broker executor for testing."""
    executor = AsyncMock()
    executor.is_connected = True
    executor.connect = AsyncMock()
    executor.disconnect = AsyncMock()
    executor.place_order = AsyncMock(return_value={
        "order_id": str(uuid4()),
        "status": "filled",
        "filled_price": 1.2345,
        "filled_volume": 1.0,
    })
    executor.close_position = AsyncMock(return_value={
        "trade_id": str(uuid4()),
        "profit": 100.0,
    })
    executor.get_positions = AsyncMock(return_value=[])
    executor.get_orders = AsyncMock(return_value=[])
    executor.get_account_info = AsyncMock(return_value={
        "balance": 10000.0,
        "equity": 10500.0,
        "margin": 500.0,
    })
    return executor


# Test data factories
def create_test_signal(**overrides) -> Signal:
    defaults = {
        "id": SignalId(str(uuid4())),
        "source": SignalSource.TRADINGVIEW,
        "action": SignalAction.BUY,
        "status": SignalStatus.PENDING,
        "symbol": Symbol("EURUSD"),
        "volume": Volume(Decimal("1.0")),
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return Signal(**defaults)


def create_test_account(**overrides) -> Account:
    defaults = {
        "id": AccountId(str(uuid4())),
        "user_id": 1,
        "broker": BrokerType.TRADELOCKER,
        "name": "Test Account",
        "balance": Money(Decimal("10000.00")),
        "equity": Money(Decimal("10000.00")),
        "is_active": True,
        "is_connected": False,
    }
    defaults.update(overrides)
    return Account(**defaults)


# SQLite async session for tests
@pytest.fixture
async def async_session():
    """Create in-memory SQLite session for tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        # Create tables (import models to register)
        from app.models.database_models import Base
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()
