---
phase: 04-application-layer
plan: 04
subsystem: application
tags: [use-cases, dtos, trade-execution, position-management, hexagonal-architecture]

# Dependency graph
requires:
  - phase: 03-domain-layer
    provides: TradeService, domain entities, ports, exceptions
  - phase: 04-01
    provides: Application package structure
  - phase: 04-02
    provides: Trade DTOs (PlaceOrderRequest, ClosePositionRequest, etc.)
provides:
  - PlaceOrderUseCase for order placement
  - ClosePositionUseCase for closing positions
  - ModifyPositionUseCase for SL/TP modifications
  - GetPositionsUseCase for querying open positions
  - GetTradesUseCase for trade history
affects: [04-06-application-services, 05-infrastructure-layer, 08-api-layer]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "DTO-in/DTO-out pattern for all use cases"
    - "Use cases validate account state before delegating to domain"
    - "Use cases instantiate domain services with injected ports"
    - "Error mapping from domain exceptions to DTO responses"

key-files:
  created:
    - app/application/use_cases/place_order.py
    - app/application/use_cases/manage_positions.py
  modified:
    - app/application/use_cases/__init__.py

key-decisions:
  - "PlaceOrderUseCase validates account is_active and is_connected before placing orders"
  - "ClosePositionUseCase supports partial closes via optional volume parameter"
  - "ModifyPositionUseCase and GetPositionsUseCase don't instantiate TradeService (simpler dependencies)"
  - "Use cases return error DTOs instead of raising exceptions for business rule violations"

patterns-established:
  - "Pattern 1: Use cases accept DTOs, convert to domain types, delegate to services, return DTOs"
  - "Pattern 2: Use cases handle domain exceptions and map to error responses in DTOs"
  - "Pattern 3: Read-only use cases (GetPositions, GetTrades) go directly to repositories"

# Metrics
duration: 5min
completed: 2026-01-20
---

# Phase 4 Plan 4: Trade Use Cases Summary

**Trade execution use cases with account validation, partial position closes, and DTO-based error handling**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-20T04:16:04Z
- **Completed:** 2026-01-20T04:21:22Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- PlaceOrderUseCase orchestrates order placement with account state validation
- Position management use cases (close, modify, query) with proper error handling
- All use cases follow DTO-in/DTO-out pattern with no infrastructure dependencies
- Error mapping from domain exceptions to user-friendly DTO responses

## Task Commits

Each task was committed atomically:

1. **Task 1: Create PlaceOrderUseCase** - `3772169` (feat)
2. **Task 2: Create position management use cases** - `7a2e1da` (feat)
3. **Task 3: Update use cases package exports** - `d22dc94` (feat)

## Files Created/Modified
- `app/application/use_cases/place_order.py` - PlaceOrderUseCase with account validation
- `app/application/use_cases/manage_positions.py` - ClosePositionUseCase, ModifyPositionUseCase, GetPositionsUseCase, GetTradesUseCase
- `app/application/use_cases/__init__.py` - Exports all signal and trade use cases

## Decisions Made

**Account validation before order placement:**
- PlaceOrderUseCase checks `account.is_active` and `account.is_connected` before delegating to TradeService
- Ensures orders are only placed for valid, connected accounts

**Partial position close support:**
- ClosePositionUseCase accepts optional `volume` parameter in ClosePositionRequest
- None volume = full close, specific volume = partial close

**Use case dependency patterns:**
- Write use cases (Place, Close, Modify) instantiate TradeService with all dependencies
- Read use cases (GetPositions, GetTrades) use repositories directly (simpler)

**Error handling pattern:**
- Use cases catch domain exceptions and return error DTOs instead of propagating exceptions
- Provides graceful degradation for business rule violations

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all imports and dependencies were available from prior plans.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Trade use cases complete and ready for:
- Account use cases (04-05) for account management operations
- Application services (04-06) for higher-level orchestration
- Infrastructure layer (Phase 5) for repository implementations
- API layer (Phase 8) for FastAPI endpoint integration

**Dependencies met:**
- Domain services provide trade execution logic
- DTOs provide input/output contracts
- Ports abstract infrastructure dependencies

**No blockers or concerns.**

---
*Phase: 04-application-layer*
*Completed: 2026-01-20*
