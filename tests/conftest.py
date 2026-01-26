"""
Test fixtures for unified trading engine tests.
"""
import os
import pytest
from unittest.mock import MagicMock, AsyncMock
from typing import Generator, AsyncGenerator

# Try to import FastAPI test client
try:
    from fastapi.testclient import TestClient
    from httpx import AsyncClient, ASGITransport
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# Ensure DATABASE_URL is set for tests that import app.main
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_trading.db")

# Don't import app at module level to avoid SQLAlchemy model conflicts
# Infrastructure tests import database_models.py, but app.main imports routes
# which import models.py. Both define User table, causing conflicts.
# Import app only when needed inside fixtures instead.
APP_AVAILABLE = True  # Assume available, fixture will handle import errors


@pytest.fixture
def mock_db_session():
    """Mock database session for tests that don't need real DB."""
    session = MagicMock()
    session.query = MagicMock(return_value=MagicMock())
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def mock_redis():
    """Mock Redis client for tests."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def client():
    """Synchronous test client for FastAPI app."""
    if not FASTAPI_AVAILABLE:
        pytest.skip("FastAPI not available")
    try:
        from app.main import app
    except ImportError:
        pytest.skip("App not available")
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client():
    """Async test client for FastAPI app."""
    if not FASTAPI_AVAILABLE:
        pytest.skip("FastAPI not available")
    try:
        from app.main import app
    except ImportError:
        pytest.skip("App not available")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_broker_executor():
    """Mock broker executor for testing signal processing."""
    executor = AsyncMock()
    executor.is_available = True
    executor.is_connected = False
    executor.initialize = AsyncMock(return_value=True)
    executor.disconnect = AsyncMock()
    executor.place_order = AsyncMock(return_value={"order_id": "test-123", "status": "filled"})
    executor.get_positions = AsyncMock(return_value=[])
    executor.get_orders = AsyncMock(return_value=[])
    return executor


@pytest.fixture
def sample_signal():
    """Sample trading signal for tests."""
    return {
        "action": "buy",
        "symbol": "EURUSD",
        "quantity": 1.0,
        "price": None,
        "stop_loss": 1.0900,
        "take_profit": 1.1100
    }


@pytest.fixture
def sample_order_request():
    """Sample order request for tests."""
    return {
        "symbol": "EURUSD",
        "side": "buy",
        "quantity": 1.0,
        "order_type": "market",
        "stop_loss": 1.0900,
        "take_profit": 1.1100
    }
