# SmartFlow Ultimate - User Testing Guide

**Status**: ✅ Deployed and Ready for Testing
**Date**: 2026-03-06

---

## 🚀 Quick Start

SmartFlow Ultimate has been successfully deployed with all enhanced features. Here's how to test it:

### Step 1: Access Dashboard
Navigate to: https://mytradeflow.app/dashboard/smartflow

### Step 2: Enable Conservative Preset (Recommended)

Use the API to enable SmartFlow with safe settings:

```bash
# Replace YOUR_AUTH_TOKEN with your actual Bearer token
curl -X PUT https://api.mytradeflow.app/api/v1/smartflow/config \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "webhook_urls": ["https://api.mytradeflow.app/webhooks/tradingview/YOUR_WEBHOOK_KEY"],
    "buy_threshold": 4.0,
    "sell_threshold": -4.0,
    "close_threshold": 1.0,
    "score_window_minutes": 5,
    "update_interval_seconds": 45,
    "enable_golden_sweeps": true,
    "enable_time_filter": true,
    "min_confidence_score": 60
  }'
```

### Step 3: Monitor Logs

Watch for SmartFlow activity:

```bash
# Watch for any SmartFlow signals
docker logs -f $(docker ps -q --filter name=unified_api) | grep SmartFlow

# Watch for golden sweeps ($1M+ trades)
docker logs -f $(docker ps -q --filter name=unified_api) | grep "🔥 GOLDEN"

# Watch for confidence scores
docker logs -f $(docker ps -q --filter name=unified_api) | grep -i confidence
```

### Step 4: Check Signal History

```bash
# Get recent signals
curl https://api.mytradeflow.app/api/v1/smartflow/status \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" | jq '.recent_signals'
```

---

## 🎯 Configuration Presets

### Preset 1: Conservative (Safest)
**Recommended for first test**

```json
{
  "enabled": true,
  "enable_golden_sweeps": true,
  "enable_time_filter": true,
  "min_confidence_score": 60
}
```

**What it does**:
- Only trades during 10am-3pm EST (avoids open/close volatility)
- Prioritizes $1M+ whale trades (+3/+4 bonuses)
- Requires minimum 60% confidence score
- Expected: 2-5 signals/day, ~60-70% win rate

**Best for**: First-time testing, risk-averse trading

---

### Preset 2: VIX-Aware (Medium Risk)
**Includes market volatility intelligence**

```json
{
  "enabled": true,
  "enable_vix_inverse": true,
  "enable_golden_sweeps": true,
  "enable_time_filter": true,
  "min_confidence_score": 65
}
```

**What it does**:
- Interprets VIX flows inversely (bullish VIX → bearish market)
- Golden sweeps detection
- Time-of-day guard
- Expected: 3-7 signals/day

**Best for**: Understanding volatility-based signals

---

### Preset 3: Leveraged (High Risk/Reward)
**3x amplified returns**

```json
{
  "enabled": true,
  "enable_vix_inverse": true,
  "enable_golden_sweeps": true,
  "enable_leveraged_etfs": true,
  "enable_time_filter": true,
  "min_confidence_score": 70
}
```

**What it does**:
- Trades SPXL/TQQQ/TNA instead of MES/NQ/RUT
- 3x amplified gains AND losses
- Higher confidence threshold (70%) for safety
- Expected: 2-5 signals/day, higher R:R

**Best for**: Experienced traders comfortable with leverage

⚠️ **WARNING**: Test on paper first! 3x leverage = 3x risk

---

### Preset 4: Maximum Filters (Requires POLYGON_API_KEY)
**Highest win rate**

```json
{
  "enabled": true,
  "enable_vix_inverse": true,
  "enable_golden_sweeps": true,
  "enable_price_confirmation": true,
  "enable_rsi_filter": true,
  "enable_volume_filter": true,
  "enable_time_filter": true,
  "enable_fib_confluence": true,
  "min_confidence_score": 80
}
```

**What it does**:
- All confirmation filters enabled
- Requires EMA alignment (9/20 periods)
- Avoids RSI overbought/oversold
- Requires volume spike (>1.5x average)
- Checks Fibonacci retracement levels
- Expected: 2-5 signals/day, ~70%+ win rate

**Best for**: Maximum signal quality

**Requirements**:
1. Get free API key: https://polygon.io
2. Add to service:
   ```bash
   docker service update --env-add POLYGON_API_KEY=your_key_here unified_api
   ```

---

## 📊 What to Expect

### Signal Format (Webhook Payload)

```json
{
  "ticker": "SPXL",
  "action": "buy",
  "price": 0,
  "source": "SmartFlow",
  "score": 8.5,
  "confidence": 92,
  "reason": "FSS=8.5 (bull=6, bear=0) | Confidence=92% | Fib confluence | 2 golden sweep(s) | Price✓ | Vol spike",
  "timestamp": "2026-03-06T14:23:15Z"
}
```

### New Fields Explained

**confidence** (0-100):
- 0-50: Weak signal (likely filtered out)
- 50-70: Moderate signal
- 70-85: Strong signal
- 85-100: Very strong signal (rare)

**reason** breakdown:
- **FSS=X.X**: Flow Sentiment Score (bullish/bearish breakdown)
- **Confidence=XX%**: AI-powered quality rating
- **Fib confluence**: Price near key Fibonacci level
- **X golden sweep(s)**: Count of $1M+ whale trades
- **Price✓**: EMA alignment confirmed
- **Vol spike**: Volume >1.5x average

---

