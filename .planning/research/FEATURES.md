# Features Research: v1.1 Additions

**Researched:** 2026-01-20
**Domain:** Trading SaaS monetization + broker connectivity
**Confidence:** MEDIUM (WebSearch verified with official docs where available)

## Executive Summary

This research identifies the features users expect from trading SaaS products across billing, broker connections, user settings, and dashboard UX. The findings are based on competitive analysis of PineConnector, 3Commas, TradersPost, TradingView, and general SaaS best practices.

**Key insights:**
1. **Billing:** Self-service is table stakes. Stripe's customer portal handles 90% of subscription management needs. Feature gating should be simple (broker count, not complex credit systems).
2. **Broker connections:** Users expect OAuth where available, clear connection status indicators, and the ability to test connections before going live.
3. **User settings:** Timezone and notification preferences are mandatory. Position sizing defaults save time for active traders.
4. **Dashboard:** Real-time status indicators with color coding (green/amber/red), quick actions for common tasks, and execution logs are expected.

**Primary recommendation:** Implement Stripe Billing with customer portal for subscriptions. Gate by broker count (Free=1, Pro=unlimited). Focus on connection health indicators and webhook debugging tools as differentiators.

---

## Billing Features

### Table Stakes
*Must have or users will leave for competitors*

| Feature | Description | Complexity | Dependencies |
|---------|-------------|------------|--------------|
| Pricing page with tier comparison | Clear 2-3 tier display with feature comparison matrix | LOW | None |
| Monthly/annual billing toggle | Annual discount (typically 16-20%) shown on pricing page | LOW | Stripe |
| Self-service checkout | Users complete purchase without contacting sales | LOW | Stripe Checkout |
| Subscription management portal | Update payment, cancel, view invoices | LOW | Stripe Customer Portal |
| Plan upgrade/downgrade | Change tiers without contacting support | MEDIUM | Stripe, feature gating |
| Email receipts | Automatic invoice emails on charge | LOW | Stripe (built-in) |
| Failed payment recovery | Dunning emails for failed charges | LOW | Stripe (built-in) |

