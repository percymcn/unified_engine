# Data Flows: Unified Trading Engine

## Live Data Ingestion

### 1. Webhook Signal Flow

```
TradingView Alert
      │
      ▼
POST /api/v1/webhooks/signal/{webhook_key}
      │
      ▼
webhooks.py:handle_signal()
├── Validate webhook_key → WebhookConfig lookup
├── Parse signal payload (symbol, action, qty, etc.)
├── Check deduplication (Redis)
└── Queue to signal_processor
      │
      ▼
signal_processor.py:process_signal()
├── Get user's enabled accounts
├── For each account:
│   ├── Get broker executor
│   ├── Normalize symbol (SymbolNormalizationService)
│   ├── Check risk limits (RiskService)
│   ├── Place order via executor
│   └── Log result
├── Store Signal in DB
└── WebSocket broadcast to UI
```

### 2. Account Balance Sync Flow

```
User clicks "Sync" or Background task
      │
      ▼
accounts.py:sync_account()
      │
      ▼
BrokerAdapter.get_account_info()
      │
      ▼
BrokerExecutor.get_accounts() / get_positions()
├── TradeLocker: SDK.get_account_state()
├── ProjectX: POST /api/Account/search
├── MT4/MT5: Manager API call
└── Tradovate: REST API call
      │
      ▼
Update TradingAccount table
├── balance, equity, margin, free_margin
└── last_sync timestamp
      │
      ▼
WebSocket push: { type: "account_update", data: {...} }
```

### 3. Position/Trade Data Flow

```
Broker Executor Response
      │
      ├── Order placed successfully
      │   ▼
      │   Create Trade record in DB
      │   ├── trade_id, account_id, symbol
      │   ├── side, quantity, price
      │   ├── status, timestamp
      │   └── WebSocket push
      │
      ├── Position opened
      │   ▼
      │   Create/Update Position record
      │   ├── position_id, symbol, side
      │   ├── entry_price, current_price
      │   ├── unrealized_pnl
      │   └── WebSocket push
      │
      └── Position closed
          ▼
          Update Position (status=closed)
          Update Trade (close_price, pnl)
          Update DailyPnL tracking
```

## Symbol Mapping

### Location

`app/domain/services/symbol_normalization_service.py`

### Flow

```
Incoming Signal: symbol="EURUSD"
      │
      ▼
SymbolNormalizationService.normalize()
├── Check symbol_aliases table for user overrides
├── Check futures_contracts table for contract mapping
└── Apply broker-specific format
      │
      ├── TradeLocker: Lookup tradableInstrumentId
      │   → SDK.get_all_instruments() → match by name
      │
      ├── ProjectX: Contract search
      │   → POST /api/Contract/search { symbol }
      │   → Returns contract_id
      │
      └── MT4/MT5: Direct symbol name
          → No mapping needed (usually)
```

### Symbol Alias Table

```sql
CREATE TABLE symbol_aliases (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    source_symbol VARCHAR(50),      -- TradingView symbol
    target_symbol VARCHAR(50),      -- Broker symbol
    broker VARCHAR(50),             -- Specific broker or NULL for all
    is_active BOOLEAN DEFAULT TRUE
);
```

## Caching (Redis)

### Location

`app/cache/redis_client.py`

### Cache Keys

| Key Pattern | TTL | Purpose |
|-------------|-----|---------|
| `session:{user_id}:{session_id}` | 24h | User sessions |
| `signal_dedup:{hash}` | 60s | Duplicate signal prevention |
| `rate_limit:{user_id}:{endpoint}` | 1m | API rate limiting |
| `account_balance:{account_id}` | 5m | Cached balance |
| `broker_status:{broker}` | 30s | Connection status |
| `instrument_cache:{broker}:{symbol}` | 4h | Symbol/instrument ID mapping |

### Deduplication

```python
# app/services/signal_deduplication_service.py

def check_duplicate(signal: SignalRequest) -> DuplicateCheckResult:
    # Generate hash from signal fields
    signal_hash = hashlib.sha256(
        f"{signal.symbol}:{signal.action}:{signal.qty}".encode()
    ).hexdigest()

    # Check Redis
    key = f"signal_dedup:{signal_hash}"
    if redis_client.exists(key):
        return DuplicateCheckResult(is_duplicate=True)

    # Set with TTL
    redis_client.setex(key, 60, "1")  # 60 second window
    return DuplicateCheckResult(is_duplicate=False)
```

## WebSocket Real-Time Updates

### Location

`app/core/websocket_manager.py`

### Endpoint

`ws://localhost:8765/ws`

### Message Types

```json
// Server → Client
{ "type": "account_update", "data": { "account_id": 1, "balance": 10000 } }
{ "type": "position_update", "data": { "position_id": 123, "pnl": 50.25 } }
{ "type": "signal_processed", "data": { "signal_id": "abc", "status": "executed" } }
{ "type": "trade_executed", "data": { "trade_id": 456, "symbol": "EURUSD" } }

// Client → Server
{ "type": "ping" }  // Heartbeat
{ "type": "subscribe", "channel": "account:1" }
```

### Heartbeat

```python
# websocket_manager.py
async def start_heartbeat(self):
    while True:
        await asyncio.sleep(30)
        for connection in self.active_connections:
            try:
                await connection.send_json({"type": "pong"})
            except:
                self.disconnect(connection)
```

## Background Tasks

### Token Refresh

```python
# app/tasks/token_refresh.py

async def refresh_expiring_tokens():
    """Refresh OAuth tokens expiring within 1 hour"""
    accounts = db.query(TradingAccount).filter(
        TradingAccount.token_expires_at < datetime.utcnow() + timedelta(hours=1)
    ).all()

    for account in accounts:
        if account.broker == BrokerType.TRADOVATE:
            await refresh_tradovate_token(account)
        elif account.broker == BrokerType.PROJECTX:
            await refresh_projectx_token(account)
```

### Daily PnL Tracking

```python
# app/services/risk_service.py

async def update_daily_pnl(account_id: int):
    """Update daily P&L for account"""
    today = date.today()
    pnl = db.query(DailyPnL).filter(
        DailyPnL.account_id == account_id,
        DailyPnL.date == today
    ).first()

    if not pnl:
        pnl = DailyPnL(
            account_id=account_id,
            date=today,
            starting_balance=account.balance
        )
        db.add(pnl)

    # Calculate from trades
    trades_today = get_trades_for_date(account_id, today)
    pnl.realized_pnl = sum(t.pnl for t in trades_today)
    pnl.trades_count = len(trades_today)
```

---
*Generated: 2026-01-22*
