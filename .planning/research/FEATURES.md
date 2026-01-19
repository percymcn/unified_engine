# Features Research: Trading Signal Routing Dashboard

## Question

What features do trading signal routing dashboards typically have? Specifically:
1. What's table stakes (users expect it)?
2. What's differentiating (competitive advantage)?
3. What should we NOT build (anti-features)?

**Research Date:** 2026-01-19
**Confidence:** MEDIUM (verified through multiple sources, cross-referenced professional platforms)

## Summary

Trading signal routing dashboards serve as command centers for automated trading operations. Research reveals a clear hierarchy of features: **real-time monitoring and execution status are non-negotiable**, **audit trails and multi-account management provide competitive differentiation**, and **over-engineering analytics tools or trying to replace TradingView are anti-patterns**.

Professional traders using signal routing platforms prioritize **speed, reliability, and transparency** over feature quantity. The most successful platforms focus on doing the core routing/monitoring exceptionally well rather than building comprehensive trading suites.

---

## Findings

### Table Stakes (Must Have)

Features users absolutely expect—missing any of these means users will leave for competitors.

| Feature | Why Required | Complexity | Notes |
|---------|--------------|------------|-------|
| **Real-time Signal Feed** | Users need instant visibility when webhooks arrive; delays cause missed opportunities | LOW | Display incoming webhooks as they arrive with timestamp, source, and payload preview |
| **Execution Status Per Broker** | Users must know if signal executed successfully on each broker | MEDIUM | Per-broker status: success/failure/pending, with error messages |
| **Broker Health Monitoring** | Connection drops cause missed trades; users need immediate notification | MEDIUM | Connection status (online/offline), latency tracking, uptime percentage |
| **Trade Log/History** | Regulatory requirement; users need audit trail for tax/compliance | LOW-MEDIUM | Filterable log of all signals received and execution outcomes |
| **Account Balance Display** | Users need current equity across all connected brokers | MEDIUM | Real-time balance updates via WebSocket, aggregated view optional |
| **Manual Trade Controls** | Users need ability to pause/resume signal routing per account | LOW | Per-account or global pause/resume toggle with confirmation |
| **Alert Notifications** | Critical failures must interrupt the user (broker disconnect, execution failure) | LOW | Browser notifications, with optional email/SMS for critical alerts |
| **Basic Filtering/Search** | Users need to find specific signals in history (by symbol, date, broker) | LOW | Search by ticker, date range, broker, execution status |
| **Responsive Layout** | Users monitor from multiple devices (desktop primary, mobile for monitoring) | LOW-MEDIUM | Must work on mobile for emergency monitoring, desktop for primary usage |
| **Security: 2FA** | Users are managing real trading accounts; 2FA is expected security baseline | MEDIUM | Two-factor authentication for login, encrypted connections (SSL/TLS) |

**Key Insight:** The table stakes list is shorter than typical trading platforms because this is a **routing dashboard, not a trading platform**. Users have TradingView for charting and analysis—they need routing reliability and transparency here.

### Differentiators (Competitive Advantage)

Features that provide competitive advantage and justify premium positioning.

| Feature | Value Add | Complexity | ROI Timing |
|---------|-----------|------------|------------|
| **Comprehensive Audit Trail** | Regulatory compliance; detailed order lifecycle tracking with timestamps at each stage | MEDIUM-HIGH | Phase 1-2 (required for serious traders) |
| **Multi-Account Position Aggregation** | Users with multiple prop firm accounts need consolidated P&L and exposure view | MEDIUM | Phase 2 (competitive differentiator) |
| **Signal Routing Rules** | Route different signals to different brokers based on conditions (symbol, time, account balance) | HIGH | Phase 3+ (advanced automation) |
| **Performance Analytics Dashboard** | Win rate, P&L breakdown by broker/strategy/symbol, execution latency stats | MEDIUM-HIGH | Phase 2-3 (data-driven traders value this) |
| **Webhook Replay/Testing** | Replay historical signals for testing without live execution; critical for strategy validation | MEDIUM | Phase 2 (reduces risk of configuration errors) |
| **Execution Quality Monitoring** | Track slippage, fill quality, latency per broker to identify best execution venues | HIGH | Phase 3+ (professional/institutional feature) |
| **Custom Alert Conditions** | User-defined alerts (e.g., "notify if 3 consecutive execution failures" or "warn if equity drops >5%") | MEDIUM | Phase 2-3 (power user feature) |
| **Trade Copying/Mirroring** | Distribute signals across multiple accounts with position sizing rules | MEDIUM-HIGH | Phase 2-3 (prop firm users need this) |
| **API Access** | Allow users to build custom integrations, export data programmatically | MEDIUM | Phase 3+ (appeals to technical users) |
| **Pre-trade Risk Checks** | Block signals that would violate risk rules (max position size, daily loss limit, symbol restrictions) | MEDIUM-HIGH | Phase 2 (risk management is premium feature) |