**Source:** [Stripe Billing Features](https://stripe.com/billing/features), [SaaS Pricing Best Practices](https://userpilot.com/blog/pricing-page-best-practices/)

### Differentiators
*Competitive advantage opportunities*

| Feature | Description | Complexity | Dependencies |
|---------|-------------|------------|--------------|
| Free tier with real value | 1 broker connection, limited webhooks, core functionality | MEDIUM | Feature gating system |
| Trial period (7-14 days) | Full Pro access before payment required | LOW | Stripe, user tracking |
| Pause instead of cancel | Recurly found 25% of pausers return vs cancelers | MEDIUM | Stripe, custom UI |
| Usage dashboard | Show webhooks processed, trades executed this period | MEDIUM | Analytics tracking |
| Transparent pricing (no "Contact Sales") | All pricing visible, no hidden enterprise tier | LOW | Pricing page design |

**Source:** [Recurly 2025 State of Subscriptions](https://niora.ai/subscription-management-saas/)

### Anti-features
*Things to deliberately NOT build*

| Anti-feature | Why to avoid | Alternative |
|--------------|--------------|-------------|
| Credit-based pricing | Confusing for users, hard to predict costs | Simple broker count gating |
| Complex usage metering | Overcomplicates billing, requires infrastructure | Flat tier pricing |
| Custom enterprise quotes | Adds sales overhead, delays conversion | Self-serve enterprise tier |
| Per-trade fees | Creates anxiety, discourages usage | Flat monthly subscription |
| Mandatory annual contracts | Increases friction, lower conversion | Monthly with annual discount |

---

## Broker Connection Features

### Table Stakes
*Users expect these from any broker integration service*

| Feature | Description | Complexity | Dependencies |
|---------|-------------|------------|--------------|
| Connection status indicator | Clear visual (green/amber/red) showing connection health | LOW | Broker health checks |
| Credential input form | Secure form for API key/password entry per broker type | LOW | Encrypted storage |
| Connection test button | "Test Connection" that validates credentials before save | MEDIUM | Broker API calls |
| Multiple accounts per broker | Support demo + live, or multiple prop accounts | MEDIUM | Account model |
| Disconnect/remove account | Clean removal with confirmation | LOW | Database cascade |
| Error messages on failure | Clear, actionable error when connection fails | LOW | Error handling |
| Last sync timestamp | Show when account was last successfully polled | LOW | Polling infrastructure |

**Broker-specific requirements:**

| Broker | Auth Type | Complexity | Notes |
|--------|-----------|------------|-------|
| TradeLocker | JWT (email/password/server) | MEDIUM | No OAuth, store credentials encrypted |
| Tradovate | OAuth 2.0 redirect | MEDIUM | Redirect flow, capture token callback |
| TopStep/ProjectX | API key + OAuth | MEDIUM | $29/mo API subscription required by user |
| MT4/MT5 | Login/password/server via MetaAPI | MEDIUM | MetaAPI cloud SDK handles connection |

**Source:** [TradeLocker API Docs](https://public-api.tradelocker.com/), [Tradovate OAuth Example](https://github.com/tradovate/example-api-oauth), [TopstepX API Access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)

### Differentiators

| Feature | Description | Complexity | Dependencies |
|---------|-------------|------------|--------------|
| OAuth flow (Tradovate) | Redirect to broker login instead of credential input | MEDIUM | OAuth callback pages |
| Connection health history | Graph showing uptime/latency over time | HIGH | Time-series storage |
| Automatic reconnection | Retry failed connections with backoff | MEDIUM | Background workers |
| Balance sync | Show real-time account balance from broker | LOW | Broker polling |
| Position sync | Show open positions pulled from broker | MEDIUM | Broker API, data model |
| Multi-account dashboard | View all accounts status in single view | LOW | UI design |
| Credential rotation reminders | Alert when tokens expire or need refresh | MEDIUM | Token expiry tracking |

### Anti-features (Broker Connections)

| Anti-feature | Why to avoid | Alternative |
|--------------|--------------|-------------|
| Storing master passwords in plain text | Security risk, compliance failure | Fernet encryption (already implemented) |
| Auto-trading without explicit consent | Legal/compliance issues, user distrust | Explicit "enable routing" toggle per account |
| Copying trades to brokers user didn't configure | Scope creep, potential financial harm | Only route to explicitly connected accounts |
| VPS/remote server execution (for prop firms) | Violates TopStep ToS, causes account suspension | Local execution only, warn users |

---

## User Settings Features

### Table Stakes
*Standard settings every trading app provides*

| Feature | Description | Complexity | Dependencies |
|---------|-------------|------------|--------------|
| Timezone selection | Dropdown to set user's timezone for all timestamps | LOW | User model field |
| Email notification preferences | On/off toggles for trade executions, errors, daily summary | LOW | User preferences model |
| Password change | Current + new password form with validation | LOW | Auth system |
| Email change | With email verification | MEDIUM | Email service |
| Profile info (name, avatar) | Basic profile customization | LOW | User model |
| Session management | View active sessions, logout other devices | MEDIUM | Session tracking |
| Delete account | GDPR compliance, full data removal | MEDIUM | Cascade deletes |

**Source:** [TradingView Settings](https://www.tradingview.com/), [TradeZella Settings](https://intercom.help/tradezella-4066d388d93c/en/articles/6497739-how-to-change-your-timezone-in-tradezella)

### Differentiators

| Feature | Description | Complexity | Dependencies |
|---------|-------------|------------|--------------|
| Default position sizing | Set default lot size per broker/instrument | LOW | User preferences |
| Risk rules (max position, daily loss limit) | Pre-trade checks before execution | HIGH | Trade execution layer |
| Webhook notification channel | Telegram/Discord/Slack integration for alerts | MEDIUM | Third-party integrations |
| API key management | Generate, revoke, view usage (already exists) | LOW | Already implemented |
| Execution mode (paper/live) | Global toggle for simulation mode | MEDIUM | Trade routing logic |
| Trade confirmation setting | Require confirm before execution vs auto-execute | MEDIUM | UI + backend flag |

### Anti-features (Settings)

| Anti-feature | Why to avoid | Alternative |
|--------------|--------------|-------------|
| Too many notification options | Decision paralysis, unused features | Simple on/off for major categories |
| Complex risk rule builder | Most users won't use, adds complexity | Simple max position + daily loss |
| Social features (following, sharing) | Scope creep, different product category | Stay focused on signal routing |

---

## Dashboard Features

### Table Stakes
*Expected dashboard elements for trading automation*

| Feature | Description | Complexity | Dependencies |
|---------|-------------|------------|--------------|
| Connection status overview | All broker connections with green/amber/red status | LOW | Health check polling |
| Today's trades count | Quick metric showing activity | LOW | Trade log queries |
| Recent executions list | Last 5-10 trades with status | LOW | Trade log |
| Webhook status indicator | Show if webhook endpoint is receiving signals | MEDIUM | Webhook tracking |
| Quick action: Test webhook | Send test signal to verify setup | LOW | Webhook endpoint |
| Quick action: View logs | Jump to execution logs | LOW | Navigation |
| Loading skeletons | Graceful loading states (already planned) | LOW | UI components |
| Real-time updates | WebSocket updates without page refresh | MEDIUM | WebSocket (exists) |

**Source:** [Dashboard UX Best Practices 2025](https://www.designrush.com/agency/ui-ux-design/dashboard/trends/dashboard-ux), [TradersPost Dashboard](https://traderspost.io/)

### Differentiators

| Feature | Description | Complexity | Dependencies |
|---------|-------------|------------|--------------|
| Webhook debug panel | View incoming webhooks with payload, test response | MEDIUM | Webhook logging |
| Signal trace | Follow signal from receipt -> routing -> execution | HIGH | Correlation tracking |
| Performance summary | Win rate, P&L (if available from broker) | HIGH | Broker position data |
| Uptime indicator | System health status (API, WebSocket, brokers) | LOW | Health endpoints |
| Quick connect new broker | Streamlined "Add Broker" flow from dashboard | LOW | Modal/wizard UI |
| Activity graph | Visual of signals/trades over time | MEDIUM | Chart library, data aggregation |

### Status Indicator Standards

Based on UX research, use consistent color coding:

| Color | Meaning | Use Cases |
|-------|---------|-----------|
| Green | Healthy, connected, success | Broker connected, trade executed |
| Amber/Yellow | Warning, degraded | Connection slow, partial failure |
| Red | Error, disconnected, failed | Broker disconnected, trade failed |
| Blue | Active, in progress | Trade pending, syncing |
| Gray | Inactive, paused | Account disabled, routing paused |

**Accessibility note:** Always pair colors with icons/text. Do not rely on color alone (color blindness consideration).

**Source:** [UI Indicators Best Practices](https://www.uinkits.com/blog-post/what-are-indicators-in-ui-design-and-how-to-use-them)

### Anti-features (Dashboard)

| Anti-feature | Why to avoid | Alternative |
|--------------|--------------|-------------|
| Charting/market data | Different product (TradingView does this) | Link to user's charting platform |
| Strategy builder | Scope creep, complex feature | Integrate with TradingView alerts |
| Social feed | Different product category | Stay focused on execution |
| Gamification (badges, streaks) | Trivializes serious trading activity | Clean, professional UI |

---

## Feature Dependencies

```
Stripe Integration
    |
    +-- Pricing Page (requires Stripe price IDs)
    +-- Checkout Flow (requires Stripe session creation)
    +-- Customer Portal (requires Stripe portal config)
    +-- Feature Gating (requires subscription status check)
            |
            +-- Broker Limit Enforcement
            +-- Plan Upgrade Prompts

Broker Connections
    |
    +-- Encrypted Credential Storage (exists)
    +-- Health Check Polling
    |       |
    |       +-- Connection Status Indicators
    |       +-- Dashboard Overview
    |
    +-- OAuth Callback Pages (Tradovate)
    |       |
    |       +-- Token Storage
    |       +-- Refresh Token Handling
    |
    +-- Trade Execution (depends on valid connection)

User Settings
    |
    +-- User Model Updates
    +-- Notification Preferences
    |       |
    |       +-- Email Service Integration
    |       +-- (Future) Telegram/Discord Integration
    |
    +-- Default Position Sizing
            |
            +-- Trade Execution (uses defaults)

Dashboard
    |
    +-- WebSocket Connection (exists)
    +-- Trade Logs (exists)
    +-- Health Endpoints (exists)
    +-- Webhook Logging (new)
            |
            +-- Debug Panel
```

---

## Complexity Assessment

| Feature | Complexity | Dependencies | Priority |
|---------|------------|--------------|----------|
| **Billing** | | | |
| Stripe Checkout integration | LOW | Stripe account | HIGH |
| Stripe Customer Portal | LOW | Stripe config | HIGH |
| Pricing page | LOW | None | HIGH |
| Feature gating (broker count) | MEDIUM | Subscription status | HIGH |
| Free tier implementation | MEDIUM | Feature gating | HIGH |
| **Broker Connections** | | | |
| Connection status indicators | LOW | Health checks | HIGH |
| Connection test button | MEDIUM | Broker APIs | HIGH |
| Tradovate OAuth flow | MEDIUM | Callback pages | HIGH |
| Balance/position sync | MEDIUM | Broker polling | MEDIUM |
| Connection health history | HIGH | Time-series data | LOW |
| **User Settings** | | | |
| Timezone selection | LOW | User model | HIGH |
| Notification preferences | LOW | User model | MEDIUM |
| Password change | LOW | Auth | MEDIUM |
| Default position sizing | LOW | User preferences | MEDIUM |
| Risk rules | HIGH | Execution layer | LOW |
| **Dashboard** | | | |
| Loading skeletons | LOW | UI components | HIGH |
| Webhook debug panel | MEDIUM | Logging | MEDIUM |
| Signal trace | HIGH | Correlation IDs | LOW |
| Activity graph | MEDIUM | Chart library | LOW |

---

## Competitive Landscape Summary

| Competitor | Pricing | Key Differentiator | What Tradeflow Should Learn |
|------------|---------|-------------------|----------------------------|
| PineConnector | One-time license ($99-$199) | MT4/MT5 focused, EA-based | Simple pricing works |
| TradersPost | $49-$199/mo | Multi-broker, stocks/futures | Dashboard UX, logs |
| 3Commas | $29-$99/mo | Signal bots, crypto focus | Multiple take-profit targets |
| Tickerly | $20-$50/mo | TradingView webhook relay | Webhook debugging tools |

**Tradeflow positioning:**
- Price: $29/mo Pro (competitive with 3Commas entry tier)
- Differentiator: Multi-broker including prop firms (TopStep), clean hexagonal architecture for reliability
- Table stakes: Must match TradersPost/PineConnector on connection status and execution logs

---

## Sources

### Primary (HIGH confidence)
- [Stripe Billing Features](https://stripe.com/billing/features)
- [Stripe Customer Portal Documentation](https://docs.stripe.com/customer-management)
- [TradeLocker API Documentation](https://public-api.tradelocker.com/)
- [Tradovate OAuth Example](https://github.com/tradovate/example-api-oauth)
- [TopstepX API Access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)

### Secondary (MEDIUM confidence)
- [Dashboard UX Best Practices 2025](https://www.designrush.com/agency/ui-ux-design/dashboard/trends/dashboard-ux) - DesignRush
- [SaaS Pricing Page Best Practices](https://userpilot.com/blog/pricing-page-best-practices/) - Userpilot
- [UI Indicators in Design](https://www.uinkits.com/blog-post/what-are-indicators-in-ui-design-and-how-to-use-them) - UIKits
- [TradersPost Platform](https://traderspost.io/) - Competitor reference
- [PineConnector](https://www.pineconnector.com/) - Competitor reference

### Tertiary (LOW confidence - WebSearch only)
- [Recurly 2025 State of Subscriptions](https://niora.ai/subscription-management-saas/) - Cited in secondary sources
- General SaaS pricing trends - Multiple blog sources

---

## Metadata

**Confidence breakdown:**
- Billing features: MEDIUM - Based on Stripe official docs + SaaS best practice articles
- Broker connections: HIGH for auth methods - Based on official API documentation
- User settings: MEDIUM - Based on competitor analysis
- Dashboard UX: MEDIUM - Based on UX research articles

**Research date:** 2026-01-20
**Valid until:** 2026-02-20 (30 days - billing/dashboard patterns stable)

**Open questions:**
1. TopStep API pricing ($29/mo) - Should Tradeflow absorb this or pass to user?
2. MT4/MT5 via MetaAPI - What's the per-account cost structure?
3. Risk rules complexity - Is simple max position enough, or do users expect more?
