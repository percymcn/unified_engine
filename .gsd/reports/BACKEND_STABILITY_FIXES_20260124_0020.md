# Backend Stability Fixes & Migration Report

**Date:** 2026-01-24  
**Commit:** Backend stability fixes + DB migration + smoke tests

## Problem

Backend was timing out on `/health` (curl exit code 28) and `/openapi.json` was potentially empty. Root cause: uvicorn `--reload` watcher was scanning entire project directory including `ui-next/` and `node_modules/`, causing performance issues.

## Solutions Implemented

### 1. Fixed Uvicorn Reload Watcher ✅

**Changes:**
- Updated `app/main.py` to set `reload_dirs=["app"]` when reload is enabled
- Updated `scripts/local_up_postgres.sh` to use `--reload-dir app`
- Updated `run_backend.py` to add `--reload-dir app` flag

**Result:**
- Reload only watches `app/` directory
- Excludes `ui-next/` and `node_modules/` from file watching
- Default behavior: no reload (stable production mode)
- Reload only enabled when `RELOAD=true` env var is set

**Files Modified:**
- `app/main.py` - Added `reload_dirs` parameter
- `scripts/local_up_postgres.sh` - Added `--reload-dir app`
- `run_backend.py` - Added `--reload-dir app`

### 2. Database Migration Script ✅

**Created:** `scripts/migrate_add_account_selection_fields.py`

**Features:**
- Detects SQLite vs PostgreSQL automatically
- Idempotent - safe to run multiple times
- Adds three columns to `trading_accounts` table:
  - `enabled_broker_account_ids` (JSON/JSONB)
  - `default_broker_account_id` (VARCHAR(100))
  - `discovered_accounts_cache` (JSON/JSONB)

**Usage:**
```bash
python3 scripts/migrate_add_account_selection_fields.py
```

**Verification:**
- Migration ran successfully on PostgreSQL
- Idempotency verified (second run shows "already exists")
- Columns added: enabled_broker_account_ids, default_broker_account_id, discovered_accounts_cache

### 3. Smoke Test Script ✅

**Created:** `scripts/smoke_backend.sh`

**Features:**
- Starts backend if not running (without reload for stability)
- Tests `/health` endpoint with 5s timeout
- Tests `/openapi.json` endpoint with 10s timeout
- Validates JSON structure
- Checks OpenAPI schema presence
- Fails loudly with logs on errors

**Usage:**
```bash
bash scripts/smoke_backend.sh
```

**Tests:**
- `/health` returns valid response
- `/openapi.json` returns valid JSON (>100 bytes)
- OpenAPI structure validation

## Commands

### Run Migration
```bash
cd /home/pharma5/unified_engine
python3 scripts/migrate_add_account_selection_fields.py
```

### Run Smoke Test
```bash
cd /home/pharma5/unified_engine
bash scripts/smoke_backend.sh
```

### Start Backend (Stable, No Reload)
```bash
cd /home/pharma5/unified_engine
export RELOAD=false
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8765
```

### Start Backend (With Reload, App Directory Only)
```bash
cd /home/pharma5/unified_engine
export RELOAD=true
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8765 --reload --reload-dir app
```

### Test Health Endpoint
```bash
curl -m 2 http://127.0.0.1:8765/health
```

### Test OpenAPI Endpoint
```bash
curl -m 10 http://127.0.0.1:8765/openapi.json | python3 -m json.tool | head -20
```

## Acceptance Criteria

✅ **curl -m 2 /health returns**
- Health endpoint responds within 2 seconds
- No timeout errors (exit code 28)

✅ **curl /openapi.json returns valid json**
- OpenAPI endpoint returns valid JSON
- JSON is >100 bytes (not empty)
- Contains OpenAPI structure

✅ **Migration script runs safely multiple times**
- First run: Adds columns
- Second run: Detects existing columns, skips
- No errors on repeated runs

## Files Changed

1. `app/main.py` - Added reload_dirs configuration
2. `scripts/local_up_postgres.sh` - Added --reload-dir app
3. `run_backend.py` - Added --reload-dir app
4. `scripts/migrate_add_account_selection_fields.py` - NEW
5. `scripts/smoke_backend.sh` - NEW

## Testing Results

### Migration Test
```
✓ Migration completed successfully
✓ Idempotency verified (second run shows "already exists")
```

### Smoke Test
```
✓ Backend started successfully
✓ /health endpoint responded
✓ /openapi.json is valid JSON with OpenAPI structure
```

## Next Steps

1. Run migration on production database when ready
2. Monitor backend performance with reload disabled in production
3. Use smoke test script in CI/CD pipeline
4. Consider adding health check endpoint to monitoring

---

**Status:** ✅ All fixes implemented and tested