**Prioritization Recommendation:**
- **Phase 1:** Audit trail (compliance requirement)
- **Phase 2:** Multi-account aggregation, webhook replay, performance analytics (80% of competitive value)
- **Phase 3+:** Advanced routing rules, execution quality monitoring, API (20% of users, high technical complexity)

### Anti-Features (Don't Build)

Features that seem valuable but should be deliberately avoided—they distract from core value or compete with integrated tools.

| Feature | Why Avoid | Alternative |
|---------|-----------|-------------|
| **Built-in Charting** | Users already use TradingView; duplicating charts is wasted effort and can never match TradingView quality | Link to TradingView chart for each symbol instead |
| **Strategy Builder/Backtesting** | TradingView does this better; building comparable tool requires massive investment | Focus on execution transparency, not strategy creation |
| **Social/Copy Trading Network** | Extremely complex, requires different business model (signal provider marketplace), regulatory complications | Allow users to share webhook URLs, but don't host signal providers |
| **News Feed Integration** | Users have TradingView, broker platforms, or dedicated news services | Avoid duplicate information sources that clutter UI |
| **Economic Calendar** | Already available on TradingView, Forex Factory, broker platforms | Don't rebuild commodity information sources |
| **Advanced Technical Indicators** | This is TradingView's domain; users aren't analyzing here, they're monitoring execution | Show price/position only, no indicator calculations |
| **Paper Trading Environment** | Brokers provide this; duplicating requires simulating 5 different broker APIs | Use broker sandbox accounts instead, focus on webhook replay for testing |
| **Custom Charting Tools** | Massive scope creep; users expect TradingView-level sophistication if you provide any charting | Display simple price/P&L line charts only, not technical analysis |
| **Trade Idea Generation** | This is a routing dashboard, not a signal provider; users have signal sources already | Never suggest trades, only route and monitor them |
| **Extensive Customization (50+ settings)** | Analysis paralysis; too many options reduce usability | Provide sensible defaults with 5-10 key settings maximum |

**Design Principle:** This is a **routing and monitoring dashboard**, not a trading platform. Stay in your lane. TradingView generates signals, brokers execute them—you connect and monitor those two reliably.

---

## Feature Dependencies

Understanding dependencies helps phase planning and prevents rework.

### Dependency Map

```
Core Infrastructure (Phase 0-1)
├── Real-time Signal Feed
│   ├── Execution Status Per Broker (depends on feed to exist)
│   ├── Trade Log/History (depends on feed capture)
│   └── Alert Notifications (depends on status events)
│
├── Broker Health Monitoring
│   ├── Alert Notifications (broker offline triggers alert)
│   └── Execution Status (health affects status interpretation)
│
└── Account Balance Display
    └── Multi-Account Aggregation (requires per-account balance first)

Advanced Features (Phase 2+)
├── Trade Log/History (foundational)
│   ├── Performance Analytics (requires historical data)
│   ├── Webhook Replay (requires stored signal data)
│   └── Audit Trail (enhanced logging of trade log)
│
├── Performance Analytics
│   └── Execution Quality Monitoring (requires performance baseline)
│
└── Pre-trade Risk Checks
    ├── Account Balance Display (needed for risk calculations)
    └── Signal Routing Rules (risk is subset of routing logic)
```

### Critical Path

**Must build first (Phase 1):**
1. Real-time Signal Feed
2. Broker Health Monitoring
3. Execution Status Per Broker
4. Trade Log/History

Everything else depends on these four being solid.

---

## Recommendations for This Project

