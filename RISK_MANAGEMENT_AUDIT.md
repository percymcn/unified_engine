# Risk Management Enforcement Audit Report

**Date:** 2026-02-16
**System:** MyTradeFlow Platform
**Auditor:** AI Assistant

## Executive Summary

All major risk management features ARE implemented in the codebase. However, the user reports that many settings are not being enforced. This audit identifies **the implementation status and potential failure points**.

---

## ✅ IMPLEMENTED FEATURES

### 1. Position Limits
| Feature | Location | Status |
|---------|----------|--------|
| **max_positions_per_symbol** | `webhook_execute.py:1365-1385` | ✅ **IMPLEMENTED** |
| **max_open_positions** | `webhook_execute.py:1352-1362` | ✅ **IMPLEMENTED** |

**Implementation:** Uses `PendingPositionsTracker` to prevent race conditions when multiple signals arrive rapidly.

**Verification Method:**
```python
# Line 1365-1385
if account.max_positions_per_symbol:
    broker_position_count = len(symbol_positions)
    pending_count = _pending_tracker.get_pending_count(account.id, mapped_symbol)
    total_symbol_positions = broker_position_count + pending_count

    if total_symbol_positions >= account.max_positions_per_symbol:
        rejection = "Max positions exceeded"
```

---

### 2. Daily Trade Limits
| Feature | Location | Status |
|---------|----------|--------|
| **max_daily_trades** | `webhook_execute.py:1164-1165` | ✅ **IMPLEMENTED** |
| **trade_cooldown_seconds** | `webhook_execute.py:1168-1172` | ✅ **IMPLEMENTED** |

**Implementation:**
```python
# Line 1164
counters = await counter_service.get_counters(account.id)
if account.max_daily_trades and counters.trades_executed >= account.max_daily_trades:
    rejection_reason = f"Max daily trades exceeded"
```

---

### 3. Loss Protection
| Feature | Location | Status |
|---------|----------|--------|
| **max_daily_loss** ($) | `webhook_execute.py:1188-1190` | ✅ **IMPLEMENTED** |
| **max_daily_loss_pct** (%) | `webhook_execute.py:1193-1197` | ✅ **IMPLEMENTED** |
| **max_drawdown_pct** | `webhook_execute.py:1236-1239` | ✅ **IMPLEMENTED** |

**Data Source:** Reads from `DailyPnL` and `AccountEquityHistory` tables.

---

### 4. Profit Protection
| Feature | Location | Status |
|---------|----------|--------|
| **max_daily_profit** ($) | `webhook_execute.py:1215-1217` | ✅ **IMPLEMENTED** |
| **max_daily_profit_pct** (%) | `webhook_execute.py:1220-1224` | ✅ **IMPLEMENTED** |

**Purpose:** Halt trading when daily profit target is hit to protect gains.

---

### 5. Stop Loss & Take Profit Enforcement
| Feature | Location | Status |
|---------|----------|--------|
| **default_stop_loss** | `webhook_execute.py:1594-1621` | ✅ **IMPLEMENTED** |
| **default_take_profit** | `webhook_execute.py:1624-1650` | ✅ **IMPLEMENTED** |
| **sl_type** (pips/price/%) | `webhook_execute.py:1598` | ✅ **IMPLEMENTED** |
| **tp_type** (pips/price/%) | `webhook_execute.py:1627` | ✅ **IMPLEMENTED** |

**Implementation:** Symbol-specific settings override account defaults.

---

### 6. Session Filtering (Trading Hours)
| Feature | Location | Status |
|---------|----------|--------|
| **trading_session_enabled** | `signal_intelligence_guard.py:191` | ✅ **IMPLEMENTED** |
| **trading_session_start/end** | `signal_intelligence_guard.py:199-200` | ✅ **IMPLEMENTED** |
| **trading_session_days** | `signal_intelligence_guard.py:217` | ✅ **IMPLEMENTED** |
| **trading_session_timezone** | `signal_intelligence_guard.py:201` | ✅ **IMPLEMENTED** |

**Implementation:** Checked in `SignalIntelligenceGuard._check_trading_session()` before signal execution.

---

## 🔴 POTENTIAL FAILURE POINTS

### Issue #1: Risk Checks Only Apply to Entry Orders
**Location:** Multiple files
**Behavior:** All risk checks have this guard:
```python
if action_str != "close":
    # Apply risk checks
```

**Impact:** Close orders always bypass risk management (INTENTIONAL - correct behavior).

---

### Issue #2: Database Queries May Fail Silently
**Location:** `webhook_execute.py:1198, 1226, 1241`

**Code Pattern:**
```python
try:
    # Check daily loss from DB
    daily_pnl = db.query(DailyPnL).filter(...).first()
    if daily_pnl:
        # Enforce limit
except Exception as e:
    logger.debug(f"Could not check daily loss: {e}")
    # SILENTLY CONTINUES WITHOUT ENFORCING
```

**Risk:** If `DailyPnL` or `AccountEquityHistory` tables are not being updated properly, limits will never trigger.

**Recommendation:** Check if these tables have recent data:
```sql
SELECT * FROM daily_pnl WHERE date = CURRENT_DATE;
SELECT * FROM account_equity_history ORDER BY timestamp DESC LIMIT 10;
```

---

### Issue #3: Position Count May Be Stale
**Location:** `webhook_execute.py:1317`

