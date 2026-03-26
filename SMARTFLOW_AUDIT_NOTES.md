# SmartFlow System Audit Notes
**Date:** 2026-03-17
**Status:** PRE-REBUILD AUDIT

---

## 1. CRITICAL DATABASE vs MODEL MISMATCHES

### 1.1 `smartflow_signal_logs` - MISSING COLUMNS
The model defines columns that do NOT exist in the database:

| Column | Model Type | Status |
|--------|-----------|--------|
| `webhooks_posted` | JSON | **MISSING IN DB** |
| `post_successful` | Boolean | **MISSING IN DB** |
| `post_errors` | Text | **MISSING IN DB** |

**Impact:** Any attempt to INSERT/UPDATE signal logs with these fields will FAIL.

**Fix Required:** Migration to add columns:
```sql
ALTER TABLE smartflow_signal_logs
ADD COLUMN webhooks_posted JSONB DEFAULT '[]',
ADD COLUMN post_successful BOOLEAN DEFAULT false,
ADD COLUMN post_errors TEXT;
```

### 1.2 `smartflow_configs` - MISSING COLUMNS
The model defines engine settings that do NOT exist in the database:

| Column | Model Type | Status |
|--------|-----------|--------|
| `enable_deterministic_mode` | Boolean | **MISSING IN DB** |
| `deterministic_min_confidence` | Float | **MISSING IN DB** |
| `deterministic_min_aligned_tfs` | Integer | **MISSING IN DB** |
| `deterministic_min_rr` | Float | **MISSING IN DB** |
| `deterministic_rr_preset` | String(20) | **MISSING IN DB** |
| `enable_quick_mode` | Boolean | **MISSING IN DB** |
| `quick_scan_interval` | Integer | **MISSING IN DB** |
| `quick_min_confidence` | Float | **MISSING IN DB** |
| `quick_min_rr` | Float | **MISSING IN DB** |
| `quick_require_15m_confirmation` | Boolean | **MISSING IN DB** |

**Impact:** Deterministic and Quick Mode settings cannot be persisted to DB.

**Fix Required:** Migration to add columns:
```sql
ALTER TABLE smartflow_configs
ADD COLUMN enable_deterministic_mode BOOLEAN DEFAULT true,
ADD COLUMN deterministic_min_confidence DOUBLE PRECISION DEFAULT 75.0,
ADD COLUMN deterministic_min_aligned_tfs INTEGER DEFAULT 4,
ADD COLUMN deterministic_min_rr DOUBLE PRECISION DEFAULT 2.0,
ADD COLUMN deterministic_rr_preset VARCHAR(20) DEFAULT 'balanced',
ADD COLUMN enable_quick_mode BOOLEAN DEFAULT true,
ADD COLUMN quick_scan_interval INTEGER DEFAULT 60,
ADD COLUMN quick_min_confidence DOUBLE PRECISION DEFAULT 60.0,
ADD COLUMN quick_min_rr DOUBLE PRECISION DEFAULT 1.5,
ADD COLUMN quick_require_15m_confirmation BOOLEAN DEFAULT true;
```

---

## 2. MODEL FILE ISSUES

### 2.1 Fixed: ForeignKey Reference (Previous Session)
- **File:** `app/models/smartflow_models.py:112`
- **Issue:** ForeignKey referenced old table name `smartflow_config.id`
- **Fix:** Changed to `smartflow_configs.id`
- **Status:** FIXED, awaiting rebuild

### 2.2 Fixed: Table Name (Previous Session)
- **File:** `app/models/smartflow_models.py:25`
- **Issue:** `__tablename__ = "smartflow_config"` didn't match DB table `smartflow_configs`
- **Fix:** Changed to `__tablename__ = "smartflow_configs"`
- **Status:** FIXED, awaiting rebuild

---

## 3. UI COMPONENT AUDIT

### 3.1 API Endpoints Called by UI

