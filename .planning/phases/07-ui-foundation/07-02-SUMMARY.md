---
phase: 07-ui-foundation
plan: 02
subsystem: ui
tags: [nextjs, jwt, cookies, auth, bff, middleware, react, typescript]

# Dependency graph
requires:
  - phase: 07-ui-foundation
    plan: 01
    provides: Next.js 14 app router with shadcn/ui components
  - phase: 06-security-hardening
    provides: Secure backend with JWT auth endpoints
provides:
  - Cookie-based JWT token management utilities
  - BFF API routes for auth (login, logout, me)
  - Login page with form UI
  - Middleware for route protection
affects: [07-03-dashboard, 07-04-account-management, 07-05-signal-display]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - httpOnly cookies for JWT storage (XSS protection)
    - BFF pattern for backend proxy
    - Middleware-based route protection
    - Discriminated union types for API responses

key-files:
  created:
    - ui-next/src/lib/auth.ts
    - ui-next/src/app/api/auth/login/route.ts
    - ui-next/src/app/api/auth/logout/route.ts
    - ui-next/src/app/api/auth/me/route.ts
    - ui-next/src/app/login/page.tsx
    - ui-next/src/middleware.ts
    - ui-next/.env.local
    - ui-next/.env.example
  modified: []

key-decisions:
  - "httpOnly cookies for JWT storage instead of localStorage (XSS protection)"
  - "BFF pattern - Next.js proxies auth to FastAPI backend"
  - "Cookie presence check in middleware, token validation server-side"
  - "Form-urlencoded format for backend login compatibility"
  - "Redirect parameter preserved on auth redirect for post-login return"

patterns-established:
  - "AUTH_COOKIE_NAME constant shared between auth.ts and routes"
  - "Discriminated union types with 'as const' for API responses"
  - "BACKEND_URL env var for backend proxy configuration"
  - "Protected routes under /dashboard/*, auth routes under /login"

# Metrics
duration: 8min
completed: 2026-01-20
---

# Phase 7 Plan 2: Auth Pages Summary

**JWT authentication with httpOnly cookies, BFF API proxy routes, login form, and middleware route protection**

## Performance

- **Duration:** 8 min
- **Started:** 2026-01-20T09:20:00Z
- **Completed:** 2026-01-20T09:28:00Z
- **Tasks:** 4
- **Files created:** 8

## Accomplishments

- Cookie-based JWT token management utilities with secure defaults
- BFF API routes proxying auth to FastAPI backend (login, logout, me)
- Login page with username/password form, loading state, and error handling
- Next.js middleware protecting /dashboard routes and redirecting /login when authenticated

## Task Commits

Each task was committed atomically:

1. **Task 1: Create auth utilities and environment config** - `ffbf41a` (feat)
2. **Task 2: Create BFF API routes for auth** - `153d30e` (feat)
3. **Task 3: Create login page with form** - `f66f387` (feat)
4. **Task 4: Create middleware for route protection** - `75a7b6c` (feat)

**Bug fix:** `954e8d5` (fix) - TypeScript literal types in login route

## Files Created/Modified

- `ui-next/src/lib/auth.ts` - Cookie-based JWT token management utilities
- `ui-next/.env.local` - Backend URL configuration
- `ui-next/.env.example` - Environment variable documentation
- `ui-next/src/app/api/auth/login/route.ts` - Login proxy with httpOnly cookie
- `ui-next/src/app/api/auth/logout/route.ts` - Logout with cookie clearing
- `ui-next/src/app/api/auth/me/route.ts` - User info with token validation
- `ui-next/src/app/login/page.tsx` - Login form with shadcn components
- `ui-next/src/middleware.ts` - Route protection middleware

## Decisions Made

1. **httpOnly cookies** - JWT stored in httpOnly cookie, not localStorage (XSS protection)
2. **BFF pattern** - Next.js API routes proxy to backend, hide backend URL from client
3. **Middleware cookie check** - Only checks cookie presence, not validity (validation via /api/auth/me)
4. **Form-urlencoded login** - Backend expects form data, not JSON
5. **Redirect parameter** - Preserved on auth redirect for post-login navigation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TypeScript literal type inference**
- **Found during:** Verification (build)
- **Issue:** NextResponse.json inferred `success: boolean` instead of literal `true`/`false`, breaking discriminated union types
- **Fix:** Added `as const` assertions and explicit generic types to NextResponse.json calls
- **Files modified:** ui-next/src/app/api/auth/login/route.ts
- **Verification:** npm run build succeeds without type errors
- **Committed in:** `954e8d5`

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Minor TypeScript fix for correct type inference. No scope creep.

## Issues Encountered

None - plan executed as specified after TypeScript fix.

## User Setup Required

None - BACKEND_URL defaults to http://localhost:8000 which matches existing backend.

## Next Phase Readiness

- Auth flow complete and ready for dashboard implementation (07-03)
- Login page will redirect to /dashboard on success
- Middleware will protect dashboard routes
- User can be fetched via /api/auth/me for dashboard display

---
*Phase: 07-ui-foundation*
*Completed: 2026-01-20*
