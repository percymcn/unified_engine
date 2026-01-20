# Plan: Test Infrastructure Setup

## Metadata

```yaml
phase: 2
plan: 01
title: Test Infrastructure Setup
wave: 1
depends_on: []
files_modified:
  - tests/conftest.py
  - pytest.ini
  - requirements.txt
autonomous: true
requirements: [TEST-01]
```

## Goal

Create the foundational test infrastructure: conftest.py with fixtures, pytest configuration, and ensure all test dependencies are documented.

## Must-Haves

### Truths (post-execution verifiable statements)
- `tests/conftest.py` exists with basic fixtures
- `pytest.ini` exists with test configuration
- pytest can collect tests without import errors from missing fixtures
- Test database and client fixtures are available

### Artifacts
- tests/conftest.py - pytest fixtures
- pytest.ini - pytest configuration

### Key Links
- tests/ directory - all test modules
- requirements.txt - dependencies list

## Context

### Problem
The test suite has no conftest.py with fixtures. Tests fail to collect due to:
1. Missing fixture definitions
2. No pytest configuration
3. Full app import chain causing cascade failures

### Solution
1. Create conftest.py with essential fixtures:
   - `client` - FastAPI TestClient
   - `db_session` - Mock database session
   - `async_client` - Async test client
2. Create pytest.ini with async mode and test paths
3. Ensure requirements.txt documents test dependencies

### References
- CONCERNS.md: "90/101 tests failing" issue
- tests/README.md (if exists)

## Tasks

### Task 1: Create pytest.ini configuration
**Type:** auto

Create pytest configuration file.

**File:** `pytest.ini`

**Content:**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
filterwarnings =
    ignore::DeprecationWarning
addopts = -v --tb=short
```

### Task 2: Create conftest.py with fixtures
**Type:** auto

Create test fixtures file with essential fixtures.

**File:** `tests/conftest.py`

**Content:**
```python
"""
Test fixtures for unified trading engine tests.
"""
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

# Try to import app
try:
    from app.main import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False


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
    if not FASTAPI_AVAILABLE or not APP_AVAILABLE:
        pytest.skip("FastAPI or app not available")
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client():
    """Async test client for FastAPI app."""
    if not FASTAPI_AVAILABLE or not APP_AVAILABLE:
        pytest.skip("FastAPI or app not available")
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
```

### Task 3: Update requirements.txt with test dependencies comment
**Type:** auto

Add comment section for test dependencies to requirements.txt.

**File:** `requirements.txt`

Add after existing content:
```
# Test Dependencies (ensure these are installed for running tests)
# pytest==7.4.3 (already listed)
# pytest-asyncio==0.21.1 (already listed)
# Note: python-socketio and websockets needed for full test collection
```

### Task 4: Verify pytest can load configuration
**Type:** auto

Run pytest --collect-only to verify fixtures load.

**Command:**
```bash
python3 -m pytest --collect-only tests/test_deployment.py 2>&1 | head -20
```

**Success criteria:** No fixture-related errors, tests collected.

## Verification

After completing all tasks:

1. **Config file exists:**
   ```bash
   test -f pytest.ini && echo "pytest.ini exists"
   ```

2. **Conftest exists:**
   ```bash
   test -f tests/conftest.py && echo "conftest.py exists"
   ```

3. **Pytest loads config:**
   ```bash
   python3 -m pytest --collect-only tests/test_deployment.py 2>&1 | grep -E "collected|error"
   ```

## Rollback

If issues arise:
1. Remove pytest.ini
2. Remove tests/conftest.py
3. Tests will fail as before (no worse)

---
*Plan created: Phase 2, TEST-01 (partial)*