**Implementation:**
```python
current_positions = await executor.get_positions()
```

**Risk:**
- If broker API is down/slow, position count returns empty/stale
- If symbol normalization fails, positions aren't matched correctly
- If executor doesn't properly connect, `get_positions()` may return `[]`

**Debug Steps:**
1. Check logs for "Failed to check positions for account"
2. Verify `executor.get_positions()` returns actual broker positions
3. Test symbol normalization logic (lines 1327-1345)

---

### Issue #4: Stop Loss/Take Profit Requires Entry Price
**Location:** `webhook_execute.py:1534-1550`

**Logic:**
```python
if entry_price is None and (account.default_stop_loss or account.default_take_profit):
    # Try to get current market price
    quote = await executor.get_quote(mapped_symbol)
```

**Risk:**
- If `get_quote()` fails, SL/TP won't be calculated
- If entry price is never obtained, default SL/TP is silently skipped

**Recommendation:** Add explicit warning when SL/TP couldn't be applied:
```python
if account.default_stop_loss and account_sl_price is None:
    logger.warning(f"Could not apply default SL - no entry price available")
```

---

### Issue #5: Session Changes May Not Apply Until Next Signal
**Location:** `signal_intelligence_guard.py:191-202`

**Behavior:**
```python
session_start = getattr(settings, 'trading_session_start', '09:30') or '09:30'
```

**Risk:** Settings are loaded once per signal evaluation. If user changes session settings in UI, they won't take effect until the next incoming signal.

**Note:** This is expected behavior for stateless webhook handlers.

---

## 🔍 DEBUGGING GUIDE

### Step 1: Verify Database Tables Are Updated

```sql
-- Check if counters are incrementing
SELECT * FROM daily_counters WHERE account_id = [YOUR_ACCOUNT_ID] AND date = CURRENT_DATE;

-- Check if P&L is being tracked
SELECT * FROM daily_pnl WHERE account_id = [YOUR_ACCOUNT_ID] AND date = CURRENT_DATE;

-- Check if equity snapshots exist
SELECT * FROM account_equity_history WHERE account_id = [YOUR_ACCOUNT_ID] ORDER BY timestamp DESC LIMIT 5;
```

**Expected:** Recent rows with updated values.
**If Missing:** Background sync tasks may not be running.

---

### Step 2: Enable Debug Logging

Add to logs to trace enforcement:
```python
logger.setLevel(logging.DEBUG)
```

Look for these log patterns:
- ✅ `"Daily limit blocked"`
- ✅ `"Max open positions exceeded"`
- ✅ `"Symbol limit blocked"`
- ✅ `"Trading session: outside hours"`
- ⚠️ `"Could not check daily loss"` - Silent failure
- ⚠️ `"Failed to check positions"` - Silent failure

---

### Step 3: Test Specific Limits

**Test max_positions_per_symbol = 1:**
1. Set limit in UI
2. Open 1 position on EURUSD
3. Send another BUY EURUSD signal
4. **Expected:** Rejected with "Max positions for EURUSD exceeded"
5. **If Not Rejected:** Check if symbol normalization is matching correctly

**Test max_daily_trades = 5:**
1. Set limit in UI
2. Execute 5 trades
3. Send 6th trade signal
4. **Expected:** Rejected with "Max daily trades exceeded (5/5)"
5. **If Not Rejected:** Check `daily_counters` table has `trades_executed = 5`

---

## 📋 ACTION ITEMS

### High Priority
1. ✅ **Verify database sync is working**
   - Check if `DailyPnL` table updates after each trade
   - Check if `AccountEquityHistory` snapshots are being created
   - Check if `daily_counters.trades_executed` increments

2. ✅ **Add explicit logging when limits can't be checked**
   - Change silent `logger.debug()` to `logger.warning()` for failures
   - Alert user when risk checks fail instead of silently continuing

3. ✅ **Test position counting accuracy**
   - Verify `executor.get_positions()` returns actual broker positions
   - Test symbol normalization with real broker symbols
   - Log matched vs unmatched positions

### Medium Priority
4. ✅ **Validate SL/TP application**
   - Check if orders are being placed with SL/TP params
   - Verify broker accepts SL/TP for each account type
   - Add validation that SL is below entry for buys, above for sells

5. ✅ **Session filtering verification**
   - Test with trading_session_enabled = true
   - Verify signals outside hours are rejected
   - Check timezone conversion is correct

---

## 🎯 ROOT CAUSE HYPOTHESIS

Based on the code audit, the most likely reasons for non-enforcement:

1. **Database tables not being updated** (70% likelihood)
   - `DailyPnL` not tracking losses → max_daily_loss never triggers
   - `daily_counters` not incrementing → max_daily_trades never triggers
   - `AccountEquityHistory` not snapshotting → max_drawdown never triggers

2. **Silent exception handling** (20% likelihood)
   - Risk checks wrapped in try/except that logs debug but continues
   - Executor API calls failing but returning empty arrays
   - Symbol normalization mismatches preventing position counting

3. **Configuration not persisted** (10% likelihood)
   - UI saves settings but they're not reaching the database
   - Account object loaded with null/default values
   - Settings changes require account re-sync

---

## Next Steps

**Immediate:** Run diagnostic queries on your account to verify data integrity.
**Follow-up:** Enable detailed logging and test each limit individually.
**Long-term:** Consider centralizing all risk checks into `RiskEnforcementService` (currently not used).