### Priority 1: Phase 1 MVP (Must Have for Launch)

**Core monitoring and execution visibility:**
- Real-time signal feed display
- Per-broker execution status with error messages
- Broker health monitoring (connection status, basic uptime)
- Trade log with filtering (date, symbol, broker, status)
- Account balance display per broker
- Manual pause/resume controls per account
- Alert notifications (browser notifications for failures)
- Basic security (2FA, encrypted connections)

**Success Metric:** User can monitor signal flow and identify execution failures in real-time.

### Priority 2: Phase 2 Enhancement (Competitive Differentiation)

**Audit and analytics features:**
- Comprehensive audit trail (detailed timestamps, order lifecycle)
- Multi-account position aggregation
- Performance analytics dashboard (win rate, P&L breakdown by broker/symbol)
- Webhook replay/testing mode
- Custom alert conditions

**Success Metric:** User can analyze performance, aggregate multi-account exposure, and test configurations safely.

### Priority 3: Phase 3+ Advanced (Power Users)

**Automation and quality features:**
- Signal routing rules (conditional routing logic)
- Pre-trade risk checks
- Execution quality monitoring (slippage, latency tracking)
- API access for custom integrations
- Trade copying/mirroring with position sizing

**Success Metric:** Power users can automate complex workflows and optimize execution quality.

### Defer to V2 or Never Build

**Out of scope:**
- Any charting beyond simple price/P&L line charts
- Strategy builder, backtesting, or trade idea generation
- Social/copy trading network
- News feeds, economic calendars
- Paper trading simulation (use broker sandboxes)

---

## Design Implications

### Information Hierarchy

Professional traders prioritize **signal transparency and broker reliability** over analytics. Dashboard layout should reflect this:

**Primary viewport (always visible):**
1. Broker health status (connection indicators)
2. Live signal feed (most recent 10-20 signals)
3. Critical alerts (failures, disconnections)

**Secondary panels (tabbed or collapsible):**
1. Trade history/log
2. Account balances
3. Performance analytics (Phase 2+)

**Tertiary functions (settings/modals):**
1. Account management
2. Alert configuration
3. Routing rules (Phase 3+)

### Complexity Budget

**Anti-pattern warning:** Many trading dashboards fail by cramming too much information on screen, causing decision fatigue.

**Rule of thumb from research:** Traders should see what they **actually use daily**, not everything possible. For signal routing:
- Daily use: Signal feed, execution status, broker health
- Weekly use: Performance analytics, trade history
- Monthly use: Account management, settings

Don't show weekly/monthly functions in primary viewport.

### Mobile vs Desktop

**Desktop = Primary Interface:**
- Users monitor signals actively during trading hours
- Need full visibility: multi-panel layout, detailed logs
- Can support 20-30 signals visible simultaneously

**Mobile = Monitoring Only:**
- Emergency monitoring outside trading hours
- Single-column layout showing critical info only
- Focus: broker health, recent signals, critical alerts
- Don't try to replicate desktop feature set

---

## Validation Gaps

Areas where research was limited and assumptions should be validated with users:

### Medium Confidence Areas

1. **Multi-account aggregation priority:** Research shows prop firm traders use multiple accounts, but unclear what % of target users need this vs single-account monitoring
   - **Recommendation:** Survey early users; defer to Phase 2 if <30% need it immediately

2. **Performance analytics depth:** Unclear which specific metrics matter most (win rate? latency? slippage?)
   - **Recommendation:** Start with basic P&L breakdown, add metrics based on user requests

3. **Webhook replay value:** Assumed high value for testing, but no direct user validation
   - **Recommendation:** Build simple version in Phase 2, gauge usage before investing in advanced features

### Low Confidence Areas (WebSearch Only)

1. **Execution quality monitoring:** Research mentions slippage/latency tracking, but unclear how to implement meaningfully with limited broker API data
   - **Recommendation:** Research broker API capabilities before committing to Phase 3

2. **API access demand:** Assumed technical users want API, but no validation of actual use cases
   - **Recommendation:** Phase 3+ only, gather requirements from early technical users first

---

## Sources

### Primary Sources (HIGH confidence)

