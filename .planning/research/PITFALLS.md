# Pitfalls Research: v1.2 Broker Integration

## Executive Summary

The three most dangerous pitfalls for v1.2 are: (1) token expiry during trading hours causing missed trades, (2) order rejection loops from invalid symbols/contracts, and (3) demo vs live environment confusion. All are preventable with proper defensive coding.

## Critical Pitfalls

### 1. Token Expiry Mid-Trade

**Severity:** CRITICAL
**Broker:** ProjectX Gateway API

**What happens:**
- JWT token expires (24h lifetime)
- Next API call returns 401 Unauthorized
- Signal routing fails silently or throws unhandled error
- User misses trade entry/exit

**Warning signs:**
- 401 errors in logs after ~24 hours of uptime
- Intermittent "Unauthorized" errors
- Trades succeed for 23 hours then fail

**Prevention strategy:**
```python
class ProjectXTokenManager:
    REFRESH_BUFFER = timedelta(hours=1)  # Refresh 1 hour before expiry

    async def get_token(self) -> str:
        if self._needs_refresh():
            await self._authenticate()
        return self._token

    def _needs_refresh(self) -> bool:
        return datetime.utcnow() > (self._expiry - self.REFRESH_BUFFER)
```

**Phase to address:** Phase 26 (ProjectX Gateway Integration)

---

### 2. Order Rejection Loops

**Severity:** CRITICAL
**Broker:** Both

**What happens:**
- Signal triggers order placement
- Broker rejects order (invalid symbol, insufficient margin, market closed)
- System retries immediately
- Retry also fails
- Infinite loop consumes resources, spams broker API

**Warning signs:**
- High API call volume for single signal
- Same error repeated in logs
- Broker rate-limits or bans API key

**Prevention strategy:**
```python
from tenacity import retry, stop_after_attempt, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(TransientError),  # Only retry transient errors
)
async def place_order(self, order):
    try:
        return await self._execute_order(order)
    except InvalidSymbolError:
        raise  # Don't retry - will always fail
    except RateLimitError:
        raise  # Don't retry - need backoff
    except ConnectionError:
        raise TransientError()  # OK to retry
```

**Phase to address:** Phase 26 & 27 (both broker integrations)

---

### 3. Environment Mismatch (Demo vs Live)

**Severity:** CRITICAL
**Broker:** Both

**What happens:**
- User configures demo credentials in UI
- Accidentally routes real money signals to demo
- Or worse: demo credentials work against live (some brokers)
- Real money at risk, or user thinks trades executed when they didn't

**Warning signs:**
- Trades showing in UI but not in broker platform
- Account balance discrepancy
- User reports "missing trades"

**Prevention strategy:**
```python
# Store environment explicitly with credentials
class BrokerCredentials:
    environment: Literal["demo", "live"]
    api_url: str  # Set based on environment

    def __post_init__(self):
        if self.environment == "demo":
            self.api_url = "https://gateway-api-demo.s2f.projectx.com"
        else:
            self.api_url = "https://gateway-api.s2f.projectx.com"

# UI must show clear environment indicator
# - Red badge for LIVE
# - Blue/green badge for DEMO
```

**Phase to address:** Phase 28 (Account Selection & Routing)

---

## High Severity Pitfalls

### 4. Rate Limiting

**Severity:** HIGH
**Broker:** ProjectX Gateway API

**What happens:**
- Multiple signals arrive quickly
- Each signal triggers API calls (auth, contract search, order)
- Broker rate-limits the account
- Subsequent signals fail

**Warning signs:**
- HTTP 429 responses
- "Too many requests" errors
- Sporadic failures during high-volume periods

**Prevention strategy:**
```python
from asyncio import Semaphore

class RateLimitedClient:
    def __init__(self, max_concurrent: int = 5):
        self._semaphore = Semaphore(max_concurrent)

    async def request(self, method, url, **kwargs):
        async with self._semaphore:
            response = await self._client.request(method, url, **kwargs)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                await asyncio.sleep(retry_after)
                return await self.request(method, url, **kwargs)
            return response
```

**Phase to address:** Phase 26 (ProjectX Gateway Integration)

---

### 5. Contract ID Mismatches (Futures Rollover)

**Severity:** HIGH
**Broker:** ProjectX (Futures)

**What happens:**
- User trades MNQ (Mini Nasdaq futures)
- Front month contract expires (e.g., MNQ March → MNQ June)
- Cached contract ID points to expired contract
- Order fails or executes wrong contract

**Warning signs:**
- Order failures near expiration dates
- "Contract not found" errors
- Wrong contract traded (old expiration)

**Prevention strategy:**
```python
class ContractCache:
    CACHE_TTL = timedelta(hours=4)  # Short TTL for futures

    def get_contract(self, symbol: str) -> Optional[int]:
        entry = self._cache.get(symbol)
        if not entry or self._is_stale(entry):
            return None  # Force refresh
        return entry.contract_id

    def _is_stale(self, entry) -> bool:
        return datetime.utcnow() > entry.cached_at + self.CACHE_TTL
```

