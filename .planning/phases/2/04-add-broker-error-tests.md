# Plan: Add Broker Error Handling Tests

## Metadata

```yaml
phase: 2
plan: 04
title: Add Broker Error Handling Tests
wave: 2
depends_on: [01]
files_modified:
  - tests/test_broker_errors.py
autonomous: true
requirements: [TEST-03]
```

## Goal

Add test coverage for broker executor error scenarios, specifically testing the graceful degradation added in Phase 1.

## Must-Haves

### Truths (post-execution verifiable statements)
- `tests/test_broker_errors.py` exists with error handling tests
- Tests verify `is_available` flag behavior
- Tests verify graceful handling of missing credentials
- Tests verify initialize() returns False when not available

### Artifacts
- tests/test_broker_errors.py - new test file

### Key Links
- app/brokers/tradelocker_executor.py - is_available flag
- app/brokers/tradovate_executor.py - is_available flag
- app/brokers/projectx_executor.py - is_available flag
- app/brokers/mt4_executor.py - is_available flag
- app/brokers/mt5_executor.py - is_available flag
- Phase 1 Plan 02 - added graceful degradation

## Context

### Problem
Phase 1 added `is_available` flag and graceful degradation to all broker executors. This behavior needs test coverage to prevent regression.

### Solution
Create test_broker_errors.py with tests for:
1. Executor sets `is_available=False` when credentials missing
2. `initialize()` returns `False` when `is_available=False`
3. No crash on instantiation with missing credentials
4. Warning logged when disabled

## Tasks

### Task 1: Create test_broker_errors.py
**Type:** auto

Create new test file for broker error handling.

**File:** `tests/test_broker_errors.py`

