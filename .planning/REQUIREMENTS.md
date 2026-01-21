# Requirements: Tradeflow

**Defined:** 2026-01-21
**Core Value:** Reliable signal-to-trade execution across all configured brokers with zero missed signals.

## v1.1 Requirements

Requirements for v1.1 Production Ready with Monetization release.

### Branding

- [ ] **BRAND-01**: Rename "Unified Engine" to "Tradeflow" everywhere (code, UI, docs, API responses)

### Infrastructure

- [ ] **INFRA-01**: Frontend accessible at https://tradeflow.fluxeo.net (port 3456)
- [ ] **INFRA-02**: Backend accessible at https://api.tradeflow.fluxeo.net (port 8765)
- [ ] **INFRA-03**: Backend bound to LAN IP for Caddy routing

### Critical Fixes

- [ ] **FIX-01**: Fix "Failed to fetch webhook configs" API error
- [ ] **FIX-02**: Use NEXT_PUBLIC_API_URL env var (no hardcoded localhost)
- [ ] **FIX-03**: Fix UI lag with loading skeletons and optimization
- [ ] **FIX-04**: Fix desktop sidebar navigation not clickable (works on mobile)
- [ ] **FIX-05**: Fix WebSocket "Disconnected" status
- [ ] **FIX-06**: Fix webhook URLs showing localhost (should show public domain)
- [ ] **FIX-07**: Fix dashboard showing "-" (fetch real data from backend)

### Symbol Mapping