| Component | Endpoints Called | Status |
|-----------|-----------------|--------|
| `webhooks-dashboard.tsx` | `/api/webhook-configs/`, `/api/accounts` | **FIXED** - accounts data extraction |
| `live-signals-dashboard.tsx` | `/api/v1/smartflow/signals` | **FIXED** - interface matches backend |
| `quick-mode-dashboard.tsx` | `/api/v1/smartflow/status`, `/api/v1/smartflow/signals` | OK |
| `deterministic-dashboard.tsx` | `/api/v1/smartflow/deterministic/performance` | OK |
| `forward-test-dashboard.tsx` | `/api/v1/smartflow/forward-test/trades` | OK |
| `compare-engines-dashboard.tsx` | `/api/v1/smartflow/backtest/compare/run` | OK |
| `elite-dashboard.tsx` | `/api/v1/smartflow/elite/*` | OK |
| `ml-dashboard.tsx` | `/api/v1/smartflow/ml/dashboard`, `/api/v1/smartflow/ml/run-optimization` | OK |
| `ai-analysis-dashboard.tsx` | `/api/v1/smartflow/trade-decisions`, `/api/v1/smartflow/ai/analysis` | OK |
| `strategies-overview.tsx` | `/api/strategies` | OK |
| `adaptive-router-dashboard.tsx` | `/api/v1/smartflow/router/*`, `/api/v1/smartflow/allocator/*` | OK |

### 3.2 Fixed UI Issues (Previous Session)
1. **webhooks-dashboard.tsx:91** - Fixed `h.map is not a function`
   - Backend returns `{accounts: [...], total: N}`
   - UI now extracts array correctly

2. **live-signals-dashboard.tsx** - Updated interface to match actual backend fields
   - Added: `bullish_flows`, `bearish_flows`, `total_premium`
   - Changed: `probability` → `score`

---

## 4. BACKEND ROUTER AUDIT

### 4.1 SmartFlow Router Endpoints (smartflow.py)
Total: 45+ endpoints

**Core Config:**
- `GET/PUT /config` - Configuration CRUD
- `GET /status` - SmartFlow status

**Signals:**
- `GET /signals` - Signal history
- `GET /scores/history` - Score charts
- `POST /test-signal` - Test webhook

**ML Learning:**
- `GET /ml/dashboard` - ML metrics
- `GET /ml/adaptive-thresholds` - Learned thresholds
- `POST /ml/optimize-thresholds` - Trigger optimization
- `GET /ml/time-optimization` - Time of day stats
- `POST /ml/detect-correlation` - Cross-ticker correlation
- `POST /ml/run-optimization` - Full ML optimization

**AI Analysis:**
- `GET /ai/analysis` - Cached analyses
- `GET /ai/analysis/stats` - Analysis stats
- `GET /ai-context` - Market context
- `GET /trade-decisions` - Trade history with AI context
- `GET /trade-decisions/stats` - Performance by mode

**Engines:**
- `GET /deterministic/performance` - Deterministic engine stats
- `GET /elite/*` - Elite backtest suite
- `GET /forward-test/*` - Forward test trades

**Backtest:**
- `POST /backtest/run` - Run single backtest
- `GET /backtest/results` - Get results
- `POST /backtest/compare/run` - Compare engines

**Router & Allocator:**
- `GET /router/status` - Active router mode
- `POST /router/mode` - Set router mode
- `GET /allocator/status` - Allocator state
- `GET /allocator/decision` - Current allocation

**Feature Engines:**
- `GET /ai-features/status` - AI feature engine status
- `GET /flow/status` - Flow engine status
- `GET /flow/features/{symbol}` - Per-symbol flow features

### 4.2 Fixed Backend Issues (Previous Session)
1. **forward-test/status endpoint** - Fixed access to non-existent model fields
   - Removed: `stop_loss`, `take_profit`, `market_regime`, `dispatched`
   - Using actual fields: `score`, `confidence`, `post_successful`, etc.

---

## 5. API PROXY ROUTES (Next.js BFF)

### 5.1 SmartFlow Proxy
- **File:** `ui-next/src/app/api/v1/smartflow/[...path]/route.ts`
- **Pattern:** Proxies all `/api/v1/smartflow/*` to backend `http://unified_api:8000/api/v1/smartflow/*`
- **Status:** OK

### 5.2 Other Proxies
- `/api/accounts` - Proxies to backend
- `/api/webhook-configs/*` - Proxies to backend
- `/api/strategies` - Proxies to backend

---

## 6. REQUIRED ACTIONS BEFORE REBUILD

### Priority 1: Database Migration
Run Alembic migration or SQL to add missing columns:
1. Add 3 columns to `smartflow_signal_logs`
2. Add 10 columns to `smartflow_configs`

### Priority 2: Verify Alembic Migration Exists
Check if migration already exists in `alembic/versions/` for these columns.

### Priority 3: Rebuild After DB Sync
Only rebuild after database schema matches model.

---

## 7. RUNTIME COMPONENTS STATUS (from previous verification)

