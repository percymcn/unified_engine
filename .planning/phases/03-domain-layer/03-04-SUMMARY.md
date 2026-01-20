---
phase: 03-domain-layer
plan: 04
subsystem: domain
tags: [domain-entities, account, position, margin, pnl, trading]

# Dependency graph
requires:
  - phase: 03-02
    provides: Domain enums (BrokerType, AccountType, PositionSide) and value objects (AccountId, Money, Symbol, Volume, Price, PositionId)
provides:
  - Account domain entity with margin calculations, balance management, and margin call detection
  - Position domain entity with unrealized P&L tracking and SL/TP validation
affects: [03-05-domain-services, repository-layer, trading-execution]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Entities are mutable (not frozen dataclasses) but use object.__setattr__ for state changes"
    - "Financial calculations that can be negative (free_margin, unrealized_pnl) return Decimal, not Money"
    - "Money value object enforces non-negative amounts for balances only"

key-files:
  created:
    - app/domain/entities/account.py
    - app/domain/entities/position.py
  modified:
    - app/domain/entities/__init__.py

key-decisions:
  - "Account.free_margin is a Decimal property, not Money field (can be negative during margin calls)"
  - "Position.unrealized_pnl is a Decimal property, not Money field (can be negative for losses)"
  - "Money value object remains strictly non-negative for balances; calculated values use Decimal"

patterns-established:
  - "Pattern 1: Domain entities use object.__setattr__ for state mutation"
  - "Pattern 2: Calculated financial values that can be negative are Decimal properties, not Money fields"
  - "Pattern 3: Margin level is Optional[Decimal] (None when no margin used)"

# Metrics
duration: 11min
completed: 2026-01-20
---

# Phase 3 Plan 4: Account & Position Entities Summary

**Account entity with margin call detection and Position entity with unrealized P&L tracking, using Decimal for negative financial calculations**

## Performance

- **Duration:** 11m 24s
- **Started:** 2026-01-20T03:08:21Z
- **Completed:** 2026-01-20T03:19:45Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Account entity manages balance, equity, and margin with automatic free margin calculation
- Position entity tracks open positions with real-time unrealized P&L calculation
- Margin level percentage calculation with margin call (<100%) and stop out (<50%) detection
- SL/TP validation ensures stops are on correct side of current price for LONG/SHORT positions
- All entities framework-independent (no FastAPI, SQLAlchemy, or ORM annotations)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Account entity** - `b501a25` (feat)
2. **Task 2: Create Position entity** - `b6f72ed` (feat)
3. **Export entities in __init__.py** - `97f6b10` (feat)

**Bug fix:** `ecad669` (fix: handle negative values in financial calculations)

## Files Created/Modified
- `app/domain/entities/account.py` - Account entity with balance, equity, margin management; margin call detection
- `app/domain/entities/position.py` - Position entity with unrealized P&L, SL/TP validation, partial close
- `app/domain/entities/__init__.py` - Export Account and Position entities

## Decisions Made
- **Free margin as Decimal property:** Changed from Money field to Decimal property because free margin can be negative during margin calls (when equity < margin). Money value object enforces non-negative amounts for balances.
- **Unrealized P&L as Decimal property:** Changed from Money field to Decimal property because unrealized P&L can be negative for losing positions. This maintains Money's invariant while allowing domain calculations.
- **Margin level returns Optional[Decimal]:** Returns None when margin is zero (no positions), otherwise percentage value. Enables margin call (< 100%) and stop out (< 50%) detection.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed negative free margin handling**
- **Found during:** Verification testing
- **Issue:** Account.__post_init__ called _update_free_margin() which tried to create Money with negative amount during margin calls. Money value object validates amount >= 0, causing ValidationError for valid margin call scenario (equity < margin).
- **Fix:** Changed free_margin from Money field to Decimal property that calculates equity - margin on access. This allows negative values while maintaining Money's non-negative invariant for balances.
- **Files modified:** app/domain/entities/account.py
- **Verification:** Created account with equity=9000, margin=10000; free_margin=-1000, is_margin_call=True
- **Committed in:** ecad669 (separate bug fix commit)

**2. [Rule 1 - Bug] Fixed negative unrealized P&L handling**
- **Found during:** Verification testing
- **Issue:** Position.unrealized_pnl property returned Money(total) where total could be negative for losing positions. Money value object validates amount >= 0, causing ValidationError for valid losing trade scenario.
- **Fix:** Changed unrealized_pnl from Money property to Decimal property that returns raw calculation. This allows negative P&L (losses) while maintaining Money's non-negative invariant for balances.
- **Files modified:** app/domain/entities/position.py
- **Verification:** Created position with commission > profit; unrealized_pnl correctly showed negative value; is_profitable=False
- **Committed in:** ecad669 (same bug fix commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 - Bug)
**Impact on plan:** Both auto-fixes essential for correct domain behavior. Money value object is designed for non-negative balances; calculated financial values that can be negative (free margin, unrealized P&L) correctly use Decimal. No scope creep.

## Issues Encountered
None - domain logic implemented as specified after fixing Money value object usage.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Account entity ready for repository implementation
- Position entity ready for position tracking in trading execution
- Domain entities fully isolated from infrastructure (no framework imports verified)
- Margin calculations tested and working correctly
- SL/TP validation tested for both LONG and SHORT positions

**Ready for:** Repository ports (03-05), domain services, and infrastructure layer implementation

---
*Phase: 03-domain-layer*
*Completed: 2026-01-20*
