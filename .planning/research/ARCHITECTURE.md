# Architecture Research: v1.2 Broker Integration

## Executive Summary

The existing hexagonal architecture is well-suited for v1.2. The key insight is that both REST API (ProjectX) and SDK (TradeLocker) patterns can coexist behind the same `BrokerPort` interface. The adapter layer absorbs the differences; domain layer remains unchanged.

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         DOMAIN LAYER                              │
│  ├── entities/: Signal, Trade, Account, BrokerCredentials       │
│  ├── ports/broker_port.py: BrokerPort (abstract interface)      │
│  └── value_objects/: Symbol, Volume, Price, OrderId             │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                      APPLICATION LAYER                            │
│  ├── ProcessSignalUseCase: Routes signals to broker adapters    │
│  └── FeatureGate: Subscription tier checks                      │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                           │
│  ├── adapters/                                                   │
│  │   ├── tradelocker_adapter.py → BrokerPort                    │
│  │   └── topstep_adapter.py → BrokerPort                        │
│  ├── brokers/                                                    │
│  │   ├── tradelocker_executor.py (SDK + Brand API)              │
│  │   ├── tradelocker_sdk_wrapper.py (async wrapper)             │
│  │   ├── projectx_executor.py (SDK + httpx)                     │
│  │   └── base_executor.py                                        │
│  └── services/                                                   │
│      └── projectx_sdk_service.py (SDK wrapper - to be removed)  │
└─────────────────────────────────────────────────────────────────┘
```

## Adapter Structure Pattern

### Common Interface (BrokerPort)

```python
# app/domain/ports/broker_port.py
class BrokerPort(ABC):
    @property
    @abstractmethod
    def broker_type(self) -> BrokerType: ...

    @abstractmethod
    async def connect(self) -> bool: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def is_connected(self) -> bool: ...

    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> bool: ...

    @abstractmethod
    async def place_order(
        self,
        symbol: Symbol,
        order_type: OrderType,
        volume: Volume,
        price: Optional[Price] = None,
        stop_loss: Optional[Price] = None,
        take_profit: Optional[Price] = None,
        comment: Optional[str] = None,
    ) -> Order: ...

    @abstractmethod
    async def close_position(
        self,
        position_id: PositionId,
        volume: Optional[Volume] = None,
    ) -> Trade: ...

    @abstractmethod
    async def get_positions(self) -> List[Position]: ...

    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]: ...
```

### REST API Adapter (ProjectX)

For v1.2, simplify to httpx-only (remove project-x-py SDK):

```python
class TopstepAdapter(BrokerPort):
    """ProjectX Gateway API adapter using httpx."""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._token_manager = ProjectXTokenManager()
        self._contract_cache: Dict[str, int] = {}  # symbol → contract_id

    async def connect(self) -> bool:
        self._client = httpx.AsyncClient(
            base_url=self._api_url,
            timeout=30.0
        )
        token = await self._token_manager.authenticate(
            self._client, self._username, self._api_key
        )
        return token is not None

    async def place_order(self, symbol, order_type, volume, ...) -> Order:
        # 1. Get contract ID (cached)
        contract_id = await self._get_contract_id(symbol.value)

        # 2. Build order payload
        order_data = {
            "accountId": self._account_id,
            "contractId": contract_id,
            "side": "buy" if "buy" in order_type.value.lower() else "sell",
            "type": "market" if "market" in order_type.value.lower() else "limit",
            "size": int(volume.value),
        }

        # 3. Call API
        response = await self._client.post("/Order/place", json=order_data)

        # 4. Convert to domain Order
        return self._to_domain_order(response.json())
```

### SDK Adapter (TradeLocker)

Keep existing pattern with async wrapper:

```python
class TradeLockerAdapter(BrokerPort):
    """TradeLocker SDK adapter using ThreadPoolExecutor wrapper."""

    def __init__(self):
        self._sdk_wrapper: Optional[TradeLockerSDKWrapper] = None
        self._instrument_cache: Dict[str, int] = {}  # symbol → instrument_id

    async def connect(self) -> bool:
        self._sdk_wrapper = TradeLockerSDKWrapper(
            environment=self._environment,
            username=self._username,
            password=self._password,
            server=self._server
        )
        return await self._sdk_wrapper.initialize()

    async def place_order(self, symbol, order_type, volume, ...) -> Order:
        # 1. Get instrument ID (cached)
        instrument_id = await self._get_instrument_id(symbol.value)

        # 2. Call SDK wrapper
        result = await self._sdk_wrapper.create_order(
            instrument_id=instrument_id,
            quantity=float(volume.value),
            side="buy" if "buy" in order_type.value.lower() else "sell",
            type_="market" if "market" in order_type.value.lower() else "limit",
            price=float(price.value) if price else None,
        )

        # 3. Convert to domain Order
        return self._sdk_result_to_order(result)