**Phase to address:** Phase 29 (Symbol Mapping Enhancement)

---

### 6. SDK Internal State Corruption

**Severity:** HIGH
**Broker:** TradeLocker SDK

**What happens:**
- TradeLocker SDK maintains internal session state
- Network hiccup corrupts internal state
- Subsequent SDK calls fail with cryptic errors
- SDK doesn't auto-recover

**Warning signs:**
- "Session expired" or "Invalid state" errors
- SDK calls fail after network blip
- Restart required to recover

**Prevention strategy:**
```python
class TradeLockerSDKWrapper:
    async def _execute_with_recovery(self, operation):
        try:
            return await operation()
        except (SessionError, StateError) as e:
            logger.warning(f"SDK state error, reinitializing: {e}")
            await self._reinitialize()
            return await operation()

    async def _reinitialize(self):
        self._executor.shutdown(wait=False)
        self._executor = ThreadPoolExecutor(max_workers=3)
        self._tl = None
        await self.initialize()
```

**Phase to address:** Phase 27 (TradeLocker SDK Integration)

---

## Medium Severity Pitfalls

### 7. Error Message Swallowing

**Severity:** MEDIUM
**Broker:** Both

**What happens:**
- Order fails with detailed error message from broker
- Code catches exception, logs generic message
- User sees "Order failed" with no context
- Debugging requires log access

**Prevention strategy:**
```python
# BAD
except Exception as e:
    logger.error("Order failed")
    return OrderResponse(success=False, error="Order failed")

# GOOD
except BrokerAPIError as e:
    logger.error(f"Order failed: {e.broker_message}", extra={
        "symbol": order.symbol,
        "broker": self.broker_type,
        "error_code": e.code
    })
    return OrderResponse(
        success=False,
        error=f"{e.code}: {e.broker_message}"  # Pass through broker's message
    )
```

**Phase to address:** Phase 26 & 27

---

### 8. Partial Fills Not Handled

**Severity:** MEDIUM
**Broker:** Both (more common with limit orders)

**What happens:**
- User places order for 10 contracts
- Market liquidity only fills 7
- System records 10 as filled
- Position tracking becomes incorrect

**Warning signs:**
- Position size mismatch between Tradeflow and broker
- User reports incorrect position display

**Prevention strategy:**
```python
# Check filled_quantity vs requested_quantity
order_response = await broker.place_order(order)
if order_response.filled_quantity < order.quantity:
    logger.warning(f"Partial fill: {order_response.filled_quantity}/{order.quantity}")
    # Store actual filled amount, not requested
    trade_record.quantity = order_response.filled_quantity
```

**Phase to address:** Phase 26 & 27

---

### 9. WebSocket Reconnection Storms

**Severity:** MEDIUM
**Broker:** TradeLocker WebSocket

**What happens:**
- WebSocket disconnects (network blip)
- Code immediately reconnects
- Server rejects (too soon)
- Code retries immediately
- Exponential backoff not implemented

**Prevention strategy:**
```python
class WebSocketManager:
    INITIAL_BACKOFF = 1  # seconds
    MAX_BACKOFF = 60

    async def _reconnect_with_backoff(self):
        backoff = self.INITIAL_BACKOFF
        while not self._connected:
            try:
                await self._connect()
            except ConnectionError:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.MAX_BACKOFF)
```

**Phase to address:** Phase 27

---

## Prevention Strategies Summary

| Pitfall | Prevention | Phase |
|---------|------------|-------|
| Token expiry | Proactive refresh 1h before expiry | 26 |
| Order rejection loops | Retry only transient errors, max 3 attempts | 26, 27 |
| Environment mismatch | Explicit environment storage, clear UI indicators | 28 |
| Rate limiting | Semaphore, respect Retry-After | 26 |
| Contract ID mismatch | Short cache TTL (4h), force refresh on error | 29 |
| SDK state corruption | Reinitialize SDK on state errors | 27 |
| Error swallowing | Pass through broker error messages | 26, 27 |
| Partial fills | Track actual filled quantity | 26, 27 |
| WebSocket storms | Exponential backoff on reconnect | 27 |

## Warning Signs Checklist

Use this during testing:

- [ ] Run for 25+ hours to test token refresh
- [ ] Send invalid symbol to test error handling
- [ ] Switch environments (demo ↔ live) to test separation
- [ ] Send 20 signals in 10 seconds to test rate limiting
- [ ] Disconnect network mid-order to test recovery
- [ ] Test near futures expiration for rollover
- [ ] Place limit order in illiquid market for partial fill

---
*Researched: 2026-01-22 for v1.2 milestone*
