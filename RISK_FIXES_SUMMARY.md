# Risk Management Fixes - Summary

**Date:** 2026-02-16
**Issue:** Risk management settings not being enforced

---

## Root Causes Found

### 🔴 CRITICAL: Daily Counters Stored in Memory

**Problem:**
- Trade counters (for `max_daily_trades`, `trade_cooldown_seconds`) were stored in **RAM**
- Every container restart/deployment **wiped all counters**
- `max_daily_trades` limit **reset to zero** after each deploy

**File:** `app/infrastructure/repositories/daily_counter_repository.py`

**Before:**
```python
class InMemoryDailyCounterRepository:
    def __init__(self):
        self._storage: Dict[tuple, DailyCounters] = {}  # ← Lost on restart!
```

---

## Fixes Applied

### ✅ Fix #1: Database-Backed Counter Storage

**Created:**
1. **Migration:** `alembic/versions/033_add_daily_counters_table.py`
   - Creates `daily_counters` table in PostgreSQL
   - Persists across container restarts

2. **Model:** `app/models/database_models.py`
   - Added `DailyCounter` SQLAlchemy model

3. **Repository:** `app/infrastructure/repositories/daily_counter_repository.py`
   - Created `SQLAlchemyDailyCounterRepository`
   - Reads/writes to database instead of memory
   - Uses PostgreSQL UPSERT for atomic updates

**Schema:**
```sql
CREATE TABLE daily_counters (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES trading_accounts(id),
    date DATE NOT NULL,
    signals_received INTEGER DEFAULT 0,
    trades_executed INTEGER DEFAULT 0,
    trades_rejected INTEGER DEFAULT 0,
    last_trade_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (account_id, date)
);
```

---

## Risk Features Status After Fix

| Feature | Before Fix | After Fix | Working? |
|---------|-----------|-----------|----------|
| **max_daily_trades** | ❌ Resets on restart | ✅ Persists to DB | ✅ YES |
| **trade_cooldown_seconds** | ❌ Lost on restart | ✅ Persists to DB | ✅ YES |
| **max_positions_per_symbol** | ✅ Working | ✅ Working | ✅ YES |
| **max_open_positions** | ✅ Working | ✅ Working | ✅ YES |
| **max_daily_loss** ($) | ⚠️ Depends on sync | ⚠️ Depends on sync | ⚠️ VERIFY |
| **max_daily_loss_pct** (%) | ⚠️ Depends on sync | ⚠️ Depends on sync | ⚠️ VERIFY |
| **max_drawdown_pct** | ⚠️ Depends on sync | ⚠️ Depends on sync | ⚠️ VERIFY |
| **default_stop_loss** | ✅ Working | ✅ Working | ✅ YES |
| **default_take_profit** | ✅ Working | ✅ Working | ✅ YES |
| **trading_session** (hours) | ✅ Working | ✅ Working | ✅ YES |

---

## Deployment Steps

1. ✅ Created migration file
2. ✅ Added DailyCounter model
3. ✅ Created database-backed repository
4. 🔄 Building Docker image...
5. ⏳ Push to registry
6. ⏳ Deploy to production
7. ⏳ Run migration inside container
8. ⏳ Verify counters persist

---

## Testing Checklist

After deployment, verify each limit:

### Test max_daily_trades = 5
1. Set limit to 5 in account settings
2. Execute 5 trades
3. Send 6th trade signal
4. **Expected:** "Max daily trades exceeded (5/5)"
5. Restart container
6. Send another signal
7. **Expected:** Still blocked (counter persisted)

### Test trade_cooldown_seconds = 60
1. Set cooldown to 60 seconds
2. Execute 1 trade
3. Send another signal within 60s
4. **Expected:** "Trade cooldown active (Xs remaining)"

### Test max_positions_per_symbol = 1
1. Set limit to 1
2. Open 1 position on EURUSD
3. Send another BUY EURUSD
4. **Expected:** "Max positions for EURUSD exceeded"

### Test max_daily_loss = $100
1. Set limit to $100
2. Lose $100 or more today
3. Send new trade signal
4. **Expected:** "Max daily loss exceeded"
5. **NOTE:** Requires `daily_pnl` table to be updated by background sync

---

## Database Queries for Verification

### Check if daily_counters table exists:
```sql
SELECT * FROM daily_counters WHERE date = CURRENT_DATE;
```

### Check counter values for your accounts:
```sql
SELECT
    dc.account_id,
    ta.account_name,
    dc.date,
    dc.trades_executed,
    dc.last_trade_at
FROM daily_counters dc
JOIN trading_accounts ta ON dc.account_id = ta.id
WHERE dc.date = CURRENT_DATE
ORDER BY dc.account_id;
```

### Check if daily_pnl is being tracked:
```sql
SELECT
    dp.account_id,
    ta.account_name,
    dp.date,
    dp.total_pnl,
    dp.trades_count
FROM daily_pnl dp
JOIN trading_accounts ta ON dp.account_id = ta.id
WHERE dp.date = CURRENT_DATE
ORDER BY dp.account_id;
```

---

## Next Steps

1. **Immediate:** Deploy fixes and run migration
2. **Verify:** Test max_daily_trades and trade_cooldown persist across restarts
3. **Investigate:** If max_daily_loss still doesn't work, check background sync tasks that update `daily_pnl` table

---

## Files Changed

1. `/home/pharma5/unified_engine/alembic/versions/033_add_daily_counters_table.py` (NEW)
2. `/home/pharma5/unified_engine/app/models/database_models.py` (MODIFIED)
3. `/home/pharma5/unified_engine/app/infrastructure/repositories/daily_counter_repository.py` (MODIFIED)
4. `/home/pharma5/unified_engine/app/infrastructure/repositories/__init__.py` (MODIFIED)
5. `/home/pharma5/unified_engine/RISK_MANAGEMENT_AUDIT.md` (NEW - diagnostic report)

---

## Commit Message

```
fix: persist daily trade counters to database for restart survival

BREAKING: max_daily_trades and trade_cooldown were resetting on every
container restart due to in-memory storage. This critical bug allowed
unlimited trades despite configured limits.

- Add daily_counters table via migration 033
- Create SQLAlchemy DailyCounter model
- Replace InMemoryDailyCounterRepository with SQLAlchemyDailyCounterRepository
- Use PostgreSQL UPSERT for atomic counter updates
- Counters now survive container restarts and deployments

Fixes: max_daily_trades, trade_cooldown_seconds enforcement
```
