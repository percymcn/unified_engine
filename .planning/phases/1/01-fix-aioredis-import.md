# Plan: Fix aioredis Deprecated Import

## Metadata

```yaml
phase: 1
plan: 01
title: Fix aioredis Deprecated Import
wave: 1
depends_on: []
files_modified:
  - app/services/funnel_automation.py
  - requirements.txt
autonomous: true
requirements: [STAB-01]
```

## Goal

Replace the deprecated `aioredis` package import with the modern `redis.asyncio` module, and remove the deprecated package from requirements.txt.

## Must-Haves

### Truths (post-execution verifiable statements)
- `app/services/funnel_automation.py` imports `redis.asyncio` instead of `aioredis`
- `requirements.txt` does NOT contain `aioredis` line
- `requirements.txt` contains `redis>=5.0.1` (already present)
- Service starts without `ModuleNotFoundError: No module named 'aioredis'`

### Artifacts
- None (modifying existing files only)

### Key Links
- `app/services/funnel_automation.py:11` - import statement
- `app/services/funnel_automation.py:35` - `aioredis.from_url()` call
- `requirements.txt:13` - deprecated aioredis line to remove

## Context

### Problem
The funnel automation service crashes on startup with:
```
ModuleNotFoundError: No module named 'aioredis'
```

This is because `aioredis` was deprecated and absorbed into `redis-py` 5.0+. The codebase has both `redis==5.0.1` and `aioredis==2.0.1` in requirements.txt, causing confusion.

### Solution
Replace the import:
```python
# Before
import aioredis

# After
from redis import asyncio as aioredis  # Alias for backwards compatibility
```

The `redis.asyncio` module provides the same `from_url()` API, so existing code using `aioredis.from_url()` will work unchanged.

### References
- CONCERNS.md: "aioredis deprecated import" section
- STACK.md: "redis (not aioredis)" recommendation

## Tasks

### Task 1: Update funnel_automation.py import
**Type:** auto

Replace the deprecated import with the modern equivalent while maintaining API compatibility.

**Instructions:**
1. Open `app/services/funnel_automation.py`
2. Find line 11: `import aioredis`
3. Replace with: `from redis import asyncio as aioredis`

**File:** `app/services/funnel_automation.py`

**Expected change:**
```python
# Line 11 - before:
import aioredis

# Line 11 - after:
from redis import asyncio as aioredis
```

### Task 2: Remove aioredis from requirements.txt
**Type:** auto

Remove the deprecated package from dependencies.

**Instructions:**
1. Open `requirements.txt`
2. Find and delete line 13: `aioredis==2.0.1`
3. Verify `redis==5.0.1` remains (line 12)

**File:** `requirements.txt`

**Expected change:**
```
# Before (lines 11-14):
# Cache & Sessions
redis==5.0.1
aioredis==2.0.1
python-multipart==0.0.6

# After (lines 11-13):
# Cache & Sessions
redis==5.0.1
python-multipart==0.0.6
```

### Task 3: Verify import works
**Type:** auto

Run a quick Python import check to verify the fix.

**Instructions:**
```bash
cd /home/pharma5/unified_engine
python3 -c "from redis import asyncio as aioredis; print('Import OK:', aioredis.from_url)"
```

**Success criteria:** Output shows `Import OK:` followed by function reference.

## Verification

After completing all tasks, verify:

1. **Import test:**
   ```bash
   python3 -c "from app.services.funnel_automation import FunnelAutomationService; print('FunnelAutomationService imported successfully')"
   ```

2. **No aioredis in requirements:**
   ```bash
   grep -c "aioredis" requirements.txt
   # Expected: 0
   ```

## Rollback

If issues arise:
1. Revert `app/services/funnel_automation.py` line 11 to `import aioredis`
2. Re-add `aioredis==2.0.1` to requirements.txt after `redis==5.0.1`
3. Run `pip install aioredis==2.0.1`

---
*Plan created: Phase 1, STAB-01*
