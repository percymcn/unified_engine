---
phase: 20-symbol-mapping-futures
plan: 03
subsystem: ui
tags: [react, next.js, typescript, rest-api, fastapi, settings]

# Dependency graph
requires:
  - phase: 20-01
    provides: SymbolAlias model and repository
  - phase: 20-02
    provides: Symbol auto-detection service

provides:
  - Symbol aliases CRUD API endpoints
  - Frontend API client for symbol aliases
  - Symbol Mapping settings page at /settings/symbols
  - Add/edit/delete symbol alias dialogs
  - Navigation link in sidebar

affects: [21-multi-account, signal-processing, account-management]

# Tech tracking
tech-stack:
  added: []
  patterns: [BFF pattern for API proxying, grouped API response for UI, dialog-based forms]

key-files:
  created:
    - app/routers/symbol_aliases.py
    - ui-next/src/lib/api/symbol-aliases.ts
    - ui-next/src/types/symbol-alias.ts
    - ui-next/src/app/dashboard/settings/symbols/page.tsx
    - ui-next/src/components/settings/symbol-alias-list.tsx
    - ui-next/src/components/settings/symbol-alias-form.tsx
    - ui-next/src/app/api/symbol-aliases/route.ts
    - ui-next/src/app/api/symbol-aliases/[id]/route.ts
  modified:
    - ui-next/src/components/sidebar.tsx
    - app/main.py

key-decisions:
  - "Return aliases grouped by broker for UI convenience"
  - "Mark auto-detected aliases with badge vs Custom"
  - "Disable broker/source fields in edit mode (only target editable)"

patterns-established:
  - "Settings pages with stats cards, explanation cards, and grouped lists"
  - "Dialog-based forms for CRUD operations"

# Metrics
duration: 6min
completed: 2026-01-21
---

# Phase 20 Plan 03: Symbol Mapping UI Summary

**Settings page for managing per-broker symbol aliases with CRUD API, grouped display, and add/edit dialogs**

## Performance

- **Duration:** 6 min
- **Started:** 2026-01-21T23:12:23Z
- **Completed:** 2026-01-21T23:18:35Z
- **Tasks:** 4 (all previously completed, verified and fixed)
- **Files modified:** 10

## Accomplishments

- Full CRUD REST API for symbol aliases with user isolation
- TypeScript API client with all operations (get, create, update, delete)
- Settings page at /dashboard/settings/symbols with broker-grouped display
- Add/edit dialogs with validation and error handling
- Auto-detected vs Custom alias badges
- Navigation link in sidebar under Settings

## Task Commits

Tasks were completed in prior execution with one fix applied:

1. **Task 1: Create Symbol Aliases API endpoints** - `f735c4c` (feat)
2. **Task 2: Create frontend API client** - `6f812a7` (feat)
3. **Task 3: Create Symbol Mapping settings page** - `dbdd2f8` (auto commit containing page and components)
4. **Task 4: Add symbol mapping link to navigation** - `f0da098` (auto commit with sidebar update)

**Bug fix:** `5ac05cb` (fix: type error in symbol mapping page)

## Files Created/Modified

### Backend
- `app/routers/symbol_aliases.py` - REST API with GET/POST/PUT/DELETE endpoints
- `app/main.py` - Router registration at /api/v1/symbol-aliases

### Frontend API
- `ui-next/src/lib/api/symbol-aliases.ts` - TypeScript API client
- `ui-next/src/types/symbol-alias.ts` - SymbolAlias, SymbolAliasGroup types
- `ui-next/src/app/api/symbol-aliases/route.ts` - BFF proxy for list/create
- `ui-next/src/app/api/symbol-aliases/[id]/route.ts` - BFF proxy for update/delete

### Frontend UI
- `ui-next/src/app/dashboard/settings/symbols/page.tsx` - Settings page
- `ui-next/src/components/settings/symbol-alias-list.tsx` - Grouped list with delete confirmation
- `ui-next/src/components/settings/symbol-alias-form.tsx` - Add/edit dialog
- `ui-next/src/components/sidebar.tsx` - Added Symbol Mapping nav link

## Decisions Made

1. **Grouped response structure** - API returns aliases grouped by broker type with display names for cleaner UI rendering
2. **Auto vs Custom badges** - Visual distinction helps users understand which mappings were system-detected vs user-created
3. **Edit mode restrictions** - Only target symbol editable when editing (source/broker define the mapping identity)
4. **Empty state guidance** - Points users to Accounts settings when no brokers connected

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed type error in accounts API response handling**
- **Found during:** Verification build
- **Issue:** Page assumed `getAccounts()` returns `{ accounts: Account[] }` but it returns `Account[]`
- **Fix:** Updated to use `Array.isArray(accountsResponse)` check
- **Files modified:** ui-next/src/app/dashboard/settings/symbols/page.tsx
- **Verification:** Build passes successfully
- **Committed in:** `5ac05cb`

---

**Total deviations:** 1 auto-fixed (bug)
**Impact on plan:** Minor type fix required for build. No scope creep.

## Issues Encountered

- ESLint unescaped entities warnings were already fixed in prior commits
- Tasks 3 and 4 were committed in "auto" commits rather than atomic task commits

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Symbol Mapping UI complete and functional
- Ready for Phase 20-04: Futures Contract Support
- Ready for Phase 21: Multi-Account & Routing (uses symbol aliases)

---
*Phase: 20-symbol-mapping-futures*
*Plan: 03*
*Completed: 2026-01-21*
