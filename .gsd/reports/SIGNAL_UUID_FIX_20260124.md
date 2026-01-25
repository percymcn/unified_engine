# Signal UUID→INT Fix Report

**Date:** 2026-01-24
**Branch:** `fix/missing-greenlet-startup`
**Commit:** (pending)

---

## SUMMARY

Fixed critical crash in signal processing where UUID-based SignalId values were being passed to `int()`, causing "invalid literal for int()" errors when processing webhook signals.

---

## ROOT CAUSE

The signal processing flow creates signals with UUID-based IDs:
```python
# process_signal.py:106
signal_id = SignalId(str(uuid.uuid4()))  # e.g., 'dbaf8a0d-35aa-447f-89b1-247fe817a75a'
```

The signal repository then crashed trying to look up existing signals:
```python
# signal_repository.py:50 (BEFORE)
stmt = select(SignalORM).where(SignalORM.id == int(signal.id.value))
# CRASH: int('dbaf8a0d-35aa-447f-89b1-247fe817a75a')
```

---

## FIXES APPLIED

### Fix 1: Signal Repository - UUID Detection (CRITICAL)
**File:** `app/infrastructure/repositories/signal_repository.py`

Added `_is_new_signal()` helper to detect UUID vs integer IDs:
- UUID strings → New signal, skip lookup, insert directly
- Integer strings → Existing signal, lookup by ID

```python
def _is_new_signal(self, signal_id: SignalId) -> bool:
    try:
        int(signal_id.value)
        return False  # Valid integer = existing signal
    except ValueError:
        return True  # UUID string = new signal
```

Updated `save()`, `delete()`, and `get_by_id()` methods to use this detection.

### Fix 2: Signal Mapper - Column Name Corrections
**File:** `app/infrastructure/mappers/signal_mapper.py`

Fixed column name mismatches:
- `orm_model.quantity` → `orm_model.volume`
- `orm_model.received_at` → `orm_model.created_at`
- `orm_model.source_id` → `orm_model.strategy_id`

Added:
- `signal_id` column population for external UUID tracking
- String status handling in `_map_status_to_domain()`

### Fix 3: Signal Repository - Column Names
**File:** `app/infrastructure/repositories/signal_repository.py`

Fixed all `received_at` references to `created_at` in:
- `get_pending()`
- `get_by_status()`
- `get_by_user()`
- `get_recent()`

### Fix 4: Risk Dashboard UI Routes (OBSERVABILITY)
**Files Created:**
- `ui-next/src/app/api/v1/risk/rejected-signals/route.ts`
- `ui-next/src/app/api/v1/risk/dashboard-summary/route.ts`
- `ui-next/src/app/api/risk/rejected-signals/route.ts`
- `ui-next/src/app/api/risk/dashboard-summary/route.ts`

These BFF proxy routes enable the dashboard to display:
- Rejected signals list
- Risk dashboard summary

---

## VERIFICATION

### Unit Tests (3 new tests added)
```bash
$ pytest tests/infrastructure/test_repositories.py::TestSQLAlchemySignalRepository -v

test_is_new_signal_detects_uuid PASSED
test_save_new_signal_with_uuid_skips_lookup PASSED
test_get_by_id_with_uuid_returns_none PASSED
```

### Integration Test
```python
# Creates signal with UUID, saves, retrieves by integer ID
Original signal ID (UUID): 6d792a2c-cd6d-4089-830e-59aedd1f806d
Saved signal ID (integer): 1
Signal saved successfully!
Retrieved signal: 1 - EURUSD buy

✅ UUID→INT FIX VERIFIED
```

### Endpoint Verification
| Endpoint | Status |
|----------|--------|
| Backend health | 200 OK |
| UI accessible | 200 OK |
| `/api/v1/risk/rejected-signals` | 401 (auth required - correct) |
| `/api/v1/risk/dashboard-summary` | 401 (auth required - correct) |
| `/api/billing/status` | 401 (auth required - correct) |
| `/api/trial/status` | 401 (auth required - correct) |

---

## FILES MODIFIED

| File | Lines Changed | Type |
|------|---------------|------|
| `app/infrastructure/repositories/signal_repository.py` | +35, -8 | Bug fix |
| `app/infrastructure/mappers/signal_mapper.py` | +42, -18 | Bug fix |
| `tests/infrastructure/test_repositories.py` | +62 | Tests |
| `ui-next/src/app/api/v1/risk/rejected-signals/route.ts` | +45 | New file |
| `ui-next/src/app/api/v1/risk/dashboard-summary/route.ts` | +40 | New file |
| `ui-next/src/app/api/risk/rejected-signals/route.ts` | +45 | New file |
| `ui-next/src/app/api/risk/dashboard-summary/route.ts` | +40 | New file |

**Total:** 7 files, ~270 insertions

---

## PHASES COMPLETED

- [x] PHASE 1: Fix webhook UUID→INT crash
- [x] PHASE 2: UI up + connected to backend
- [x] PHASE 3: Automated tests (pytest)
- [x] PHASE 4: Observability for rejections + guard
- [x] PHASE 5: Billing/trial check

---

## STATUS: COMPLETE

Signal processing can now handle UUID-based IDs correctly. The fix:
1. Detects new signals by checking if ID is valid integer
2. Skips database lookup for new signals
3. Inserts directly and returns entity with DB-generated integer ID
4. Maps columns correctly between domain and ORM layers
