---
phase: 19-broker-connections-ui
plan: 02
subsystem: ui
tags: [react, next.js, broker-ui, connection-status, error-handling, toast]

# Dependency graph
requires:
  - phase: 19-01
    provides: Backend connection test endpoint (/api/v1/accounts/test-connection)
provides:
  - Three-state connection status indicators (green/amber/red)
  - Test Connection button in account form
  - User-friendly error messages throughout account operations
  - Error utility library for consistent error handling
affects: [20-symbol-mapping, 21-multi-account, user-settings, dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Central error utility library for user-friendly error mapping
    - Inline test connection with loading state in forms
    - Three-state status indicators pattern (connected/connecting/disconnected)

key-files:
  created:
    - ui-next/src/app/api/accounts/test-connection/route.ts
    - ui-next/src/lib/errors/account-errors.ts
  modified:
    - ui-next/src/types/broker.ts
    - ui-next/src/components/brokers/broker-health-card.tsx
    - ui-next/src/components/accounts/account-form.tsx
    - ui-next/src/components/accounts/account-card.tsx
    - ui-next/src/components/accounts/account-list.tsx
    - ui-next/src/lib/api/accounts.ts

key-decisions:
  - "Three-state status: connected (green), connecting (amber), disconnected (red)"
  - "Test Connection uses dedicated BFF route to backend endpoint"
  - "Error utility library maps technical errors to user-friendly messages with suggestions"
  - "Test result clears when credentials or broker changes"

patterns-established:
  - "ConnectionStatus type: centralized status enum for consistency"
  - "parseAccountError + formatErrorForToast: error handling pattern"
  - "Inline form error display with toast notification for persistent feedback"

# Metrics
duration: 15min
completed: 2026-01-21
---

# Phase 19 Plan 02: Frontend Connection Status UI Summary

**Three-state broker status indicators with Test Connection button and comprehensive user-friendly error messaging**

## Performance

- **Duration:** 15 min
- **Started:** 2026-01-21T20:09:27Z
- **Completed:** 2026-01-21T20:24:00Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- Three-state connection indicators (green/amber/red) with distinct icons and messages
- Test Connection button validates credentials before save with inline results
- Centralized error utility maps all account errors to user-friendly messages
- Toast notifications with specific error reasons and suggested actions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add three-state status indicators** - `a756832` (feat)
   - Added ConnectionStatus type to broker.ts
   - Updated BrokerHealthCard with STATUS_CONFIG for three visual states

2. **Task 2: Add Test Connection button to account form** - `16bf67e` (feat)
   - Added BFF route /api/accounts/test-connection
   - Added testConnection() function to accounts API lib
   - Added Test Connection button with loading and result states

3. **Task 3: Improve error messages throughout** - `ff23340` + `b537e35` (feat)
   - Created account-errors.ts utility library
   - Updated account-list.tsx with parseAccountError for all operations
   - Updated account-card.tsx sync error handling
   - Added inline form error display

**Plan metadata:** (this commit)

## Files Created/Modified

### Created
- `ui-next/src/app/api/accounts/test-connection/route.ts` - BFF route proxying to backend test endpoint
- `ui-next/src/lib/errors/account-errors.ts` - Error parsing utility with user-friendly message mapping

### Modified
- `ui-next/src/types/broker.ts` - Added ConnectionStatus type
- `ui-next/src/components/brokers/broker-health-card.tsx` - Three-state indicators with STATUS_CONFIG
- `ui-next/src/components/accounts/account-form.tsx` - Test Connection button, result display, inline error
- `ui-next/src/components/accounts/account-card.tsx` - Improved sync error handling with toast
- `ui-next/src/components/accounts/account-list.tsx` - User-friendly errors for all CRUD operations
- `ui-next/src/lib/api/accounts.ts` - Added testConnection() function

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Three-state via STATUS_CONFIG object | Centralized configuration for icon, color, label, subtext per state |
| Test button disabled until required fields filled | Prevents unnecessary API calls, better UX |
| Error utility with categorization | Maps auth/network/broker/validation errors to appropriate messages |
| Toast + inline error for form failures | Persistent notification plus immediate visual feedback |
| Test result clears on input change | Prevents stale results confusing users |

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed successfully.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 19 (Broker Connections UI) is now complete:
- [x] CONN-01: Connection status indicators (green/amber/red)
- [x] CONN-02: Connection test button validates credentials
- [x] CONN-05: Last sync timestamp (was already implemented in AccountCard)
- [x] CONN-06: Clear error messages on connection failure

Ready for Phase 20 (Symbol Mapping & Futures).

---
*Phase: 19-broker-connections-ui*
*Completed: 2026-01-21*
