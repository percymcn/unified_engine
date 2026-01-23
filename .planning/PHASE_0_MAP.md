# Phase 0: System Architecture Map - Signal Intelligence Layer

**Date:** January 22, 2026  
**Milestone:** TradeFlow VSD Milestone 1.2 - Signal Intelligence Layer

## Core Signal Router Entrypoint

### Primary Flow
```
Webhook Request → app/routers/webhooks.py
  → ProcessSignalUseCase.execute() (app/application/use_cases/process_signal.py)
    → SignalService.process_signal() (app/domain/services/signal_service.py)
      → Broker execution
```

### Entry Points
1. **Main Webhook Router:** `app/routers/webhooks.py`
   - `/api/v1/webhooks/tradingview` - TradingView webhooks
   - `/api/v1/webhooks/trailhacker` - TrailHacker webhooks
   - `/api/v1/webhooks/signal/{webhook_key}` - Routed signals via webhook config

2. **Legacy Signal Router:** `app/webhooks/signal_router.py`
   - Used by some endpoints but being phased out

3. **Signal Processor Service:** `app/services/signal_processor.py`
   - Legacy service, still used by some endpoints
   - Contains `process_signal()` and `process_webhook()` methods

## Signal Normalization Model

### Domain Entity
- **File:** `app/domain/entities/signal.py`
- **Class:** `Signal`
- **Fields:**
  - `id: SignalId`
  - `source: SignalSource` (TRADINGVIEW, TRAILHACKER, etc.)
  - `symbol: Symbol`
  - `action: SignalAction` (BUY, SELL, CLOSE)
  - `volume: Volume`
  - `price: Price`
  - `stop_loss: StopLoss`
  - `take_profit: TakeProfit`
  - `target_accounts: List[AccountId]`
  - `comment: str`
  - `strategy_id: str`
  - `strategy_name: str`
  - `raw_payload: Dict`

### DTO Layer
- **Request DTO:** `app/application/dto/signal_dto.py::ProcessSignalRequest`
- **Response DTO:** `app/application/dto/signal_dto.py::ProcessSignalResponse`

### Normalization Points
1. **Webhook Router** (`app/routers/webhooks.py`):
   - Lines 85-110: TradingView payload → ProcessSignalRequest
   - Lines 183-208: TrailHacker payload → ProcessSignalRequest
   - Lines 391-576: Routed signal → ProcessSignalRequest

2. **ProcessSignalUseCase** (`app/application/use_cases/process_signal.py`):
   - Lines 104-129: `_to_domain_entity()` converts DTO → Signal entity

## Risk Engine Hooks

### Current Risk Enforcement
- **Service:** `app/domain/services/risk_enforcement_service.py`
- **Integration:** `app/routers/webhooks.py` lines 409-519
- **Checks:**
  - Daily trade limits
  - Concurrent position limits
  - Symbol limits
  - Cooldown periods
  - Daily loss limits
  - Drawdown limits

### Risk Settings Storage
- **User Model:** `app/models/models.py::User`
  - Global risk defaults stored as columns:
    - `default_max_daily_trades`
    - `default_max_open_positions`
    - `default_max_daily_loss`
    - `default_max_daily_loss_pct`
    - `default_max_drawdown_pct`
    - `default_trade_cooldown_seconds`
    - `risk_management_enabled`
- **Account Model:** `app/models/database_models.py::TradingAccount`
  - Account-specific overrides
  - `extra_metadata: JSON` - Can store additional settings

### Risk API
- **Router:** `app/routers/risk.py`
- **Endpoints:**
  - `GET /api/v1/risk/settings` - Get user risk settings
  - `PUT /api/v1/risk/settings` - Update user risk settings

## Execution Dispatch Functions

### Domain Service
- **File:** `app/domain/services/signal_service.py`
- **Method:** `process_signal(signal: Signal)`
- **Flow:** Routes to broker adapters via BrokerPort interface

### Broker Executors
- **Location:** `app/brokers/`
- **Executors:**
  - `mt4_executor.py::MT4Executor`
  - `mt5_executor.py::MT5Executor`
  - `tradelocker_executor.py::TradeLockerExecutor`
  - `tradovate_executor.py::TradovateExecutor`
  - `projectx_executor.py::ProjectXExecutor`

## User Risk Settings Loading

### Current Implementation
1. **User Context:** Retrieved via `get_current_user` dependency
2. **Account Context:** Retrieved from `TradingAccount` model
3. **Settings Merge:** `AccountRiskSettings.from_account()` merges user defaults + account overrides

### Settings Access Pattern
```python
# In webhooks.py
user = get_current_user()  # or from webhook_config.user_id
account = db.query(TradingAccount).filter(...).first()
risk_settings = AccountRiskSettings.from_account(account)
```

## UI Dashboard Components

### Frontend Location
- **Path:** `ui/src/`
- **Components:** `ui/src/components/`

### Key Components (to locate)
- Position/Trade cards: Need to find position display components
- Dashboard: `ui/src/pages/` or similar
- Modals: Need to find existing modal components

### API Client
- **File:** `ui/src/utils/api-client.ts` or `api-client-enhanced.ts`
- **Pattern:** Uses fetch/axios for API calls

## History/Log Tables

### Existing Tables
1. **Signals Table:** `app/models/models.py::Signal`
   - Stores all processed signals
   - Fields: id, broker, account_id, symbol, action, status, created_at, executed_at

2. **WebhookLog Table:** `app/models/models.py::WebhookLog`
   - Stores webhook receipts
   - Fields: id, source, payload, headers, status, created_at

3. **RejectedSignal Table:** `app/models/database_models.py::RejectedSignal`
   - Stores risk-blocked signals
   - Fields: user_id, account_id, symbol, action, reason, reason_detail

### History Access
- **Signals:** `app/services/signal_processor.py::get_signal_history()`
- **Webhooks:** `app/services/signal_processor.py::get_webhook_history()`
- **Rejected:** `app/routers/risk.py::get_rejected_signals()`

## Guard Layer Injection Point

### Recommended Location
**File:** `app/application/use_cases/process_signal.py`  
**Method:** `ProcessSignalUseCase.execute()`  
**Insertion Point:** After line 74 (`await self._signal_repo.save(signal)`) and before line 77 (`await self._signal_service.process_signal(signal)`)

### Why This Location?
1. Signal is normalized (domain entity)
2. Signal is persisted (for history)
3. Before broker execution
4. Broker-agnostic (works for all brokers)
5. Single point of control

### Guard Layer Interface
```python
class GuardDecision(Enum):
    EXECUTE = "execute"
    SKIP = "skip"
    PAUSE_NEW_ENTRIES = "pause_new_entries"
    WARN_MODAL_REQUIRED = "warn_modal_required"

@dataclass
class GuardResult:
    decision: GuardDecision
    annotations: Dict[str, Any]  # History tags, discard reason, UI payload
    updated_counters: Optional[Dict] = None
```

## Database Schema

### Migration Location
- **Path:** `alembic/versions/`
- **Pattern:** `0XX_description.py`
- **Latest:** `017_add_deduplication_settings.py`

### User Model Extensions
- Risk settings stored in `users` table columns (migration 013)
- Can extend `extra_metadata` JSON field for new settings
- Or add new columns via migration

## Next Steps

1. Create migration for 3 new tables
2. Implement guard layer service
3. Integrate guard layer into ProcessSignalUseCase
4. Add settings to user risk_settings (via JSON or columns)
5. Update UI components
6. Add tests
7. Generate API docs
