# SmartFlow Enhanced Features

**Date**: 2026-03-05
**Status**: Backend Complete - Frontend UI Update Pending

---

## What Was Enhanced

### 1. VIX/UVXY Inverse Logic ✅

**Purpose**: Use VIX and UVXY options flow as inverse market sentiment indicators

**Implementation**:
- Bullish VIX/UVXY call flow → Bearish market signal (sell)
- Bearish VIX/UVXY put flow → Bullish market signal (buy)
- VIX golden sweep >$100k → Adjusts sell threshold to -3 for faster triggering
- Toggle: `enable_vix_inverse` (default: False)

**Files Modified**:
- `app/services/smartflow_service.py`: Lines 184-274 (compute_sentiment_score)
- `app/models/smartflow_models.py`: Line 46 (enable_vix_inverse column)
- `app/routers/smartflow.py`: Lines 41, 60, 163, 182 (API integration)

**Test Case**:
```bash
# Simulate VIX golden sweep scenario
curl -X POST http://localhost:9001/test-flow \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "VIX",
    "flow_type": "sweep",
    "side": "bullish",
    "option_type": "call",
    "premium": 150000,
    "expiry": "weekly"
  }'
# Expected: Bearish SPY signal generated
```

---

### 2. IWM Ticker Support ✅

**Purpose**: Track Russell 2000 (small-cap) options flow

**Implementation**:
- Added IWM to tracked tickers list
- Maps IWM → RUT futures for signal delivery
- Leveraged ETF: TNA (buy), TZA (sell)
- Double weighting for IWM/RUT flows (whale priority)
- Skip monthly IWM golden sweeps (likely hedging)

**Files Modified**:
- `app/services/smartflow_service.py`: Line 113 (ticker_map), 120 (leveraged_etf_map), 450 (tracked_tickers)

---

### 3. Enhanced Scoring Weights ✅

**Purpose**: More accurate flow sentiment based on flow type and urgency

**Old Scoring**:
- Blocks: +0.5 bonus
- Sweeps: +0.5 bonus
- All treated similarly

**New Scoring**:
- **Blocks**: *0.5 multiplier (low conviction, institutional hedging)
- **Splits**: *1.5 multiplier (urgent, breaking into smaller orders)
- **Sweeps**: *2.0 multiplier (aggressive, high conviction)

**Premium Tiers** (unchanged):
- >$50k: Base score 1
- >$100k: Base score 2
- >$500k: Base score 3

**Special Multipliers**:
- NDX (QQQ) flows: **2x all weights** (whale priority)
- RUT (IWM) flows: **2x all weights** (whale priority)

**Files Modified**:
- `app/services/smartflow_service.py`: Lines 215-225 (flow_multiplier logic)

---

### 4. Golden Sweeps Detection ✅

**Purpose**: Identify and heavily weight institutional "blind-follow" trades

**Criteria**:
- Premium > $1M (OTM preferred)
- Flow type = sweep (aggressive)
- Expiry bonus:
  - Weekly/same-day/daily: **+4 bonus** (blind-follow level)
  - Other: **+3 bonus**

**Skip Rules**:
- Monthly IWM/RUT golden sweeps (likely hedging, not directional)

**Toggle**: `enable_golden_sweeps` (default: False)

**Files Modified**:
- `app/services/smartflow_service.py`: Lines 227-245 (golden sweep logic)
- `app/models/smartflow_models.py`: Line 47 (enable_golden_sweeps column)

**Dashboard Indicator**:
- Shows count of golden sweeps in signal reason
- Example: `FSS=8.5 (bull=3, bear=1) | 2 golden sweep(s)`

---

### 5. Leveraged ETF Output ✅

**Purpose**: Trade leveraged ETFs instead of futures for 3x amplified returns

**Mappings**:
- **SPY**: SPXL (buy), SPXU (sell)
- **QQQ**: TQQQ (buy), SQQQ (sell)
- **IWM**: TNA (buy), TZA (sell)

**Toggle**: `enable_leveraged_etfs` (default: False)

