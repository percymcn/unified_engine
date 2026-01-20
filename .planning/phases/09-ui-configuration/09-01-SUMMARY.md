---
phase: 09-ui-configuration
plan: 01
subsystem: ui
tags: [nextjs, react, typescript, shadcn-ui, account-management, crud]

# Dependency graph
requires:
  - phase: 08-ui-dashboard
    provides: Dashboard foundation with BFF pattern and routing structure
  - phase: 07-ui-foundation
    provides: Next.js setup with auth, shadcn/ui components, dark theme
provides:
  - Full CRUD account management UI under /settings/accounts
  - Account card component with balance display and actions
  - Account form with broker-specific credential fields
  - BFF API routes for account operations
  - Settings navigation structure for future configuration pages
affects: [09-02, 09-03, 09-04]

# Tech tracking
tech-stack:
  added: [shadcn/ui dialog component]
  patterns:
    - Settings submenu structure in sidebar
    - Responsive grid layout for account cards
    - Currency formatting with Intl API
    - Relative time formatting for last sync
    - Masked credential display (first 4 + last 4 chars)
    - Delete confirmation dialogs for destructive actions

key-files:
  created:
    - ui-next/src/lib/api/accounts.ts
    - ui-next/src/app/api/accounts/route.ts
    - ui-next/src/app/api/accounts/[id]/route.ts
    - ui-next/src/app/api/accounts/[id]/sync/route.ts
    - ui-next/src/app/api/accounts/[id]/balance/route.ts
    - ui-next/src/components/accounts/account-card.tsx
    - ui-next/src/components/accounts/account-form.tsx
    - ui-next/src/components/accounts/account-list.tsx
    - ui-next/src/app/dashboard/settings/accounts/page.tsx
    - ui-next/src/components/ui/dialog.tsx
  modified:
    - ui-next/src/components/sidebar.tsx

key-decisions:
  - "Account types already existed with comprehensive broker credential config"
  - "Settings navigation structure with separate section for configuration pages"
  - "Accounts moved from top-level to /settings/accounts/ path"
  - "Dialog component added for delete confirmation and form modals"
  - "Account credentials masked in display (show first 4 and last 4 chars)"
  - "Currency formatting with Intl.NumberFormat for internationalization"
  - "Relative time display for last sync (Just now, 5m ago, 2h ago)"

patterns-established:
  - "Settings submenu pattern: uppercase section label with grouped links"
  - "Account card pattern: grid layout with balance metrics and action buttons"
  - "Form modal pattern: dialog-based forms for create/edit operations"
  - "Delete confirmation pattern: separate dialog with destructive variant button"
  - "Sync action pattern: inline sync button with loading state"

# Metrics
duration: 17min
completed: 2026-01-20
---

# Phase 09 Plan 01: Account Management Page Summary

**Full CRUD account management with broker-specific credential forms, balance display, and settings navigation structure**

## Performance

- **Duration:** 17 min
- **Started:** 2026-01-20T19:19:48Z
- **Completed:** 2026-01-20T19:36:54Z
- **Tasks:** 8 (Task 1 already complete)
- **Files created:** 11
- **Files modified:** 1

## Accomplishments

- Complete account management CRUD interface with create, edit, delete, and sync operations
- Broker-specific credential forms that adapt based on selected broker (MT4/MT5, TradeLocker, etc.)
- Balance display with equity, margin, and free margin formatted by currency
- Settings navigation structure ready for API Keys (09-03) and Webhooks (09-04)
- BFF API routes proxying all account operations to backend with httpOnly cookie auth

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Account Types** - Already complete (types/account.ts existed)
2. **Task 2: Create Account API Service** - `db03b86` (feat)
3. **Task 3: Create BFF Routes for Accounts** - `c40d601` (feat)
4. **Task 4: Create Account Card Component** - `e0d102a` (feat)
5. **Task 5: Create Account Form Component** - `7aa5594` (feat)
6. **Task 6: Create Account List Component** - `586b869` (feat)
7. **Task 7: Create Accounts Management Page** - `d4930cb` (feat)
8. **Task 8: Add Settings Navigation** - `ca0f1c7` (feat)

## Files Created/Modified

**Created:**
- `ui-next/src/lib/api/accounts.ts` - Account API service with CRUD operations
- `ui-next/src/app/api/accounts/route.ts` - BFF routes for list and create
- `ui-next/src/app/api/accounts/[id]/route.ts` - BFF routes for get, update, delete
- `ui-next/src/app/api/accounts/[id]/sync/route.ts` - BFF route for broker sync
- `ui-next/src/app/api/accounts/[id]/balance/route.ts` - BFF route for balance fetch
- `ui-next/src/components/accounts/account-card.tsx` - Account display card with actions
- `ui-next/src/components/accounts/account-form.tsx` - Create/edit form with broker-specific fields
- `ui-next/src/components/accounts/account-list.tsx` - Grid layout with empty state
- `ui-next/src/app/dashboard/settings/accounts/page.tsx` - Accounts management page
- `ui-next/src/components/ui/dialog.tsx` - Dialog component (shadcn/ui)

**Modified:**
- `ui-next/src/components/sidebar.tsx` - Added Settings section with Accounts, API Keys, Webhooks links

## Decisions Made

1. **Settings Navigation Structure** - Created Settings section in sidebar with submenu for Accounts, API Keys (09-03), and Webhooks (09-04) instead of top-level links
2. **Account Path Location** - Moved accounts from `/dashboard/accounts` to `/dashboard/settings/accounts` to align with plan specification and future configuration pages
3. **Credential Masking** - Display account IDs with first 4 and last 4 characters visible (e.g., "1234...5678") for security
4. **Currency Formatting** - Use Intl.NumberFormat for proper currency display with locale support
5. **Relative Time Display** - Show last sync as relative time ("Just now", "5m ago", "2h ago") for better UX
6. **Broker-Specific Forms** - Dynamic form fields based on broker selection using BROKER_CREDENTIAL_CONFIG from types
7. **Dialog Pattern** - Use shadcn/ui dialog for both form modals and delete confirmation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Installed dialog component**
- **Found during:** Task 4 (Account Card Component)
- **Issue:** Dialog component needed for delete confirmation and form modals but not installed
- **Fix:** Ran `npx shadcn@latest add dialog` to install component
- **Files modified:** ui-next/src/components/ui/dialog.tsx
- **Verification:** Dialog import succeeds, delete confirmation works
- **Committed in:** e0d102a (Task 4 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical UI component)
**Impact on plan:** Dialog component essential for delete confirmation (plan requirement). No scope creep.

## Issues Encountered

None - all tasks completed as planned.

## User Setup Required

None - no external service configuration required. Account management uses existing backend API.

## Next Phase Readiness

- Account management foundation complete
- Settings navigation structure ready for Signal Routing (09-02), API Keys (09-03), and Webhooks (09-04)
- BFF pattern established for all account operations
- No blockers for next plans

---
*Phase: 09-ui-configuration*
*Completed: 2026-01-20*
