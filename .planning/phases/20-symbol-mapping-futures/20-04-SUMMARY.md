---
phase: 20-symbol-mapping-futures
plan: 04
subsystem: futures, contracts, trading
tags: [futures, contracts, expiration, rollover, CME, TopStep, ProjectX]

# Dependency graph
requires:
  - phase: 20-01
    provides: Symbol normalization service for futures code detection
  - phase: 17-01
    provides: TopStep/ProjectX SDK integration for futures trading
provides:
  - FuturesContract domain model and database tables
  - Contract code parsing (NQH25 -> NQ + March + 2025)
  - Expiration date calculation (third Friday for indices)
  - Contract rollover detection and next contract determination
  - User contract position tracking
  - Expiration notification system
  - Dashboard expiration alerts UI
affects: [risk-management, trading-signals, account-management]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Domain entity with validation for futures contracts
    - Service pattern for contract lifecycle management
    - Use case pattern for scheduled expiration checks
    - BFF pattern for contract data in dashboard

key-files:
  created:
    - app/domain/entities/futures_contract.py
    - app/domain/services/futures_contract_service.py
    - app/domain/services/contract_tracker.py
    - app/application/use_cases/check_contract_expirations.py
    - app/routers/contracts.py
    - ui-next/src/components/positions/expiration-badge.tsx
    - ui-next/src/app/api/dashboard/contracts/route.ts
    - alembic/versions/008_add_futures_contracts.py
    - tests/test_futures_contracts.py
  modified:
    - app/main.py
    - app/models/models.py
    - ui-next/src/app/dashboard/page.tsx

key-decisions:
  - "Third Friday expiration for equity index futures (ES, NQ, YM, RTY)"
  - "Quarterly month codes H, M, U, Z for index futures"
  - "3-day default rollover window before expiration"
  - "Notification tiers: warning (7d), urgent (3d), critical (1d)"

patterns-established:
  - "Contract code parsing with regex for various formats (NQH25, ESM2025)"
  - "ExpiringPosition dataclass for position tracking"
  - "RolloverSuggestion with urgency levels"

# Metrics
duration: 5min
completed: 2026-01-21
---

# Phase 20 Plan 04: Futures Contract Support Summary

**Futures contract expiration tracking with CME month codes, third-Friday expiration calculation, rollover detection, and dashboard alerts for TopStep/ProjectX brokers**

## Performance

- **Duration:** 5 min (mostly completed by prior work, Task 5 completion)
- **Started:** 2026-01-21T23:33:26Z
- **Completed:** 2026-01-21T23:38:55Z
- **Tasks:** 5
- **Files modified:** 12

## Accomplishments

- FuturesContract domain model with validation and expiration properties
- Contract code parsing supporting NQH25, ESM2025, YMU5 formats
- Expiration calculation for equity index (third Friday) and commodity futures
- Quarterly/monthly next contract determination with year rollover
- User contract position tracking per account
- Expiration check use case for scheduled notifications
- Dashboard UI with ExpirationAlerts component showing warnings
- Comprehensive test suite with 32 passing tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Create FuturesContract domain model** - `bb6fa86` (feat)
2. **Task 2: Create FuturesContractService** - `e10129f` (feat)
3. **Task 3: Create contract expiration tracking** - `d16262f` (feat)
4. **Task 4: Create rollover notification system** - `029ba24` (feat)
5. **Task 5: Add futures UI indicators** - `f334042` (feat)

## Files Created/Modified

**Created:**
- `app/domain/entities/futures_contract.py` - FuturesContract dataclass with validation
- `app/domain/services/futures_contract_service.py` - Contract parsing, expiration calc, next contract
- `app/domain/services/contract_tracker.py` - Position tracking, expiring position detection
- `app/application/use_cases/check_contract_expirations.py` - Scheduled notification use case
- `app/routers/contracts.py` - API endpoints for contract operations
- `ui-next/src/components/positions/expiration-badge.tsx` - ExpirationBadge, ExpirationAlerts components
- `ui-next/src/app/api/dashboard/contracts/route.ts` - BFF endpoint for expiring contracts
- `alembic/versions/008_add_futures_contracts.py` - Database migration
- `tests/test_futures_contracts.py` - 32 comprehensive tests

**Modified:**
- `app/models/models.py` - Added FuturesContract and UserContractPosition models
- `app/main.py` - Registered contracts router
- `ui-next/src/app/dashboard/page.tsx` - Added expiration alerts card

## Decisions Made

1. **Third Friday expiration for equity indices** - Standard CME practice for ES, NQ, YM, RTY
2. **Month code mapping from CME standard** - F(Jan) through Z(Dec) with quarterly H, M, U, Z
3. **3-day default rollover window** - Typical institutional practice before expiration
4. **Three notification tiers** - warning (7d), urgent (3d), critical (1d) for escalating urgency
5. **Graceful degradation in UI** - Empty array returned on API errors, dashboard still functional

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all implementations followed the plan specifications.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Futures contract support complete for TopStep/ProjectX brokers
- Symbol normalization + futures contracts provides full symbol handling for futures
- Phase 20 (Symbol Mapping & Futures) complete
- Ready for Phase 21 (Multi-Account & Routing)

---
*Phase: 20-symbol-mapping-futures*
*Plan: 04*
*Completed: 2026-01-21*
