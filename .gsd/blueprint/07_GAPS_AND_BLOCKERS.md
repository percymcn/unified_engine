# Gaps and Blockers: Unified Trading Engine

## What Prevents "Add Account → Live Data on Dashboard"

### TradeLocker Flow

| Step | Status | Blocker |
|------|--------|---------|
| 1. Add TradeLocker credentials | WORKS | - |
| 2. Test connection | WORKS | SDK mode functional |
| 3. Save account to DB | WORKS | - |
| 4. Fetch balance/equity | WORKS | Via SDK or Brand API |
| 5. Fetch positions | WORKS | SDK returns positions |
| 6. Display on dashboard | WORKS | Via /api/v1/accounts/{id}/balance |
| 7. Receive webhook signal | WORKS | - |
| 8. Route to account | WORKS | SignalProcessor handles |
| 9. Execute trade | PARTIAL | Symbol mapping may fail for some instruments |

**Known Issues:**
- `tradableInstrumentId` lookup requires SDK initialization
- WebSocket for real-time updates not fully wired (SDK doesn't expose)
- Brand API mode has limited endpoint coverage

### ProjectX/TopStep Flow

| Step | Status | Blocker |
|------|--------|---------|
| 1. Add TopStep credentials | WORKS | Username + API key |
| 2. Test connection | WORKS | Gateway API auth |
| 3. Save account to DB | WORKS | - |
| 4. Fetch accounts | WORKS | POST /api/Account/search |
| 5. Fetch positions | WORKS | POST /api/Position/searchOpen |
| 6. Execute trade | WORKS | POST /api/Order/place |
| 7. Token refresh | PARTIAL | 24h expiry, needs proactive refresh |

**Known Issues:**
- Token refresh not implemented proactively (expires after 24h)
- Contract ID caching has no TTL (stale on futures rollover)
- project-x-py SDK still referenced but should be removed

### MT4/MT5 Flow

| Step | Status | Blocker |
|------|--------|---------|
| 1. Configure Manager API | BLOCKED | Requires external MT Manager bridge |
| 2. Connect to broker | BLOCKED | Manager API not running |
| 3. Fetch accounts | BLOCKED | - |

**Known Issues:**
- MT4/MT5 Manager API server must be deployed separately
- No built-in Manager bridge in this codebase
- Most users won't have Manager access

### Tradovate Flow

| Step | Status | Blocker |
|------|--------|---------|
| 1. OAuth authorization | WORKS | Redirect flow implemented |
| 2. Token storage | WORKS | Encrypted in DB |
| 3. Token refresh | PARTIAL | Background task exists but may not trigger |
| 4. Fetch accounts | WORKS | REST API call |
| 5. Execute trade | PARTIAL | REST implementation exists |

**Known Issues:**
- WebSocket for real-time data not fully implemented
- Token refresh task (`tradovate_token_refresh_loop`) needs validation

## Provable Gaps (From Code Analysis)

### 1. Token Expiry Handling

**File:** `app/brokers/projectx_executor.py:121-159`

```python
# Token stored but no refresh mechanism
self._session.headers.update({"Authorization": f"Bearer {token}"})
```

**Gap:** ProjectX JWT expires in 24h. No proactive refresh before expiry. User will see 401 errors after ~24 hours.

**Evidence:** No `token_expires_at` tracking in httpx mode, no refresh task.

### 2. Contract ID Cache Staleness

**File:** `app/brokers/projectx_executor.py:357-376`

```python
# Contract search on every order
contract_response = await self._session.post(
    "/Contract/search",
    json={"symbol": order.symbol}
)
```

**Gap:** No caching of contract IDs. Each order triggers a contract search. Futures contracts roll over, but there's no cache invalidation logic.

### 3. WebSocket Real-Time Not Wired to Brokers

**File:** `app/core/websocket_manager.py`

**Gap:** WebSocket manager broadcasts to UI, but does NOT receive real-time updates FROM brokers. Updates only happen when:
- User manually syncs
- Background task runs
- Signal is processed

**Evidence:** No broker WebSocket listeners in `signal_processor.py` or adapters.

### 4. SDK Dependency Conflict

**File:** `requirements.txt`

```
tradelocker==...
project-x-py==...  # Should be removed per v1.2 research
```

**Gap:** `project-x-py` is still installed but v1.2 research recommends removing it and using httpx-only.

### 5. Risk Page BFF Route Missing Headers

**File:** `ui-next/src/app/api/risk/settings/route.ts`

**Gap:** (Fixed in v1.1.1) Previously called backend directly without auth token. Now uses `getTokenFromCookies()`.

### 6. Symbol Normalization Edge Cases

**File:** `app/domain/services/symbol_normalization_service.py`

**Gap:** Symbol mapping works for common pairs but:
- Futures continuous contracts (MNQ1!, ES1!) not mapped to current front month
- No automatic rollover date handling
- User must manually set symbol aliases

### 7. Alembic Multiple Heads

**Evidence:** `alembic/versions/` has migrations without strict linear dependency.

```bash
# Running alembic heads shows multiple
alembic heads
# 001... 002...
```

**Gap:** Migration history has branches. Running `upgrade head` may fail or produce inconsistent state.

## Summary: Top 5 Blockers for Live Trading

| Priority | Blocker | Impact | Fix Effort |
|----------|---------|--------|------------|
| 1 | ProjectX token expiry (24h) | Trades fail after 24h | Medium - Add token manager |
| 2 | No broker WebSocket listeners | Manual sync only | High - Implement per-broker |
| 3 | MT4/MT5 needs Manager API | Can't use MT4/MT5 | External - Need bridge server |
| 4 | Contract cache staleness | Futures rollover issues | Low - Add TTL |
| 5 | Symbol mapping gaps | Some symbols fail | Medium - Expand mapping |

## What DOES Work

- TradeLocker SDK mode: Full trading capability
- ProjectX Gateway API: Trading works (with 24h token limit)
- Tradovate OAuth + REST: Basic trading works
- Webhook signal routing: Fully functional
- Risk management: Daily limits, drawdown tracking
- Multi-account routing: Signals route to all enabled accounts
- UI dashboard: Shows accounts, balances, trades

---
*Generated: 2026-01-22*
