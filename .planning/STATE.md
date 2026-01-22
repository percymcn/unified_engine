# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-21)

**Core value:** Reliable signal-to-trade execution across all configured brokers with zero missed signals.
**Current focus:** v1.1 Production Ready with Monetization

## Current Position

Phase: 24 - Enhanced Features & Monetization v2 (IN PROGRESS)
Plan: 5 of 8 complete (Wave 1 near complete)
Status: Phase 24 in progress - Wave 1 executing
Last activity: 2026-01-22 - Completed 24-02-PLAN.md (4-Tier Pricing Backend)

Progress: [#############################_] 96% (v1.1+) - Phase 24 Wave 1 near complete

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
| 18 | MetaAPI SDK | 3 | Complete (1/1 plan) |
| 19 | Broker Connections UI | 4 | Complete (2/2 plans) |
| 20 | Symbol Mapping & Futures | 6 | Complete (4/4 plans) |
| 21 | Multi-Account & Routing | 6 | Complete (3/3 plans) |
| 22 | Risk Management | 16 | Complete (4/4 plans) |
| 23 | User Settings & Dashboard | 18 | Complete (5/5 plans) |
| 24 | Enhanced Features & Monetization v2 | 43 | In Progress (5/8 plans) |

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
| 18-01 | Use metaapi-cloud-sdk as unified MT4/MT5 API | Official SDK provides better reliability, real-time streaming, cloud access |
| 18-01 | Dual-mode MT4/MT5 with fallback to httpx | Maintains backward compatibility with self-hosted Manager API setups |
| 19-01 | 10-second timeout for connection tests | Reasonable balance between allowing slow connections and not making users wait |
| 19-01 | Dual-mode testing (SDK + fallback) | Matches existing executor patterns, ensures testing works even without SDKs |
| 19-02 | Three-state status: connected/connecting/disconnected | Clear visual feedback with green/amber/red indicators |
| 19-02 | Central error utility library for account errors | Maps technical errors to user-friendly messages with suggestions |
| 19-02 | Test result clears on input change | Prevents stale test results from confusing users |
| 20-01 | Preserve symbol numbers in normalization | US30, NAS100 are valid symbols - only strip delimited futures codes |
| 20-01 | CME front months only (H/M/U/Z) | Only strip recognized CME month codes, not arbitrary letters |
| 20-01 | User alias priority over known mappings | Custom user mappings should override system defaults |
| 20-02 | Pattern-based detection over explicit configuration | Reduces manual setup, works across brokers |
| 20-02 | Confidence scoring for detection quality | UI can warn when low confidence |
| 20-02 | User aliases take priority over auto-detected | User customizations always override system |
| 20-02 | Don't fail account creation if alias creation fails | Graceful degradation |
| 20-03 | Return aliases grouped by broker for UI | Cleaner rendering, single API call for grouped view |
| 20-03 | Auto vs Custom badges for alias source | Visual distinction helps users understand mapping origin |
| 20-03 | Edit mode only allows target symbol change | Source/broker define mapping identity |
| 20-04 | Third Friday expiration for equity indices | Standard CME practice for ES, NQ, YM, RTY |
| 20-04 | 3-day default rollover window | Typical institutional practice before expiration |
| 20-04 | Three notification tiers: warning, urgent, critical | Escalating urgency at 7d, 3d, 1d before expiration |
| 21-01 | Cache group_name and group_color in TradingAccount | Avoid joins for list queries, cascade updates on group change |
| 21-01 | Set accounts.group_id to NULL on group deletion | Preserve accounts, don't orphan data |
| 21-01 | Partial updates for account settings (non-None only) | Standard PATCH semantics, avoids accidental resets |
| 21-02 | Four routing strategies (all_accounts, specific_accounts, rules_based, default_only) | Covers all use cases from simple single-account to complex conditional routing |
| 21-02 | Higher priority rules evaluated first | Clear evaluation order for rule-based routing |
| 21-02 | Rules-based routing falls back to default account | Ensures signals are not lost due to configuration gaps |
| 21-02 | Webhook key in URL path for routed signals | Clean REST design, no auth header needed for TradingView |
| 21-03 | RadioGroup for routing strategy selection | Clear visual separation of 4 strategies with conditional UI sections |
| 21-03 | Tabs for account settings organization | Position Sizing, Risk Limits, Routing - logical grouping reduces cognitive load |
| 21-03 | Separate groups page with manage dialog | Keep accounts list focused, groups as organizational layer |
| 22-01 | In-memory counter repository | Simple for single-instance; Redis for multi-instance can be added later |
| 22-01 | Close actions bypass all risk checks | Closing positions should never be blocked for risk reasons |
| 22-01 | Evaluate each account individually for risk | Allows partial execution when some accounts blocked |
| 22-01 | Log all rejections to database | Provides audit trail and analytics for users |
| 22-02 | Four position sizing modes | Fixed, percent_balance, percent_equity, risk_based cover all trading styles |
| 22-02 | Default symbol specs for 30+ instruments | Forex, indices, futures defaults with broker API fallback |
| 22-02 | Auto-refresh balance after trades | Ensures accurate dynamic position sizing for next trade |
| 22-02 | Graceful fallback for position sizing | Use signal quantity if calculation fails, prevents trade rejection |
| 22-03 | Daily P&L tracks realized and unrealized separately | Total P&L = realized + unrealized for accurate loss limit checks |
| 22-03 | Drawdown from peak equity (high water mark) | More accurate than starting balance, tracks true account performance |
| 22-03 | Risk-reward bypasses if no SL/TP | Allows flexibility for signals without explicit stop/target prices |
| 22-03 | Risk services are optional dependencies | Graceful degradation for backward compatibility |
| 22-03 | Daily loss limits halt trading until next day | Prevents cascading losses, resets on new trading day |
| 22-04 | Global risk settings on User model | Provides defaults for all accounts with per-account override capability |
| 22-04 | Dashboard summary aggregates all accounts | Single API call efficiency, calculates usage percentages |
| 22-04 | Progress bar color thresholds at 80%/90% | Visual warning system: amber at 80%, red at 90% before hard limits |
| 23-01 | Username read-only in profile form | Cannot be changed after registration |
| 23-01 | Email uniqueness validation on update | Prevents duplicate emails |
| 23-01 | Password strength 5-factor scoring | Length(8+, 12+), mixed case, digits, special chars |
| 23-02 | Curated timezone list for dropdown | 30+ common timezones instead of full pytz list (500+) for better UX |
| 23-02 | Master email toggle disables child toggles | When email_notifications off, all sub-toggles disabled |
| 23-02 | Real-time clock preview | Updates every second to show timezone selection effect immediately |
| 23-02 | BFF pattern for preferences API | Secure cookie-based auth, proxies to backend |
| 23-04 | Skeleton components match grid layouts | Prevent layout shift during loading |
| 23-04 | WebSocket subscribeToSignals/subscribeToOrders | Real-time dashboard stat updates |
| 23-04 | 2-second pulse animation for updates | Visual feedback when stats change |
| 23-04 | Test webhook returns 200 on backend errors | Graceful frontend error handling |
| 23-05 | recharts AreaChart for equity visualization | Color-coded gradient (green positive, red negative) |
| 23-05 | Time range selector 7d/30d/90d | User can view different equity history periods |
| 23-05 | Backend dashboard router for widget endpoints | Single router file with executions, equity, positions endpoints |
| 23-05 | Dashboard layout reorganized into rows | Stats, Equity+Trial, Brokers, Positions+Executions, Risk widgets |
| 23-03 | next-themes with attribute="class" | Tailwind CSS uses class-based dark mode |
| 23-03 | UserProvider inside WebSocketProvider | User context available to all dashboard components |
| 23-03 | useUser hook returns { user, loading, error, refetch } | Standard pattern for data fetching hooks |
| 24-06 | Handle different broker ID formats dynamically | TradeLocker (numeric), ProjectX (alphanumeric), Tradovate (numeric), MetaAPI (UUID) |
| 24-06 | Use existing is_signal_enabled field for account selection | TradingAccount model already has is_signal_enabled boolean field |
| 24-06 | Three routing modes: specific account, broker type, all selected | Covers all use cases from single account to broadcast |
| 24-02 | 4-tier model uses tier_1, tier_2, tier_3, tier_4 identifiers | Consistent naming for pricing tiers with numeric suffix |
| 24-02 | Legacy plan="pro" maps to tier_3 for backward compatibility | Existing users with "pro" continue working |
| 24-02 | Broker limits: tier_1=1, tier_2=2, tier_3=3, tier_4=4 | Each tier unlocks one additional broker connection |
| 24-02 | Broker limit exceeded returns 402 Payment Required | More appropriate HTTP status for payment-gated features |

## Known Tech Debt

- ~~Dashboard stats use placeholder data~~ (FIXED in 12-02)
- WebSocket event bridge incomplete (workaround: manual ws_manager calls)
- asyncpg not installed (graceful degradation)
- npm audit: 3 high severity vulnerabilities (dev-only, eslint-related)
- Alembic has multiple heads (001, 002)
- ~~Base URL hardcoded in some UI routes~~ (FIXED in 12-01)

## Session Continuity

Last session: 2026-01-22
Stopped at: Completed 24-02-PLAN.md (4-Tier Pricing Backend)
Resume file: None
Status: Phase 24 Wave 1 in progress (5/8 complete)

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

1. **Phase 24 (Enhanced Features & Monetization v2)** - IN PROGRESS (5/8 plans)

   **Wave 1 (parallel) - 5/5 COMPLETE:**
   - 24-01: Trial System Backend - COMPLETE
   - 24-02: 4-Tier Pricing Backend - COMPLETE
   - 24-03: Signal Deduplication - COMPLETE
   - 24-06: Broker Account Selection Backend - COMPLETE
   - 24-08: Landing Page Enhancements - COMPLETE

   **Wave 2 (depends on Wave 1) - 0/3 PENDING:**
   - 24-04: Trial UI & Upgrade Prompts (TRIAL-04, TRIAL-06, TRIAL-07)
   - 24-05: 4-Tier Pricing UI (BILL-09)
   - 24-07: Broker Account Selection UI (ACCT-11, ACCT-12)

2. Run `/gsd:execute-plan 24-04` to begin Wave 2
