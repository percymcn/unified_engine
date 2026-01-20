---
phase: 05-infrastructure-adapters
plan: 02
subsystem: infrastructure
tags: [sqlalchemy, orm, mappers, domain-entities, value-objects, hexagonal-architecture]

# Dependency graph
requires:
  - phase: 03-domain-layer
    provides: Domain entities (Signal, Trade, Account, Position, Order) with value objects
  - phase: 05-01
    provides: Infrastructure package structure
provides:
  - Bidirectional mappers for all 5 entity types (Signal, Trade, Account, Position, Order)
  - ORM ↔ domain conversion handling value objects and enums
  - Mapper package with clean public API
affects:
  - 05-03-sqlalchemy-repositories (will use these mappers)
  - 05-04-unit-of-work (repositories depend on mappers)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mapper pattern for ORM/domain isolation"
    - "Bidirectional conversion with to_entity() and to_model()"
    - "Value object conversion (Symbol, Volume, Price, Money)"
    - "Enum mapping between ORM and domain types"

key-files:
  created:
    - app/infrastructure/mappers/__init__.py
    - app/infrastructure/mappers/signal_mapper.py
    - app/infrastructure/mappers/trade_mapper.py
    - app/infrastructure/mappers/account_mapper.py
    - app/infrastructure/mappers/position_mapper.py
    - app/infrastructure/mappers/order_mapper.py
  modified: []

key-decisions:
  - "Mappers handle field name differences (quantity→volume, entry_price→open_price)"
  - "Enum mapping uses explicit dictionaries for clarity and maintainability"
  - "Money value objects use abs() for non-negative constraint, preserve sign in calculations"
  - "Status inference from timestamps when ORM lacks explicit status field (Trade)"
  - "OrderType combines ORM OrderType + OrderSide (MARKET+BUY → BUY)"

patterns-established:
  - "Static methods for mapper operations (no instance state needed)"
  - "Optional orm_model parameter in to_model() for update vs create"
  - "Private helper methods for enum mapping (_map_status_to_domain, etc.)"
  - "Handle None/Optional fields gracefully with conditional value object creation"

# Metrics
duration: 9min
completed: 2026-01-20
---

# Phase 5 Plan 2: Entity Mappers Summary

**Bidirectional ORM ↔ domain mappers for Signal, Trade, Account, Position, Order with value object and enum conversion**

## Performance

- **Duration:** 9 min 15 sec
- **Started:** 2026-01-20T06:13:37Z
- **Completed:** 2026-01-20T06:22:52Z
- **Tasks:** 7
- **Files modified:** 6 created

## Accomplishments

- Created 5 entity mappers with bidirectional conversion (to_entity, to_model)
- Implemented value object conversion (Symbol, Volume, Price, Money, StopLoss, TakeProfit)
- Mapped enum types between ORM (SQLAlchemy Enum) and domain (str, Enum)
- Handled field name mismatches (quantity→volume, entry_price→open_price, etc.)
- Established mapper package with clean public API

## Task Commits

Each task was committed atomically:

1. **Task 1: Create mappers package** - `a2abff4` (chore)
2. **Task 2: Create Signal mapper** - `1b7cf7d` (feat)
3. **Task 3: Create Trade mapper** - `dcb8910` (feat)
4. **Task 4: Create Account mapper** - `8f37085` (feat)
5. **Task 5: Create Position mapper** - `585352d` (feat)
6. **Task 6: Create Order mapper** - `af532a1` (feat)
7. **Task 7: Update mappers __init__ with exports** - `e101f60` (feat)

## Files Created/Modified

- `app/infrastructure/mappers/__init__.py` - Package exports for all mappers
- `app/infrastructure/mappers/signal_mapper.py` - Signal ORM ↔ domain conversion
- `app/infrastructure/mappers/trade_mapper.py` - Trade ORM ↔ domain conversion
- `app/infrastructure/mappers/account_mapper.py` - Account ORM ↔ domain conversion
- `app/infrastructure/mappers/position_mapper.py` - Position ORM ↔ domain conversion
- `app/infrastructure/mappers/order_mapper.py` - Order ORM ↔ domain conversion

## Decisions Made

**1. Field name mapping strategy**
- ORM uses different field names than domain (quantity vs volume, entry_price vs open_price)
- Mappers handle translation transparently
- Rationale: Maintains domain language purity while adapting to existing ORM schema

**2. Enum conversion via explicit dictionaries**
- Created mapping dictionaries for each enum type (SignalStatus, OrderType, BrokerType, etc.)
- Separate methods for to_domain and to_orm conversions
- Rationale: Clear, maintainable, easy to debug vs dynamic mapping

**3. Money value object handling**
- Money requires non-negative amounts, but P&L can be negative
- Use abs() for Money creation, preserve sign in Decimal calculations
- Rationale: Respects domain invariants while handling real-world scenarios

**4. Status inference from timestamps**
- Trade ORM lacks status field, infer from closed_at timestamp
- Position uses PositionStatus.OPEN ↔ is_active mapping
- Rationale: Work with existing ORM schema without modifications

**5. OrderType combination**
- ORM has separate OrderType (MARKET/LIMIT/STOP) and OrderSide (BUY/SELL)
- Domain has combined OrderType (BUY/SELL/BUY_LIMIT/SELL_LIMIT/BUY_STOP/SELL_STOP)
- Mappers combine/split as needed
- Rationale: Domain model is more expressive, ORM model is normalized

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - mappers implemented cleanly following domain and ORM specifications.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for next phase (05-03 SQLAlchemy Repositories):**
- All 5 entity mappers complete and tested
- Bidirectional conversion verified
- Value object and enum mapping working
- Clean public API via package exports

**What repositories will use:**
- SignalMapper for signal persistence
- TradeMapper for trade history
- AccountMapper for account state
- PositionMapper for open positions
- OrderMapper for order tracking

**No blockers or concerns.**

---
*Phase: 05-infrastructure-adapters*
*Completed: 2026-01-20*