- [Trading Dashboard: Essential Tools for Modern Market Analysis and Control](https://pocketoption.com/blog/en/interesting/trading-platforms/trading-dashboard/) - Comprehensive overview of professional dashboard requirements
- [SignalStack - Code-Free Order Automation Tools for Active Traders](https://signalstack.com/) - Direct competitor, feature comparison
- [How to configure webhook alerts — TradingView](https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/) - Official TradingView webhook documentation
- [Troubleshooting Webhook Issues in TradingView: A Comprehensive Guide](https://blog.traderspost.io/article/troubleshooting-webhook-issues-in-tradingview-a-comprehensive-guide) - Common issues and monitoring requirements
- [FINRA Rule 7360: Audit Trail Requirements](https://www.finra.org/rules-guidance/rulebooks/finra-rules/7360) - Regulatory requirements for trade logging

### Secondary Sources (MEDIUM confidence)

- [7+ Best Stock Market Dashboard Templates for 2026](https://tailadmin.com/blog/stock-market-dashboard-templates/) - Current dashboard design patterns
- [Best Trading Platforms in 2026 - Fee Comparison Included](https://brokerchooser.com/best-brokers/best-trading-platform) - Multi-broker platform comparison
- [5 Best Futures Trading Platforms (2026 Ranking)](https://www.newtrading.io/futures-trading-platforms/) - Professional platform features
- [Dashboard Anti-Patterns: 12 Mistakes—and the Patterns That Replace Them](https://startingblockonline.org/dashboard-anti-patterns-12-mistakes-and-the-patterns-that-replace-them/) - UI design anti-patterns
- [The Ultimate Guide to the 10 Most Important Trading Metrics](https://edgewonk.com/blog/the-ultimate-guide-to-the-10-most-important-trading-metrics) - Analytics prioritization
- [10 best trade monitoring software for RIAs](https://www.investmentnews.com/glossary/10-best-trade-monitoring-software-for-rias/262149) - Institutional monitoring features
- [The Ultimate Guide to Managing Multiple MT4 & MT5 Accounts Simultaneously](https://copygram.app/blog/education/ultimate-guide-manage-multiple-mt4-mt5-accounts) - Multi-account management patterns
- [How to Trade Multiple Accounts Simultaneously: Best Tips & Tools](https://www.quantvps.com/blog/trade-multiple-accounts-simultaneously) - Account switching UX patterns

### Tertiary Sources (LOW confidence - general guidance only)

- [Trading Dashboard for Advanced Traders - RBC Direct Investing](https://www.rbcdirectinvesting.com/trading-platforms/trading-dashboard.html) - General dashboard concepts
- [9 Best Trading Dashboard Examples for Smarter Trading Decisions](https://www.quantizeanalytics.co.uk/trading-dashboard-examples/) - Dashboard design examples
- [Best Futures Brokers with TradingView Connection in 2026](https://brokerchooser.com/best-brokers/best-futures-brokers-with-tradingview) - Integration patterns

---

## Metadata

**Research Methodology:**
- WebSearch: 13 queries covering dashboard features, signal routing platforms, multi-broker requirements, audit trails, and anti-patterns
- Cross-referenced findings across professional platforms (SignalStack, TradersPost, Interactive Brokers)
- Validated against regulatory requirements (FINRA audit trail rules)
- Compared desktop/institutional features vs retail/individual trader needs

**Confidence Breakdown:**
- Table stakes features: **HIGH** - Strong consensus across multiple platforms and sources
- Differentiators: **MEDIUM** - Identified from competitive analysis but need user validation for priority
- Anti-features: **HIGH** - Clear from dashboard anti-patterns research and competitive positioning
- Dependencies: **HIGH** - Logical technical dependencies verified with implementation patterns
- Recommendations: **MEDIUM** - Based on research but need validation with target user interviews

**Research Limitations:**
- No direct user interviews with target users (TradingView webhook users routing to multiple brokers)
- Limited information on broker-specific API capabilities (may affect execution status detail level)
- Assumed desktop-primary usage; mobile usage patterns not deeply researched
- Regulatory compliance requirements based on US regulations (FINRA); international requirements not researched

**Valid Until:** 2026-03-19 (60 days)
- Trading platform features are relatively stable
- Re-validate if major broker API changes or new competitors emerge
- Monitor TradingView webhook changes (they actively develop this feature)
