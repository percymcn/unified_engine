---
phase: 12-critical-fixes-infrastructure
plan: 01
subsystem: ui
tags: [branding, environment-variables, next.js, webhook]

# Dependency graph
requires:
  - phase: 07-ui-foundation
    provides: Next.js UI structure and components
provides:
  - Tradeflow branding throughout UI
  - Consistent BACKEND_URL defaults (port 8765)
  - Public webhook URL configuration
affects: [13-stripe-billing, 14-landing-page, 19-broker-connections]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Use BACKEND_URL for server-side API calls (default 8765)
    - Use NEXT_PUBLIC_BACKEND_URL for client-side WebSocket
    - Use NEXT_PUBLIC_WEBHOOK_BASE_URL for user-facing webhook URLs

key-files:
  created: []
  modified:
    - ui-next/src/components/sidebar.tsx
    - ui-next/src/app/dashboard/page.tsx
    - ui-next/src/app/(dashboard)/page.tsx
    - ui-next/src/app/api/auth/login/route.ts
    - ui-next/src/app/api/auth/me/route.ts
    - ui-next/src/app/api/api-keys/route.ts
    - ui-next/src/app/api/api-keys/[id]/route.ts
    - ui-next/src/app/api/brokers/health/route.ts
    - ui-next/src/app/dashboard/settings/webhooks/page.tsx
    - ui-next/.env.example

key-decisions:
  - "Keep BACKEND_URL and NEXT_PUBLIC_BACKEND_URL separate for server/client distinction"
  - "Add NEXT_PUBLIC_WEBHOOK_BASE_URL for public-facing webhook URLs"
  - "Default port 8765 everywhere for consistency with FastAPI backend"

patterns-established:
  - "Environment variable layering: WEBHOOK_BASE_URL > BACKEND_URL > localhost default"
  - "Branding: All user-visible text uses 'Tradeflow' product name"

# Metrics
duration: 8min
completed: 2026-01-21
---

# Phase 12 Plan 01: Branding and Environment Configuration Summary

**Rebranded UI to Tradeflow, standardized API routes to port 8765, and configured webhook URLs for production domain**

## Performance

- **Duration:** 8 min
- **Started:** 2026-01-21T07:34:23Z
- **Completed:** 2026-01-21T08:32:18Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments

- All UI text changed from "Unified Engine" to "Tradeflow"
- Version footer updated to "Tradeflow v1.1"
- All API routes now default to port 8765 (was 8000 in some files)
- Webhook page uses NEXT_PUBLIC_WEBHOOK_BASE_URL for public-facing URLs
- Environment variables documented in .env.example

## Task Commits

Each task was committed atomically:

1. **Task 1: Rebrand UI text to Tradeflow** - `44d9b45` (feat)
2. **Task 2: Standardize BACKEND_URL defaults to port 8765** - `dc06577` (fix)
3. **Task 3: Configure webhook URL to use public domain** - `5e9c2a7` (feat)

## Files Created/Modified

- `ui-next/src/components/sidebar.tsx` - Tradeflow branding in header and footer
- `ui-next/src/app/dashboard/page.tsx` - Tradeflow welcome message
- `ui-next/src/app/(dashboard)/page.tsx` - Tradeflow welcome message (alternate route)
- `ui-next/src/app/api/auth/login/route.ts` - Port 8765 default
- `ui-next/src/app/api/auth/me/route.ts` - Port 8765 default
- `ui-next/src/app/api/api-keys/route.ts` - Port 8765 default
- `ui-next/src/app/api/api-keys/[id]/route.ts` - Port 8765 default
- `ui-next/src/app/api/brokers/health/route.ts` - Changed to BACKEND_URL with 8765 default
- `ui-next/src/app/dashboard/settings/webhooks/page.tsx` - Webhook base URL configuration
- `ui-next/.env.example` - Documented all three env vars with comments

## Decisions Made

- **Environment variable layering:** WEBHOOK_BASE_URL falls back to BACKEND_URL falls back to localhost:8765
- **Server vs client env vars:** BACKEND_URL for API routes (server-side), NEXT_PUBLIC_* for client components
- **.env.local not committed:** Contains local/production secrets, excluded by .gitignore

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `.env.local` is in `.gitignore` (correctly) - only `.env.example` committed for documentation
- Next.js build shows ENOENT for standalone output (unrelated to changes, existing issue with (dashboard) group route)

## User Setup Required

None - no external service configuration required. The `.env.local` file is already set up for local development.

## Next Phase Readiness

- Branding complete, ready for landing page (Phase 14)
- Environment configuration complete, ready for production deployment
- Next plan (12-02) can proceed with signal processing fixes

---
*Phase: 12-critical-fixes-infrastructure*
*Completed: 2026-01-21*