**Content:**
```python
"""
Tests for broker executor error handling and graceful degradation.
Verifies Phase 1 stability fixes (STAB-02).
"""
import pytest
from unittest.mock import patch, MagicMock
import logging


class TestBrokerGracefulDegradation:
    """Test that broker executors handle missing credentials gracefully."""

    def test_tradelocker_unavailable_without_api_key(self):
        """TradeLocker should set is_available=False when API key is missing."""
        # Mock settings to return empty config
        mock_config = {
            "api_url": "https://api.tradelocker.com",
            "ws_url": "wss://ws.tradelocker.com",
            "api_key": None,  # Missing!
            "environment": "demo"
        }

        with patch('app.core.config.settings.get_broker_config', return_value=mock_config):
            # Should not crash
            from app.brokers.tradelocker_executor import TradeLockerExecutor
            executor = TradeLockerExecutor()

            assert executor.is_available is False
            assert executor.api_key is None

    def test_tradovate_unavailable_without_credentials(self):
        """Tradovate should set is_available=False when credentials missing."""
        mock_config = {
            "api_url": "https://api.tradovate.com",
            "ws_url": "wss://ws.tradovate.com",
            "user_id": None,  # Missing!
            "password": None,  # Missing!
            "app_id": "test",
            "app_version": "1.0",
            "cid": None,
            "sec": None
        }

        with patch('app.core.config.settings.get_broker_config', return_value=mock_config):
            from app.brokers.tradovate_executor import TradovateExecutor
            executor = TradovateExecutor()

            assert executor.is_available is False

    def test_projectx_unavailable_without_token(self):
        """ProjectX should set is_available=False when API token missing."""
        mock_config = {
            "api_url": "https://api.projectx.com",
            "ws_url": "wss://ws.projectx.com",
            "api_token": None,  # Missing!
            "environment": "demo"
        }

        with patch('app.core.config.settings.get_broker_config', return_value=mock_config):
            from app.brokers.projectx_executor import ProjectXExecutor
            executor = ProjectXExecutor()

            assert executor.is_available is False

    def test_mt4_unavailable_without_credentials(self):
        """MT4 should set is_available=False when credentials missing."""
        mock_config = {
            "api_url": "http://localhost:8080",
            "manager_host": "localhost",
            "manager_port": 443,
            "manager_login": None,  # Missing!
            "manager_password": None  # Missing!
        }

        with patch('app.core.config.settings.get_broker_config', return_value=mock_config):
            from app.brokers.mt4_executor import MT4Executor
            executor = MT4Executor()

            assert executor.is_available is False

    def test_mt5_unavailable_without_credentials(self):
        """MT5 should set is_available=False when credentials missing."""
        mock_config = {
            "api_url": "http://localhost:8080",
            "manager_host": "localhost",
            "manager_port": 443,
            "manager_login": None,  # Missing!
            "manager_password": None  # Missing!
        }

        with patch('app.core.config.settings.get_broker_config', return_value=mock_config):
            from app.brokers.mt5_executor import MT5Executor
            executor = MT5Executor()

            assert executor.is_available is False


class TestBrokerInitializeWhenUnavailable:
    """Test that initialize() returns False when executor is unavailable."""

    @pytest.mark.asyncio
    async def test_tradelocker_initialize_returns_false_when_unavailable(self):
        """TradeLocker initialize() should return False when is_available=False."""
        mock_config = {
            "api_url": "https://api.tradelocker.com",
            "ws_url": "wss://ws.tradelocker.com",
            "api_key": None,
            "environment": "demo"
        }

        with patch('app.core.config.settings.get_broker_config', return_value=mock_config):
            from app.brokers.tradelocker_executor import TradeLockerExecutor
            executor = TradeLockerExecutor()

            result = await executor.initialize()
            assert result is False

    @pytest.mark.asyncio
    async def test_tradovate_initialize_returns_false_when_unavailable(self):
        """Tradovate initialize() should return False when is_available=False."""
        mock_config = {
            "api_url": "https://api.tradovate.com",
            "ws_url": "wss://ws.tradovate.com",
            "user_id": None,
            "password": None,
            "app_id": "test",
            "app_version": "1.0",
            "cid": None,
            "sec": None
        }

        with patch('app.core.config.settings.get_broker_config', return_value=mock_config):
            from app.brokers.tradovate_executor import TradovateExecutor
            executor = TradovateExecutor()

            result = await executor.initialize()
            assert result is False


class TestBrokerLogging:
    """Test that appropriate warnings are logged."""

    def test_tradelocker_logs_warning_when_disabled(self, caplog):
        """TradeLocker should log warning when disabled due to missing key."""
        mock_config = {
            "api_url": "https://api.tradelocker.com",
            "ws_url": "wss://ws.tradelocker.com",
            "api_key": None,
            "environment": "demo"
        }

        with caplog.at_level(logging.WARNING):
            with patch('app.core.config.settings.get_broker_config', return_value=mock_config):
                from app.brokers.tradelocker_executor import TradeLockerExecutor
                executor = TradeLockerExecutor()

        assert "disabled" in caplog.text.lower() or "not configured" in caplog.text.lower()
```

### Task 2: Verify new tests pass
**Type:** auto

Run the new broker error tests.

**Command:**
```bash
python3 -m pytest tests/test_broker_errors.py -v 2>&1 | tail -20
```

**Success criteria:** All tests pass (may need `pytest.mark.skip` if imports fail).

### Task 3: Add skip decorators if needed
**Type:** auto

If tests can't import broker executors due to missing dependencies, add skip:
```python
try:
    from app.brokers.tradelocker_executor import TradeLockerExecutor
    BROKERS_AVAILABLE = True
except ImportError:
    BROKERS_AVAILABLE = False

@pytest.mark.skipif(not BROKERS_AVAILABLE, reason="Broker imports unavailable")
class TestBrokerGracefulDegradation:
    ...
```

## Verification

After completing all tasks:

```bash
python3 -m pytest tests/test_broker_errors.py -v --tb=short
# Expected: Tests pass or are skipped with clear reason
```

## Rollback

If issues arise:
1. Remove tests/test_broker_errors.py
2. TEST-03 remains incomplete

---
*Plan created: Phase 2, TEST-03*
