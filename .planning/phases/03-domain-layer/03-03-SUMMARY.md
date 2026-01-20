---
phase: 03-domain-layer
plan: 03
subsystem: domain
tags: [domain-entities, business-logic, signal, trade, order]

# Dependency Graph
requires:
  - 03-02  # Domain enums and value objects
provides:
  - Signal entity with validation and state transitions
  - Trade entity with lifecycle and P&L calculations
  - Order entity with fill tracking and validation
affects:
  - 03-04  # Repository ports will use these entities
  - 03-05  # Domain services will orchestrate these entities

# Tech Stack
tech-stack:
  added: []
  patterns:
    - Rich domain entities with business logic
    - State machine pattern for signal lifecycle
    - Immutable value objects for type safety

# File Tracking
key-files:
  created:
    - app/domain/entities/signal.py
    - app/domain/entities/trade.py
    - app/domain/entities/order.py
  modified:
    - app/domain/entities/__init__.py

# Decisions
decisions:
  - id: filled_volume_as_decimal
    title: "Use Decimal for filled_volume instead of Volume value object"
    rationale: "Volume value object requires positive values, but filled_volume starts at zero"
    context: "Order entity needs to track zero filled volume for new orders"
    alternatives: "Could use Optional[Volume], but Decimal is simpler and more direct"

# Metrics
duration: 7m 13s
completed: 2026-01-20
---

# Phase 03 Plan 03: Trading Domain Entities Summary

**One-liner:** Created Signal, Trade, and Order entities with rich business logic, validation, and state transitions using domain primitives.

## What Was Built

### Signal Entity
Created `app/domain/entities/signal.py` with:
- Signal lifecycle management (PENDING → PROCESSING → PROCESSED/FAILED/SKIPPED)
- Validation rules:
  - BUY/SELL actions require volume
  - Stop loss placement validation for BUY (below entry) and SELL (above entry)
- State transition methods: `mark_processing()`, `mark_processed()`, `mark_failed()`, `mark_skipped()`
- Target account management with `add_target_account()`
- Properties: `is_pending`, `is_processed`, `is_failed`

### Trade Entity
Created `app/domain/entities/trade.py` with:
- Trade lifecycle management (OPEN → CLOSED/PARTIALLY_CLOSED)
- Methods:
  - `close()`: Close entire trade at specified price
  - `partial_close()`: Close portion and return new Trade for closed part
  - `update_sl_tp()`: Modify stop loss and take profit levels
- Profit/Loss calculation:
  - Calculates P&L based on price difference and order type (BUY/SELL)
  - Accounts for commission and swap costs
  - Stores as Money value object with currency
- Properties: `is_open`, `is_closed`, `is_profitable`

### Order Entity
Created `app/domain/entities/order.py` with:
- Order validation:
  - Limit/Stop orders require price (enforced in `__post_init__`)
- Fill tracking:
  - `filled_volume` as Decimal (allows zero for unfilled orders)
  - `fill()`: Record partial or complete fills, update status
  - `remaining_volume` property for unfilled portion
- Lifecycle methods:
  - `cancel()`: Cancel pending order (blocks executed orders)
  - `reject()`: Mark order as rejected with reason
  - `modify()`: Update price, SL, TP for pending orders
- Status tracking: PENDING, EXECUTED, CANCELLED, REJECTED, PARTIALLY_FILLED
- Properties: `is_pending`, `is_filled`, `is_market_order`

### Entity Exports
Updated `app/domain/entities/__init__.py` to export Signal, Trade, and Order entities for convenient importing.

## Technical Approach

### Domain Purity
All entities:
- Use only domain primitives (value objects and enums from app.domain)
- Zero framework dependencies (no FastAPI, SQLAlchemy, etc.)
- Enforce business invariants in constructors and methods
- Raise domain exceptions for business rule violations

### Design Patterns
- **Rich Domain Model**: Entities contain behavior, not just data
- **State Machine**: Signal has explicit state transitions with validation
- **Value Objects**: Leverage frozen dataclasses for type safety (Symbol, Volume, Price, Money)
- **Business Rule Enforcement**: Invalid operations raise BusinessRuleViolation exceptions