| Component | Expected | Status |
|-----------|----------|--------|
| API Container | 2GB memory | OK |
| Celery Worker | Running | OK |
| Celery Beat | Running | OK |
| Redis | Running | OK |
| PostgreSQL | Running | OK |
| Signal Generation | Active | BLOCKED by mapper error |
| Webhook Delivery | Active | BLOCKED by mapper error |
| Broker Execution | Active | BLOCKED by mapper error |

---

## 8. BLOCKING ERROR (Current)

```
sqlalchemy.orm.exc.InvalidRequestError:
Could not determine join condition between parent/child tables
on relationship SmartFlowConfig.signal_logs
```

**Root Cause:** ForeignKey referenced `smartflow_config.id` but table is `smartflow_configs`
**Fix Applied:** Changed to `smartflow_configs.id` in model
**Status:** Awaiting rebuild to apply fix

---

## SUMMARY

### Critical Fixes Applied (awaiting rebuild):
1. Table name: `smartflow_config` → `smartflow_configs`
2. ForeignKey: `smartflow_config.id` → `smartflow_configs.id`
3. UI accounts data extraction
4. UI live signals interface
5. Backend forward-test/status endpoint

### Database Migration Required:
- 13 columns missing across 2 tables
- Must run migration BEFORE rebuild

### After Rebuild:
- Signal logging will work
- Webhook delivery will resume
- Engine tracking will persist
- Dashboard data will be accurate

---

## 9. DATABASE vs MIGRATIONS DISCREPANCY

### 9.1 Table Name Mismatch
- **Migrations:** Reference `smartflow_config` (singular)
- **Database:** Actually has `smartflow_configs` (plural)
- **Model (fixed):** Now uses `smartflow_configs` (plural)

**Conclusion:** Database was likely created manually or via different process than migrations.
Migrations are STALE and should not be relied upon for this table.

### 9.2 Missing ForeignKey Constraint
- **Model expects:** FK from `signal_logs.config_id` → `smartflow_configs.id`
- **Database has:** NO FK constraint on `smartflow_signal_logs`
- **Impact:** Orphan records possible but SQLAlchemy handles relationship in Python

### 9.3 Signal Logs - Webhook Columns
- **Original migration 6aba51c2624e** defines: `webhooks_posted`, `post_successful`, `post_errors`
- **Database reality:** These columns DO NOT EXIST
- **Likely cause:** Database was created before/differently from migration

### 9.4 Current Alembic Version
Database is at version `048_add_webhook_configs` - migrations have run but table schema differs from migration definitions.

---

## 10. RECOMMENDED FIXES

### Option A: Add Missing Columns via SQL (Quick Fix)
```sql
-- Add missing columns to smartflow_signal_logs
ALTER TABLE smartflow_signal_logs
ADD COLUMN IF NOT EXISTS webhooks_posted JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS post_successful BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS post_errors TEXT;

-- Add missing columns to smartflow_configs
ALTER TABLE smartflow_configs
ADD COLUMN IF NOT EXISTS enable_deterministic_mode BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS deterministic_min_confidence DOUBLE PRECISION DEFAULT 75.0,
ADD COLUMN IF NOT EXISTS deterministic_min_aligned_tfs INTEGER DEFAULT 4,
ADD COLUMN IF NOT EXISTS deterministic_min_rr DOUBLE PRECISION DEFAULT 2.0,
ADD COLUMN IF NOT EXISTS deterministic_rr_preset VARCHAR(20) DEFAULT 'balanced',
ADD COLUMN IF NOT EXISTS enable_quick_mode BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS quick_scan_interval INTEGER DEFAULT 60,
ADD COLUMN IF NOT EXISTS quick_min_confidence DOUBLE PRECISION DEFAULT 60.0,
ADD COLUMN IF NOT EXISTS quick_min_rr DOUBLE PRECISION DEFAULT 1.5,
ADD COLUMN IF NOT EXISTS quick_require_15m_confirmation BOOLEAN DEFAULT true;
```

### Option B: Create New Alembic Migration
Create migration 049 to add missing columns properly.

### Option C: Service Can Operate Without These Columns
The smartflow_service.py handles missing columns gracefully by not using them.
However, webhook tracking will be lost without signal_logs webhook columns.

---

## 11. SMARTFLOW SERVICE DEFENSIVE CODING

The backend `smartflow_service.py` is designed to be defensive:
- Uses `getattr()` with defaults for config fields that may not exist
- Handles missing database columns gracefully
- Falls back to hardcoded defaults when DB columns missing

This means the service WILL WORK even without database columns,
but persistence of settings will be lost until columns are added.
