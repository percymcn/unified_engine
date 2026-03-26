# SmartFlow 2026 - Levels, Trailing, VWAP & Enhanced Features Upgrade

## Overview

This upgrade adds key levels confluence (PDH/PDL/Fibonacci), **VWAP confluence**, trailing stops, regime-asymmetric logic, news sentiment, and enhanced microstructure integration to SmartFlow.

---

## New Configuration Flags

### SmartFlowService (smartflow_service.py)

```python
# ========================================
# KEY LEVELS & CONFLUENCE
# ========================================
enable_levels_confluence = True           # Use key levels if available
levels_confluence_min_deterministic = 65.0  # Min confluence for deterministic
levels_confluence_min_quick = 55.0        # Min confluence for quick mode
use_fib_targets = True                    # Use Fib extensions as targets
fib_target_levels = ['1.272', '1.618']    # Which Fib extensions to use

# ========================================
# REGIME-ASYMMETRIC LOGIC
# ========================================
enable_regime_asymmetric = True

# Trending Up requirements (TIGHTENED)
uptrend_flow_require = 'HIGH'             # Require HIGH/EXTREME flow for longs
uptrend_fib_extensions = True             # Use Fib extensions as targets
uptrend_imbalance_min = 0.45              # Min imbalance for longs in uptrend
uptrend_rr_min = 4.0                      # 1:4 R:R in uptrend
uptrend_target_pct = 0.8                  # 0.8% target (from 0.2% risk = 1:4)
uptrend_ensemble_min_probability = 0.66   # Override base 0.62 in trending_up (NEW)

# Trending Down requirements
downtrend_flow_require = 'MEDIUM'         # MEDIUM+ flow for shorts in downtrend
downtrend_pdh_pdl_targets = True          # Use PDH/PDL as targets
downtrend_rr_min = 3.0                    # 1:3 R:R in downtrend

# ========================================
# TRAILING STOP CONFIGURATION (ENHANCED)
# ========================================
enable_trailing_stop = True
trailing_breakeven_trigger = 2.0          # After 2x risk → trail to VWAP/EMA21
trailing_partial_exit_trigger = 3.0       # At 3x risk → partial exit 50%
trailing_partial_exit_pct = 50.0          # Exit 50% at partial
trailing_atr_multiplier = 1.0             # Trail with 1x ATR (fallback)
# VWAP/EMA21 trailing (NEW)
trailing_to_vwap = True                   # Trail to VWAP after 2x (NEW)
trailing_to_ema21 = True                  # Also consider EMA21 (NEW)
trailing_vwap_buffer_pct = 0.1            # 0.1% buffer below VWAP for longs (NEW)
trailing_partial_at_3x = True             # Close 50% at 3x risk (NEW)
trailing_remainder_to_vwap = True         # Trail remainder to VWAP - buffer (NEW)

# ========================================
# NEWS SENTIMENT (ENHANCED)
# ========================================
enable_news_sentiment = True
news_sentiment_boost_min = 0.08           # Min +8% probability boost (NEW)
news_sentiment_boost_max = 0.12           # Max +12% probability boost (UPDATED)
news_sentiment_threshold = 0.5            # Min sentiment for boost (NEW)
news_sentiment_flow_require = 'MEDIUM'    # Min flow for news boost (NEW)
news_sentiment_cache_ttl_minutes = 60     # Cache hourly (UPDATED)

# ========================================
# VWAP CONFLUENCE (NEW)
# ========================================
enable_vwap_confluence = True             # Use VWAP for confluence
vwap_distance_threshold_pct = 0.5         # Max distance for confluence (0.5%)
vwap_confluence_boost = 0.12              # +12% probability boost
vwap_tight_distance_pct = 0.3             # Tight distance for extra boost
vwap_tight_boost = 0.15                   # +15% boost when tight
vwap_mean_reversion_boost = 0.18          # +18% for mean-reversion near VWAP
vwap_min_bias_for_long = 0.4              # Min bias for long in trending up
vwap_trailing_enabled = True              # Use VWAP for trailing reference
```

### EnsembleConfigV2 (ensemble_scorer_v2.py)

