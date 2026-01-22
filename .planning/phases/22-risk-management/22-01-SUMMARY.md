# Phase 22 Plan 01: Risk Enforcement Service Summary

**Plan executed:** 2026-01-22
**Duration:** ~30 minutes

## One-liner

Core risk enforcement engine that evaluates daily limits, concurrent positions, symbol limits, and cooldowns before signal execution with rejection logging.

## What Was Built

### 1. RejectedSignal Model (Task 1)
Created database model for logging signals blocked by risk management:
- `RejectedSignalReason` enum: daily_limit, concurrent_limit, symbol_limit, cooldown, daily_loss, drawdown, risk_reward, disabled
- `RejectedSignal` model with full context: user_id, account_id, symbol, action, quantity, source, reason, reason_detail, limit_value, current_value
- Composite index on user_id + created_at for efficient queries
- Migration 011_add_rejected_signals.py

### 2. Daily Counter Service (Task 2)
Domain service for tracking daily signal/trade counts:
- `DailyCounters` dataclass with signals_received, trades_executed, trades_by_symbol, last_trade_at
- `DailyCounterService` with get_counters, increment_signals, increment_trades methods
- Date-based automatic reset (counters reset at midnight UTC)
- `InMemoryDailyCounterRepository` with automatic cleanup of old entries

### 3. Risk Enforcement Service (Task 3)
Core domain service evaluating all risk limits:
- `RiskViolation` dataclass capturing reason, detail, limit_value, current_value
- `RiskEvaluation` result with passed/blocked status and violation list
- `AccountRiskSettings` dataclass with from_account() factory method
- Four risk checks:
  1. Daily trade limit (max_daily_trades)
  2. Concurrent position limit (max_open_positions)
  3. Per-symbol position limit (max_positions_per_symbol)
  4. Trade cooldown (trade_cooldown_seconds)
- Close actions always bypass checks
- Async evaluate() for production, sync evaluate_sync() for testing

### 4. Webhook Integration (Task 4)
Risk enforcement integrated into signal processing pipeline:
- Risk check runs after routing, before signal execution
- Each target account evaluated individually
- Blocked signals logged to RejectedSignal table with full context
- Approved accounts proceed to execution
- Daily counters incremented after successful trade
- Response includes risk_blocked_accounts when applicable
- All accounts blocked returns early with "blocked": true

### 5. Per-Symbol Limit Column (Task 5)
Added max_positions_per_symbol to TradingAccount:
- Default value of 1 (one position per symbol)
- Idempotent migration (checks if column exists)

### 6. Risk API Router (Task 6)
Full API for risk management visibility:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/risk/rejected-signals` | GET | Paginated list of blocked signals with filters |
| `/api/v1/risk/rejected-signals/summary` | GET | Aggregated stats by rejection reason |
| `/api/v1/risk/daily-stats/{account_id}` | GET | Daily counters and limit status for account |
| `/api/v1/risk/daily-stats` | GET | Stats for all user accounts |
| `/api/v1/risk/evaluate` | POST | Test if hypothetical signal would be blocked |
| `/api/v1/risk/reasons` | GET | List all rejection reason codes |

## Files Created/Modified

### New Files
- `app/domain/services/risk_enforcement_service.py` - Core risk evaluation logic
- `app/domain/services/daily_counter_service.py` - Daily trade tracking
- `app/infrastructure/repositories/daily_counter_repository.py` - In-memory counter storage
- `app/infrastructure/adapters/position_counter_adapter.py` - Position count queries
- `app/routers/risk.py` - Risk management API endpoints
- `alembic/versions/011_add_rejected_signals.py` - Database migration

### Modified Files
- `app/models/database_models.py` - Added RejectedSignal, RejectedSignalReason
- `app/domain/services/__init__.py` - Exports for new services
- `app/infrastructure/repositories/__init__.py` - Exports for new repository
- `app/routers/webhooks.py` - Risk enforcement integration
- `app/main.py` - Risk router registration

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| In-memory counter repository | Simple for single-instance; Redis for multi-instance can be added later |
| Close actions bypass all checks | Closing positions should never be blocked for risk reasons |
| Evaluate each account individually | Allows partial execution when some accounts blocked |
| Log all rejections to database | Provides audit trail and analytics for users |
| Sync evaluate_sync() method | Enables easy unit testing without async overhead |
| PositionCounterAdapter with dual-mode | Works with both sync and async database sessions |

## Phase 22 Requirements Addressed

- [x] RISK-01: Maximum signals per day (configurable limit) - via max_daily_trades
- [x] RISK-02: Maximum concurrent trades per broker - via max_open_positions per account
- [x] RISK-03: Maximum concurrent trades total - via max_open_positions
- [x] RISK-04: Block signals when any limit reached (with notification) - rejection logging
- [x] RISK-11: Per-symbol trade limits - via max_positions_per_symbol
- [x] RISK-12: Cooldown period between trades - via trade_cooldown_seconds

## Commits

| Hash | Description |
|------|-------------|
| da82aa9 | feat(22-01): add RejectedSignal model and migration |
| ec690b2 | feat(22-01): add DailyCounterService for trade tracking |
| 7cf7dcf | feat(22-01): add RiskEnforcementService for trade limit enforcement |
| 7e4bff8 | feat(22-01): integrate risk enforcement with signal processing |
| 0c4ced4 | feat(22-01): add risk management API router |

## Next Steps

Plan 22-02 (Position Sizing Engine) will build on this foundation:
- RISK-05: Fixed lot size per trade
- RISK-06: Percentage of balance/equity
- RISK-07: Risk-based position sizing (% risk per trade)
- RISK-08: Dynamic sizing based on account state
- RISK-13: Override signal quantity with calculated size

Plan 22-03 (Drawdown & Loss Tracking) will add:
- RISK-09: Maximum daily loss limit
- RISK-10: Maximum drawdown limit
- RISK-14: Trading halt when limits reached
