---
phase: 05-infrastructure-adapters
plan: 06
subsystem: infra
tags: [tradelocker, broker-adapter, hexagonal-architecture, domain-ports]

# Dependency graph
requires:
  - phase: 05-01
    provides: Infrastructure package structure
  - phase: 05-02
    provides: Entity mappers for ORM conversion
  - phase: 03-05
    provides: BrokerPort interface definition
  - phase: 03-02
    provides: Domain enums and value objects
provides:
  - TradeLocker broker adapter implementing BrokerPort interface
  - Domain-to-executor type conversion for TradeLocker operations
  - TradeLocker-specific authentication and connection handling
affects: [05-11-DI-Container, 06-api-layer, application-services]

# Tech tracking
tech-stack:
  added: [python-socketio==5.10.0]
  patterns: [broker-adapter-pattern, domain-executor-wrapper]

key-files:
  created:
    - app/infrastructure/adapters/tradelocker_adapter.py
  modified:
    - app/infrastructure/adapters/__init__.py

key-decisions:
  - "TradeLockerAdapter wraps existing TradeLockerExecutor rather than duplicating API integration"
  - "Domain value objects (Symbol, Volume, Price) converted to primitives at adapter boundary"
  - "Executor responses converted back to domain entities (Order, Position, Trade)"
  - "TradeLocker authenticates on connect via API key (no separate auth step)"
  - "Account ID stored in adapter instance for tracking executor calls"

patterns-established:
  - "Broker adapters implement BrokerPort and wrap existing executor implementations"
  - "Type conversion happens at adapter boundary: domain objects → primitives → executor → domain entities"
  - "Adapters handle broker-specific exception mapping to domain exceptions"

# Metrics
duration: 25min
completed: 2026-01-20
---

# Phase 5 Plan 6: TradeLocker Adapter Summary

**TradeLocker broker adapter wrapping TradeLockerExecutor with domain-typed BrokerPort interface for hexagonal architecture compliance**

## Performance

- **Duration:** 25 min
- **Started:** 2026-01-20T06:47:12Z
- **Completed:** 2026-01-20T07:12:37Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Implemented TradeLockerAdapter conforming to BrokerPort interface
- Wrapped existing TradeLockerExecutor with domain value object conversions
- Enabled domain layer to interact with TradeLocker via pure domain types
- Established broker adapter pattern for remaining broker integrations

## Task Commits

Each task was committed atomically:

1. **Task 1: Create TradeLocker adapter** - `31c90bd` (feat)
2. **Task 2: Add adapter to exports** - `a3d70cf` (chore - already complete)

**Plan metadata:** (to be added in final commit)

## Files Created/Modified
- `app/infrastructure/adapters/tradelocker_adapter.py` - TradeLocker BrokerPort implementation wrapping TradeLockerExecutor
- `app/infrastructure/adapters/__init__.py` - Export TradeLockerAdapter for package access

## Decisions Made

**1. Wrap executor rather than duplicate API integration**
- TradeLockerAdapter delegates to TradeLockerExecutor for all API calls
- Adapter focuses solely on type conversion between domain and executor
- Preserves existing, tested TradeLocker integration logic

**2. Convert domain types at adapter boundary**
- Domain value objects (Symbol, Volume, Price) converted to primitives (str, float)
- Executor responses (dicts, Pydantic models) converted to domain entities
- Clean separation: domain layer never sees primitives, executor never sees domain types

**3. Store account_id in adapter instance**
- TradeLocker executor methods require account_id parameter
- BrokerPort interface doesn't expose account_id in all methods
- Adapter stores account_id from authenticate() call for subsequent operations

**4. Map between domain and executor enums**
- Domain OrderType (BUY, SELL, BUY_LIMIT) → Executor strings ("market_buy", "buy_limit")
- Domain OrderStatus (PENDING, EXECUTED) → Executor strings ("pending", "filled")
- Explicit mapping dictionaries for clarity and maintainability

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing python-socketio dependency**
- **Found during:** Task 1 (TradeLocker adapter import)
- **Issue:** TradeLockerExecutor imports socketio module, but python-socketio not installed in venv despite being in requirements.txt
- **Fix:** Activated venv and ran `pip install python-socketio==5.10.0`
- **Files modified:** None (venv only)
- **Verification:** Import succeeds, adapter instantiates without error
- **Committed in:** (not committed - venv installation)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Dependency installation necessary for import. No scope creep.

## Issues Encountered

**Issue: Task 2 already completed in prior execution**
- __init__.py already had TradeLockerAdapter export from commit c86091b (plan 05-08)
- Other broker adapters (TopStep, Tradovate, MT4, MT5) also already implemented
- Created empty commit to document Task 2 completion status
- All verification checks pass

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready:**
- TradeLocker adapter implements full BrokerPort interface
- Adapter pattern established for remaining broker adapters (TopStep, Tradovate, MT4, MT5)
- Domain layer can now interact with TradeLocker through ports

**Next steps:**
- DI Container (Plan 05-11) can inject TradeLockerAdapter where BrokerPort is needed
- Application services can use BrokerPort interface without knowing about TradeLocker specifics
- Similar adapters for other brokers follow same pattern

**No blockers or concerns.**

---
*Phase: 05-infrastructure-adapters*
*Completed: 2026-01-20*