```python
# Base thresholds
min_probability = 0.62                    # Base: > 62% confident (UPDATED from 0.65)
min_expected_value = 0.0                  # Must have positive EV

# Regime-specific probability overrides (NEW)
uptrend_min_probability = 0.66            # Stricter for trending_up: > 66% (NEW)
uptrend_flow_require = 'HIGH'             # Require HIGH/EXTREME flow for uptrend (NEW)
uptrend_imbalance_min = 0.45              # Min imbalance for uptrend longs (NEW)

# Levels confluence boost
levels_confluence_boost = 0.22            # +22% probability boost
levels_confluence_min = 70.0              # Minimum confluence for boost
levels_flow_min = 'HIGH'                  # Minimum flow conviction for boost
levels_imbalance_min = 0.4                # Minimum imbalance for boost

# News sentiment boost (ENHANCED)
news_sentiment_min_boost = 0.08           # Min +8% from news (NEW)
news_sentiment_max_boost = 0.12           # Max +12% from news (UPDATED)
news_sentiment_threshold = 0.5            # Min sentiment for boost (NEW)
news_sentiment_flow_require = 'MEDIUM'    # Min flow for news boost (NEW)

# VWAP confluence boost
vwap_confluence_boost = 0.12              # +12% probability boost
vwap_distance_threshold = 0.5             # Max distance for confluence (%)
vwap_tight_distance = 0.3                 # Tight distance for extra boost
vwap_tight_boost = 0.15                   # +15% boost when tight
vwap_mean_reversion_boost = 0.18          # +18% for mean-reversion near VWAP
```

### IndicatorConfig (indicators.py)

```python
# Regime-specific PCT targets
uptrend_pct_target = 0.8                  # 0.8% target in uptrend (1:4 R:R)
uptrend_pct_target_max = 1.0              # Max 1.0% target (1:5 R:R)
downtrend_pct_target = 0.6                # Standard 0.6% in downtrend (1:3 R:R)

# Integration weights
use_levels_confluence = True
levels_confluence_weight = 0.15
use_microstructure = True
microstructure_weight = 0.10
use_news_sentiment = True
news_sentiment_weight = 0.05
use_crypto_funding = True
funding_weight = 0.08
```

### ForwardTestConfig (forward_test.py)

```python
# Levels confluence
use_levels_confluence = True
levels_confluence_min = 65.0

# Trailing stops
use_trailing_stop = True
trailing_breakeven_trigger = 2.0
trailing_partial_trigger = 3.0
trailing_partial_pct = 50.0

# News sentiment
use_news_sentiment = True
news_boost_max = 0.05

# Regime-asymmetric logic
use_regime_asymmetric = True
uptrend_target_pct = 0.8
uptrend_flow_require = 'HIGH'

# Feature variant for A/B testing
feature_variant = 'levels+trailing'  # 'current', 'levels+trailing', 'high_flow_uptrend'
```

---

## Testing Checklist

### Pre-Deployment Validation

- [ ] **Unit Tests**
  - [ ] `test_levels_service.py` - PDH/PDL calculation, Fib levels, confluence scoring
  - [ ] `test_trailing_stop.py` - Breakeven, partial exit, trailing logic
  - [ ] `test_regime_asymmetric.py` - Uptrend/downtrend filter logic
  - [ ] `test_vwap_service.py` - VWAP calculation, bias scoring, confluence (NEW)

- [ ] **Integration Tests**
  - [ ] SmartFlow service loads levels each cycle
  - [ ] SmartFlow service calculates VWAP confluence (NEW)
  - [ ] Ensemble scorer applies levels confluence boost correctly
  - [ ] Ensemble scorer applies VWAP confluence boost correctly (NEW)
  - [ ] Regime detector calculates enhanced bias with VWAP (NEW)

- [ ] **API Tests**
  - [ ] Polygon daily bars fetch works
  - [ ] News headlines fetch works
  - [ ] ProjectX realtime data integration (if enabled)

### Backtest Variants (4 required)

#### Variant 1: Current (Baseline)
```bash
python scripts/backtest_active_system.py \
  --config current \
  --pct_stop 0.2 \
  --pct_target 0.6 \
  --levels_confluence_enabled false \
  --trailing_enabled false \
  --output results_current.json
```

Expected metrics (90-day MES):
- Trades: ~127
- Win Rate: ~44.9%
- Profit Factor: ~1.41
- Sharpe: ~2.02
- Max DD: ~4.68%

