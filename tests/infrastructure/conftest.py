"""
Test fixtures for infrastructure layer tests.

Provides isolated fixtures that avoid SQLAlchemy model conflicts
by using mock sessions instead of importing the full app.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any


@pytest.fixture
def mock_async_session():
    """Mock async SQLAlchemy session for repository tests."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_executor():
    """Mock broker executor for adapter tests."""
    executor = AsyncMock()
    executor.is_connected = True
    executor.connect = AsyncMock()
    executor.disconnect = AsyncMock()
    executor.initialize = AsyncMock(return_value=True)
    executor.place_order = AsyncMock(return_value={
        "order_id": "test-123",
        "status": "filled",
        "symbol": "EURUSD",
        "volume": 1.0,
    })
    executor.close_position = AsyncMock(return_value={
        "trade_id": "trade-456",
        "profit": 100.0,
    })
    executor.modify_position = AsyncMock(return_value={
        "position_id": "pos-789",
        "stop_loss": 1.0900,
    })
    executor.get_positions = AsyncMock(return_value=[])
    executor.get_orders = AsyncMock(return_value=[])
    executor.get_account_info = AsyncMock(return_value={
        "balance": 10000.0,
        "equity": 10000.0,
        "margin": 1000.0,
        "free_margin": 9000.0,
    })
    executor.cancel_order = AsyncMock(return_value=True)
    return executor


@pytest.fixture
def mock_session_factory():
    """Mock session factory for container and UoW tests."""
    factory = MagicMock()
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    factory.create_session = MagicMock(return_value=mock_session)
    return factory


@pytest.fixture
def mock_event_publisher():
    """Mock event publisher for tests."""
    publisher = AsyncMock()
    publisher.connect = AsyncMock()
    publisher.disconnect = AsyncMock()
    publisher.publish = AsyncMock()
    publisher.is_connected = True
    return publisher


@pytest.fixture
def mock_broker_port():
    """Mock broker port for use case tests."""
    broker = AsyncMock()
    broker.broker_type = "TRADELOCKER"
    broker.is_connected = True
    broker.authenticate = AsyncMock()
    broker.place_order = AsyncMock(return_value={
        "order_id": "test-order-123",
        "symbol": "EURUSD",
        "volume": 1.0,
        "price": 1.1000,
    })
    broker.close_position = AsyncMock(return_value={
        "trade_id": "test-trade-456",
        "profit": 100.0,
    })
    broker.modify_position = AsyncMock(return_value={
        "position_id": "pos-789",
        "stop_loss": 1.0900,
        "take_profit": 1.1100,
    })
    broker.get_positions = AsyncMock(return_value=[])
    broker.get_orders = AsyncMock(return_value=[])
    broker.get_account_info = AsyncMock(return_value={
        "balance": 10000.0,
        "equity": 10000.0,
    })
    broker.cancel_order = AsyncMock(return_value=True)
    return broker