### Validation Strategy
- Constructor validation via `__post_init__()` for structural invariants
- Method validation for state-dependent operations
- Clear error messages with context dictionaries

## Key Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `app/domain/entities/signal.py` | Created Signal entity | 108 |
| `app/domain/entities/trade.py` | Created Trade entity | 131 |
| `app/domain/entities/order.py` | Created Order entity | 135 |
| `app/domain/entities/__init__.py` | Export new entities | +6 |

## Decisions Made

### 1. filled_volume as Decimal (not Volume value object)
**Context:** Order entity needs to track filled volume starting from zero.

**Problem:** Volume value object requires positive values (cannot be zero), but unfilled orders have zero filled volume.

**Decision:** Use `Decimal` for `filled_volume` instead of `Volume`.

**Rationale:**
- Allows zero value for unfilled orders
- Simpler than Optional[Volume] with None handling
- Still provides precision for financial calculations
- Can easily convert to Volume when needed for comparisons

**Alternatives Considered:**
- Optional[Volume]: More complex, requires None checks everywhere
- Custom FilledVolume value object: Overkill for this simple case

### 2. BusinessRuleViolation signature adjustment
**Context:** Existing BusinessRuleViolation requires both rule name and message.

**Problem:** In Signal entity, needed to pass rule identifier for consistent exception handling.

**Decision:** Updated all BusinessRuleViolation calls to include rule identifier (e.g., "cannot_process_signal").

**Impact:** More consistent exception handling and better debugging with explicit rule names.

## Verification Results

All verification checks passed:

✅ Signal entity imports successfully
✅ Trade entity imports successfully
✅ Order entity imports successfully
✅ No framework imports (FastAPI/SQLAlchemy) in domain entities
✅ Signal validates BUY/SELL requires volume
✅ Trade has `close()` and `partial_close()` methods
✅ Order validates limit orders require price

### Test Output
```bash
# Signal validation test
PASS: Signal validates BUY requires volume

# Trade lifecycle methods test
PASS: Trade has close() method
PASS: Trade has partial_close() method

# Order validation test
PASS: Order validates limit orders require price
```

## Deviations from Plan

None - plan executed exactly as written. All three entities created with required functionality and validation.

## Integration Points

### Upstream Dependencies (Required)
- `app/domain/enums`: SignalSource, SignalAction, SignalStatus, OrderType, OrderStatus, TradeStatus
- `app/domain/value_objects`: SignalId, Symbol, Volume, Price, Money, StopLoss, TakeProfit, AccountId, OrderId
- `app/domain/exceptions`: ValidationError, BusinessRuleViolation, SignalValidationError

### Downstream Consumers (Will Use)
- **Plan 03-04** (Repository Ports): Will define interfaces for persisting these entities
- **Plan 03-05** (Domain Services): Will orchestrate signal processing, trade execution, order management
- **Infrastructure Layer**: Will map entities to/from SQLAlchemy models
- **Application Layer**: Will use entities in use cases and API handlers

## Next Phase Readiness

**Status:** ✅ Ready for Plan 03-04 (Repository Ports)

**What's Next:**
- Define repository port interfaces for Signal, Trade, Order
- Define broker port interfaces for order execution and trade management
- Continue building domain layer without framework dependencies

**Blockers:** None

**Concerns:** None - all entities tested and working correctly with domain primitives.

## Artifacts

### Commits (in order)
1. `81f5f1c` - feat(03-03): create Signal domain entity
2. `ce9d866` - feat(03-03): create Trade domain entity
3. `5e23b48` - feat(03-03): create Order domain entity
4. `b3fbf3e` - feat(03-03): export new entities in __init__.py

### Lines of Code
- Signal: 108 lines
- Trade: 131 lines
- Order: 135 lines
- Total: 374 lines of domain logic

---

**Generated:** 2026-01-20
**Duration:** 7 minutes 13 seconds
**Status:** ✅ Complete
