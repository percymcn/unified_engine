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

- [x] **SYM-01**: Handle symbol suffix variations (US30, US30.pro, US30PR, US30.raw)
- [x] **SYM-02**: Custom symbol mapping per broker (user configurable UI)
- [x] **SYM-03**: Auto-detect broker symbol format on connection
- [x] **SYM-04**: Symbol alias system (map TradingView symbol to each broker's format)
- [x] **SYM-05**: Support futures contract rollover (especially TopStep/ProjectX)
- [x] **SYM-06**: Contract expiration tracking and auto-roll notifications

### Multi-Account & Broker Selection

- [x] **ACCT-01**: Users can connect multiple accounts per broker
- [x] **ACCT-02**: Users can connect multiple brokers simultaneously
- [x] **ACCT-03**: Route signals to specific accounts or all accounts
- [x] **ACCT-04**: Per-account position sizing rules
- [x] **ACCT-05**: Per-account risk limits (max position, daily loss)
- [x] **ACCT-06**: Account grouping ("Prop Firm Accounts", "Personal Accounts")
- [ ] **ACCT-07**: TradeLocker SDK: Fetch all accounts (live, demo), checkbox selection UI
- [ ] **ACCT-08**: TopStep/ProjectX SDK: Fetch all accounts (live, evaluation, express)
- [ ] **ACCT-09**: Tradovate: Fetch all accounts via API, show type/status
- [ ] **ACCT-10**: MetaAPI (MT4/MT5): Fetch all connected accounts, show login/server/type
- [ ] **ACCT-11**: Checkbox list per broker - user picks which accounts receive signals
- [ ] **ACCT-12**: Support routing signals to multiple accounts simultaneously
- [ ] **ACCT-13**: Store selected account IDs per user in database
- [ ] **ACCT-14**: Handle different broker ID formats dynamically

### Broker SDKs (Full Implementation)

- [x] **SDK-01**: TradeLocker - 100% SDK coverage (all endpoints from official `tradelocker` package)
- [ ] **SDK-02**: Tradovate - Full OAuth + all trading/account/market data endpoints
- [x] **SDK-03**: TopStep/ProjectX - All contracts, rollovers, order types, positions via `project-x-py`
- [ ] **SDK-04**: MetaAPI (MT4/MT5) - Complete feature parity via `metaapi-cloud-sdk`
- [ ] **SDK-05**: Document all supported features per broker in UI
- [ ] **SDK-06**: Enterprise-complete: if SDK supports it, Tradeflow supports it

### Trading Features (Full SDK Coverage)

- [ ] **TRADE-01**: Order types: market, limit, stop, stop-limit (all SDKs)
- [ ] **TRADE-02**: Stop loss: fixed pips, fixed price, percentage
- [ ] **TRADE-03**: Take profit: fixed pips, fixed price, percentage
- [ ] **TRADE-04**: Trailing stop: fixed pips, percentage
- [ ] **TRADE-05**: Position sizing: fixed lot size mode
- [ ] **TRADE-06**: Position sizing: percentage of balance mode
- [ ] **TRADE-07**: Position sizing: percentage of equity mode
- [ ] **TRADE-08**: Position sizing: risk-based (X% risk per trade)
- [ ] **TRADE-09**: Partial close support
- [ ] **TRADE-10**: Modify existing orders (SL/TP adjustment)
- [ ] **TRADE-11**: Break-even automation
- [ ] **TRADE-12**: Research each SDK documentation for full feature list

### Signal Protection & Deduplication

- [ ] **SIGNAL-01**: Max positions per symbol (e.g., max 1 open position on US30)
- [ ] **SIGNAL-02**: Max total positions across all symbols (e.g., max 10 total)
- [ ] **SIGNAL-03**: Max trades per day per symbol
- [ ] **SIGNAL-04**: Max trades per day total
- [ ] **SIGNAL-05**: Signal cooldown per symbol (ignore same signal within X seconds)
- [ ] **SIGNAL-06**: If position already open for symbol, ignore duplicate entry signals
- [ ] **SIGNAL-07**: All signal limits configurable per user in settings
- [ ] **SIGNAL-08**: Log rejected signals with reason (duplicate, limit reached, etc.)
- [ ] **SIGNAL-09**: Dashboard shows rejected signal notifications with reasons

### Broker Connections

- [x] **CONN-01**: Connection status indicators (green/amber/red) for each broker
- [x] **CONN-02**: Connection test button to validate credentials before save
- [ ] **CONN-03**: Tradovate OAuth 2.0 redirect flow (/auth/tradovate/callback)
- [ ] **CONN-04**: Generic OAuth callback handler (/auth/callback)
- [x] **CONN-05**: Last sync timestamp visible per account
- [x] **CONN-06**: Clear error messages on connection failure

### Free Trial

- [ ] **TRIAL-01**: Free trial with dual limit: 100 trades OR 3 days (whichever first)
- [ ] **TRIAL-02**: Track trade count per user in database
- [ ] **TRIAL-03**: Track trial start date per user
- [ ] **TRIAL-04**: Dashboard shows remaining trades AND days left
- [ ] **TRIAL-05**: Block signal execution when either limit reached
- [ ] **TRIAL-06**: Show upgrade prompt when trial exhausted
- [ ] **TRIAL-07**: After trial expiry, user must select paid tier to continue

### Billing (4-Tier Pricing)

- [ ] **BILL-01**: Pricing page with 4-tier comparison
- [ ] **BILL-02**: Stripe Checkout integration (self-service purchase)
- [ ] **BILL-03**: Stripe Customer Portal (update payment, cancel, invoices)
- [ ] **BILL-04**: Tier 1: 1 broker - $19.99/month
- [ ] **BILL-05**: Tier 2: 2 brokers - $39.99/month
- [ ] **BILL-06**: Tier 3: 3 brokers - $69.99/month
- [ ] **BILL-07**: Tier 4: All 4 brokers (everything) - $129.99/month
- [ ] **BILL-08**: Update Stripe products/prices for all tiers
- [ ] **BILL-09**: Update landing page pricing section with all tiers
- [ ] **BILL-10**: Feature gating for broker count per tier
- [ ] **BILL-11**: Stripe webhook handling for subscription events

### Landing Page

- [ ] **LAND-01**: Modern 2026 enterprise-grade design
- [ ] **LAND-02**: Hero section with compelling value proposition
- [ ] **LAND-03**: Social proof (logos, testimonials, stats)
- [ ] **LAND-04**: Feature showcase with animations
- [ ] **LAND-05**: Clear, competitive pricing section (4 tiers)
- [ ] **LAND-06**: Trust signals (security badges, uptime stats)
- [ ] **LAND-07**: Mobile-first responsive design
- [ ] **LAND-08**: Fast loading, SEO optimized
- [ ] **LAND-09**: Competitor comparison section
- [ ] **LAND-10**: Live demo or video walkthrough
- [ ] **LAND-11**: Top-of-the-line polish that stands out in 2026 market
- [ ] **LAND-12**: Customer testimonials section (realistic placeholder reviews)
- [ ] **LAND-13**: Animated trading chart graphic (line chart moving up/down)
- [ ] **LAND-14**: Captivating social proof that converts visitors

### User Settings

- [ ] **SET-01**: User Profile page (edit name, email, avatar)
- [ ] **SET-02**: Password change form (current + new with validation)
- [ ] **SET-03**: Timezone selection dropdown for all timestamps
- [ ] **SET-04**: Notification preferences (trade alerts, errors, daily summary)
- [ ] **SET-05**: Dark/light mode toggle
- [ ] **SET-06**: Update/add credit card via Stripe customer portal
- [ ] **SET-07**: Dashboard header must show ACTUAL logged-in user's username/email

### Dashboard

- [ ] **DASH-01**: Loading skeletons for graceful loading states
- [ ] **DASH-02**: Real-time updates via WebSocket (fix existing)
- [ ] **DASH-03**: Connection status overview (all brokers at glance)
- [ ] **DASH-04**: Quick action: Test webhook button
- [ ] **DASH-05**: Today's trades count metric
- [ ] **DASH-06**: Recent executions list (last 10 trades)
- [ ] **DASH-07**: Equity chart (balance over time graph)
- [ ] **DASH-08**: Trial status display: "X trades remaining" or "X days left"
- [ ] **DASH-09**: Current open positions overview
- [ ] **DASH-10**: Risk usage meters (positions used vs max, daily trades vs max)
- [ ] **DASH-11**: Recent rejected signals with reasons

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
| SYM-01 | 20 | Complete |
| SYM-02 | 20 | Complete |
| SYM-03 | 20 | Complete |
| SYM-04 | 20 | Complete |
| SYM-05 | 20 | Complete |
| SYM-06 | 20 | Complete |
| ACCT-01 | 21 | Not started |
| ACCT-02 | 21 | Not started |
| ACCT-03 | 21 | Not started |
| ACCT-04 | 21 | Not started |
| ACCT-05 | 21 | Not started |
| ACCT-06 | 21 | Not started |
| ACCT-07 | 24 | Not started |
| ACCT-08 | 24 | Not started |
| ACCT-09 | 24 | Not started |
| ACCT-10 | 24 | Not started |
| ACCT-11 | 24 | Not started |
| ACCT-12 | 24 | Not started |
| ACCT-13 | 24 | Not started |
| ACCT-14 | 24 | Not started |
| TRADE-01 | 24 | Not started |
| TRADE-02 | 24 | Not started |
| TRADE-03 | 24 | Not started |
| TRADE-04 | 24 | Not started |
| TRADE-05 | 24 | Not started |
| TRADE-06 | 24 | Not started |
| TRADE-07 | 24 | Not started |
| TRADE-08 | 24 | Not started |
| TRADE-09 | 24 | Not started |
| TRADE-10 | 24 | Not started |
| TRADE-11 | 24 | Not started |
| TRADE-12 | 24 | Not started |
| SIGNAL-01 | 24 | Not started |
| SIGNAL-02 | 24 | Not started |
| SIGNAL-03 | 24 | Not started |
| SIGNAL-04 | 24 | Not started |
| SIGNAL-05 | 24 | Not started |
| SIGNAL-06 | 24 | Not started |
| SIGNAL-07 | 24 | Not started |
| SIGNAL-08 | 24 | Not started |
| SIGNAL-09 | 24 | Not started |
| TRIAL-01 | 24 | Not started |
| TRIAL-02 | 24 | Not started |
| TRIAL-03 | 24 | Not started |
| TRIAL-04 | 24 | Not started |
| TRIAL-05 | 24 | Not started |
| TRIAL-06 | 24 | Not started |
| TRIAL-07 | 24 | Not started |
| BILL-08 | 24 | Not started |
| BILL-09 | 24 | Not started |
| BILL-10 | 24 | Not started |
| BILL-11 | 24 | Not started |
| LAND-12 | 24 | Not started |
| LAND-13 | 24 | Not started |
| LAND-14 | 24 | Not started |
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
| SET-05 | 23 | Not started |
| SET-06 | 23 | Not started |
| SET-07 | 23 | Not started |
| DASH-01 | 23 | Not started |
| DASH-02 | 23 | Not started |
| DASH-03 | 23 | Not started |
| DASH-04 | 23 | Not started |
| DASH-05 | 23 | Not started |
| DASH-06 | 23 | Not started |
| DASH-07 | 23 | Not started |
| DASH-08 | 23 | Not started |
| DASH-09 | 23 | Not started |
| DASH-10 | 23 | Not started |
| DASH-11 | 23 | Not started |

**Coverage:**
- v1.1 requirements: 127 total
- Mapped to phases: 127
- Unmapped: 0

---
*Requirements defined: 2026-01-21*
*Last updated: 2026-01-21 after adding new Phase 24 requirements (TRIAL, TRADE, SIGNAL, ACCT, BILL, LAND enhancements)*