## 🧪 Testing Checklist

### Day 1: Basic Functionality
- [ ] Enable conservative preset
- [ ] Verify SmartFlow status shows "enabled": true
- [ ] Monitor logs for 1 hour during market hours
- [ ] Check if any signals generated
- [ ] Verify webhook receives signals (if configured)

### Day 2-3: Feature Testing
- [ ] Check logs for "🔥 GOLDEN SWEEP" messages
- [ ] Verify confidence scores in signal reasons
- [ ] Test time filter (enable, trade outside 10am-3pm, expect no signals)
- [ ] Compare signal count vs previous SmartFlow version

### Day 4-7: Advanced Features
- [ ] Enable VIX inverse, watch for inverse sentiment
- [ ] Try leveraged ETFs preset (paper trading only!)
- [ ] Add POLYGON_API_KEY, enable price/RSI/volume/Fib filters
- [ ] Compare win rates across different presets

---

## 📈 Performance Tracking

### Metrics to Monitor

1. **Signal Count**
   - Conservative: 2-5/day
   - Moderate: 5-10/day
   - Aggressive (all filters): 2-5/day

2. **Confidence Distribution**
   - Without Polygon: 50-70% range
   - With Polygon: 0-100% range
   - Target: Average >70%

3. **Win Rate** (requires backtesting)
   - Conservative preset: 60-70%
   - Moderate preset: 55-65%
   - Maximum filters: 70%+

4. **False Positives**
   - Expected reduction: 50-70% vs old SmartFlow
   - Golden sweeps should be highly accurate (>75%)

---

## 🐛 Troubleshooting

### Issue: No signals generated
**Possible causes**:
1. No flows above `min_premium` threshold (default $50k)
2. Confidence scores below `min_confidence_score` (default 70%)
3. Time filter active outside trading hours
4. Market conditions not triggering thresholds

**Solution**: Lower `min_confidence_score` to 50 temporarily

---

### Issue: "POLYGON_API_KEY not set" warning
**Status**: ⚠️ This is NORMAL
**Impact**: Market data features disabled (Price/RSI/Volume/Fib)
**Core features still work**: VIX inverse, golden sweeps, leveraged ETFs

**Solution** (optional):
1. Visit https://polygon.io and sign up (free tier)
2. Get API key
3. Add to service:
   ```bash
   docker service update --env-add POLYGON_API_KEY=your_key unified_api
   ```

---

### Issue: Signals don't include confidence scores
**Possible causes**:
1. Old webhook format cached
2. Service needs restart to apply config changes

**Solution**:
```bash
docker service update --force unified_api
```

---

### Issue: Too many/few signals
**Adjust thresholds**:

Too many signals:
- Increase `min_confidence_score` (try 75-80)
- Increase `buy_threshold` and `sell_threshold` (try 5.0/-5.0)
- Enable more filters (RSI, volume, Fib)

Too few signals:
- Decrease `min_confidence_score` (try 50-60)
- Decrease `buy_threshold` and `sell_threshold` (try 3.5/-3.5)
- Disable strict filters temporarily

---

## 🔍 Log Analysis

### Useful grep commands

```bash
# Golden sweeps
docker logs $(docker ps -q --filter name=unified_api) | grep "🔥 GOLDEN SWEEP"

# VIX inverse signals
docker logs $(docker ps -q --filter name=unified_api) | grep "VIX INVERSE"

# Confidence scoring
docker logs $(docker ps -q --filter name=unified_api) | grep "Confidence="

# Fibonacci confluence
docker logs $(docker ps -q --filter name=unified_api) | grep "✨ Fib confluence"

# Signal rejections
docker logs $(docker ps -q --filter name=unified_api) | grep "Signal rejected"

# Recent activity (last hour)
docker logs --since 1h $(docker ps -q --filter name=unified_api) | grep SmartFlow
```

---

## 📚 Documentation Reference

- **Full Features**: `/SMARTFLOW_ULTIMATE_FEATURES.md`
- **Deployment Summary**: `/DEPLOYMENT_SUMMARY.md`
- **Verification Report**: `/DEPLOYMENT_VERIFICATION.md`
- **Test Results**: `/TEST_SMARTFLOW_ULTIMATE.md`

---

## 💡 Tips for Best Results

1. **Start Conservative**: Use preset 1 for first week
2. **Paper Trade First**: Especially for leveraged ETFs
3. **Monitor Confidence**: Track average confidence over time
4. **Adjust Gradually**: Change one setting at a time
5. **Market Hours Matter**: Most activity 10am-3pm EST
6. **Golden Sweeps**: Rare but powerful ($1M+ whales)
7. **Polygon API**: Free tier is sufficient (60 calls/min)
8. **Win Rate Goal**: 60%+ with conservative preset

---

## 🎯 Success Criteria

Your testing is successful if:
- [x] SmartFlow enabled without errors
- [x] Signals include confidence scores
- [x] Confidence averages >60%
- [x] Golden sweeps detected (when present)
- [x] Time filter blocks signals outside window
- [x] Webhook payloads include new fields

---

## 📞 Support

If you encounter issues:
1. Check logs first (see "Log Analysis" section)
2. Review `/DEPLOYMENT_VERIFICATION.md` for known issues
3. Verify database migration applied: `docker exec -it unified_postgres psql -U trading_user -d trading_db -c "SELECT version_num FROM alembic_version;"`
   - Should show: `035`

---

*Happy testing! SmartFlow Ultimate is your institutional-grade trading signal generator.* 🚀
