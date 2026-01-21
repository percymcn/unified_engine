# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-21)

**Core value:** Reliable signal-to-trade execution across all configured brokers with zero missed signals.
**Current focus:** v1.1 Production Ready with Monetization

## Current Position

Phase: 17 - TopStep/ProjectX SDK (COMPLETE)
Plan: 1 of 1 complete
Status: Phase complete, ready for Phase 18
Last activity: 2026-01-21 - Completed 17-01-PLAN.md (Migrate TopStep to project-x-py SDK)

Progress: [#############---] 50% (v1.1) - Phase 17 complete

## v1.1 Milestone Goals

**Goal:** Rebrand to Tradeflow, fix critical bugs, integrate official broker SDKs, add Stripe monetization, build enterprise landing page, implement comprehensive risk management.

**Requirements:** 82 active

| Category | Items | Phase |
|----------|-------|-------|
| Branding | 1 | 12 |
| Infrastructure | 3 | 12 |
| Critical Fixes | 7 | 12 |
| UI Navigation | 3 | 12 |
| Billing | 7 | 13 |
| Landing Page | 11 | 14 |
| TradeLocker SDK | 1 | 15 |
| Tradovate OAuth | 3 | 16 |
| TopStep SDK | 1 | 17 |
| MetaAPI SDK | 3 | 18 |
| Broker Connections | 4 | 19 |
| Symbol Mapping | 6 | 20 |
| Multi-Account | 6 | 21 |
| Risk Management | 16 | 22 |
| User Settings | 4 | 23 |
| Dashboard | 6 | 23 |

## Roadmap Overview

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 12 | Critical Fixes & Infrastructure | 14 | Complete (5/5 plans) |
| 13 | Stripe Billing | 7 | Gap closure complete (4/6 plans) |
| 14 | Landing Page | 11 | Complete (7/7 plans, incl. gap closure) |
| 15 | TradeLocker SDK | 1 | Complete (1/1 plan) |
| 16 | Tradovate OAuth | 3 | Complete (4/4 plans) |
| 17 | TopStep/ProjectX SDK | 1 | Complete (1/1 plan) |
| 18 | MetaAPI SDK | 3 | Not started |
| 19 | Broker Connections UI | 4 | Not started |
| 20 | Symbol Mapping & Futures | 6 | Not started |
| 21 | Multi-Account & Routing | 6 | Not started |
| 22 | Risk Management | 16 | Not started |
| 23 | User Settings & Dashboard | 10 | Not started |

## Previous Milestone

**v1.0 Shipped:** 2026-01-21
- 11 phases, 63 plans executed
- 33 requirements satisfied
- Archives: `.planning/milestones/v1.0-*`

## Accumulated Decisions

| Phase | Decision | Rationale |
|-------|----------|-----------|
| 12-01 | Environment variable layering for webhooks | WEBHOOK_BASE_URL > BACKEND_URL > localhost for flexible deployment |
| 12-01 | Separate BACKEND_URL and NEXT_PUBLIC_BACKEND_URL | Server-side vs client-side distinction in Next.js |
| 12-01 | Default port 8765 everywhere | Consistency with FastAPI backend configuration |
| 12-02 | BFF pattern for dashboard stats | Aggregate signals/accounts/trades in single API call |
| 12-02 | Return zeros on API failure | Graceful degradation, better UX than error messages |
| 12-03 | Sidebar shrink-0 + z-10 for stacking | Prevent flex compression and ensure sidebar stays above content |
| 12-03 | Controlled Sheet state for mobile menu | Use pathname effect to auto-close on navigation |
| 12-03 | startsWith() for nested route detection | Active state works for /settings/accounts/edit, etc. |
| 12-04 | Return empty array on API failures for list endpoints | Better UX - users see "no configs" instead of error on first use |
| 12-04 | Preserve 401 errors in BFF routes | Auth errors should still propagate to trigger login redirect |
| 12-04 | Skeleton loading states matching page layout | Smooth transition from loading to content |
| 12-04 | Retry button in all error states | Recoverable errors should be retryable |
| 12-05 | Cloudflare Tunnel over Caddy | User already using Cloudflare for routing |
| 12-05 | Frontend port 3456, backend port 8765 | Avoid port conflicts |
| 13-03 | Return 200 on webhook processing errors | Prevent Stripe retries while acknowledging receipt |
| 13-03 | Map cancel_at_period_end to "canceling" status | Show users their subscription is ending but still active |
| 13-03 | User lookup by stripe_customer_id with metadata fallback | Handle first-time checkout linking |
| 13-06 | Auto-create Stripe customer on first checkout | Simpler UX - no separate registration step needed |
| 13-06 | Reject checkout if already Pro | Prevent duplicate subscriptions, direct to portal |
| 13-06 | FRONTEND_URL defaults to production URL | Deployment works without configuration |
| 14-01 | Sticky header with scroll-based transparency | Modern aesthetic with transparent-to-solid effect |
| 14-01 | CSS blob animations for gradient backgrounds | Organic movement with staggered delays |
| 14-01 | Landing components in /components/landing/ | Organized component structure for marketing pages |
| 14-02 | Intersection Observer with CSS transitions | No external animation library needed, smooth staggered reveal |
| 14-03 | Intersection Observer for stats entrance animation | Scroll-triggered reveal without external animation library |
| 14-03 | Green accent color for trust icons | Positive/secure association for credibility |
| 14-03 | Hardcoded metrics for now | 10K+ signals, 99.9% uptime, 5 brokers, <100ms - to be dynamic later |
| 14-04 | Free tier CTA to /register, Pro to /api/billing/checkout | Different user journeys: Free starts registration, Pro goes to Stripe |
| 14-04 | Comparison table color-coded icons | Green check (true), red X (false), yellow dash (varies) for clarity |
| 14-06 | Radix accordion for FAQ | Consistent with existing UI component library |
| 14-06 | Twitter card metadata alongside Open Graph | Better social sharing coverage |
| 14-06 | Dynamic copyright year | Uses new Date().getFullYear() to stay current |
| 14-07 | Middleware allows landing page for unauthenticated | NextResponse.next() instead of redirect to /login |
| 14-07 | Full registration form at /register | Better UX than redirect to /login?mode=register |
| 14-07 | Dark theme registration page | Matches landing page aesthetic |
| 15-01 | Dual-mode TradeLocker (SDK + Brand API) | SDK preferred for user auth, Brand API fallback for broker integrations |
| 15-01 | ThreadPoolExecutor for async SDK wrapper | Sync SDK must not block async event loop, max_workers=3 |
| 15-01 | Keep WebSocket separate from SDK | SDK doesn't expose WebSocket, needed for real-time updates |
| 16-01 | In-memory OAuth state store | Simple for single-instance; needs Redis for multi-instance production |
| 16-01 | Tokens in URL fragment | Fragment not sent to server, frontend reads via JavaScript |
| 16-01 | BFF pattern for OAuth callback | Server-side token exchange, no CORS issues, secure |
| 16-02 | 5-minute refresh buffer before token expiry | Ensures tokens don't expire during API calls |
| 16-02 | Idempotent migration for token columns | Handles cases where SQLAlchemy creates tables on startup |
| 16-02 | Background task runs every 5 minutes | Proactive token refresh via asyncio loop |
| 16-03 | Dual-mode auth: OAuth when token provided, password fallback | Backward compatible authentication strategy |
| 16-03 | Lazy token refresh via _ensure_valid_token() | Refresh tokens before each API call for OAuth mode |
| 16-03 | ExecutorOrderResponse/ExecutorTradeResponse schemas | Separate executor layer types from API layer types |
| 16-04 | Separate OAuth button component | Encapsulates OAuth initiation logic, reusable |
| 16-04 | Tokens in URL fragment for callback | Fragments not sent to server, more secure |
| 16-04 | Keep credential fields as fallback | Some users may prefer manual credential entry |
| 17-01 | Dual-mode ProjectX executor (SDK + httpx) | SDK preferred, httpx fallback for reliability |
| 17-01 | ProjectXSDKService wrapper for project-x-py | Matches existing service patterns |
| 17-01 | TradingSuite per-instrument context | SDK requires instrument context for operations |
| 17-01 | SDK_AVAILABLE flag for conditional imports | Graceful degradation when SDK not installed |

## Known Tech Debt

- ~~Dashboard stats use placeholder data~~ (FIXED in 12-02)
- WebSocket event bridge incomplete (workaround: manual ws_manager calls)
- asyncpg not installed (graceful degradation)
- npm audit: 3 high severity vulnerabilities (dev-only, eslint-related)
- Alembic has multiple heads (001, 002)
- ~~Base URL hardcoded in some UI routes~~ (FIXED in 12-01)

## Session Continuity

Last session: 2026-01-21T18:48:25Z
Stopped at: Completed 17-01-PLAN.md (Migrate TopStep to project-x-py SDK)
Resume file: None
Status: Phase 17 complete, ready for Phase 18

## Gap Closure Status

**Phase 13 Verification Results (2026-01-21):**
- Score: 2/7 must-haves verified initially
- 13-04 broker limits: Already implemented (accounts.py uses require_broker_slot)
- 13-06 executed: Added missing checkout/portal/status/plans endpoints

**Gaps Closed by 13-06:**
1. POST /api/billing/checkout - Create Stripe Checkout session
2. GET /api/billing/portal - Stripe Customer Portal URL
3. GET /api/billing/status - Subscription status
4. GET /api/billing/plans - Plan details

**Phase 14 Verification Results (2026-01-21):**
- 14-07 executed: Fixed middleware redirect, added /register page

**Gaps Closed by 14-07:**
1. Middleware allows "/" for unauthenticated visitors (was redirecting to /login)
2. /register page exists (CTAs were pointing to non-existent page)

## Next Steps

1. Begin Phase 18 (MetaAPI SDK)
2. Continue through Phases 19-23 for v1.1 completion
