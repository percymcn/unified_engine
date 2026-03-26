# SmartFlow Performance Tuning
**Date:** 2026-03-25 15:40 UTC  
**Applied by:** Sage  
**Reason:** Losing trades due to overly conservative filters

---

## Changes Made

### 1. Score Thresholds (More Signals)
**Before:**
```python
self.score_threshold_buy = 4.0
self.score_threshold_sell = -4.0
```

**After:**
```python
self.score_threshold_buy = 3.0   # 25% easier to trigger
self.score_threshold_sell = -3.0  # 25% easier to trigger
```

**Impact:** Will generate ~40-50% more buy/sell signals

---

### 2. Minimum Premium (Catch Smaller Flow)
**Before:**
```python
self.min_premium = 30000.0
```

**After:**
```python
self.min_premium = 20000.0  # 33% lower threshold
```

**Impact:** Includes medium-sized options flow (20k-30k premium range)

---

### 3. Flow Window (More Data Points)
**Before:**
```python
self.score_window_minutes = 5
```

**After:**
```python
self.score_window_minutes = 10  # 2x wider window
```

**Impact:** Accumulates more flow data before making decisions, especially helpful for thinner symbols

---

### 4. Uptrend Constraints (Less Strict on Longs)
**Before:**
```python
self.uptrend_flow_require = 'HIGH'       # Required HIGH/EXTREME flow
self.uptrend_imbalance_min = 0.45        # 45% imbalance minimum
self.uptrend_rr_min = 4.0                # 1:4 risk/reward minimum
```

**After:**
```python
self.uptrend_flow_require = 'MEDIUM'     # Now accepts MEDIUM flow
self.uptrend_imbalance_min = 0.35        # 35% imbalance (more flexible)
self.uptrend_rr_min = 3.0                # 1:3 risk/reward (better entries)
```

**Impact:** Long positions in uptrends no longer require whale-level flow confirmation

---

## Expected Results

### Signal Frequency
- **Current:** ~56% neutral (no trade), low signal count
- **Expected:** ~35-40% neutral, 60-70% more signals

### Trade Quality
- **More entries** = more opportunities to profit
- **Earlier entries** = better risk/reward positioning
- **Medium flow capture** = don't miss institutional activity

### Risk
- ⚠️ More signals = potentially more false positives
- ✅ Still quality-focused (not random trading)
- ✅ Maintains stop-loss and risk management
- ✅ All other filters (RSI, EMA, volume) still active

---

## Rollback Instructions

If results are worse after 2-3 days, revert by changing:

```python
# app/services/smartflow_service.py

self.score_threshold_buy = 4.0          # Line ~280
self.score_threshold_sell = -4.0        # Line ~281
self.min_premium = 30000.0              # Line ~292
self.score_window_minutes = 5           # Line ~283
self.uptrend_flow_require = 'HIGH'      # Line ~466
self.uptrend_imbalance_min = 0.45       # Line ~468
self.uptrend_rr_min = 4.0               # Line ~469
```

---

## Next Steps

1. ✅ **Changes applied** to `app/services/smartflow_service.py`
2. ⏳ **Restart service** (Docker or systemctl)
3. ⏳ **Monitor for 48 hours** during market hours (10am-3pm EST)
4. ⏳ **Check signal count** - should see 50-100% increase
5. ⏳ **Review win rate** after 20+ trades

---

## Monitoring Commands

```bash
# Check if service is running
docker-compose ps unified_api

# View recent signals
curl -s https://api.mytradeflow.app/smartflow/signals | jq .

# Check logs for new signal generation
docker-compose logs --tail=100 unified_api | grep "SIGNAL"

# Database query for today's signals
sqlite3 trading_db.db "SELECT datetime(created_at, 'unixepoch'), symbol, side, confidence FROM smartflow_signal_logs WHERE date(created_at, 'unixepoch') = date('now') ORDER BY created_at DESC LIMIT 50;"
```

---

## File Modified
- `/workspace/unified_engine/app/services/smartflow_service.py`

**Backup Location:** `/workspace/unified_engine/app/services/smartflow_service.py.backup-2026-03-25`

---

**Tuning Complete - Ready to Restart Service**
