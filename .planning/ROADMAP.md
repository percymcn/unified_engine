# Roadmap: Tradeflow

## Overview

v1.1 transforms Tradeflow from a working signal router into a production-ready SaaS with Stripe monetization, official broker SDKs, comprehensive risk management, and enterprise-grade landing page. Starting from v1.0's hexagonal architecture foundation, we fix critical UI bugs, add billing infrastructure, migrate to official SDKs, implement symbol mapping and multi-account support, and build comprehensive trade controls.

## Milestones

- ✅ **v1.0 MVP** - Phases 1-11 (shipped 2026-01-21)
- 🚧 **v1.1 Production Ready** - Phases 12-23 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (12, 13, 14): Planned v1.1 work
- Decimal phases (12.1, 12.2): Urgent insertions if needed

- [x] **Phase 12: Critical Fixes & Infrastructure** - Fix broken UI, rebrand, configure public URLs
- [x] **Phase 13: Stripe Billing** - Payment infrastructure with checkout, portal, webhooks
- [x] **Phase 14: Landing Page** - Enterprise 2026 marketing page with pricing
- [x] **Phase 15: TradeLocker SDK** - Migrate to official tradelocker package
- [x] **Phase 16: Tradovate OAuth** - Custom OAuth 2.0 implementation
- [x] **Phase 17: TopStep/ProjectX SDK** - Migrate to project-x-py package
- [x] **Phase 18: MetaAPI SDK** - MT4/MT5 via metaapi-cloud-sdk
- [x] **Phase 19: Broker Connections UI** - Status indicators, test buttons, error handling
- [ ] **Phase 20: Symbol Mapping & Futures** - Symbol aliases, rollover, expiration tracking
- [ ] **Phase 21: Multi-Account & Routing** - Multiple accounts per broker, routing rules
- [ ] **Phase 22: Risk Management** - Trade limits, position sizing, drawdown controls
- [ ] **Phase 23: User Settings & Dashboard** - Profile, settings, dashboard polish

## Phase Details

### Phase 12: Critical Fixes & Infrastructure
**Goal**: Fix all broken UI functionality and configure production URLs
**Depends on**: v1.0 complete
**Requirements**: BRAND-01, INFRA-01, INFRA-02, INFRA-03, FIX-01, FIX-02, FIX-03, FIX-04, FIX-05, FIX-06, FIX-07, NAV-01, NAV-02, NAV-03
**Success Criteria** (what must be TRUE):
  1. All "Unified Engine" references renamed to "Tradeflow"
  2. Frontend accessible at https://tradeflow.fluxeo.net
  3. Backend accessible at https://api.tradeflow.fluxeo.net
  4. Desktop sidebar navigation fully clickable
  5. WebSocket shows "Connected" status
  6. Webhook URLs display public domain (not localhost)
  7. Dashboard metrics show real data (not "-")
**Research**: Unlikely (bug fixes, established patterns)
**Plans**: TBD

### Phase 13: Stripe Billing
**Goal**: Complete Stripe integration with checkout, portal, and subscription gating
**Depends on**: Phase 12
**Requirements**: BILL-01, BILL-02, BILL-03, BILL-04, BILL-05, BILL-06, BILL-07
**Success Criteria** (what must be TRUE):
  1. Pricing page shows Free vs Pro tier comparison
  2. User can complete checkout and subscribe to Pro
  3. User can access Stripe Customer Portal to manage subscription
  4. Free tier limits user to 1 broker connection
  5. Pro tier ($29/mo) allows unlimited broker connections
  6. Stripe webhooks update subscription status in database
  7. Feature gating enforces tier limits in UI and API
**Research**: Likely (external API)
**Research topics**: Stripe Checkout flow, Customer Portal setup, webhook best practices
**Plans**: TBD

### Phase 14: Landing Page
**Goal**: Enterprise-grade 2026 marketing page that converts visitors to customers
**Depends on**: Phase 13 (needs Stripe products configured)
**Requirements**: LAND-01, LAND-02, LAND-03, LAND-04, LAND-05, LAND-06, LAND-07, LAND-08, LAND-09, LAND-10, LAND-11
**Success Criteria** (what must be TRUE):
  1. Landing page at "/" with modern 2026 design
  2. Hero section clearly communicates value proposition
  3. Social proof section with testimonials/stats
  4. Feature showcase with smooth animations
  5. Pricing section links to Stripe checkout
  6. Page loads fast (<3s) and is SEO optimized
  7. Fully responsive on mobile devices
