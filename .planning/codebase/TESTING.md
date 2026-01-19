# Testing Patterns

**Analysis Date:** 2026-01-19

## Test Framework

**Runner:**
- pytest 7.4.3
- pytest-asyncio 0.21.1 for async test support
- Config: No `pytest.ini` or `conftest.py` detected at root

**Assertion Library:**
- pytest's built-in assertions (`assert`)

**Test Client:**
- FastAPI's `TestClient` for API endpoint testing
- `from fastapi.testclient import TestClient`

**Run Commands:**
```bash
python tests/run_tests.py                    # Run all test suites with custom runner
python tests/run_tests.py --suite test_api.py  # Run specific test suite
python tests/run_tests.py --coverage         # Run with coverage analysis
pytest tests/test_api.py                     # Direct pytest execution
pytest tests/test_api.py -v                  # Verbose mode
```

## Test File Organization

**Location:**
- All tests in dedicated `tests/` directory at project root
- Not co-located with source code

**Naming:**
- Pattern: `test_*.py` (e.g., `test_api.py`, `test_brokers.py`, `test_webhooks.py`)
- Test classes: `Test{Component}` (e.g., `TestAuthentication`, `TestMT4Executor`)
- Test functions: `test_{scenario}` (e.g., `test_create_access_token`, `test_connect_success`)

**Structure:**
```
tests/
├── run_tests.py              # Custom test runner with reporting
├── test_api.py               # API endpoint tests (19,797 lines)
├── test_brokers.py           # Broker executor tests (16,851 lines)
├── test_webhooks.py          # Webhook processing tests (14,985 lines)
├── test_websockets.py        # WebSocket tests (17,683 lines)
├── test_e2e.py               # End-to-end workflow tests (20,632 lines)
├── test_ui_integration.py    # UI integration tests (19,699 lines)
├── test_deployment.py        # Deployment & health tests (20,575 lines)
├── test_performance.py       # Performance & load tests (24,280 lines)
├── test_analytics.py         # Analytics router tests (2,634 lines)
└── test_notifications.py     # Notification router tests (3,303 lines)
```

## Test Structure

**Suite Organization:**
```python
class TestAuthentication:
    """Test authentication and authorization functionality."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def test_user_data(self):
        """Sample user data for testing."""
        return {
            "email": "test@example.com",
            "password": "testpassword123"
        }

    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
```

**Patterns:**
- Class-based test organization by feature/component
- Docstrings on test classes and individual tests
- Fixtures defined within test classes using `@pytest.fixture`
- Setup/teardown via fixtures (no explicit setUp/tearDown methods)

**Async Tests:**
```python
@pytest.mark.asyncio
async def test_connect_success(self, executor):
    """Test successful connection to MT4 Manager."""
    result = await executor.connect()
    assert result is True
```

## Mocking

**Framework:** `unittest.mock` from Python standard library

**Patterns:**

**Patching External HTTP Calls:**
```python
from unittest.mock import Mock, AsyncMock, patch

@pytest.mark.asyncio
async def test_place_order_success(self, executor, sample_signal):
    executor.is_connected = True

    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "retcode": 0,
            "order": 12345
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        result = await executor.place_order(sample_signal)
        assert result is not None
```

**Database Mocking:**
```python
def test_user_registration(self, client, test_user_data):
    with patch('app.db.database.get_db') as mock_db:
        mock_db_session = Mock()
        mock_db.return_value = mock_db_session

        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None

        response = client.post("/auth/register", json=test_user_data)
```

**What to Mock:**
- External HTTP/API calls (`aiohttp.ClientSession`, broker APIs)
- Database sessions (`get_db` dependency)
- Authentication/authorization (`get_current_user`)
- Time-dependent operations
- WebSocket connections

**What NOT to Mock:**
- Pydantic model validation
- Internal business logic
- Simple utility functions
- FastAPI routing (use TestClient instead)

## Fixtures and Factories

**Test Data Pattern:**
```python
@pytest.fixture
def sample_signal(self):
    return SignalRequest(
        broker=BrokerType.MT4,
        symbol="EURUSD",
        order_type=OrderType.MARKET,
        side=OrderSide.BUY,
        quantity=0.1,
        price=1.1000,
        stop_loss=1.0900,
        take_profit=1.1100
    )

@pytest.fixture
def executor(self):
    config = {
        "manager_api_url": "http://localhost:4444",
        "manager_login": 1,
        "manager_password": "test"
    }
    return MT4Executor(config)
```

**User/Auth Fixtures:**
```python
@pytest.fixture
def test_user(db: Session):
    """Create test user"""
    user = User(
        email="test@test.com",
        username="testuser",
        hashed_password="hashed",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user):
    """Get auth headers"""
    return {"Authorization": f"Bearer test-token-{test_user.id}"}
```

