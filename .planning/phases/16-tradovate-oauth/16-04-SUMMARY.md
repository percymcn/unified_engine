---
phase: 16
plan: 4
subsystem: frontend
tags: [oauth, tradovate, ui, next.js, bff]
depends_on:
  requires: [16-01, 16-02, 16-03]
  provides: [oauth-ui, oauth-flow-complete]
  affects: [19-broker-connections]
tech-stack:
  added: []
  patterns: [bff-oauth, url-fragment-tokens, useCallback, useSearchParams]
key-files:
  created:
    - ui-next/src/components/accounts/tradovate-oauth-button.tsx
    - ui-next/src/app/api/tradovate/authorize/route.ts
  modified:
    - ui-next/src/components/accounts/account-form.tsx
    - ui-next/src/components/accounts/account-list.tsx
    - ui-next/src/app/api/accounts/route.ts
decisions:
  - id: oauth-button-component
    summary: Separate OAuth button component for reusability
    rationale: Encapsulates OAuth initiation logic, can be reused in other contexts
  - id: url-fragment-tokens
    summary: Tokens passed via URL fragment, not query string
    rationale: Fragments not sent to server, only accessible via JavaScript - more secure
  - id: fallback-credentials
    summary: Keep credential fields as fallback for Tradovate
    rationale: Some users may prefer manual credential entry over OAuth
  - id: loading-state-combined
    summary: Combined loading and OAuth processing states in render
    rationale: Single loading UI handles both initial load and OAuth callback
metrics:
  duration: 4m 10s
  completed: 2026-01-21
---

# Phase 16 Plan 4: Frontend OAuth UI Summary

**One-liner:** Tradovate OAuth UI with environment selector, BFF authorization route, and callback handling with toast notifications.

## What Was Built

### 1. Tradovate OAuth Button Component
**File:** `ui-next/src/components/accounts/tradovate-oauth-button.tsx`

A dedicated component for initiating Tradovate OAuth flow:
- Environment selector (Demo/Live) with descriptive text
- Loading state during OAuth initiation
- Error handling with user-visible messages
- Redirects to Tradovate authorization page

### 2. BFF Authorization Route
**File:** `ui-next/src/app/api/tradovate/authorize/route.ts`

Server-side route to initiate OAuth:
- Extracts environment from query params
- Authenticates using httpOnly cookie
- Proxies to backend `/api/v1/auth/tradovate/authorize`
- Returns authorization URL to frontend

### 3. Updated Account Form
**File:** `ui-next/src/components/accounts/account-form.tsx`

Modified to show OAuth option for Tradovate:
- OAuth section appears when Tradovate broker selected (new accounts only)
- Visual separator between OAuth and credential options
- Credential fields remain as fallback (dimmed)
- Other brokers retain standard credential flow

### 4. OAuth Callback Handler
**File:** `ui-next/src/components/accounts/account-list.tsx`

Handles OAuth callback when user returns from Tradovate:
- Parses URL params for `tradovate_connected` and `error`
- Extracts tokens from URL fragment (`#tokens=...`)
- Creates account with OAuth tokens via API
- Shows success/error toast notifications
- Cleans URL after processing

### 5. Updated BFF Accounts Route
**File:** `ui-next/src/app/api/accounts/route.ts`

Enhanced POST handler for OAuth token support:
- Documents both credential and OAuth creation flows
- Explicit handling of `oauth_tokens` field
- Preserves all credential types for different brokers

## OAuth Flow Summary

```
1. User selects Tradovate in AccountForm
2. User chooses environment (Demo/Live)
3. User clicks "Connect with Tradovate"
4. Frontend calls /api/tradovate/authorize
5. BFF proxies to backend, gets authorization URL
6. Frontend redirects to Tradovate
7. User authorizes on Tradovate
8. Tradovate redirects to /api/auth/tradovate/callback
9. BFF exchanges code for tokens
10. BFF redirects to /dashboard/settings/accounts?tradovate_connected=true#tokens=...
11. AccountList reads tokens from fragment
12. AccountList creates account via /api/accounts POST
13. Toast shows success, URL cleaned
```

## Commits

| Hash | Message |
|------|---------|
| e0c183f | feat(16-04): create Tradovate OAuth button component |
| 86ba02a | feat(16-04): add BFF route for OAuth initiation |
| f0243c5 | feat(16-04): update account form to show OAuth for Tradovate |
| 20cfc26 | feat(16-04): handle OAuth callback in account list |
| 3dd61fe | feat(16-04): update BFF accounts route for OAuth tokens |

## Verification Results

- [x] "Connect with Tradovate" button visible when Tradovate selected
- [x] Environment selector works (demo/live)
- [x] Clicking button calls BFF route
- [x] OAuth tokens supported in account creation
- [x] Success toast implementation ready
- [x] Error handling shows appropriate messages
- [x] URL cleaned after callback processing
- [x] Loading state prevents double-processing
- [x] TypeScript compilation passes

## Deviations from Plan

None - plan executed exactly as written.

## Technical Notes

1. **useCallback for handleOAuthConnect:** Prevents unnecessary re-renders and satisfies exhaustive-deps rule

2. **URL Fragment Security:** Tokens in fragment (`#tokens=`) are never sent to server in HTTP requests, only accessible via JavaScript

3. **Combined Loading State:** Single loading UI for both initial fetch and OAuth processing simplifies component logic

4. **Fallback Credentials:** Credential fields kept visible (dimmed) for users who prefer manual entry or when OAuth isn't available

## Next Phase Readiness

Phase 16 (Tradovate OAuth) is now complete:
- Plan 1: Backend OAuth endpoints
- Plan 2: Token storage and refresh service
- Plan 3: Backend executor integration
- Plan 4: Frontend OAuth UI

All Tradovate OAuth requirements satisfied. Ready for Phase 17 (TopStep/ProjectX SDK).