**Behavior**:
- When enabled, BUY signals use bullish leveraged ETF (SPXL, TQQQ, TNA)
- SELL signals use bearish leveraged ETF (SPXU, SQQQ, TZA)
- CLOSE signals use the same ticker as the open signal

**Files Modified**:
- `app/services/smartflow_service.py`: Lines 117-121 (leveraged_etf_map), 330-335 (buy logic), 355-360 (sell logic)
- `app/models/smartflow_models.py`: Line 48 (enable_leveraged_etfs column)

**Webhook Payload**:
```json
{
  "ticker": "SPXL",
  "action": "buy",
  "price": 0,
  "source": "SmartFlow",
  "score": 6.5,
  "reason": "FSS=6.5 (bull=4, bear=0) | Leveraged ETF",
  "timestamp": "2026-03-05T..."
}
```

---

### 6. Configuration Fields ✅

**New Database Columns** (smartflow_config table):
```sql
-- Enhanced toggles
enable_vix_inverse BOOLEAN DEFAULT FALSE NOT NULL
enable_golden_sweeps BOOLEAN DEFAULT FALSE NOT NULL
enable_leveraged_etfs BOOLEAN DEFAULT FALSE NOT NULL
vix_golden_threshold FLOAT DEFAULT 100000.0 NOT NULL
min_premium FLOAT DEFAULT 50000.0 NOT NULL
```

**Migration File**:
- `alembic/versions/035_add_smartflow_enhanced_toggles.py`

**API Updates**:
- `SmartFlowConfigRequest`: Added 5 new optional fields
- `SmartFlowConfigResponse`: Added 5 new fields
- PUT `/api/v1/smartflow/config`: Syncs toggles to service

---

### 7. Enhanced Signal Reasoning ✅

**Purpose**: Provide transparency on why signals were generated

**Old Format**:
```json
{
  "ticker": "MES",
  "action": "buy",
  "score": 5.2
}
```

**New Format**:
```json
{
  "ticker": "SPXL",
  "action": "buy",
  "score": 8.5,
  "reason": "FSS=8.5 (bull=6, bear=1) | 1 golden sweep(s) | Leveraged ETF",
  "lever_etf": "SPXL"
}
```

**Reason Components**:
- FSS value and bull/bear counts
- Golden sweep count (if detected)
- Leveraged ETF flag
- VIX inverse indicator (if applicable)

**Files Modified**:
- `app/services/smartflow_service.py`: Lines 62-72 (SmartFlowSignal dataclass), 316-322 (reason generation), 401-413 (webhook payload)

---

### 8. VIX Bias Indicator ✅

**Purpose**: Show overall market sentiment based on VIX flows

**Dashboard Field**: `vix_bias`

**Values**:
- `null`: VIX tracking disabled or no signal
- `"Bullish market (VIX bearish)"`: VIX score < -2
- `"Bearish market (VIX bullish)"`: VIX score > 2

**Files Modified**:
- `app/services/smartflow_service.py`: Lines 521-528 (get_status)

---

## Files Changed Summary

### Backend
1. **app/services/smartflow_service.py** - Core logic enhancements
2. **app/models/smartflow_models.py** - New config columns
3. **app/routers/smartflow.py** - API endpoint updates
4. **alembic/versions/035_add_smartflow_enhanced_toggles.py** - Database migration

### Frontend (Pending)
- **ui-next/src/app/dashboard/smartflow/page.tsx** - Add toggle switches for new features
- **ui-next/src/app/dashboard/smartflow/page.tsx** - Add VIX bias indicator
- **ui-next/src/app/dashboard/smartflow/page.tsx** - Add IWM sentiment card
- **ui-next/src/app/dashboard/smartflow/page.tsx** - Show signal reasons in table

---

## Deployment Steps

### 1. Run Database Migration

```bash
# Apply migration to add new columns
DATABASE_URL="postgresql://trading_user:trading_password@localhost:5432/trading_db" \
  python3 -m alembic upgrade head
```

### 2. Build & Deploy Backend

