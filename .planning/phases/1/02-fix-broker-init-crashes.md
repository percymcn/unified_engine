# Plan: Fix Broker Executor Initialization Crashes

## Metadata

```yaml
phase: 1
plan: 02
title: Fix Broker Executor Initialization Crashes
wave: 1
depends_on: []
files_modified:
  - app/brokers/tradelocker_executor.py
  - app/brokers/tradovate_executor.py
  - app/brokers/projectx_executor.py
  - app/brokers/mt4_executor.py
  - app/brokers/mt5_executor.py
autonomous: true
requirements: [STAB-02]
```

## Goal

Make broker executors start gracefully when API keys are missing or None, instead of crashing with `'NoneType' object has no attribute 'encode'` or similar errors.

## Must-Haves

### Truths (post-execution verifiable statements)
- TradeLocker executor initializes without crash when `TRADELOCKER_API_KEY` is None
- All broker executors check for None credentials before using them
- Missing credentials log a warning but don't crash the service
- Executors set `self.is_available = False` when credentials are missing

### Artifacts
- None (modifying existing files only)

### Key Links
- `app/brokers/tradelocker_executor.py:30-32` - accesses config["api_key"] without None check
- `app/brokers/base_executor.py:14-18` - BaseExecutor.__init__ pattern
- CONCERNS.md: "TradeLocker API Key Null Encoding" bug

## Context

### Problem
The TradeLocker executor (and potentially others) crash during initialization when API keys are not configured:

```
TradeLocker initialization failed: 'NoneType' object has no attribute 'encode'
```

This happens because the executor tries to use the API key (e.g., setting headers) before checking if it exists.

### Solution
Add defensive checks in each executor's `__init__` method:
1. Check if required credentials exist
2. If missing, set `self.is_available = False` and log a warning
3. Skip initialization of HTTP clients/sessions when credentials are missing
4. Add `is_available` property that other code can check

### References
- CONCERNS.md: "TradeLocker API Key Null Encoding" section
- CONCERNS.md: "Broker Executor Initialization" fragile area

## Tasks

### Task 1: Fix TradeLocker executor initialization
**Type:** auto

Add None checks and graceful degradation when API key is missing.

**Instructions:**
1. Open `app/brokers/tradelocker_executor.py`
2. In `__init__`, after getting config values, add credential validation
3. Set `self.is_available = False` if credentials are missing
4. In `initialize()`, return early if not available

**File:** `app/brokers/tradelocker_executor.py`

**Expected changes:**

After line 33 (`self.access_token = None`), add:
```python
        # Check for required credentials
        self.is_available = bool(self.api_key)
        if not self.is_available:
            logger.warning("TradeLocker executor disabled: API key not configured")
```

In `initialize()` method (line 38), add early return:
```python
    async def initialize(self) -> bool:
        """Initialize TradeLocker connection"""
        if not self.is_available:
            logger.info("TradeLocker skipped: credentials not configured")
            return False
        try:
            # ... existing code
```

Also fix the duplicate initialization bug (lines 25-29 call `super().__init__` twice and set `self.config` twice).

### Task 2: Fix Tradovate executor initialization
**Type:** auto

Add similar defensive checks.

**Instructions:**
1. Open `app/brokers/tradovate_executor.py`
2. Find the `__init__` method
3. Add `self.is_available = bool(...)` check after credential assignment
4. Add early return in `initialize()` if not available

**File:** `app/brokers/tradovate_executor.py`

### Task 3: Fix ProjectX executor initialization
**Type:** auto

Add similar defensive checks.

**Instructions:**
1. Open `app/brokers/projectx_executor.py`
2. Find the `__init__` method
3. Add `self.is_available = bool(...)` check after credential assignment
4. Add early return in `initialize()` if not available

**File:** `app/brokers/projectx_executor.py`

### Task 4: Fix MT4 executor initialization
**Type:** auto

Add similar defensive checks.

**Instructions:**
1. Open `app/brokers/mt4_executor.py`
2. Find the `__init__` method
3. Add `self.is_available = bool(...)` check after credential assignment
4. Add early return in `initialize()` if not available

**File:** `app/brokers/mt4_executor.py`

### Task 5: Fix MT5 executor initialization
**Type:** auto

Add similar defensive checks.

**Instructions:**
1. Open `app/brokers/mt5_executor.py`
2. Find the `__init__` method
3. Add `self.is_available = bool(...)` check after credential assignment
4. Add early return in `initialize()` if not available

**File:** `app/brokers/mt5_executor.py`

### Task 6: Verify executors can be imported
**Type:** auto

Run import checks to verify no crashes occur.

**Instructions:**
```bash
cd /home/pharma5/unified_engine
python3 -c "
from app.brokers.tradelocker_executor import TradeLockerExecutor
from app.brokers.tradovate_executor import TradovateExecutor
from app.brokers.projectx_executor import ProjectXExecutor
from app.brokers.mt4_executor import MT4Executor
from app.brokers.mt5_executor import MT5Executor
print('All executors imported successfully')
"
```

**Success criteria:** Output shows "All executors imported successfully" with no exceptions.

## Verification

After completing all tasks, verify:

1. **Import test with no env vars:**
   ```bash
   unset TRADELOCKER_API_KEY TRADOVATE_API_KEY PROJECTX_API_KEY
   python3 -c "
   from app.brokers.tradelocker_executor import TradeLockerExecutor
   exec = TradeLockerExecutor()
   print(f'TradeLocker is_available: {exec.is_available}')
   "
   # Expected: is_available: False (no crash)
   ```

2. **Check warnings in logs** (should see "disabled: API key not configured" warnings)

## Rollback

If issues arise:
1. Revert changes to each `*_executor.py` file
2. Ensure API keys are set in environment before starting service

---
*Plan created: Phase 1, STAB-02*