```

## Token Management

### Storage Pattern

```python
class TokenManager:
    """Manages JWT tokens with automatic refresh."""

    def __init__(self, refresh_buffer: timedelta = timedelta(hours=1)):
        self._token: Optional[str] = None
        self._expiry: Optional[datetime] = None
        self._refresh_buffer = refresh_buffer
        self._lock = asyncio.Lock()

    async def get_valid_token(self, auth_func: Callable) -> str:
        async with self._lock:
            if self._needs_refresh():
                await self._refresh(auth_func)
            return self._token

    def _needs_refresh(self) -> bool:
        if not self._token or not self._expiry:
            return True
        return datetime.utcnow() > (self._expiry - self._refresh_buffer)
```

### Refresh Strategy

| Broker | Token Expiry | Refresh Strategy |
|--------|--------------|------------------|
| ProjectX | 24 hours | Refresh 1 hour before expiry |
| TradeLocker | Handled by SDK | SDK manages internally |

## Contract/Symbol Mapping

### TradingView → Broker Format

```python
class SymbolMapper:
    """Maps TradingView symbols to broker-specific formats."""

    # TradingView → ProjectX contract name
    PROJECTX_MAP = {
        "MNQ1!": "MNQH5",  # Mini Nasdaq, front month
        "MES1!": "MESH5",  # Mini S&P, front month
        "ES1!": "ESH5",    # S&P, front month
        "NQ1!": "NQH5",    # Nasdaq, front month
    }

    # TradingView → TradeLocker symbol
    TRADELOCKER_MAP = {
        "EURUSD": "EURUSD",
        "BTCUSD": "BTCUSD",
        "US30": "US30",
        "NAS100": "NAS100",
    }

    def map_symbol(self, tv_symbol: str, broker: BrokerType) -> str:
        if broker == BrokerType.TOPSTEP:
            return self.PROJECTX_MAP.get(tv_symbol, tv_symbol)
        elif broker == BrokerType.TRADELOCKER:
            return self.TRADELOCKER_MAP.get(tv_symbol, tv_symbol)
        return tv_symbol
```

### Contract ID Resolution

```python
async def resolve_contract_id(self, symbol: str) -> int:
    """Resolve symbol to broker-specific contract ID."""

    # Check cache first
    if symbol in self._contract_cache:
        return self._contract_cache[symbol]

    # Query broker
    response = await self._client.post(
        "/Contract/search",
        json={"symbol": symbol}
    )

    contracts = response.json()
    if not contracts:
        raise ValueError(f"Contract not found: {symbol}")

    contract_id = contracts[0]["id"]
    self._contract_cache[symbol] = contract_id
    return contract_id
```

## Data Flow

```
TradingView Webhook
       │
       ▼
   FastAPI Endpoint (/api/v1/signals/webhook)
       │
       ▼
   ProcessSignalUseCase
       │
       ├─── Get user's selected accounts
       │
       ├─── For each account:
       │    │
       │    ▼
       │    Get BrokerAdapter (from DI container)
       │    │
       │    ▼
       │    Map symbol to broker format
       │    │
       │    ▼
       │    Call adapter.place_order()
       │    │
       │    ├─── [ProjectX] httpx → Gateway API
       │    │
       │    └─── [TradeLocker] SDK wrapper → tradelocker package
       │
       └─── Aggregate results, store trade logs
```

## Build Order Recommendation

### Recommended Order

1. **Phase 26: ProjectX Gateway Integration**
   - Remove project-x-py SDK dependency
   - Harden httpx implementation
   - Add token manager
   - Add contract ID caching
   - **Why first:** Simpler (no SDK complexity), can test quickly

2. **Phase 27: TradeLocker SDK Integration**
   - Harden SDK wrapper
   - Add instrument ID caching
   - Improve error handling
   - **Why second:** Already working, just needs polish

3. **Phase 28: Account Selection & Routing**
   - UI for account connection
   - Test & Connect flow
   - Account selection persistence
   - **Why third:** Depends on working broker connections

4. **Phase 29: Symbol Mapping Enhancement**
   - Unified symbol mapper
   - Futures contract rollover
   - **Why last:** Polish, existing mapping works

### Rationale

- Start with ProjectX because removing SDK simplifies the codebase
- TradeLocker SDK already works well, just needs hardening
- UI changes come after backend is solid
- Symbol mapping is polish layer

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| Adapter pattern | HIGH | Already implemented, proven |
| httpx for ProjectX | HIGH | Existing code works |
| SDK wrapper pattern | HIGH | ThreadPoolExecutor is standard |
| Token management | HIGH | Standard JWT patterns |
| Symbol mapping | MEDIUM | Futures rollover needs testing |
| Contract caching | MEDIUM | Cache invalidation strategy TBD |

---
*Researched: 2026-01-22 for v1.2 milestone*