```bash
cd /home/pharma5/unified_engine

# Build new API image
docker build -t 192.168.1.254:5000/unified-engine/api:smartflow-enhanced -f Dockerfile .

# Push to registry
docker push 192.168.1.254:5000/unified-engine/api:smartflow-enhanced

# Update service
docker service update --image 192.168.1.254:5000/unified-engine/api:smartflow-enhanced unified_api
```

### 3. Update Frontend UI (Pending)

Frontend updates needed:
- Add 3 toggle switches: VIX Inverse, Golden Sweeps, Leveraged ETFs
- Add VIX bias badge/indicator
- Add IWM sentiment score card
- Show signal reasons in recent signals table
- Add advanced config section for thresholds

---

## Testing Checklist

### Backend Testing

1. **VIX Inverse**:
   ```bash
   # Enable VIX inverse
   curl -X PUT http://localhost:8765/api/v1/smartflow/config \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"enabled": true, "enable_vix_inverse": true, "webhook_urls": [...]}'

   # Wait for VIX flow data, check for inverse signals
   curl http://localhost:8765/api/v1/smartflow/status
   ```

2. **Golden Sweeps**:
   ```bash
   # Enable golden sweeps
   curl -X PUT http://localhost:8765/api/v1/smartflow/config \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"enabled": true, "enable_golden_sweeps": true, ...}'

   # Check logs for "🔥 GOLDEN SWEEP" messages
   docker logs $(docker ps -q --filter name=unified_api) | grep "GOLDEN SWEEP"
   ```

3. **Leveraged ETFs**:
   ```bash
   # Enable leveraged ETFs
   curl -X PUT http://localhost:8765/api/v1/smartflow/config \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"enabled": true, "enable_leveraged_etfs": true, ...}'

   # Wait for signal, check ticker is SPXL/TQQQ/TNA instead of MES/NQ/RUT
   curl http://localhost:8765/api/v1/smartflow/status | jq '.recent_signals'
   ```

4. **IWM Support**:
   ```bash
   # Check IWM appears in latest_scores
   curl http://localhost:8765/api/v1/smartflow/status | jq '.latest_scores.IWM'
   ```

---

## Next Steps: Price/Volume Confirmation Filters

The user requested additional filters to improve signal quality and reduce false positives:

### Planned Enhancements

1. **Price Confirmation** - EMA filters
   - Buy: Require SPY/QQQ above 9/20 EMA
   - Sell: Require SPY/QQQ below 9/20 EMA
   - ~20-30% junk reduction

2. **RSI Filter**
   - Skip buys if RSI(14) > 70 (overbought)
   - Skip sells if RSI(14) < 30 (oversold)
   - RSI divergence detection

3. **Volume Spike Check**
   - Only trade if volume > 1.5x 20-period average
   - Filter out "testing" institutional activity

4. **Time-of-Day Guard**
   - Avoid first/last 30 minutes (open/close chop)
   - Or limit to 10am-3pm EST

5. **Fade on Overload**
   - If 3+ flows same direction but price doesn't move in 5 min → close/reverse

6. **Confidence Score**
   - Calculate % confidence based on aligned factors
   - Only execute signals > 70% confidence

**Implementation Notes**:
- Requires Polygon.io API integration for EMA/RSI/volume data
- Add `confidence_score` field to signals
- Add confirmation filter toggles to config
- Should be toggleable (default: OFF for backward compatibility)

---

## Summary

✅ **Backend Complete**:
- VIX/UVXY inverse logic
- IWM ticker support
- Enhanced scoring weights
- Golden sweeps detection
- Leveraged ETF output
- Database schema updated
- API endpoints updated

⏳ **Frontend Pending**:
- Dashboard UI toggles
- VIX bias indicator
- IWM sentiment card
- Signal reason display

⏳ **Confirmation Filters Planned**:
- Price/EMA confirmation
- RSI filtering
- Volume spike check
- Time-of-day guard
- Confidence scoring

---

*SmartFlow is now significantly more sophisticated with institutional-grade flow analysis capabilities!*
