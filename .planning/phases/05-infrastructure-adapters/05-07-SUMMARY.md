---
phase: 05-infrastructure-adapters
plan: 07
subsystem: broker-integration
tags: [adapter, topstep, projectx, hexagonal-architecture]
completed: 2026-01-20
duration: 25min

dependencies:
  requires:
    - 03-05-port-interfaces
    - 05-01-infrastructure-package-structure
    - 05-02-entity-mappers
  provides:
    - topstep-broker-adapter
    - projectx-gateway-integration
  affects:
    - 05-11-di-container
    - 05-12-infrastructure-tests

tech_stack:
  added: []
  patterns:
    - adapter-pattern
    - domain-value-object-conversion
    - executor-wrapping

files:
  created:
    - app/infrastructure/adapters/topstep_adapter.py
  modified:
    - app/infrastructure/adapters/__init__.py

decisions:
  - title: "TopStep uses ProjectXExecutor implementation"
    rationale: "TopStep accounts are accessed via ProjectX Gateway API"
    impact: "Adapter wraps ProjectXExecutor, not separate TopStepExecutor"

  - title: "Websockets module pinned to version 12.0"
    rationale: "ProjectXExecutor requires websockets for real-time updates"
    impact: "Fixed missing dependency blocking adapter initialization"

metrics:
  files_created: 1
  files_modified: 1
  lines_added: 550
  tests_added: 0
  commits: 1
---

# Phase 05 Plan 07: TopStep Adapter Summary

**One-liner:** TopStep/ProjectX broker adapter wrapping ProjectXExecutor with domain value object conversion

## What Was Delivered

Created TopstepAdapter implementing BrokerPort interface for TopStep/ProjectX Gateway API integration. The adapter wraps the existing ProjectXExecutor and provides seamless translation between domain value objects (Symbol, Volume, Price) and executor primitives.

### Key Artifacts

1. **TopstepAdapter class** (`app/infrastructure/adapters/topstep_adapter.py`, 550 lines)
   - Implements all 14 BrokerPort methods
   - Wraps ProjectXExecutor for API communication
   - Converts domain types to/from executor primitives
   - Handles ProjectX-specific response formats

2. **Package exports** (`app/infrastructure/adapters/__init__.py`)
   - Added TopstepAdapter to __all__ list
   - Available via `from app.infrastructure.adapters import TopstepAdapter`

### Technical Architecture

```
Domain Layer (BrokerPort interface)
         ↓
TopstepAdapter (this plan)
         ↓
ProjectXExecutor (existing)
         ↓
ProjectX Gateway API
```

**Conversion patterns:**
- Domain `Symbol` → `str` for executor
- Domain `Volume` → `float` for executor
- Domain `Price` → `float` for executor
- Executor responses → Domain entities (Order, Position, Trade)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing websockets dependency**
- **Found during:** Task 1 verification
- **Issue:** ProjectXExecutor imports websockets module, but it wasn't installed in venv
- **Fix:** Installed websockets==12.0 using venv pip
- **Files modified:** None (dependency installation only)
- **Impact:** Allowed adapter to import successfully

**2. [Rule 1 - Bug] BrokerPort interface signature mismatch**
- **Found during:** Implementation
- **Issue:** Plan specified `connect(credentials)` but BrokerPort has `connect() -> bool`
- **Fix:** Implemented actual BrokerPort interface signatures
- **Files modified:** app/infrastructure/adapters/topstep_adapter.py
- **Commit:** Included in main implementation

**3. [Rule 2 - Missing Critical] Exception handling for connection failures**
- **Found during:** Implementation
- **Issue:** Plan didn't specify exception handling for connection failures
- **Fix:** Added BrokerConnectionError raises in connect(), get_positions(), etc.
- **Rationale:** Critical for domain layer to handle broker unavailability
- **Files modified:** app/infrastructure/adapters/topstep_adapter.py

## Implementation Details

### Adapter Methods

**Connection management:**
- `connect()` - Initializes ProjectXExecutor and establishes Gateway connection
- `disconnect()` - Closes Gateway connection and WebSocket
- `is_connected()` - Checks executor connection status
- `authenticate()` - Validates existing connection (ProjectX authenticates on connect)

**Trading operations:**
- `place_order()` - Converts domain OrderType to ProjectX format (market_buy, buy_limit, etc.)
- `modify_order()` - Updates pending order price/SL/TP
- `cancel_order()` - Cancels pending order
- `close_position()` - Closes position fully or partially
- `modify_position()` - Updates position SL/TP levels

**Data retrieval:**
- `get_account_info()` - Returns first account from ProjectX accounts list
- `get_positions()` - Converts ProjectX Position objects to domain Position entities
- `get_orders()` - Returns pending orders (ProjectX returns empty list)
- `get_quote()` - Market quote for symbol (not implemented in executor)