**Research**: Likely (design patterns, conversion optimization)
**Research topics**: 2026 SaaS landing page trends, animation libraries, SEO best practices
**Plans**: TBD

### Phase 15: TradeLocker SDK
**Goal**: Migrate TradeLocker adapter to official tradelocker Python SDK
**Depends on**: Phase 12
**Requirements**: SDK-01
**Success Criteria** (what must be TRUE):
  1. TradeLocker adapter uses official `tradelocker` package
  2. All existing TradeLocker functionality preserved
  3. JWT authentication via SDK (not custom implementation)
  4. Orders, positions, account data work via official SDK
**Research**: Likely (new SDK integration)
**Research topics**: tradelocker package API, authentication flow, available endpoints
**Plans**: TBD

### Phase 16: Tradovate OAuth
**Goal**: Implement Tradovate OAuth 2.0 redirect flow with token management
**Depends on**: Phase 12
**Requirements**: SDK-02, CONN-03, CONN-04
**Success Criteria** (what must be TRUE):
  1. User can initiate Tradovate OAuth from account connection page
  2. /auth/tradovate/callback handles OAuth redirect
  3. Access token stored securely (Fernet encrypted)
  4. Token refresh handles 1-hour expiry automatically
  5. All Tradovate trading/account endpoints work via custom adapter
**Research**: Likely (custom OAuth implementation, MEDIUM confidence)
**Research topics**: Tradovate OAuth flow, token refresh strategy, API endpoints
**Plans**: TBD

### Phase 17: TopStep/ProjectX SDK
**Goal**: Migrate TopStep adapter to official project-x-py SDK
**Depends on**: Phase 12
**Requirements**: SDK-03
**Success Criteria** (what must be TRUE):
  1. TopStep adapter uses official `project-x-py` package
  2. All contracts, order types, positions work via SDK
  3. Futures rollover handled correctly
  4. API key authentication working
**Research**: Likely (new SDK integration)
**Research topics**: project-x-py package API, futures contracts, rollover handling
**Plans**: TBD

### Phase 18: MetaAPI SDK
**Goal**: Complete MT4/MT5 integration via metaapi-cloud-sdk with feature documentation
**Depends on**: Phase 12
**Requirements**: SDK-04, SDK-05, SDK-06
**Success Criteria** (what must be TRUE):
  1. MetaAPI adapter uses official `metaapi-cloud-sdk`
  2. MT4 and MT5 accounts both work
  3. Real-time position/quote streaming functional
  4. All supported broker features documented in UI
  5. Feature parity: if SDK supports it, Tradeflow supports it
**Research**: Likely (new SDK integration)
**Research topics**: metaapi-cloud-sdk streaming API, MT4/MT5 differences
**Plans**: TBD

### Phase 19: Broker Connections UI
**Goal**: Polish broker connection experience with status, testing, and error handling
**Depends on**: Phases 15-18 (SDK migrations complete)
**Requirements**: CONN-01, CONN-02, CONN-05, CONN-06
**Success Criteria** (what must be TRUE):
  1. Connection status indicators (green/amber/red) for each broker
  2. "Test Connection" button validates credentials before save
  3. Last sync timestamp visible for each account
  4. Clear, actionable error messages on connection failure
**Research**: Unlikely (UI patterns, internal work)
**Plans**: 2 (19-01 Backend Test Endpoint, 19-02 Frontend Status UI)

### Phase 20: Symbol Mapping & Futures
**Goal**: Handle symbol variations across brokers with aliases and futures rollover
**Depends on**: Phase 19
**Requirements**: SYM-01, SYM-02, SYM-03, SYM-04, SYM-05, SYM-06
**Success Criteria** (what must be TRUE):
  1. Symbol suffix variations handled (US30, US30.pro, US30PR, US30.raw)
  2. Custom symbol mapping configurable per broker in UI
  3. System auto-detects broker symbol format on connection
  4. TradingView symbol maps to each broker's format via aliases
  5. Futures contract rollover supported (especially TopStep/ProjectX)
  6. Contract expiration tracking with auto-roll notifications
**Research**: Likely (broker-specific symbol formats)
**Research topics**: Each broker's symbol naming conventions, futures rollover dates
**Plans**: TBD

