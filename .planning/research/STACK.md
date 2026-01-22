# Stack Research: v1.2 Broker Integration

## Executive Summary

For v1.2, the stack decision is clear: use `httpx` for ProjectX Gateway API (direct HTTP) and the official `tradelocker` SDK for TradeLocker. The existing codebase already has this architecture in place - v1.2 focuses on hardening these implementations for production reliability.

## HTTP Client Recommendation

**Library:** `httpx` (already in use)
**Version:** 0.27.x (current)

**Why httpx:**
- Native async/await support (perfect for FastAPI)
- Connection pooling built-in
- Timeout configuration per-request
- Already used in existing ProjectX executor
- Better error handling than `requests`

**Why NOT aiohttp:**
- httpx API is cleaner and more requests-like
- Less boilerplate for simple REST calls
- httpx is the modern standard for async HTTP in Python

## ProjectX Gateway API Integration

### Authentication Pattern

```python
# POST /api/Auth/loginKey
{
    "userName": "your_username",
    "apiKey": "your_api_key"
}
# Response: JWT token (text/plain or JSON)
```

**Key points:**
- JWT token has 24-hour expiry
- Store token in `Authorization: Bearer {token}` header
- Demo: `https://gateway-api-demo.s2f.projectx.com`
- Live: `https://gateway-api.s2f.projectx.com`

### Token Refresh Strategy

```python
class ProjectXTokenManager:
    def __init__(self):
        self._token: Optional[str] = None
        self._expiry: Optional[datetime] = None

    async def get_token(self, client: httpx.AsyncClient) -> str:
        if self._is_expired():
            await self._refresh_token(client)
        return self._token

    def _is_expired(self) -> bool:
        if not self._expiry:
            return True
        # Refresh 1 hour before expiry for safety
        return datetime.utcnow() > (self._expiry - timedelta(hours=1))
```

### Adapter Structure

The existing `projectx_executor.py` already implements httpx mode at lines 121-159. Key improvements for v1.2:

1. **Extract token management** to separate class
2. **Add retry logic** for transient failures
3. **Contract ID caching** to reduce `/Contract/search` calls

### Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/Auth/loginKey` | POST | Authenticate, get JWT |
| `/api/Account/search` | POST | List accounts |
| `/api/Contract/search` | POST | Find contract by symbol |
| `/api/Contract/available` | POST | List available contracts |
| `/api/Order/place` | POST | Place order |
| `/api/Order/cancel` | POST | Cancel order |
| `/api/Position/searchOpen` | POST | Get open positions |
| `/api/Position/closeContract` | POST | Close position |

## TradeLocker SDK Integration

### SDK Usage Pattern

```python
from tradelocker import TLAPI

# SDK is synchronous - wrap with ThreadPoolExecutor
tl = TLAPI(
    environment="https://demo.tradelocker.com",
    username="user@email.com",
    password="password",
    server="Demo Server"
)

# Get account
acc_num = tl.get_acc_nums()[0]
acc_id = tl.get_acc_ids()[0]

# Get instruments
instruments = tl.get_all_instruments()  # Returns DataFrame
instrument_id = instruments[instruments['name'] == 'EURUSD']['tradableInstrumentId'].iloc[0]

# Place order
tl.create_order(
    instrument_id=instrument_id,
    quantity=0.1,
    side="buy",
    type_="market"
)
```

### Adapter Structure

The existing `tradelocker_sdk_wrapper.py` provides async wrapper using `ThreadPoolExecutor`. Key improvements for v1.2:

1. **Instrument ID caching** - avoid repeated lookups
2. **Connection health monitoring** - detect stale SDK instances
3. **Graceful SDK restart** - handle SDK internal errors

### SDK vs Brand API

| Aspect | SDK Mode | Brand API Mode |
|--------|----------|----------------|
| Auth | Username/password/server | Brand API key |
| Tokens | Handled internally | Must manage JWT |
| WebSocket | Not exposed | Must implement |
| Recommended | Yes (simpler) | Fallback only |

## Error Handling Patterns

### Retry with Exponential Backoff

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
async def place_order_with_retry(self, order: OrderRequest) -> OrderResponse:
    return await self._place_order(order)
```

### Circuit Breaker for Broker Failures

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def execute_trade(self, ...):
    ...
```

## What NOT to Use

### project-x-py SDK

**DO NOT USE** the `project-x-py` pip package for v1.2. Reasons:

1. **Complexity** - TradingSuite lifecycle management is error-prone
2. **Per-instrument connections** - Each instrument needs separate suite
3. **Cancellation limitations** - Cannot cancel orders without instrument context
4. **Direct API is simpler** - httpx to Gateway API is straightforward

The existing code shows the SDK's complexity:
- `projectx_sdk_service.py` creates new `TradingSuite` per operation
- Must track which suite placed which order
- Order cancellation returns "requires instrument context"

### requests library

Use `httpx` instead for async support.

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| httpx for ProjectX | HIGH | Already implemented, proven pattern |
| TradeLocker SDK | HIGH | Official SDK, async wrapper exists |
| Token refresh | HIGH | Standard JWT pattern, 24h expiry is generous |
| Contract caching | MEDIUM | Need to handle contract rollover for futures |
| Error retry | HIGH | Standard tenacity patterns |

---
*Researched: 2026-01-22 for v1.2 milestone*
