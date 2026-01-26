# TradeFlow Production Hardening Report

**Date:** 2026-01-26
**Status:** Phase 0 Complete - Baseline Established

---

## Executive Summary

TradeFlow is a multi-user trading SaaS platform that routes TradingView webhook alerts to broker accounts (TradeLocker, ProjectX/TopStep, Tradovate, MT4, MT5). This report documents the current state, identifies gaps, and provides a remediation roadmap.

**Overall Assessment:** ~75% production-ready. Core execution pipeline works. Multi-account routing and some broker integrations need completion.

---

## Phase 0: Baseline Assessment

### Backend Health
```
Status: HEALTHY
Redis: connected
Brokers: mt4=true, mt5=true, tradelocker=false, tradovate=false, projectx=false
```

### Database Status
- **Tables:** 40 (properly structured)
- **Alembic:** Single head at revision 024 (no migration issues)
- **Key Tables:**
  - `users` - User accounts
  - `trading_accounts` - Broker accounts (with webhook_key)
  - `credentials` - Encrypted credentials (Fernet)
  - `webhook_configs` - User-level webhook routing config
  - `signals` - Persisted signals with status
  - `execution_logs` - Trade execution audit trail
  - `webhook_logs` - Raw webhook payload logs
  - `rejected_signals` - Risk guard rejections
  - `discard_bin` - Discarded signals for debugging

### API Endpoints Inventory
| Category | Prefix | Key Endpoints |
|----------|--------|---------------|
| Webhook Ingestion | `/api/v1/webhook` | `POST /execute` - Main TradingView handler |
| Accounts | `/api/v1/accounts` | CRUD, test-connection, discover |
| Broker Contracts | `/api/v1/brokers` | `GET /contracts` (canonical schemas) |
| Signals | `/api/v1/signals` | History, active, execute |
| Risk | `/api/v1/risk` | Guards, rejected signals, limits |
| Signal Intelligence | `/api/v1/signal-intelligence` | Counters, momentum, confirmations |
| Webhooks Config | `/api/v1/webhook-configs` | User routing preferences |

### Broker Adapters
| Broker | Executor | SDK/API | Status |
|--------|----------|---------|--------|
| MT4 | `mt4_executor.py` | MetaAPI SDK | ✅ Working |
| MT5 | `mt5_executor.py` | MetaAPI SDK | ✅ Working |
| TradeLocker | `tradelocker_executor.py` | TradeLocker SDK | ⚠️ Needs credentials |
| Tradovate | `tradovate_executor.py` | REST API + OAuth | ⚠️ Needs credentials |
| ProjectX | `projectx_executor.py` | Gateway API | ⚠️ Needs credentials |

---

## What's Working ✅

### 1. Core Execution Pipeline
The TradingView → Execution pipeline is fully implemented:
```
Webhook Received → Payload Parsed → Account Resolved (by webhook_key) →
Signal Intelligence Guard → Risk Validation → Broker Execution → Persistence
```

Located in: `app/routers/webhook_execute.py`

### 2. Signal Intelligence Guard
- Staleness check (configurable max age)
- Momentum warnings (rapid-fire detection)
- User confirmation modals for risky signals
- Pause new entries mode
- Counter tracking per symbol/account

### 3. Risk Management
- Daily trade limits
- Concurrent position limits
- Per-symbol position limits
- Cooldown periods
- Daily loss limits
- Drawdown limits
- Rejected signal logging with reasons

### 4. Persistence Layer
- Complete audit trail: `webhook_logs`, `signals`, `execution_logs`
- Rejected signals tracked: `rejected_signals`
- Discarded signals preserved: `discard_bin`
- Performance metrics: `performance_metrics`, `daily_pnl`

### 5. Credential Management
- Encrypted storage via Fernet
- Per-user credentials in `credentials` table
- OAuth token storage in `trading_accounts`
- Test connection endpoint validates before saving

### 6. Contract Schemas
- Backend: `app/contracts/brokers.json` (canonical source)
- UI: `ui-next/src/lib/brokers/credentialSchemas.ts`
- API: `GET /api/v1/brokers/contracts`

---

## Gaps Identified 🔴

### Critical (P0)

#### 1. Multi-Account Routing Incomplete
**Current:** Webhook routes to ONE account (first match by webhook_key or default)
**Required:** Route to MULTIPLE accounts simultaneously

```python
# Current in webhook_execute.py:159
account = db.query(TradingAccount).filter(
    TradingAccount.webhook_key == webhook_key
).first()  # Only gets ONE
```

**Fix Required:**
- Support `target_account_ids` in webhook payload
- Support `all_enabled` routing mode
- Execute on multiple accounts and aggregate results

