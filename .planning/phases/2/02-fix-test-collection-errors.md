# Plan: Fix Test Collection Errors

## Metadata

```yaml
phase: 2
plan: 02
title: Fix Test Collection Errors
wave: 1
depends_on: []
files_modified:
  - tests/test_analytics.py
  - tests/test_api.py
  - tests/test_brokers.py
  - tests/test_e2e.py
  - tests/test_notifications.py
  - tests/test_ui_integration.py
  - tests/test_webhooks.py
  - tests/test_websockets.py
autonomous: true
requirements: [TEST-01]
```

## Goal

Fix the 8 test collection errors caused by import failures. Tests should collect without errors even when optional dependencies are missing.

## Must-Haves

### Truths (post-execution verifiable statements)
- `pytest --collect-only` shows 0 collection errors
- All test files can be imported without crashing
- Tests that require unavailable dependencies are skipped gracefully

### Artifacts
- None (modifying existing test files)

### Key Links
- tests/test_analytics.py - fails on `from app.main import app`
- tests/test_api.py - fails on `from app.main import app`
- tests/test_brokers.py - fails on broker imports
- app/brokers/tradelocker_executor.py:11 - `import socketio` fails

## Context

### Problem
8 test files fail to collect because they import `app.main` which triggers the full import chain:
```
app.main → app.services.signal_processor → app.brokers.tradelocker_executor → import socketio
```

When `socketio` (python-socketio) isn't installed, all tests that import app.main fail.

### Solution
Wrap app imports in try/except and skip tests when dependencies unavailable:
```python
try:
    from app.main import app
    APP_AVAILABLE = True
except ImportError as e:
    APP_AVAILABLE = False
    APP_IMPORT_ERROR = str(e)

# In test class or function:
@pytest.mark.skipif(not APP_AVAILABLE, reason=f"App import failed: {APP_IMPORT_ERROR}")
```

### References
- pytest --collect-only output showing 8 errors
- ModuleNotFoundError: No module named 'socketio'

## Tasks

### Task 1: Fix test_analytics.py imports
**Type:** auto

Wrap app import with try/except and add skip decorator.

**File:** `tests/test_analytics.py`

**Pattern to apply:**
```python
import pytest

# Safe import with fallback
try:
    from app.main import app
    from fastapi.testclient import TestClient
    APP_AVAILABLE = True
    APP_IMPORT_ERROR = None
except ImportError as e:
    APP_AVAILABLE = False
    APP_IMPORT_ERROR = str(e)
    app = None
    TestClient = None
```

Then add to test class:
```python
@pytest.mark.skipif(not APP_AVAILABLE, reason=f"App import failed: {APP_IMPORT_ERROR}")
class TestAnalytics:
    ...
```

### Task 2: Fix test_api.py imports
**Type:** auto

Apply same pattern to test_api.py.

**File:** `tests/test_api.py`

### Task 3: Fix test_brokers.py imports
**Type:** auto

Apply safe import pattern to test_brokers.py.

**File:** `tests/test_brokers.py`

### Task 4: Fix test_e2e.py imports
**Type:** auto

Apply safe import pattern to test_e2e.py.

**File:** `tests/test_e2e.py`

### Task 5: Fix test_notifications.py imports
**Type:** auto

Apply safe import pattern to test_notifications.py.

**File:** `tests/test_notifications.py`

### Task 6: Fix test_ui_integration.py imports
**Type:** auto

Apply safe import pattern to test_ui_integration.py.

**File:** `tests/test_ui_integration.py`

### Task 7: Fix test_webhooks.py imports
**Type:** auto

Apply safe import pattern to test_webhooks.py.

**File:** `tests/test_webhooks.py`

### Task 8: Fix test_websockets.py imports
**Type:** auto

Apply safe import pattern to test_websockets.py.

**File:** `tests/test_websockets.py`

### Task 9: Verify all tests collect
**Type:** auto

Run pytest --collect-only and verify 0 errors.

**Command:**
```bash
python3 -m pytest --collect-only tests/ 2>&1 | grep -E "collected|error"
```

**Success criteria:** Shows "X items" collected, 0 errors.

## Verification

After completing all tasks:

```bash
python3 -m pytest --collect-only tests/ 2>&1 | tail -5
# Expected: "X items" with no "errors"
```

## Rollback

If issues arise:
1. Revert test file changes via git
2. Tests will fail to collect as before

---
*Plan created: Phase 2, TEST-01 (partial)*