#### Variant 2: Levels + Trailing + Sentiment
```bash
python scripts/backtest_active_system.py \
  --config levels_trailing \
  --pct_stop 0.2 \
  --pct_target 0.6 \
  --levels_confluence_enabled true \
  --levels_confluence_min 65 \
  --trailing_enabled true \
  --news_sentiment_enabled true \
  --output results_levels_trailing.json
```

Expected improvement:
- Win Rate: +3-5% (from levels filtering)
- Profit Factor: +0.15-0.25 (from trailing)
- Sharpe: +0.3-0.5

#### Variant 3: High-Flow Uptrend
```bash
python scripts/backtest_active_system.py \
  --config high_flow_uptrend \
  --pct_stop 0.2 \
  --uptrend_target_pct 0.8 \
  --uptrend_flow_require HIGH \
  --uptrend_imbalance_min 0.45 \
  --regime_asymmetric_enabled true \
  --output results_high_flow_uptrend.json
```

Expected improvement:
- R:R: 1:4+ in uptrends
- Fewer trades, higher quality
- Better performance in trending markets

#### Variant 4: VWAP Confluence (NEW)
```bash
python scripts/backtest_active_system.py \
  --config vwap_confluence \
  --pct_stop 0.2 \
  --pct_target 0.6 \
  --vwap_confluence_enabled true \
  --vwap_distance_threshold 0.5 \
  --vwap_gating_enabled true \
  --vwap_min_bias_for_long 0.4 \
  --output results_vwap_confluence.json
```

Expected improvement:
- Win Rate: +2-4% (VWAP filtering)
- Better entries near VWAP (mean-reversion)
- +12-18% prob boost for tight VWAP setups
- Improved R:R in trending regimes

### Forward Test Validation

- [ ] Run forward test with `feature_variant='levels+trailing'` for 1 week
- [ ] Monitor levels confluence filter effectiveness
- [ ] Monitor trailing stop activations
- [ ] Monitor VWAP confluence filter effectiveness (NEW)
- [ ] Track VWAP bias alignment with trade direction (NEW)
- [ ] Compare P&L against baseline

---

## Files Modified

| File | Changes |
|------|---------|
| `app/services/levels_service.py` | **NEW** - PDH/PDL, Fib levels, confluence scoring, news sentiment |
| `app/services/vwap_service.py` | **NEW** - VWAP calculation, bias scoring, confluence, session reset |
| `app/services/ensemble_scorer_v2.py` | Added levels_confluence, vwap_distance_pct, vwap_bias features, probability boosts |
| `app/services/smartflow_service.py` | Levels filter, VWAP filter, regime-asymmetric logic, trailing stops, news sentiment |
| `app/services/indicators.py` | Uptrend R:R fix (1:4-1:5), new feature fields |
| `app/services/regime_detector_v2.py` | Enhanced bias calculation with microstructure/funding/levels/sentiment/VWAP |
| `app/services/forward_test.py` | New tracking fields, feature variants |

---

## Expected Performance Lift

| Metric | Current | With Levels+Trailing+VWAP | Expected Lift |
|--------|---------|--------------------------|---------------|
| Win Rate | 44.9% | 50-53% | +5-8% |
| Profit Factor | 1.41 | 1.60-1.80 | +0.19-0.39 |
| Sharpe Ratio | 2.02 | 2.40-2.70 | +0.38-0.68 |
| Max Drawdown | 4.68% | 3.8-4.3% | -0.4-0.9% |

### VWAP-Specific Improvements

| Feature | Impact |
|---------|--------|
| VWAP Distance Filter | Filters low-quality entries far from VWAP |
| VWAP Bias Alignment | +12% prob boost for aligned trades |
| Tight VWAP Setups | +15-18% boost for < 0.3% distance |
| Mean-Reversion Near VWAP | Better fade entries in choppy regimes |
| VWAP-Based Trailing | Dynamic trailing reference point |

### Uptrend Tightening Improvements (NEW)

| Feature | Impact |
|---------|--------|
| 66% Ensemble Threshold | Stricter probability for uptrend longs |
| HIGH Flow Required | No uptrend longs without HIGH/EXTREME flow |
| Imbalance > 0.45 | Requires order flow imbalance confirmation |
| Expected Uptrend WR | +3-6% win rate in trending_up regime |
| Reduced False Signals | Fewer low-quality uptrend entries |

