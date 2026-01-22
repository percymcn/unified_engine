# GSD Workflow Roadmap

**Created:** 2026-01-22
**Goal:** Fix critical stability issues preventing clean service startup

---

## Phase 1: Stability Fixes

**Objective:** Make the existing system run without crashes on startup.

**Status:** ✅ COMPLETE

### Wave 1: Core Fixes

| Plan | Title | Status | Verification |
|------|-------|--------|--------------|
| 01 | Fix aioredis Deprecated Import | ✅ Done | Verified on disk |
| 02 | Fix Broker Executor Initialization Crashes | ✅ Done | Verified on disk |
| 03 | Remove Hardcoded Test API Key | ✅ Done | Verified on disk |

### Wave 2: Verification

| Plan | Title | Status | Verification |
|------|-------|--------|--------------|
| 04 | Verify Phase 1 Stability Fixes | ✅ Done | All tests passed |

---

## Phase 1 Success Criteria

All criteria met:

- ✅ Backend starts without `ModuleNotFoundError: No module named 'aioredis'`
- ✅ Backend starts without broker initialization crashes (even with missing API keys)
- ✅ NATS connection failure doesn't crash the service (graceful fallback)
- ✅ No hardcoded API keys in source code

---

## Verification Summary

### Plan 01: aioredis Fix
- **File:** `app/services/funnel_automation.py` line 11
- **Change:** `import aioredis` → `from redis import asyncio as aioredis`
- **File:** `requirements.txt`
- **Change:** Removed `aioredis==2.0.1` line
- **Status:** ✅ Verified - no aioredis in requirements, import works

### Plan 02: Broker Executor Fixes
- **Files:** All 5 broker executors (`tradelocker`, `tradovate`, `projectx`, `mt4`, `mt5`)
- **Changes:** Added `is_available` flag, credential checks, early returns in `initialize()`
- **Status:** ✅ Verified - all executors import without NoneType crashes

### Plan 03: Hardcoded Key Removal
- **File:** `app/routers/auth.py`
- **Change:** Removed `test-api-key` fallback block
- **Status:** ✅ Verified - no hardcoded keys found in codebase

### Plan 04: Verification
- **Tests:** All verification tasks passed
- **Status:** ✅ Complete - Phase 1 ready for handoff

---

## Next Steps

Phase 1 complete. System is now stable for:
- Clean service startup
- Graceful handling of missing credentials
- Production-ready authentication (no hardcoded keys)

---

*Last Updated: 2026-01-22*