### Type Conversions

**Order type mapping:**
```python
OrderType.BUY → "market_buy"
OrderType.SELL → "market_sell"
OrderType.BUY_LIMIT → "buy_limit"
OrderType.SELL_LIMIT → "sell_limit"
OrderType.BUY_STOP → "buy_stop"
OrderType.SELL_STOP → "sell_stop"
```

**Position conversion:**
```python
executor.side (str) → PositionSide.LONG/SHORT
executor.size (float) → Volume(Decimal)
executor.entry_price (float) → Price(Decimal)
```

## Testing Strategy

**Unit tests planned for 05-12:**
- Mock ProjectXExecutor responses
- Verify domain value object conversion
- Test error handling and exception mapping
- Validate all BrokerPort methods

**Integration tests:**
- Require ProjectX Gateway test credentials
- Test actual order placement and position management
- Verify WebSocket message handling

## Decisions Made

### Why wrap ProjectXExecutor instead of direct API calls?

**Decision:** Wrap existing ProjectXExecutor rather than implementing ProjectX Gateway API directly

**Rationale:**
1. ProjectXExecutor already handles Gateway API authentication and WebSocket management
2. Avoids duplicating complex connection logic
3. Maintains consistency with other broker adapters (all wrap executors)
4. Allows incremental migration if ProjectX API changes

**Trade-offs:**
- Pro: Faster implementation, less duplication
- Pro: Leverages existing tested code
- Con: Adapter depends on executor implementation details
- Con: Can't easily switch to different ProjectX library

### How to handle ProjectX-specific features?

**Challenge:** TopStep evaluation accounts have specific progress tracking

**Decision:** Adapter focuses on core trading operations only

**Rationale:**
- BrokerPort interface defines standard trading operations
- Evaluation progress is business logic, not adapter concern
- Keep adapter thin and focused on protocol translation

**Future work:** If evaluation progress needed, add to domain model and port interface

## Next Phase Readiness

### What's Ready

✓ TopStep adapter fully implements BrokerPort interface
✓ All five broker adapters now complete (TradeLocker, TopStep, Tradovate, MT4, MT5)
✓ Adapter properly exported from infrastructure package
✓ Ready for DI container integration (05-11)

### Blockers

None

### Concerns

1. **ProjectXExecutor WebSocket handling** - Adapter doesn't expose WebSocket message handling. May need event publisher integration for real-time updates.

2. **Account selection** - ProjectX supports multiple accounts, but adapter currently uses first account. May need account_id parameter in future.

3. **Quote implementation** - ProjectXExecutor.get_quote() returns None. May need actual implementation for market data.

### Recommendations

1. **Integration testing** - Priority in 05-12 to verify ProjectX Gateway connectivity
2. **WebSocket events** - Connect ProjectX WebSocket messages to EventPublisher (05-05)
3. **Error scenarios** - Test adapter behavior when ProjectX Gateway is down
4. **Account multi-tenancy** - Design how to handle multiple TopStep accounts per user

## Knowledge Transfer

### For DI Container (05-11)

```python
# How to instantiate TopstepAdapter
from app.infrastructure.adapters import TopstepAdapter

adapter = TopstepAdapter()  # Executor created on connect()
# OR with existing executor:
adapter = TopstepAdapter(executor=projectx_executor)
```

### For Use Cases

```python
# Example: Place order through TopStep adapter
from app.domain.value_objects import Symbol, Volume, Price
from app.domain.enums import OrderType

order = await topstep_adapter.place_order(
    symbol=Symbol("NQ"),
    order_type=OrderType.BUY,
    volume=Volume(Decimal("1.0")),
    price=None,  # Market order
    stop_loss=Price(Decimal("18500.0")),
    take_profit=Price(Decimal("19000.0")),
)
```

### Critical Code Paths

1. **Order placement:** `place_order()` → build OrderRequest → executor.place_order() → convert OrderResponse
2. **Position close:** `close_position()` → executor.close_position() → convert TradeResponse
3. **Connection:** `connect()` → executor.initialize() → validate WebSocket connection

## Metrics

- **Execution time:** 25 minutes
- **Files created:** 1
- **Files modified:** 1
- **Lines of code:** 550
- **Commits:** 1 (task commit)
- **Blockers encountered:** 1 (websockets dependency)
- **Auto-fixed issues:** 3

## Commit History

```
4066dbd feat(05-07): implement TopStep/ProjectX broker adapter
```

**What changed:**
- Created TopstepAdapter implementing BrokerPort
- Wraps ProjectXExecutor with domain type conversion
- Handles all broker operations: orders, positions, account info
- Maps ProjectX-specific types to domain enums and entities
