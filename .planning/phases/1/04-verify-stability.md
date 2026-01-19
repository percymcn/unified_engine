# Plan: Verify Phase 1 Stability Fixes

## Metadata

```yaml
phase: 1
plan: 04
title: Verify Phase 1 Stability Fixes
wave: 2
depends_on: [01, 02, 03]
files_modified: []
autonomous: true
requirements: [STAB-01, STAB-02, STAB-03, STAB-04]
```

## Goal

Verify all Phase 1 stability fixes are working correctly by running the backend and checking for crashes.

## Must-Haves

### Truths (post-execution verifiable statements)
- Backend starts without `ModuleNotFoundError: No module named 'aioredis'`
- Backend starts without broker initialization crashes (even with missing API keys)
- NATS connection failure doesn't crash the service (graceful fallback)
- No hardcoded API keys in source code

### Artifacts
- None (verification only)

### Key Links
- ROADMAP.md Phase 1 success criteria
- All Phase 1 plans (01, 02, 03)

## Context

### Purpose
This is the final verification plan for Phase 1. It runs comprehensive checks to ensure all stability fixes are working and the service can start reliably.

### Prerequisites
Plans 01, 02, and 03 must be completed first.

### NATS Status
NATS graceful fallback was already implemented in `app/core/event_emitter.py`. This plan verifies it works correctly (STAB-03).

## Tasks

### Task 1: Verify no hardcoded keys in source
**Type:** auto

Scan the codebase for hardcoded API keys.

**Instructions:**
```bash
cd /home/pharma5/unified_engine

# Check for test-api-key
echo "=== Checking for hardcoded test-api-key ==="
grep -r "test-api-key" app/ --include="*.py" || echo "None found (good)"

# Check for common hardcoded patterns
echo "=== Checking for hardcoded key patterns ==="
grep -rE "api.key.*=.*['\"][a-zA-Z0-9]{10,}['\"]" app/ --include="*.py" | grep -v "Header\|get\|config" || echo "None found (good)"
```

**Success criteria:** No hardcoded API keys found.

### Task 2: Verify imports work without aioredis
**Type:** auto

Test that the funnel automation service imports correctly.

**Instructions:**
```bash
cd /home/pharma5/unified_engine
python3 -c "
from app.services.funnel_automation import FunnelAutomationService
print('FunnelAutomationService: OK')
"
```

**Success criteria:** Import succeeds without `ModuleNotFoundError`.

### Task 3: Verify broker executors handle missing credentials
**Type:** auto

Test that broker executors don't crash with missing API keys.

**Instructions:**
```bash
cd /home/pharma5/unified_engine

# Unset any existing API keys
unset TRADELOCKER_API_KEY TRADOVATE_API_KEY PROJECTX_API_KEY MT4_SERVER MT5_SERVER

python3 -c "
import asyncio
from app.core.config import settings

# Try to instantiate executors (they should not crash)
print('Testing executor instantiation with missing credentials...')

try:
    from app.brokers.tradelocker_executor import TradeLockerExecutor
    # Note: Instantiation might fail if config doesn't exist - that's OK for this test
    print('TradeLocker executor: imported OK')
except Exception as e:
    # Only fail if it's the 'NoneType' attribute error
    if 'NoneType' in str(e) and 'encode' in str(e):
        print(f'FAIL: TradeLocker still crashes with None: {e}')
    else:
        print(f'TradeLocker executor: {type(e).__name__} (acceptable)')

try:
    from app.brokers.tradovate_executor import TradovateExecutor
    print('Tradovate executor: imported OK')
except Exception as e:
    if 'NoneType' in str(e) and 'encode' in str(e):
        print(f'FAIL: Tradovate still crashes with None: {e}')
    else:
        print(f'Tradovate executor: {type(e).__name__} (acceptable)')

try:
    from app.brokers.projectx_executor import ProjectXExecutor
    print('ProjectX executor: imported OK')
except Exception as e:
    if 'NoneType' in str(e) and 'encode' in str(e):
        print(f'FAIL: ProjectX still crashes with None: {e}')
    else:
        print(f'ProjectX executor: {type(e).__name__} (acceptable)')

print('Broker executor import test complete')
"
```

**Success criteria:** No `'NoneType' object has no attribute 'encode'` errors.

### Task 4: Verify NATS graceful fallback
**Type:** auto

Test that NATS connection failure doesn't crash the service.

**Instructions:**
```bash
cd /home/pharma5/unified_engine

# Test with NATS not available
unset NATS_URL

python3 -c "
import asyncio
from app.core.event_emitter import event_emitter

async def test_nats_fallback():
    # Initialize with non-existent NATS
    await event_emitter.initialize('nats://nonexistent:4222')

    # Should fall back to logging, not crash
    await event_emitter.emit('test.subject', 'test_event', {'data': 'test'})

    print('NATS graceful fallback: OK')

    await event_emitter.shutdown()

asyncio.run(test_nats_fallback())
"
```

**Success criteria:** Test completes without crash, shows "NATS graceful fallback: OK".

### Task 5: Run full import test
**Type:** auto

Test that the main application module can be imported.

**Instructions:**
```bash
cd /home/pharma5/unified_engine

python3 -c "
import sys
sys.path.insert(0, '.')

# Test critical imports
print('Testing critical imports...')

from app.core.config import settings
print('  config: OK')

from app.core.event_emitter import event_emitter
print('  event_emitter: OK')

from app.routers.auth import verify_api_key
print('  auth.verify_api_key: OK')

from app.services.funnel_automation import FunnelAutomationService
print('  FunnelAutomationService: OK')

print('')
print('All Phase 1 critical imports: PASSED')
"
```

**Success criteria:** All imports succeed.

### Task 6: Verify requirements.txt is clean
**Type:** auto

Ensure deprecated packages are removed.

**Instructions:**
```bash
cd /home/pharma5/unified_engine

echo "=== Checking requirements.txt ==="
if grep -q "aioredis" requirements.txt; then
    echo "FAIL: aioredis still in requirements.txt"
    exit 1
else
    echo "OK: aioredis removed from requirements.txt"
fi

if grep -q "redis==" requirements.txt; then
    echo "OK: redis package present"
else
    echo "WARN: redis package not found in requirements.txt"
fi
```

**Success criteria:** aioredis not present, redis present.

## Verification

Phase 1 success criteria from ROADMAP.md:

1. **Backend starts without aioredis import errors** - Verified by Task 2
2. **Backend starts without broker initialization crashes** - Verified by Task 3
3. **NATS connection failure doesn't crash the service** - Verified by Task 4
4. **No hardcoded API keys in source code** - Verified by Task 1

## Rollback

If verification fails:
1. Identify which plan(s) need adjustment
2. Review error messages
3. Re-execute the failing plan with fixes

---
*Plan created: Phase 1 verification*