### Phase 21: Multi-Account & Routing
**Goal**: Support multiple accounts per broker with flexible signal routing
**Depends on**: Phase 20
**Requirements**: ACCT-01, ACCT-02, ACCT-03, ACCT-04, ACCT-05, ACCT-06
**Success Criteria** (what must be TRUE):
  1. User can connect multiple accounts per broker
  2. User can connect multiple brokers simultaneously
  3. Signal routing configurable: specific accounts or all accounts
  4. Per-account position sizing rules
  5. Per-account risk limits (max position, daily loss)
  6. Account grouping ("Prop Firm", "Personal") works
**Research**: Unlikely (extends existing patterns)
**Plans**: TBD

### Phase 22: Risk Management
**Goal**: Comprehensive trade controls with limits, sizing, and drawdown protection
**Depends on**: Phase 21
**Requirements**: RISK-01, RISK-02, RISK-03, RISK-04, RISK-05, RISK-06, RISK-07, RISK-08, RISK-09, RISK-10, RISK-11, RISK-12, RISK-13, RISK-14, RISK-15, RISK-16
**Success Criteria** (what must be TRUE):
  1. Maximum signals per day configurable and enforced
  2. Concurrent trade limits (per broker and total) enforced
  3. Signals blocked when limits reached (with notification)
  4. Position sizing works: fixed lot, % balance, % equity, risk per trade
  5. Daily loss limit stops trading when hit
  6. Maximum drawdown limit stops trading when hit
  7. Per-symbol trade limits enforced
  8. Cooldown period between trades configurable
  9. Trade size scales with balance (auto-adjust)
  10. Risk-reward ratio enforcement works
  11. All limits customizable per user
  12. Dashboard shows usage vs limits (progress bars)
**Research**: Likely (trading risk patterns)
**Research topics**: Risk management best practices, position sizing formulas
**Plans**: TBD

### Phase 23: User Settings & Dashboard
**Goal**: Polish user experience with profile, settings, and dashboard improvements
**Depends on**: Phase 22
**Requirements**: SET-01, SET-02, SET-03, SET-04, DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06
**Success Criteria** (what must be TRUE):
  1. User Profile page allows editing name, email, avatar
  2. Password change works with validation
  3. Timezone selection affects all displayed timestamps
  4. Notification preferences configurable
  5. Dashboard has loading skeletons
  6. WebSocket real-time updates work
  7. Connection status overview shows all brokers at glance
  8. Test webhook quick action works
  9. Today's trades count metric displayed
  10. Recent executions list shows last 10 trades
**Research**: Unlikely (UI polish, established patterns)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 12 → 13 → 14 → 15 → 16 → 17 → 18 → 19 → 20 → 21 → 22 → 23

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 12. Critical Fixes & Infrastructure | 5/5 | ✅ Complete | 2026-01-21 |
| 13. Stripe Billing | 6/6 | ✅ Complete | 2026-01-21 |
| 14. Landing Page | 7/7 | ✅ Complete | 2026-01-21 |
| 15. TradeLocker SDK | 1/1 | ✅ Complete | 2026-01-21 |
| 16. Tradovate OAuth | 4/4 | ✅ Complete | 2026-01-21 |
| 17. TopStep/ProjectX SDK | 1/1 | ✅ Complete | 2026-01-21 |
| 18. MetaAPI SDK | 1/1 | ✅ Complete | 2026-01-21 |
| 19. Broker Connections UI | 2/2 | ✅ Complete | 2026-01-21 |
| 20. Symbol Mapping & Futures | 0/TBD | Not started | - |
| 21. Multi-Account & Routing | 0/TBD | Not started | - |
| 22. Risk Management | 0/TBD | Not started | - |
| 23. User Settings & Dashboard | 0/TBD | Not started | - |

## Milestone Summary

### v1.1 Production Ready with Monetization

**Goal:** Transform Tradeflow into production-ready SaaS with Stripe billing, official broker SDKs, and comprehensive risk management.

**Phases:** 12 (Phase 12-23)
**Requirements:** 82 total

**Key Deliverables:**
1. Production URLs and branding complete
2. Stripe monetization (Free/Pro tiers)
3. Enterprise-grade landing page
4. All 4 broker SDKs using official packages
5. Symbol mapping and futures rollover
6. Multi-account support with routing
7. Complete risk management system
8. Polished user settings and dashboard
