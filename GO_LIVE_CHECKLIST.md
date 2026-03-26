# SmartFlow 2026 - Go-Live Checklist

## Final Backtest Results (90-Day, Tightened DD)

| Ticker | Trades | WR% | P&L | PF | Sharpe | DD% | Uptrend$ |
|--------|--------|-----|-----|-----|--------|-----|----------|
| MES | 74 | 48.6% | $1,494 | 1.44 | 2.62 | **4.12%** | +$5 |
| MNQ | 70 | 62.9% | $1,834 | 2.37 | 6.42 | **2.17%** | +$2 |
| NQ | 70 | 62.9% | $20,149 | 2.59 | 7.08 | 12.63%* | +$88 |
| **Total** | **214** | **58.1%** | **$23,478** | **2.13** | **5.37** | - | **+$96** |

*NQ DD higher due to larger contract size - consider MNQ for lower DD profile

### Target Validation

| Target | Result | Status |
|--------|--------|--------|
| Uptrend P&L Positive | +$96 | ✅ PASS |
| PF >= 1.8 | 2.13 | ✅ PASS |
| Sharpe >= 2.0 | 5.37 | ✅ PASS |
| DD < 8% | 12.63% (NQ) | ⚠️ Use MES/MNQ |

---

## Config Changes Applied

### Risk Manager (risk_manager.py)

```python
max_position_pct: 3.5%      # Was 5%
max_concurrent_positions: 3  # NEW
max_daily_drawdown_pct: 2.5% # Was 3%
max_portfolio_risk_pct: 12%  # Was 15%

# Regime-based sizing
regime_size_mults = {
    'trending_up': 1.0,
    'trending_down': 1.0,
    'vol_expansion': 0.65,   # 65% size
    'vol_contraction': 0.9,
    'chaotic': 0.4,          # 40% size
    'mean_reverting': 0.8,
}
```

### Uptrend Protection (ensemble_scorer_v2.py)

```python
uptrend_min_probability: 0.66  # vs 0.62 base
uptrend_flow_require: 'HIGH'   # HIGH/EXTREME only
uptrend_imbalance_min: 0.45    # Order flow imbalance
```

### Trailing Stop (smartflow_service.py)

```python
trailing_to_vwap: True
trailing_to_ema21: True
trailing_vwap_buffer_pct: 0.1  # 0.1% buffer
trailing_partial_at_3x: True   # 50% exit at 3x risk
```

---

## Paper Trading Protocol (2-4 Weeks)

### Phase 1: Paper Trading (Week 1-2)

1. **Run 1-2 MES equivalent** for 100-200 trades
2. **Track metrics:**
   - Win Rate target: ≥52%
   - Profit Factor target: ≥1.6
   - Sharpe target: ≥2.0
   - Max DD target: <10%

3. **Monitor divergence:**
   - Compare live fills vs backtest assumptions
   - Track slippage (expect +0.5-1 tick vs backtest)
   - Note any systematic fill quality issues

### Phase 2: Small Live (Week 3-4)

**Go live when:**
- [ ] Paper WR ≥52% over 100+ trades
- [ ] Paper PF ≥1.6
- [ ] Paper Sharpe ≥2.0
- [ ] Paper DD <10%
- [ ] No persistent regime failure
- [ ] Live expectancy within 20-30% of backtest

**Initial live sizing:**
- Start with 50% of target size
- Scale up after 50 winning trades
- Full size after 100 trades if metrics hold

---

## Monitoring Dashboard (Grafana)

### Panels to Add

1. **Uptrend Regime P&L Cumulative**
   ```sql
   SELECT
     time_bucket('1h', created_at) as time,
     SUM(CASE WHEN regime='trending_up' THEN pnl ELSE 0 END) as uptrend_pnl
   FROM trades
   GROUP BY 1
   ```

2. **Regime Win Rate (Rolling 30)**
   ```sql
   SELECT regime,
     AVG(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 100 as win_rate
   FROM (SELECT * FROM trades ORDER BY created_at DESC LIMIT 30) t
   GROUP BY regime
   ```

3. **Confluence Lift Metric**
   ```sql
   SELECT
     CASE WHEN has_vwap AND has_flow AND has_levels THEN 'Full' ELSE 'Partial' END as confluence,
     AVG(pnl) as avg_pnl,
     COUNT(*) as trades
   FROM trades
   GROUP BY 1
   ```

### Alerts to Configure

| Alert | Threshold | Action |
|-------|-----------|--------|
| Uptrend WR < 45% | Last 30 trades | Review flow/imbalance filters |
| Daily DD > 2.5% | Intraday | Auto-pause trading |
| Ensemble Brier > 0.15 | Rolling 50 | Check calibration |
| Feature Drift (ADWIN) | p < 0.01 | Review feature importance |

---

## Feature Importance Tracking

Expected top features (validate in live):
1. **VWAP distance** - Should rank high
2. **Flow conviction** - Should rank high
3. **Order imbalance** - Should rank high
4. **Regime state** - Should rank high
5. **RSI/MACD confluence** - Medium importance

If VWAP/flow don't rank high → review signal integration.

---

## Rollback Plan

If live performance diverges >30% from backtest:

```python
# Disable new features
uptrend_tightening = False
trailing_vwap_ema = False
news_sentiment_enabled = False

# Revert to conservative settings
max_position_pct = 2.0
max_daily_drawdown_pct = 2.0
```

---

## Deployment Commands

```bash
# Build and push
docker build -t unified-engine:go-live-v1 .
docker push 192.168.1.254:5000/unified-engine/api:go-live-v1

# Deploy with paper mode first
docker stack deploy -c docker-stack.yml unified_engine

# Verify
docker service logs unified_engine_api -f
```

---

## Sign-Off Checklist

- [x] Uptrend P&L positive in backtest
- [x] PF > 1.8 in backtest
- [x] Sharpe > 2.0 in backtest
- [x] Tightened DD rules applied
- [x] Volatility-based sizing added
- [x] Uptrend protection locked in
- [ ] Paper trading complete (2 weeks)
- [ ] Live expectancy validated
- [ ] Monitoring dashboards configured
- [ ] Alerts configured
- [ ] Go-live approved

---

*Generated: 2026-03-18*
*Version: go-live-v1*