#### 2. Routing Rules Not Implemented
**Required:**
- Per-symbol routing rules (route NAS100 to account A, ES to account B)
- Per-strategy routing (strategy_id → specific accounts)
- Default account fallback per broker

**Database Ready:** `webhook_configs` has `specific_account_ids`, `symbol_filters` columns
**Missing:** Logic to apply rules during routing

### High (P1)

#### 3. Symbol Normalization Integration
**Tables Exist:** `broker_symbol_formats`, `symbol_aliases`, `futures_contracts`
**Missing Verification:**
- Is `broker_symbol_formats` used during execution?
- How does TV ticker → broker contract ID mapping work?

#### 4. Account Discovery Verification
Each broker executor has `list_accounts()` but need to verify:
- ProjectX multi-account (same email, multiple challenges) works
- TradeLocker account selection from discovered list
- UI properly displays and allows selection

### Medium (P2)

#### 5. Execution Trace UI
**Needed:** A view showing complete webhook → execution flow
- Raw payload received
- Account resolution result
- Guard decision with annotations
- Execution attempts per account
- Final result

#### 6. UI Contract Sync
**Fixed Today:** Updated `app/contracts/brokers.json`:
- TradeLocker: `environment` → `sdk_environment` with URL values
- Tradovate: Added `app_version` field

---

## Fixes Applied This Session

### 1. TradeLocker Environment URL Mapping
**Files Changed:**
- `app/contracts/brokers.json` - Changed `backend_name` to `sdk_environment`, options to full URLs
- `ui-next/src/lib/brokers/credentialSchemas.ts` - Already had correct mapping
- `app/routers/accounts.py` - Accept both `sdk_environment` and `environment`
- `app/routers/broker_health.py` - Same fix
- `app/services/signal_processor.py` - Same fix
- `app/application/use_cases/test_connection.py` - Same fix

### 2. Tradovate App Version Field
**Files Changed:**
- `app/contracts/brokers.json` - Added `app_version` field
- `ui-next/src/lib/brokers/credentialSchemas.ts` - Already had correct field
- `app/routers/accounts.py` - Pass `app_version` to executor
- `app/application/use_cases/test_connection.py` - Include in auth request

---

## Verification Commands

### Backend Health
```bash
curl -s http://localhost:8765/health | jq
```

### Broker Contracts
```bash
curl -s http://localhost:8765/api/v1/brokers/contracts | jq '.brokers | keys'
```

### Webhook Test (Invalid Key)
```bash
curl -s http://localhost:8765/api/v1/webhook/execute \
  -X POST -H "Content-Type: application/json" \
  -d '{"webhook_key": "invalid", "action": "buy", "symbol": "EURUSD"}'
# Expected: 403 Invalid webhook_key
```

### Database Tables
```bash
psql -U trading_user -d trading_db -c "\dt" | wc -l
# Expected: 40+ tables
```

### Alembic Status
```bash
cd /home/pharma5/unified_engine
DATABASE_URL="..." alembic current
# Expected: 024_webhook_key_unique_index (head)
```

---

## Remediation Roadmap

### Phase 1: Multi-Account Routing (P0)
1. Update `webhook_execute.py` to support `target_account_ids` array
2. Add parallel execution to multiple accounts
3. Aggregate results with per-account status
4. Update `WebhookConfig` to support routing modes

### Phase 2: Routing Rules (P0)
1. Implement symbol-based routing in `webhook_config`
2. Implement strategy-based routing
3. Add routing rule evaluation in execution pipeline
4. Log routing decisions for debugging

### Phase 3: Account Discovery (P1)
1. Verify ProjectX multi-challenge account support
2. Test TradeLocker account discovery with real credentials
3. Add UI for selecting accounts from discovered list
4. Store account metadata (contract IDs, symbols available)

### Phase 4: Symbol Mapping (P1)
1. Verify `broker_symbol_formats` usage in executors
2. Implement TradingView ticker → broker symbol lookup
3. Add UI for managing symbol aliases
4. Support futures rollover (ES → ESH6, ESM6, etc.)

### Phase 5: Execution Trace UI (P2)
1. Create `/dashboard/execution-trace/[webhook_id]` page
2. Query `webhook_logs`, `signals`, `execution_logs` by webhook_id
3. Display timeline of events with annotations

---

## What Remains

| Item | Priority | Status |
|------|----------|--------|
| Multi-account simultaneous execution | P0 | Not Started |
| Symbol-based routing rules | P0 | Not Started |
| Strategy-based routing rules | P1 | Not Started |
| Account discovery verification | P1 | Not Started |
| Symbol normalization verification | P1 | Not Started |
| Execution trace UI | P2 | Not Started |
| Smoke test scripts | P1 | Partially done |

---

*Report generated: 2026-01-26*
