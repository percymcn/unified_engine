# SmartFlow Golden Baseline v1

**Created:** 2026-03-18T05:30:00Z
**Status:** FROZEN
**Validation:** Pre-freeze check PASSED

---

## Code Identity

| Property | Value |
|----------|-------|
| Git Commit | `496ec1e5495eab893e9e8aaeef151137ea95820b` |
| Git Message | backup: pre-deterministic-indicators working state |
| Image Tag | `latest` |
| Image Built | 2026-03-18T00:50:03-04:00 |
| App Version | 1.2.1 |

---

## Runtime Services

Expected services for healthy operation:

| Service | Port |
|---------|------|
| unified_trading_api | 8000 |
| unified_trading_postgres | 5432 |
| unified_trading_redis | 6379 |
| unified_trading_celery-worker | - |
| unified_trading_celery-beat | - |

---

## Database Schema

**Alembic Version:** `047_portfolio_risk`

### SmartFlow Tables

| Table | Row Count |
|-------|-----------|
| smartflow_config | 3 |
| smartflow_signal_logs | 2,919 |
| smartflow_strategies | 10 |
| smartflow_score_history | 16,298 |
| smartflow_market_regimes | - |
| smartflow_patterns | - |
| smartflow_signal_outcomes | - |
| smartflow_model_state | - |
| smartflow_ml_metrics | - |
| smartflow_correlation_signals | - |

### Strategy Tables

| Table | Purpose |
|-------|---------|
| strategy_backtest_snapshots | Backtest performance history |
| strategy_forward_test_snapshots | Live forward test metrics |
| strategy_health_snapshots | Drift detection snapshots |
| strategy_evaluations | Strategy evaluation records |
| strategy_candidates | Pending strategy candidates |
| strategy_performance | Performance tracking |

### Key Constraints

- `smartflow_signal_logs_config_id_fkey` → `smartflow_config.id`

---

## Runtime Chain

```
Market Data
    ↓
Regime Detection (regime_detector_v2)
    ↓
Quick Anchor (quick_strategy)
    ↓
Adaptive Router (smartflow_engine_router)
    ↓
Strategy Registry Eligibility
    ↓
Strategy Engine Execution
    ↓
AI Feature Engine → Flow Feature Engine
    ↓
Signal Agreement Layer
    ↓
Signal Guard
    ↓
Allocator
    ↓
Portfolio Risk
    ↓
Execution Quality
    ↓
Webhook Execution
    ↓
Broker Execution
    ↓
DB / Logs / Dashboard
```

---

## Strategy Registry

### Router-Eligible Strategies

| Strategy ID | Type | Status | Health | Sharpe | Win Rate |
|-------------|------|--------|--------|--------|----------|
| unified_v1 | unified | built_in | healthy | 3.20 | 55.9% |
| deterministic_v1 | deterministic | approved_for_router | healthy | 3.20 | 55.9% |
| quick_v1 | quick | approved_for_router | healthy | 2.88 | 51.0% |
| flow_v1 | flow | approved_for_router | healthy | 3.63 | 54.5% |
| ai_v1_proxy | ai | approved_for_router | healthy | 3.90 | 55.9% |
| breakout_v1 | breakout | approved_for_router | healthy | 2.92 | 50.0% |
| mean_reversion_v1 | mean_reversion | approved_for_router | healthy | 2.92 | 50.0% |
| pyramid_dynamic_v1 | pyramid | approved_for_router | healthy | 1.24 | 53.0% |

### Forward Testing

| Strategy ID | Type | Status | Health |
|-------------|------|--------|--------|
| trend_v1 | trend | forward_testing | unknown |
| liquidity_reversal_v1 | liquidity_reversal | forward_testing | unknown |

### Routing Configuration

- **Slim Map Engines:** quick, unified
- **Manual-Only Engines:** ai, flow
- **Routing Mode:** AUTO_BY_REGIME

---

## Production Accounts

| ID | Broker | Status |
|----|--------|--------|
| 79 | PROJECTX | Active |
| 63 | TRADELOCKER | Active |
| 77 | TRADELOCKER | Active |
| 76 | PROJECTX | Active |

---

## Celery Tasks

| Task | Schedule |
|------|----------|
| sync_all_accounts | Every 5 minutes |
| sync_positions | Every 10 minutes |
| update_smartflow_outcomes | Every 15 minutes |
| reset_daily_counters | Daily 6:01 PM EST |
| capture_strategy_health_snapshots | Every 30 minutes |
| capture_forward_test_snapshots | Every 5 minutes |
| capture_portfolio_risk_snapshot | Hourly |

---

## API Endpoints

### SmartFlow
- `GET /api/v1/smartflow/config`
- `GET /api/v1/smartflow/signals`
- `GET /api/v1/smartflow/strategies`
- `GET /api/v1/smartflow/score-history`
- `GET /api/v1/smartflow/regime`

### Health
- `GET /health`
- `GET /api/v1/brokers/health`

### Strategy Registry
- `GET /api/v1/strategies`
- `GET /api/v1/strategies/status`

---

## Dashboard Tabs

SmartFlow dashboard components:
- Elite Dashboard
- Deterministic Dashboard
- Quick Mode Dashboard
- Compare Engines Dashboard
- Forward Test Dashboard
- Adaptive Router Dashboard
- Strategies Overview
- Live Signals Dashboard
- Webhooks Dashboard

---

## Metadata Contract

Expected signal metadata fields:
- `selected_strategy_id`
- `selected_engine`
- `current_regime`
- `decision_source`
- `confidence`
- `confidence_reason`
- `guard_status`
- `allocator_weight`
- `flow_score`
- `ai_score`
- `agreement_score`

---

## Validation Status

| Check | Result |
|-------|--------|
| Pre-freeze validation | PASS |
| Critical blockers | 0 |
| High blockers | 0 |
| Table/Model alignment | FIXED |
| FK relationships | VERIFIED |

---

## Usage

To compare current state against this baseline:

```bash
# Load baseline
cat .smartflow_data/baselines/SMARTFLOW_GOLDEN_BASELINE_v1.json | jq .

# Check integrity endpoint
curl -s http://localhost:8000/api/v1/smartflow/integrity/status | jq .

# Compare specific section
curl -s http://localhost:8000/api/v1/smartflow/integrity/drift | jq .
```