- [ ] **SYM-01**: Handle symbol suffix variations (US30, US30.pro, US30PR, US30.raw)
- [ ] **SYM-02**: Custom symbol mapping per broker (user configurable UI)
- [ ] **SYM-03**: Auto-detect broker symbol format on connection
- [ ] **SYM-04**: Symbol alias system (map TradingView symbol to each broker's format)
- [ ] **SYM-05**: Support futures contract rollover (especially TopStep/ProjectX)
- [ ] **SYM-06**: Contract expiration tracking and auto-roll notifications

### Multi-Account

- [ ] **ACCT-01**: Users can connect multiple accounts per broker
- [ ] **ACCT-02**: Users can connect multiple brokers simultaneously
- [ ] **ACCT-03**: Route signals to specific accounts or all accounts
- [ ] **ACCT-04**: Per-account position sizing rules
- [ ] **ACCT-05**: Per-account risk limits (max position, daily loss)
- [ ] **ACCT-06**: Account grouping ("Prop Firm Accounts", "Personal Accounts")

### Broker SDKs (Full Implementation)

- [x] **SDK-01**: TradeLocker - 100% SDK coverage (all endpoints from official `tradelocker` package)
- [ ] **SDK-02**: Tradovate - Full OAuth + all trading/account/market data endpoints
- [x] **SDK-03**: TopStep/ProjectX - All contracts, rollovers, order types, positions via `project-x-py`
- [ ] **SDK-04**: MetaAPI (MT4/MT5) - Complete feature parity via `metaapi-cloud-sdk`
- [ ] **SDK-05**: Document all supported features per broker in UI
- [ ] **SDK-06**: Enterprise-complete: if SDK supports it, Tradeflow supports it

### Broker Connections

- [x] **CONN-01**: Connection status indicators (green/amber/red) for each broker
- [x] **CONN-02**: Connection test button to validate credentials before save
- [ ] **CONN-03**: Tradovate OAuth 2.0 redirect flow (/auth/tradovate/callback)
- [ ] **CONN-04**: Generic OAuth callback handler (/auth/callback)
- [x] **CONN-05**: Last sync timestamp visible per account
- [x] **CONN-06**: Clear error messages on connection failure

### Billing

- [ ] **BILL-01**: Pricing page with tier comparison (Free vs Pro)
- [ ] **BILL-02**: Stripe Checkout integration (self-service purchase)
- [ ] **BILL-03**: Stripe Customer Portal (update payment, cancel, invoices)
- [ ] **BILL-04**: Free tier with 1 broker connection limit
- [ ] **BILL-05**: Pro tier ($29/mo) with unlimited broker connections
- [ ] **BILL-06**: Stripe webhook handling for subscription events
- [ ] **BILL-07**: Feature gating based on subscription tier

### Landing Page

- [ ] **LAND-01**: Modern 2026 enterprise-grade design
- [ ] **LAND-02**: Hero section with compelling value proposition
- [ ] **LAND-03**: Social proof (logos, testimonials, stats)
- [ ] **LAND-04**: Feature showcase with animations
- [ ] **LAND-05**: Clear, competitive pricing section
- [ ] **LAND-06**: Trust signals (security badges, uptime stats)
- [ ] **LAND-07**: Mobile-first responsive design
- [ ] **LAND-08**: Fast loading, SEO optimized
- [ ] **LAND-09**: Competitor comparison section
- [ ] **LAND-10**: Live demo or video walkthrough
- [ ] **LAND-11**: Top-of-the-line polish that stands out in 2026 market

### User Settings

- [ ] **SET-01**: User Profile page (edit name, email, avatar)
- [ ] **SET-02**: Password change form (current + new with validation)
- [ ] **SET-03**: Timezone selection dropdown for all timestamps
- [ ] **SET-04**: Notification preferences (trade alerts, errors, daily summary)

### Dashboard

- [ ] **DASH-01**: Loading skeletons for graceful loading states
- [ ] **DASH-02**: Real-time updates via WebSocket (fix existing)
- [ ] **DASH-03**: Connection status overview (all brokers at glance)
- [ ] **DASH-04**: Quick action: Test webhook button
- [ ] **DASH-05**: Today's trades count metric
- [ ] **DASH-06**: Recent executions list (last 10 trades)

### UI Navigation

- [ ] **NAV-01**: Fix sidebar back button behavior
- [ ] **NAV-02**: Active state indicators on current page
- [ ] **NAV-03**: Mobile menu functionality

### Trade Control & Risk Management

- [ ] **RISK-01**: Maximum signals per day (configurable limit)
- [ ] **RISK-02**: Maximum concurrent trades per broker
- [ ] **RISK-03**: Maximum concurrent trades total (across all brokers)
- [ ] **RISK-04**: Block signals when any limit reached (with notification)
- [ ] **RISK-05**: Position sizing - fixed lot size
- [ ] **RISK-06**: Position sizing - percentage of balance
- [ ] **RISK-07**: Position sizing - percentage of equity
- [ ] **RISK-08**: Position sizing - risk per trade (pips/points based)
- [ ] **RISK-09**: Daily loss limit (stop trading if hit)
- [ ] **RISK-10**: Maximum drawdown limit (stop trading if hit)
- [ ] **RISK-11**: Per-symbol trade limits (max positions per instrument)
- [ ] **RISK-12**: Cooldown period between trades (configurable delay)
- [ ] **RISK-13**: Trade size scaling by balance (auto-adjust lot size)
- [ ] **RISK-14**: Risk-reward ratio enforcement (reject trades below threshold)
- [ ] **RISK-15**: All limits customizable per user (global defaults + overrides)
- [ ] **RISK-16**: Dashboard shows usage vs limits (visual progress bars)

## v2 Requirements

Deferred to v1.2+. Tracked but not in current roadmap.

### Advanced Billing

- **BILL-V2-01**: Annual billing option with discount (16-20% off)
- **BILL-V2-02**: Trial period (7-14 days Pro access)
- **BILL-V2-03**: Pause subscription instead of cancel
- **BILL-V2-04**: Usage dashboard (webhooks processed, trades executed)

### Advanced Broker Features

- **CONN-V2-01**: Connection health history graph (uptime/latency over time)
- **CONN-V2-02**: Automatic reconnection with exponential backoff
- **CONN-V2-03**: Credential rotation reminders (token expiry alerts)

### Advanced Settings

- **SET-V2-01**: Webhook notification channels (Telegram/Discord/Slack)
- **SET-V2-02**: Execution mode toggle (paper/live)
- **SET-V2-03**: Trade confirmation setting

### Advanced Dashboard

- **DASH-V2-01**: Webhook debug panel (view payloads, test responses)
- **DASH-V2-02**: Signal trace (follow signal from receipt to execution)
- **DASH-V2-03**: Performance summary (win rate, P&L)
- **DASH-V2-04**: Activity graph (signals/trades over time)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Mobile app | Web-first approach, PWA works |
| Additional broker integrations | Stabilize current 5 first |
| Multi-tenancy | Single-user/single-org for v1 |
| Credit-based pricing | Confusing, use simple tier gating |
| Per-trade fees | Creates anxiety, discourages usage |
| Charting/market data | TradingView does this better |
| Strategy builder | Scope creep, integrate with TradingView alerts |
| Social features | Different product category |
| Gamification | Trivializes serious trading |
| VPS/remote execution | Violates TopStep ToS |

## Traceability

Which phases cover which requirements. Updated by create-roadmap.

| Requirement | Phase | Status |
|-------------|-------|--------|
| BRAND-01 | 12 | Not started |
| INFRA-01 | 12 | Not started |
| INFRA-02 | 12 | Not started |
| INFRA-03 | 12 | Not started |
| FIX-01 | 12 | Not started |
| FIX-02 | 12 | Not started |
| FIX-03 | 12 | Not started |
| FIX-04 | 12 | Not started |
| FIX-05 | 12 | Not started |
| FIX-06 | 12 | Not started |
| FIX-07 | 12 | Not started |
| NAV-01 | 12 | Not started |
| NAV-02 | 12 | Not started |
| NAV-03 | 12 | Not started |
| BILL-01 | 13 | Not started |
| BILL-02 | 13 | Not started |
| BILL-03 | 13 | Not started |
| BILL-04 | 13 | Not started |
| BILL-05 | 13 | Not started |
| BILL-06 | 13 | Not started |
| BILL-07 | 13 | Not started |
| LAND-01 | 14 | Not started |
| LAND-02 | 14 | Not started |
| LAND-03 | 14 | Not started |
| LAND-04 | 14 | Not started |
| LAND-05 | 14 | Not started |
| LAND-06 | 14 | Not started |
| LAND-07 | 14 | Not started |
| LAND-08 | 14 | Not started |
| LAND-09 | 14 | Not started |
| LAND-10 | 14 | Not started |
| LAND-11 | 14 | Not started |
| SDK-01 | 15 | Complete |
| SDK-02 | 16 | Complete |
| CONN-03 | 16 | Complete |
| CONN-04 | 16 | Complete |
| SDK-03 | 17 | Complete |
| SDK-04 | 18 | Complete |
| SDK-05 | 18 | Complete |
| SDK-06 | 18 | Complete |
| CONN-01 | 19 | Complete |
| CONN-02 | 19 | Complete |
| CONN-05 | 19 | Complete |
| CONN-06 | 19 | Complete |
| SYM-01 | 20 | Not started |
| SYM-02 | 20 | Not started |
| SYM-03 | 20 | Not started |
| SYM-04 | 20 | Not started |
| SYM-05 | 20 | Not started |
| SYM-06 | 20 | Not started |
| ACCT-01 | 21 | Not started |
| ACCT-02 | 21 | Not started |
| ACCT-03 | 21 | Not started |
| ACCT-04 | 21 | Not started |
| ACCT-05 | 21 | Not started |
| ACCT-06 | 21 | Not started |
| RISK-01 | 22 | Not started |
| RISK-02 | 22 | Not started |
| RISK-03 | 22 | Not started |
| RISK-04 | 22 | Not started |
| RISK-05 | 22 | Not started |
| RISK-06 | 22 | Not started |
| RISK-07 | 22 | Not started |
| RISK-08 | 22 | Not started |
| RISK-09 | 22 | Not started |
| RISK-10 | 22 | Not started |
| RISK-11 | 22 | Not started |
| RISK-12 | 22 | Not started |
| RISK-13 | 22 | Not started |
| RISK-14 | 22 | Not started |
| RISK-15 | 22 | Not started |
| RISK-16 | 22 | Not started |
| SET-01 | 23 | Not started |
| SET-02 | 23 | Not started |
| SET-03 | 23 | Not started |
| SET-04 | 23 | Not started |
| DASH-01 | 23 | Not started |
| DASH-02 | 23 | Not started |
| DASH-03 | 23 | Not started |
| DASH-04 | 23 | Not started |
| DASH-05 | 23 | Not started |
| DASH-06 | 23 | Not started |

**Coverage:**
- v1.1 requirements: 82 total
- Mapped to phases: 82
- Unmapped: 0

---
*Requirements defined: 2026-01-21*
*Last updated: 2026-01-21 after initial definition*