### Trailing + Partial Exit Improvements (NEW)

| Feature | Impact |
|---------|--------|
| VWAP/EMA21 Trailing | Trail to whichever is tighter after 2x |
| 50% Partial at 3x | Lock in profits, let remainder run |
| VWAP - 0.1% Buffer | Tighter trailing for remainder |
| Expected Trailing WR | +5-10% captured profit from trailing |
| Reduced Giveback | Less profit given back on reversals |

### News Sentiment Improvements (NEW)

| Feature | Impact |
|---------|--------|
| 0.08-0.12 Prob Boost | +8-12% when sentiment > 0.5 + MEDIUM flow |
| Hourly Cache | Fresh sentiment without API overload |
| Keyword Scoring | Fast, Pi5-safe sentiment detection |
| Flow Confirmation | News boost only with flow support |

---

## Backtest Checklist: Current vs New

### Expected Improvements

| Metric | Current | With All Enhancements | Expected Lift |
|--------|---------|----------------------|---------------|
| Win Rate | 44.9% | 48-51% | +3-6% |
| Profit Factor | 1.41 | 1.56-1.71 | +0.15-0.30 |
| Sharpe Ratio | 2.02 | 2.30-2.60 | +0.28-0.58 |
| Uptrend P&L | -$200 | +$400-800 | Positive |
| Trailing Captures | 0% | 40-60% | Better exits |

### Backtest Commands

```bash
# Variant 1: Current Baseline
python scripts/backtest_active_system.py \
  --config current \
  --uptrend_ensemble_override false \
  --trailing_vwap_ema false \
  --news_enhanced false \
  --output results_current.json

# Variant 2: Uptrend Tightening Only
python scripts/backtest_active_system.py \
  --config uptrend_tight \
  --uptrend_min_prob 0.66 \
  --uptrend_flow_require HIGH \
  --uptrend_imbalance_min 0.45 \
  --output results_uptrend_tight.json

# Variant 3: VWAP/EMA21 Trailing + Partial
python scripts/backtest_active_system.py \
  --config trailing_vwap \
  --trailing_to_vwap true \
  --trailing_to_ema21 true \
  --trailing_partial_at_3x true \
  --trailing_vwap_buffer 0.1 \
  --output results_trailing_vwap.json

# Variant 4: News Sentiment Enhanced
python scripts/backtest_active_system.py \
  --config news_enhanced \
  --news_boost_min 0.08 \
  --news_boost_max 0.12 \
  --news_sentiment_threshold 0.5 \
  --news_flow_require MEDIUM \
  --output results_news_enhanced.json

# Variant 5: All Enhancements Combined
python scripts/backtest_active_system.py \
  --config all_enhanced \
  --uptrend_min_prob 0.66 \
  --trailing_to_vwap true \
  --trailing_partial_at_3x true \
  --news_boost_max 0.12 \
  --output results_all_enhanced.json
```

---

## Rollback Plan

If issues arise, disable new features:

```python
# SmartFlowService
enable_levels_confluence = False
enable_regime_asymmetric = False
enable_trailing_stop = False
enable_news_sentiment = False
enable_vwap_confluence = False  # NEW

# IndicatorConfig
use_levels_confluence = False
uptrend_pct_target = 0.6  # Back to 1:3

# ForwardTestConfig
feature_variant = 'current'
```

---

## Deployment Commands

```bash
# 1. Build Docker image
docker build -t unified-engine:levels-upgrade .

# 2. Push to registry
docker push 192.168.1.254:5000/unified-engine/api:levels-upgrade

# 3. Deploy to swarm
docker stack deploy -c docker-stack.yml unified_engine

# 4. Verify
docker service logs unified_engine_api -f
```

---

## Monitoring Alerts

Set up alerts for:
- Levels confluence filter rejection rate > 50%
- Trailing stop activations < 10% (may indicate regime issue)
- News sentiment API failures
- Ensemble probability boost frequency
- VWAP confluence filter rejection rate > 40% (NEW)
- VWAP bias misalignment > 30% of trades (NEW)
- VWAP calculation failures (session reset issues)

---

*Generated: 2026-03-18*
*Version: levels-trailing-vwap-v2*
