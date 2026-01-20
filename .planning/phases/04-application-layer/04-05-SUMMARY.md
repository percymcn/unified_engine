---
phase: 04-application-layer
plan: 05
subsystem: application
tags: [use-cases, accounts, hexagonal-architecture, dto]

# Dependency graph
requires:
  - phase: 03-domain-layer
    provides: Account entity, repository ports, broker ports
  - phase: 04-02
    provides: Account DTOs for request/response contracts
provides:
  - Account query use cases (GetAccountsUseCase, GetAccountUseCase)
  - Account connection use case (ConnectAccountUseCase)
  - Account sync use case (SyncAccountUseCase)
affects: [04-06-application-services, 05-adapters, api-layer]

# Tech tracking
tech-stack:
  added: []
  patterns: [account-connection-pattern, broker-sync-pattern]

key-files:
  created:
    - app/application/use_cases/manage_accounts.py
  modified:
    - app/application/use_cases/__init__.py

key-decisions:
  - "ConnectAccountUseCase retrieves broker account info and updates account state in single operation"
  - "SyncAccountUseCase counts positions and orders from broker for summary statistics"
  - "GetAccountsUseCase supports filtering by broker type and active status"
  - "All account use cases return error DTOs instead of raising exceptions for graceful degradation"

patterns-established:
  - "Account connection pattern: connect broker, update state, fetch info, save"
  - "Broker sync pattern: verify connection, fetch data, update entities, return counts"
  - "Query filtering pattern: support optional filters (broker, active_only) in list use cases"

# Metrics
duration: 2min
completed: 2026-01-20
---

# Phase 04 Plan 05: Account Use Cases Summary

**Four account management use cases with broker connection, sync, and query capabilities using DTO-in/DTO-out pattern**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-20T04:25:24Z
- **Completed:** 2026-01-20T04:27:36Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- GetAccountsUseCase for listing user accounts with broker and active status filtering
- GetAccountUseCase for retrieving single account details as DTO
- ConnectAccountUseCase for connecting accounts to brokers with state synchronization
- SyncAccountUseCase for refreshing account data from broker including positions/orders counts

## Task Commits

Each task was committed atomically:

1. **Task 1: Create account management use cases** - `5e99623` (feat)
   - GetAccountsUseCase with filtering by broker and active status
   - GetAccountUseCase for single account retrieval
   - ConnectAccountUseCase with broker connection and account info sync
   - SyncAccountUseCase with position/order counting
   - Error handling with graceful degradation to error DTOs

2. **Task 2: Update use cases package exports** - `228a951` (feat)
   - Export all four account use cases from package
   - Group exports by domain area (signal, trade, account)

## Files Created/Modified
- `app/application/use_cases/manage_accounts.py` - Four account management use cases with query, connection, and sync capabilities
- `app/application/use_cases/__init__.py` - Added account use case exports

## Decisions Made

1. **ConnectAccountUseCase retrieves broker account info immediately after connection**
   - Rationale: Ensures account state is synchronized with broker immediately upon connection
   - Updates balance, equity, and margin in single atomic operation

2. **SyncAccountUseCase includes position and order counts**
   - Rationale: Provides summary statistics without requiring separate repository queries
   - Fetches counts from broker during sync for real-time accuracy

3. **GetAccountsUseCase supports filtering by broker and active status**
   - Rationale: Common query patterns for listing accounts (e.g., "show my active MT4 accounts")
   - Filter logic applied after repository fetch to keep repository interface simple

4. **All account use cases return error DTOs instead of raising exceptions**
   - Rationale: Follows pattern established in 04-04 for graceful degradation
   - ConnectAccountUseCase catches AccountNotFoundError, AccountDisabledError, BrokerConnectionError

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for:**
- Phase 04-06: Application Services integration layer can compose these use cases
- Phase 05: Adapter implementations can provide concrete BrokerPort and Repository implementations
- API layer can expose these use cases as HTTP endpoints

**Provides:**
- Complete account use case coverage (query, connect, sync)
- DTO contracts for account operations
- Broker connection patterns for adapters to implement

**Dependencies satisfied:**
- Depends on domain Account entity (available from 03-04)
- Depends on AccountRepository, BrokerPort interfaces (available from 03-05)
- Depends on Account DTOs (available from 04-02)

---
*Phase: 04-application-layer*
*Completed: 2026-01-20*