**Location:**
- Fixtures defined within test classes (no shared `conftest.py`)
- Reusable fixtures at class level with `@pytest.fixture` decorator

## Coverage

**Requirements:** Not enforced (no minimum coverage threshold detected)

**Tools:**
- pytest-cov plugin (referenced in `run_tests.py`)
- Coverage command line flag: `--coverage`

**View Coverage:**
```bash
python tests/run_tests.py --coverage        # Generate all reports
pytest --cov=app --cov-report=html tests/   # HTML report in htmlcov/
pytest --cov=app --cov-report=term-missing  # Terminal with missing lines
```

**Reports Generated:**
- HTML: `htmlcov/` directory
- JSON: `coverage.json`
- Terminal: `--cov-report=term-missing`

## Test Types

**Unit Tests:**
- Scope: Individual functions and methods in isolation
- Location: `test_api.py` (authentication, security functions)
- Pattern: Mock external dependencies, test single responsibility
- Example: `test_create_access_token`, `test_password_hashing`

**Integration Tests:**
- Scope: Component interactions (API endpoints with database, broker executors with HTTP clients)
- Location: `test_brokers.py`, `test_webhooks.py`, `test_api.py`
- Pattern: Mock external APIs but test internal component integration
- Example: `test_place_order_success` (tests executor logic with mocked HTTP)

**E2E Tests:**
- Scope: Complete workflows
- Location: `test_e2e.py` (20,632 lines)
- Pattern: Full request-to-response cycles

**Performance Tests:**
- Scope: Load testing, stress testing
- Location: `test_performance.py` (24,280 lines)
- Framework: Custom performance test suite

## Common Patterns

**Async Testing:**
```python
import pytest

@pytest.mark.asyncio
async def test_async_operation(self, executor):
    """Test async broker operation"""
    result = await executor.connect()
    assert result is True
    assert executor.is_connected is True
```

**Error Testing:**
```python
@pytest.mark.asyncio
async def test_place_order_not_connected(self, executor, sample_signal):
    """Test order placement when not connected."""
    executor.is_connected = False

    with pytest.raises(Exception, match="Not connected to MT4"):
        await executor.place_order(sample_signal)
```

**API Endpoint Testing:**
```python
def test_get_notifications(auth_headers, test_user, db: Session):
    """Test get notifications endpoint"""
    # Create test data
    notification = Notification(
        user_id=test_user.id,
        type=NotificationType.SYSTEM,
        title="Test"
    )
    db.add(notification)
    db.commit()

    # Test endpoint
    response = client.get("/api/v1/notifications", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

**Status Code Testing:**
```python
# Success cases
assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

# Error cases
assert response.status_code == 401  # Unauthorized
assert response.status_code == 404  # Not found
```

**Response Validation:**
```python
response = client.get("/api/v1/analytics/dashboard", headers=auth_headers)
assert response.status_code == 200
data = response.json()
assert "total_users" in data
assert "active_users" in data
```

## Custom Test Runner

**Location:** `tests/run_tests.py`

**Features:**
- Comprehensive test report generation
- Suite-by-suite execution with timing
- JSON report output (`test_report.json`)
- Coverage integration
- Emoji-based status indicators (✅ PASS, ❌ FAIL)

**Test Suites Defined:**
1. Broker Executors (`test_brokers.py`)
2. Webhook Processing (`test_webhooks.py`)
3. API Endpoints (`test_api.py`)
4. WebSocket Connections (`test_websockets.py`)
5. End-to-End Workflows (`test_e2e.py`)
6. UI Integration (`test_ui_integration.py`)
7. Deployment & Health (`test_deployment.py`)
8. Performance & Load (`test_performance.py`)

**Usage:**
```python
runner = TestRunner()
success = runner.run_all_tests()
runner.generate_report()
```

## Test Environment Setup

**Path Configuration:**
```python
import sys
import os

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.models.schemas import UserCreate
```

**Test Client Creation:**
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
```

**Database Fixtures:**
- Tests expect `db: Session` parameter from dependency injection
- Database session management through fixtures
- Test data cleanup handled by fixtures

## Assertion Patterns

**Boolean Assertions:**
```python
assert result is True
assert executor.is_connected is True
```

**Type Assertions:**
```python
assert isinstance(token, str)
assert isinstance(response.json(), list)
```

**Value Assertions:**
```python
assert len(positions) == 1
assert positions[0].symbol == "EURUSD"
assert token is not None
```

**Comparison Assertions:**
```python
assert response.status_code == 200
assert len(token) > 50
```

**Membership Assertions:**
```python
assert "total_users" in data
assert hashed.startswith("$2b$")  # bcrypt hash prefix
```

---

*Testing analysis: 2026-01-19*
