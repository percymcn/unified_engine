# 🎯 TradeFlow Component Hierarchy & API Binding Map

## Visual Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     APP.TSX (Root Container)                         │
│  Theme: #002b36 bg, #00ffc2 accent, Inter/Outfit fonts             │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
        ┌───────▼────────┐            ┌────────▼─────────┐
        │  UserContext   │            │  BrokerContext   │
        │  (Auth/Role)   │            │  (TL/TS/TF)      │
        └───────┬────────┘            └────────┬─────────┘
                │                              │
                └──────────────┬───────────────┘
                               │
        ┌──────────────────────┴──────────────────────┐
        │                                             │
┌───────▼────────┐                          ┌────────▼─────────┐
│  Header         │                          │  Sidebar Nav     │
│  - Logo         │                          │  - 11 Sections   │
│  - User Badge   │                          │  - Role Filter   │
│  - Plan Badge   │                          │  - Active State  │
└────────────────┘                          └──────────────────┘
                                                     │
        ┌────────────────────────────────────────────┴────────────────┐
        │                    BROKER TABS                               │
        │  [TradeLocker] [Topstep] [TruForex]                         │
        └────────────────────────────────────────────────────────────┘
                                 │
        ┌────────────────────────┴────────────────────────────────────┐
        │                                                              │
        │               MAIN CONTENT AREA (Section Router)            │
        │                                                              │
        └──────────────────────────────────────────────────────────────┘
```

---

## 📊 SECTION 1: DASHBOARD (Overview)

### Component: `DashboardOverview`
**Route Context**: Multi-broker aggregation view  
**Theme**: Cards with rounded-lg, #001f29 bg, #00ffc2 borders

#### Sub-Components & API Bindings:

```
DashboardOverview/
├── MetricsGrid (4 cards)
│   ├── ActiveOrdersCard
│   │   └── GET /api/unify/v1/orders?status=PENDING
│   │       • UI: Card with count badge
│   │       • Refresh: Real-time (Supabase channel: orders:userId)
│   │       • Visual: #00ffc2 count, TrendingUp icon
│   │
│   ├── OpenPositionsCard
│   │   └── GET /api/unify/v1/positions
│   │       • UI: Card with count + total value
│   │       • Refresh: Real-time (Supabase channel: positions:userId)
│   │       • Visual: Green/Red P&L color coding
│   │
│   ├── DailyPnLCard
│   │   └── GET /api/unify/v1/positions (calculate sum unrealized_pnl)
│   │       • UI: Card with +/- indicator
│   │       • Refresh: Every 5s (position price updates)
│   │       • Visual: Animated number changes
│   │
│   └── AccountValueCard
│       └── GET Supabase: broker_accounts.equity (sum)
│           • UI: Card with sparkline chart
│           • Refresh: On sync
│           • Visual: Mini equity curve
│
├── HealthStatusBanner (NEW)
│   └── GET /api/unify/v1/health
│       • UI: Top banner (hidden if healthy)
│       • Colors: Green/Yellow/Red based on status
│       • Display: Broker-level health breakdown
│       • Polling: Every 60s
│
├── RiskHeatmapWidget (NEW)
│   └── GET Supabase: positions (with real-time)
│       • UI: Treemap chart (recharts)
│       • Size: Notional value (qty * price)
│       • Color: P&L gradient (red → green)
│       • Interactive: Click → filter PositionsMonitor
│
├── EquityCurveChart (NEW)
│   └── GET Supabase: equity_history
│       • WHERE: user_id, broker, last 90 days
│       • UI: LineChart (recharts)
│       • Lines: equity (solid), balance (dashed)
│       • Real-time: Insert events append new points
│
├── RecentActivityTable
│   └── GET Supabase: orders + positions (UNION, ORDER BY timestamp DESC LIMIT 10)
│       • UI: Table with status badges
│       • Real-time: Both channels
│       • Actions: Click row → navigate to detail
│
└── QuickActionsBar
    ├── SyncAllButton
    │   └── POST /api/unify/v1/sync/all
    │       • UI: Button with loading state
    │       • Action: Sync all broker accounts
    │
    ├── TestWebhookButton
    │   └── POST /api/unify/v1/test-webhook
    │       • UI: Button → Modal with JSON editor
    │       • Action: Validate webhook payload
    │
    └── ExportDataButton
        └── GET Supabase: orders + positions (CSV export)
            • UI: Button with download icon
            • Action: Client-side CSV generation
```

**Data Flow:**
```
┌──────────────┐
│   Supabase   │ ──Real-time──> DashboardOverview
│   Tables     │                      │
└──────────────┘                      ├─> MetricsGrid
                                      ├─> RiskHeatmap
┌──────────────┐                      ├─> EquityCurve
│  /health API │ ──Polling (60s)──>  └─> HealthBanner
└──────────────┘
```

---

## 📝 SECTION 2: ACCOUNTS

### Component: `AccountsManager`
**Route Context**: Broker registration & connection management  
**Per-Broker**: Yes (TradeLocker, Topstep, TruForex)

#### Sub-Components & API Bindings:

```
AccountsManager/
├── ConnectedAccountsList
│   └── GET Supabase: broker_accounts WHERE user_id = current AND broker = selected
│       • UI: Card list with status badges
│       • Fields: account_name, balance, equity, last_sync, status
│       • Actions: [Edit] [Sync] [Delete]
│       • Real-time: broker_accounts channel (balance/equity updates)
│
├── RegistrationForms (Per-Broker)
│   ├── TradeLockerForm
│   │   └── POST /register/tradelocker
│   │       • UI: Modal form
│   │       • Fields: email, password, server, account_id
│   │       • Response: api_key (shown once!)
│   │       • Action: INSERT broker_accounts (credentials encrypted)
│   │
│   ├── TopstepForm
│   │   └── POST /register/topstep
│   │       • UI: Modal form
│   │       • Fields: username, password, account_number
│   │       • Response: api_key
│   │
│   └── TruForexForm
│       └── POST /register/truforex
│           • UI: Modal form
│           • Fields: mt_version (4/5), server, login, password
│           • Response: api_key
│
├── ApiKeyDisplay (One-Time)
│   • UI: Alert card with copy button
│   • Warning: "Save this key, it won't be shown again"
│   • Copy to clipboard with toast confirmation
│
├── SyncButtons
│   ├── SyncAccountButton
│   │   └── POST /sync/{broker}/{account_id}
│   │       • UI: Button with spinner
│   │       • Updates: balance, equity, last_sync
│   │
│   └── SyncAllBrokerButton
│       └── POST /sync/all/{broker}
│           • UI: Button (sync all accounts for broker)
│
└── DeleteAccountModal
    └── DELETE Supabase: broker_accounts WHERE id = selected
        • UI: Confirmation modal
        • Warning: "This will delete API keys and disconnect broker"
        • CASCADE: Also deletes related orders, positions
```

**Data Flow:**
```
┌─────────────────┐
│ Registration    │
│ Form (Modal)    │
└────────┬────────┘
         │ POST /register/{broker}
         ▼
┌─────────────────┐
│ Backend Server  │ ──Encrypt─> Store credentials
│ (Supabase Edge) │             │
└────────┬────────┘             ▼
         │                 ┌──────────────┐
         │ Return api_key  │   Supabase   │
         ▼                 │ broker_acc.. │
┌─────────────────┐        └──────────────┘
│ ApiKeyDisplay   │
│ (One-Time Show) │
└─────────────────┘
```

---

## 🔗 SECTION 3: WEBHOOKS

### Component: `WebhookTemplates`
**Route Context**: TradingView integration & webhook management  
**Per-Broker**: Yes (different JSON templates per broker)

#### Sub-Components & API Bindings:

```
WebhookTemplates/
├── WebhookURLDisplay
│   └── GET Supabase: broker_accounts.api_key (construct URL)
│       • URL Format: https://api.empiretrading.io/api/unify/v1/webhook/{broker}
│       • Auth Header: Bearer {api_key}
│       • UI: Card with copy button
│       • Visual: Code block with syntax highlighting
│
├── SigningSecretDisplay (NEW)
│   └── GET Supabase: broker_accounts.credentials_encrypted (extract webhook_secret)
│       • UI: Masked string with reveal button
│       • Copy: Full secret on click
│       • HMAC: Used for signature generation
│
├── TemplateGallery
│   ├── TemplateCategory: "Entries"
│   │   ├── MarketBuyTemplate
│   │   ├── MarketSellTemplate
│   │   ├── LimitEntryTemplate
│   │   └── StopEntryTemplate
│   │       • UI: Grid of template cards
│   │       • Each: JSON snippet + [Copy] button
│   │       • Auto-inject: api_key, webhook_secret
│   │
│   ├── TemplateCategory: "Exits"
│   │   ├── PartialCloseTemplate
│   │   └── CloseAllTemplate
│   │
│   └── TemplateCategory: "Modifications"
│       ├── SetStopLossTemplate
│       ├── SetTakeProfitTemplate
│       └── TrailingStopTemplate
│
├── TestAlertPlayground (NEW MAJOR COMPONENT)
│   ├── JSONEditor
│   │   • UI: Textarea with Monaco editor
│   │   • Syntax: JSON validation
│   │   • Placeholder: Pre-filled template
│   │
│   ├── TestWebhookButton
│   │   └── POST /api/unify/v1/test-webhook
│   │       • Validation only (no execution)
│   │       • Returns: Parsed order + validation errors
│   │
│   ├── ValidationResults
│   │   • UI: Alert cards (success/error)
│   │   • Errors: List with field names + reasons
│   │
│   └── OrderPreview (NEW)
│       • UI: Visual card showing:
│         - Entry Price: ${price or 'Market'}
│         - Stop Loss: ${sl} (distance, pips)
│         - Take Profit: ${tp} (R:R ratio)
│         - Position Size: ${qty} lots
│         - Risk: $${risk_usd} (${risk_pct}%)
│       • Visual: Mini chart with SL/TP lines
│       • Library: Lightweight Charts
│
├── DirectAPIExamples (NEW)
│   └── Language Tabs: [cURL] [Python] [Node.js]
│       • UI: Code blocks with copy buttons
│       • Examples: Equivalent REST API calls
│
└── WebhookHistoryTable
    └── GET Supabase: webhook_events ORDER BY received_at DESC LIMIT 50
        • UI: Table with expand rows
        • Columns: timestamp, source, status, signature_valid
        • Expand: Show full payload (JSON pretty-print)
        • Filter: By broker, processed status
```

**Data Flow:**
```
┌──────────────────┐
│  TradingView     │
│  Alert Webhook   │
└────────┬─────────┘
         │ POST with signature
         ▼
┌──────────────────────┐
│ /webhook/{broker}    │
│ Verify HMAC-SHA256   │ ──Log──> webhook_events table
└────────┬─────────────┘
         │ Valid
         ▼
┌──────────────────────┐
│ Order Executor       │
│ (Risk Check)         │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Broker API           │
│ (Place Order)        │ ──Log──> orders table
└──────────────────────┘
```

---

## 📊 SECTION 4: TRADING CONFIGURATION

### Component: `TradingConfiguration`
**Route Context**: SL/TP/lot size settings per broker  
**Per-Broker**: Yes (different constraints per broker)

#### Sub-Components & API Bindings:

```
TradingConfiguration/
├── LotSizingConfig
│   ├── LotSizeModeToggle
│   │   • UI: Radio group [Fixed Lots] [% of Account]
│   │   • Binding: trading_config.lot_size_mode
│   │
│   ├── FixedLotSizeSlider
│   │   └── PUT Supabase: trading_config.fixed_lot_size
│   │       • UI: Slider (0.01 - 10.00, step 0.01)
│   │       • Visual: Live value display
│   │       • Validation: Broker min/max enforcement
│   │
│   └── PercentageLotSizeSlider
│       └── PUT Supabase: trading_config.percentage_lot_size
│           • UI: Slider (0.01% - 10.00%, step 0.01)
│           • Calculation: Auto-calc lots from account balance
│
├── StopLossConfig
│   ├── SLModeToggle
│   │   • UI: Radio [Percentage] [Pips] [ATR] [R:R]
│   │   • Binding: trading_config.sl_mode
│   │
│   ├── SLPercentageSlider
│   │   └── PUT Supabase: trading_config.sl_percentage
│   │       • Range: 0.01% - 10.00%
│   │       • Step: 0.01%
│   │
│   ├── SLPipsSlider
│   │   └── PUT Supabase: trading_config.sl_pips
│   │       • Range: 0.1 - 200.0 pips
│   │       • Step: 0.1
│   │
│   └── TrailingStopConfig
│       ├── UseTrailingToggle (Switch)
│       └── TrailingDistanceSlider
│           └── PUT Supabase: trading_config.trailing_sl_distance
│               • Range: 0.01% - 5.00%
│
├── TakeProfitConfig
│   ├── TPModeToggle
│   │   • UI: Radio [Percentage] [Pips] [R:R]
│   │
│   ├── TPPercentageSlider
│   │   └── PUT Supabase: trading_config.tp_percentage
│   │       • Range: 0.01% - 20.00%
│   │
│   ├── RiskRewardSlider
│   │   └── PUT Supabase: trading_config.risk_reward_ratio
│   │       • Range: 0.01:1 - 5.00:1
│   │       • Visual: "1:2.5" format display
│   │
│   └── PartialTPConfig
│       ├── UsePartialTPToggle
│       ├── PartialTPPercentSlider (1% - 99%)
│       └── PartialTPLevelSlider (0.01% - 5.00%)
│           • All: PUT Supabase: trading_config
│
├── PresetButtons (NEW)
│   ├── ConservativePreset
│   │   • SL: 1%, TP: 2%, R:R 2:1
│   ├── BalancedPreset
│   │   • SL: 2%, TP: 4%, R:R 2:1
│   └── AggressivePreset
│       • SL: 3%, TP: 9%, R:R 3:1
│       • UI: Buttons that update all sliders at once
│
├── BrokerConstraintsInfo (NEW)
│   └── Display based on selected broker:
│       • TradeLocker: Min 0.01, Max 100 lots
│       • Topstep: Min 1, Max 50 contracts
│       • TruForex: Min 0.01 lots = 1,000 units
│       • UI: Info alert card
│
└── SaveConfigButton
    └── PUT Supabase: trading_config (full record)
        • UI: Primary button (sticky to bottom)
        • Toast: "Configuration saved successfully"
        • Validation: All values within broker limits
```

**Data Flow:**
```
┌──────────────────┐
│  Slider Change   │
└────────┬─────────┘
         │ Debounce 300ms
         ▼
┌──────────────────┐
│  Validate Range  │
│  (Broker Limits) │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ PUT Supabase     │
│ trading_config   │ ──Update──> Database
└──────────────────┘
```

---

## 🛡️ SECTION 5: RISK CONTROLS

### Component: `RiskControls`
**Route Context**: Risk management & position limits  
**Per-Broker**: Yes

#### Sub-Components & API Bindings:

```
RiskControls/
├── RiskToggle (Master Switch)
│   └── PUT Supabase: risk_settings.enabled
│       • UI: Large toggle with label
│       • Disables: All risk checks when off
│
├── DailyLossLimits
│   ├── MaxDailyLossUSDSlider
│   │   └── PUT Supabase: risk_settings.max_daily_loss_usd
│   │       • Range: $0 - $10,000
│   │       • Step: $50
│   │       • Visual: Red zone at 80%
│   │
│   └── MaxDailyLossPctSlider
│       └── PUT Supabase: risk_settings.max_daily_loss_pct
│           • Range: 0.1% - 10.0%
│           • Step: 0.1%
│           • Calculate: From account balance
│
├── TradeLimits
│   ├── MaxTradesPerDaySlider
│   │   └── PUT Supabase: risk_settings.max_trades_per_day
│   │       • Range: 1 - 100
│   │       • UI: Number input + slider
│   │
│   ├── MaxOpenTradesSlider (NEW)
│   │   └── PUT Supabase: risk_settings.max_open_trades
│   │       • Range: 1 - 50
│   │       • Real-time: Show current open count
│   │
│   └── MaxConcurrentPositionsSlider (NEW)
│       └── PUT Supabase: risk_settings.max_concurrent_positions
│           • Range: 1 - 10
│           • Different from trades (1 trade can have multiple fills)
│
├── PerTradeLimits
│   ├── MaxRiskPerTradeUSDSlider
│   │   └── PUT Supabase: risk_settings.max_risk_per_trade_usd
│   │       • Range: $10 - $5,000
│   │
│   └── MaxRiskPerTradePctSlider
│       └── PUT Supabase: risk_settings.max_risk_per_trade_pct
│           • Range: 0.1% - 5.0%
│
├── LeverageControl
│   └── LeverageCapSlider
│       └── PUT Supabase: risk_settings.leverage_cap
│           • Range: 1:1 - 500:1
│           • Per broker: TradeLocker/TruForex max 500, Topstep N/A
│
├── InstrumentFilters (NEW)
│   ├── AllowedInstrumentsInput
│   │   └── PUT Supabase: risk_settings.allowed_instruments (text array)
│   │       • UI: Tag input (create-react-tags)
│   │       • Example: ["EURUSD", "GBPUSD", "ES", "NQ"]
│   │       • Logic: Whitelist (if empty, allow all)
│   │
│   └── DeniedInstrumentsInput
│       └── PUT Supabase: risk_settings.denied_instruments
│           • UI: Tag input
│           • Example: ["XAUUSD", "BTCUSD"]
│           • Logic: Blacklist (priority over allowed)
│
├── RiskSummaryPanel (NEW)
│   └── GET Supabase: Real-time calculation
│       ├── CurrentDailyLoss
│       │   • Query: SUM(unrealized_pnl) WHERE today
│       │   • UI: Progress bar (green → yellow → red)
│       │   • Alert: Flash red if > 80% of limit
│       │
│       ├── TradesTodayCount
│       │   • Query: COUNT(orders) WHERE timestamp > today
│       │   • UI: "X / Y trades used"
│       │
│       └── CurrentOpenTrades
│           • Query: COUNT(positions)
│           • UI: "X / Y positions open"
│
└── SaveRiskSettingsButton
    └── PUT Supabase: risk_settings (full record)
        • Validation: All limits logical (e.g., max_open <= max_trades)
```

**Data Flow:**
```
┌──────────────────┐
│  Risk Settings   │
│  (User Input)    │
└────────┬─────────┘
         │ Save
         ▼
┌──────────────────┐
│   Supabase DB    │
│  risk_settings   │
└────────┬─────────┘
         │
         ▼
┌──────────────────────┐
│  Order Executor      │ ──Check──> Risk Engine
│  (Webhook Handler)   │              │
└──────────────────────┘              │
                                      ▼
                            ┌─────────────────┐
                            │ ALLOW or REJECT │
                            │ (Log to logs)   │
                            └─────────────────┘
```

---

## 📋 SECTION 6: ORDERS

### Component: `OrdersManager`
**Route Context**: Order history & management  
**Per-Broker**: Yes

#### Sub-Components & API Bindings:

```
OrdersManager/
├── OrdersTable
│   └── GET Supabase: orders
│       • WHERE: user_id = current AND broker = selected
│       • ORDER BY: timestamp DESC
│       • Real-time: Supabase channel orders:userId
│       • Columns:
│         - Timestamp (formatted)
│         - Symbol
│         - Side (BUY/SELL badge)
│         - Type (MARKET/LIMIT/STOP)
│         - Qty
│         - Price (or "Market")
│         - Status (PENDING/FILLED/REJECTED/CANCELLED)
│         - Tag (strategy name)
│         - Actions: [Cancel] [Details]
│       • UI: Shadcn Table with hover states
│       • Pagination: 50 rows per page
│
├── FilterBar
│   ├── StatusFilter
│   │   • UI: Select dropdown (All, Pending, Filled, Rejected)
│   │   • Filter: WHERE status IN (...)
│   │
│   ├── SymbolFilter
│   │   • UI: Autocomplete input
│   │   • Filter: WHERE symbol LIKE %query%
│   │
│   ├── DateRangeFilter
│   │   • UI: Date picker (Shadcn Calendar)
│   │   • Filter: WHERE timestamp BETWEEN start AND end
│   │
│   └── TagFilter
│       • UI: Tag select
│       • Filter: WHERE tag = selected
│
├── CancelOrderButton
│   └── DELETE /api/unify/v1/order/{orderId}
│       • UI: Icon button in table row
│       • Confirm: Modal "Cancel order?"
│       • Only: If status = PENDING
│       • Update: orders.status = 'CANCELLED'
│
├── OrderDetailsModal
│   └── GET Supabase: orders WHERE id = selected
│       • UI: Dialog/Modal
│       • Display:
│         - All order fields
│         - Broker order ID
│         - Filled quantity / avg price
│         - Reject reason (if rejected)
│         - Related position link
│       • Actions: [View Position] [Resubmit]
│
├── OrderStatsCards (NEW)
│   ├── TotalOrdersCard
│   │   • Query: COUNT(orders) WHERE timestamp > 30 days
│   │
│   ├── FillRateCard
│   │   • Query: FILLED / (FILLED + REJECTED) * 100
│   │   • UI: Percentage with trend icon
│   │
│   └── AvgFillTimeCard
│       • Query: AVG(filled_at - timestamp)
│       • UI: Seconds or minutes
│
└── ResubmitOrderButton (NEW)
    └── POST /api/unify/v1/order (same payload as original)
        • UI: Button in details modal
        • Action: Clone order and resubmit
        • Use case: Resubmit rejected orders
```

**Data Flow:**
```
┌──────────────────┐
│  Orders Table    │ <──Real-time── Supabase orders channel
│  (OrdersManager) │                     │
└────────┬─────────┘                     │
         │ User clicks [Cancel]          │
         ▼                               │
┌──────────────────┐                     │
│ DELETE /order/id │ ──Update──> orders.status = 'CANCELLED'
└──────────────────┘
```

---

## 📈 SECTION 7: POSITIONS

### Component: `PositionsMonitor`
**Route Context**: Open positions & P&L tracking  
**Per-Broker**: Yes

#### Sub-Components & API Bindings:

```
PositionsMonitor/
├── PositionsTable
│   └── GET Supabase: positions
│       • WHERE: user_id = current AND broker = selected
│       • Real-time: Supabase channel positions:userId (P&L updates)
│       • Columns:
│         - Symbol
│         - Side (LONG/SHORT badge with arrow)
│         - Qty
│         - Entry Price
│         - Current Price (live updates)
│         - Unrealized P&L ($) [Flash green/red on change]
│         - Unrealized P&L (%) [Color-coded]
│         - Stop Loss
│         - Take Profit
│         - Open Time (time ago)
│         - Actions: [Modify SL/TP] [Close]
│       • UI: Table with row animations
│       • Sort: By P&L, open time, symbol
│
├── LivePnLUpdater (Background Service)
│   • Subscribes: positions:userId channel
│   • Updates: current_price, unrealized_pnl every 1-5s
│   • Animation: Flash effect on P&L change
│
├── ModifySLTPModal
│   └── PUT /api/unify/v1/positions/{positionId}
│       • UI: Dialog with two inputs
│       • Fields: new_stop_loss, new_take_profit
│       • Visual: Show distance from current price
│       • Validation: SL must be < entry (LONG), > entry (SHORT)
│       • Update: positions.stop_loss, positions.take_profit
│
├── ClosePositionButton
│   └── DELETE /api/unify/v1/positions/{positionId}
│       • UI: Red button with confirm modal
│       • Action: Send close order to broker
│       • Result: Position removed from table
│       • Log: Insert into orders table (type=MARKET, side=opposite)
│
├── PartialCloseButton (NEW)
│   └── PUT /api/unify/v1/positions/{positionId}/partial
│       • UI: Button → Modal with qty input
│       • Field: close_qty (slider, max = position.qty)
│       • Action: Close portion of position
│       • Update: position.qty -= close_qty
│
├── PositionStatsCards
│   ├── TotalUnrealizedPnLCard
│   │   • Query: SUM(unrealized_pnl)
│   │   • UI: Large card with +/- sign
│   │   • Color: Green (profit) / Red (loss)
│   │
│   ├── WinRateCard
│   │   • Query: COUNT(closed_positions WHERE pnl > 0) / COUNT(total_closed)
│   │   • UI: Percentage with progress ring
│   │
│   └── LargestPositionCard
│       • Query: MAX(qty * current_price)
│       • UI: Symbol + notional value
│
├── PositionChartModal (NEW)
│   └── GET equity_history WHERE open_time < timestamp < (now or close_time)
│       • UI: Dialog with TradingView Lightweight Charts
│       • Display: Price action from entry to current
│       • Markers: Entry point, SL line, TP line
│       • Interactive: Drag SL/TP to modify
│
└── FilterBar
    ├── SymbolFilter
    ├── SideFilter (Long/Short/All)
    └── SortOptions (P&L, Open Time, Size)
```

**Data Flow:**
```
┌──────────────────────┐
│  Supabase Realtime   │ ──Every 1-5s──> Broker feeds update current_price
│  positions channel   │
└──────────┬───────────┘
           │ Broadcast change
           ▼
┌──────────────────────┐
│  PositionsTable      │ <──Flash animation on P&L change
│  (Live P&L)          │
└──────────┬───────────┘
           │ User clicks [Modify SL/TP]
           ▼
┌──────────────────────┐
│ PUT /positions/id    │ ──Update──> Broker API + Supabase
└──────────────────────┘
```

---

## 🔑 SECTION 8: API KEYS

### Component: `ApiKeyManager`
**Route Context**: API key management & rotation  
**Per-Broker**: Yes (one key per broker_account)

#### Sub-Components & API Bindings:

```
ApiKeyManager/
├── ApiKeysList
│   └── GET Supabase: broker_accounts.api_key_hash, created_at, last_sync
│       • WHERE: user_id = current AND broker = selected
│       • Display:
│         - Masked Key: "sk_live_abc...xyz" (last 4 chars visible)
│         - Created: Date (time ago)
│         - Last Used: last_sync timestamp
│         - Status: Active/Revoked badge
│       • UI: Card list with expand option
│
├── GenerateKeyButton
│   └── POST /api/unify/v1/keys
│       • UI: Primary button "Generate New Key"
│       • Action: Create new api_key, hash with SHA-256
│       • INSERT: broker_accounts (or update if exists)
│       • Display: One-time show of full key (ApiKeyModal)
│       • Warning: "Save this key, it won't be shown again"
│
├── ApiKeyModal (One-Time Display)
│   • UI: Dialog with large code block
│   • Display: Full api_key (e.g., sk_live_abc123xyz789)
│   • Actions:
│     - [Copy to Clipboard] (with toast)
│     - [Download as .env] (downloads .env file)
│     - [I've Saved It] (closes modal)
│   • Security: Key never stored in plaintext after this
│
├── RotateKeyButton
│   └── PUT /api/unify/v1/keys/{id}/rotate
│       • UI: Icon button with confirm modal
│       • Action:
│         1. Generate new api_key
│         2. UPDATE api_key_hash
│         3. INSERT admin_actions (audit log)
│         4. EMIT NATS: ai.user.key.rotated
│       • Display: New key in ApiKeyModal
│       • Warning: "Old webhooks will stop working"
│
├── RevokeKeyButton
│   └── DELETE /api/unify/v1/keys/{id}
│       • UI: Red button with double confirm
��       • Action: DELETE broker_accounts (or mark status=revoked)
│       • Cascade: Related orders/positions retained (historical)
│
├── KeyUsageStats (NEW)
│   └── GET Supabase: webhook_events WHERE api_key = selected
│       • Display:
│         - Total Requests: COUNT(webhook_events)
│         - Last 24h: COUNT WHERE received_at > now() - 24h
│         - Success Rate: signature_valid = true / total
│       • UI: Mini stats row under each key
│
└── SecurityInfo
    • UI: Alert card
    • Content:
      - API keys are hashed (SHA-256) in database
      - Never share your keys
      - Rotate keys every 90 days
      - Use different keys for prod/test
```

**Data Flow:**
```
┌──────────────────┐
│ Generate Key Btn │
└────────┬─────────┘
         │ POST /keys
         ▼
┌──────────────────────┐
│  Server generates    │
│  random api_key      │ ──Hash (SHA-256)──> Store hash in DB
└────────┬─────────────┘
         │ Return plaintext (one-time)
         ▼
┌──────────────────────┐
│  ApiKeyModal         │ <── User must save!
│  (One-time show)     │
└──────────────────────┘
```

---

## 💳 SECTION 9: BILLING

### Component: `BillingPortal`
**Route Context**: Subscription & payment management  
**Global**: Not per-broker

#### Sub-Components & API Bindings:

```
BillingPortal/
├── CurrentPlanCard
│   └── GET Supabase: subscriptions WHERE user_id = current
│       • Display:
│         - Plan: Starter/Pro/Elite badge
│         - Status: Active/Trialing/Past Due
│         - Next Billing: current_period_end date
│         - Amount: $20/$40/$60
│         - Payment Method: Card ending in XXXX
│       • UI: Large card at top
│
├── TrialInfoBanner
│   └── IF status = 'trialing':
│       • Display: Days remaining (trial_end - now)
│       • Display: Trades used (COUNT orders WHERE > trial_start)
│       • Logic: Expire when (days > 3) OR (trades >= 100)
│       • UI: Blue alert banner
│       • Action: [Upgrade Now] button
│
├── PlanCardsGrid
│   • UI: 3 columns (Starter, Pro, Elite)
│   • Each card:
│     - Name + price ($20/$40/$60)
│     - Trial badge
│     - Features list with checkmarks
│     - CTA button: [Start Trial] or [Upgrade] or [Current Plan]
│   • Highlight: Pro marked as "Popular"
│   • Border: Current plan has #00ffc2 border
│
├── UpgradeButton
│   └── POST /api/unify/v1/subscription/checkout
│       • UI: Button in plan card
│       • Action: Create Stripe Checkout Session
│       • Redirect: To Stripe hosted page
│       • Return URL: /billing/success
│       • Payload: { plan: 'starter'|'pro'|'elite', user_id }
│
├── ManageSubscriptionButton
│   └── POST /api/unify/v1/subscription/portal
│       • UI: Button in CurrentPlanCard
│       • Action: Create Stripe Customer Portal Session
│       • Redirect: To Stripe portal (update card, view invoices, cancel)
│
├── UsageStatsCards (NEW)
│   ├── TradesThisMonthCard
│   │   └── GET Supabase: COUNT(orders) WHERE timestamp > start_of_month
│   │       • Display: X trades used
│   │       • Compare: Against plan limit (Starter: 100, Pro/Elite: unlimited)
│   │       • UI: Progress bar
│   │
│   ├── ConnectedBrokersCard
│   │   └── GET Supabase: COUNT(broker_accounts)
│   │       • Display: X / Y brokers connected
│   │       • Limit: Starter=1, Pro=2, Elite=3
│   │
│   └── FluxeoStrategiesCard (NEW)
│       • Display: X / Y strategies used
│       • Limit: Starter=0, Pro=1, Elite=3
│       • Link: [View Strategies] → Strategies page
│
├── InvoiceHistoryTable (NEW)
│   └── GET Stripe API: /invoices?customer={customer_id}
│       • Columns: Invoice ID, Date, Amount, Status, PDF
│       • UI: Table with download buttons
│       • Download: GET invoice.pdf from Stripe
│
└── CancelSubscriptionButton
    └── POST /api/unify/v1/subscription/cancel
        • UI: Text link at bottom
        • Confirm: Modal with reason dropdown
        • Action: Set cancel_at_period_end = true
        • Result: Access continues until period end
```

**Data Flow:**
```
┌──────────────────┐
│  User clicks     │
│  [Upgrade]       │
└────────┬─────────┘
         │ POST /subscription/checkout
         ▼
┌──────────────────────┐
│  Server creates      │
│  Stripe Session      │ ──Redirect──> Stripe Checkout
└──────────────────────┘                    │
                                            │ User completes payment
                                            ▼
                                   ┌────────────────────┐
                                   │ Stripe Webhook     │
                                   │ subscription.created
                                   └────────┬───────────┘
                                            │
                                            ▼
                                   ┌────────────────────┐
                                   │ UPDATE Supabase    │
                                   │ subscriptions      │
                                   │ + profiles.plan    │
                                   └────────────────────┘
```

---

## 🛡️ SECTION 10: ADMIN (ADMIN ROLE ONLY)

### Component: `AdminPanel`
**Route Context**: System administration & monitoring  
**Access**: isAdmin = true only

#### Sub-Components & API Bindings:

```
AdminPanel/
├── SystemStatsGrid
│   ├── TotalUsersCard
│   │   └── GET Supabase: COUNT(profiles)
│   │       • UI: Large number card
│   │
│   ├── ActiveUsersCard
│   │   └── GET Supabase: COUNT(profiles) WHERE last_login > now() - 30 days
│   │
│   ├── TotalRevenueCard
│   │   └── GET Supabase: SUM(subscriptions.amount)
│   │       • Calculate: MRR (monthly recurring revenue)
│   │
│   ├── ActiveTradesCard
│   │   └── GET Supabase: COUNT(positions) (all users)
│   │
│   └── SystemHealthCard
│       └── GET /api/unify/v1/health
│           • Display: Overall status + broker health
│
├── UsersTable
│   └── GET Supabase: profiles (admin bypasses RLS)
│       • Columns:
│         - Email
│         - Name
│         - Role (admin/user/viewer)
│         - Plan (starter/pro/elite)
│         - Status (active/suspended)
│         - Created Date
│         - Actions: [View] [Impersonate] [Suspend] [Upgrade]
│       • UI: Full-width table with filters
│       • Pagination: 100 rows per page
│
├── ImpersonateButton
│   └── POST /api/unify/v1/admin/impersonate/{userId}
│       • UI: Icon button in users table
│       • Action: Set JWT claim impersonated_user_id
│       • Result: Admin sees user's view of dashboard
│       • Banner: "Viewing as {user.email}" [Exit Impersonation]
│       • Audit: Log to admin_actions
│
├── SuspendUserButton
│   └── PUT /api/unify/v1/admin/users/{userId}/suspend
│       • UI: Icon button (require reason modal)
│       • Action: UPDATE profiles.status = 'suspended'
│       • Result: User cannot login
│       • Audit: Log to admin_actions
│
├── UpgradePlanButton (Admin Override)
│   └── PUT /api/unify/v1/admin/users/{userId}/plan
│       • UI: Dropdown in users table
│       • Action: UPDATE profiles.plan_tier (bypass Stripe)
│       • Use case: Free upgrade for support/partnerships
│       • Audit: Log to admin_actions
│
├── AuditLogTable
│   └── GET Supabase: admin_actions ORDER BY timestamp DESC
│       • Columns:
│         - Timestamp
│         - Admin (who performed action)
│         - Action (user_suspended, plan_upgraded, etc.)
│         - Target User
│         - Details (JSON expand)
│         - IP Address
│       • Filter: By admin, action type, date range
│       • Export: CSV download
│
├── SystemMetricsChart (NEW)
│   └── GET /api/unify/v1/metrics (Prometheus format)
│       • Display:
│         - Orders per hour (line chart)
│         - Rejections by reason (pie chart)
│         - Webhook latency (histogram)
│       • Library: Recharts
│       • Refresh: Every 30s
│
└── BroadcastMessageForm (NEW)
    └── POST /api/unify/v1/admin/broadcast
        • UI: Form with textarea
        • Fields: Title, message, target (all/starter/pro/elite)
        • Action: INSERT notification for all matching users
        • Display: Toast on user dashboards
```

**Data Flow:**
```
┌──────────────────┐
│  Admin views     │
│  UsersTable      │ <── SELECT * FROM profiles (bypass RLS)
└────────┬─────────┘
         │ Click [Impersonate]
         ▼
┌──────────────────────┐
│  Set JWT claim       │
│  impersonated_user   │ ──Log──> admin_actions table
└────────┬─────────────┘
         │ Redirect to dashboard
         ▼
┌──────────────────────┐
│  DashboardOverview   │ <── Shows user's data (not admin's)
│  (Impersonated View) │
└──────────────────────┘
```

---

## 📄 SECTION 11: LOGS

### Component: `LogsViewer`
**Route Context**: Application logs & debugging  
**Per-Broker**: Yes (filter by broker)

#### Sub-Components & API Bindings:

```
LogsViewer/
├── LogsTable
│   └── GET Supabase: logs
│       • WHERE: user_id = current AND broker = selected
│       • ORDER BY: timestamp DESC
│       • Real-time: Supabase channel logs:userId (tail mode toggle)
│       • Columns:
│         - Timestamp (formatted with ms)
│         - Level (success/info/warning/error badge)
│         - Type (order/position/webhook/risk/sync/auth)
│         - Message (truncated with expand)
│         - Details (JSON, expand icon)
│         - Correlation ID (link related logs)
│       • UI: Monospace font table
│       • Pagination: 100 rows per page
│
├── FilterBar
│   ├── LevelFilter
│   │   • UI: Chips (All, Success, Info, Warning, Error)
│   │   • Filter: WHERE level = selected
│   │
│   ├── TypeFilter
│   │   • UI: Dropdown (All, Order, Position, Webhook, etc.)
│   │   • Filter: WHERE type = selected
│   │
│   ├── DateRangeFilter
│   │   • UI: Date picker
│   │   • Filter: WHERE timestamp BETWEEN start AND end
│   │
│   ├── SearchFilter
│   │   • UI: Input with search icon
│   │   • Filter: WHERE message LIKE %query%
│   │
│   └── CorrelationIDFilter (NEW)
│       • UI: Input (paste correlation_id)
│       • Filter: WHERE correlation_id = value
│       • Use case: Trace request through system
│
├── TailModeToggle (NEW)
│   • UI: Switch "Live Tail Mode"
│   • Enabled: Auto-scroll to bottom on new logs
│   • Disabled: Static table with manual refresh
│   • Real-time: Supabase subscription active when enabled
│
├── LogDetailsModal
│   • UI: Dialog showing full log entry
│   • Display:
│     - All fields (timestamp, level, type, etc.)
│     - Details JSON (pretty-printed with syntax highlighting)
│     - Related Logs button (query by correlation_id)
│   • Actions: [Copy JSON] [Copy Correlation ID]
│
├── ExportLogsButton
│   └── GET Supabase: logs (with current filters applied)
│       • Action: Export to CSV
│       • Filename: logs_{broker}_{timestamp}.csv
│       • Client-side: Use papaparse or similar
│
├── ClearLogsButton (Retention Policy)
│   └── DELETE Supabase: logs WHERE timestamp < now() - 90 days
│       • UI: Button in header (admin only)
│       • Confirm: "Delete logs older than 90 days?"
│       • Note: Automated by cron job, this is manual trigger
│
└── LogStatsCards
    ├── TotalLogsCard
    │   • Query: COUNT(logs) WHERE today
    │
    ├── ErrorRateCard
    │   • Query: COUNT(level='error') / COUNT(total)
    │   • UI: Percentage with trend
    │
    └── MostCommonErrorCard
        • Query: GROUP BY message, COUNT(*) ORDER BY count DESC LIMIT 1
        • Display: Most frequent error message
```

**Data Flow:**
```
┌──────────────────────┐
│  System Event        │
│  (Order placed,      │
│   Position updated)  │
└────────┬─────────────┘
         │ INSERT log
         ▼
┌──────────────────────┐
│  Supabase logs       │
│  table               │ ──Real-time (if tail mode)──> LogsTable
└──────────────────────┘                                    │
                                                            │ Display with color
                                                            ▼
                                                   ┌────────────────────┐
                                                   │ Success: Green     │
                                                   │ Error: Red         │
                                                   │ Warning: Yellow    │
                                                   └────────────────────┘
```

---

## 🎨 THEME & STYLING SYSTEM

### Global Theme Variables

```css
:root {
  /* Primary Colors */
  --bg-primary: #002b36;      /* Main background */
  --bg-secondary: #001f29;    /* Cards, sidebar */
  --bg-tertiary: #003847;     /* Hover states */
  
  /* Accent Colors */
  --accent-primary: #00ffc2;  /* Buttons, highlights */
  --accent-hover: #00e6ad;    /* Hover state */
  
  /* Text Colors */
  --text-primary: #ffffff;    /* Main text */
  --text-secondary: #94a3b8;  /* Muted text */
  --text-tertiary: #64748b;   /* Disabled text */
  
  /* Semantic Colors */
  --success: #10b981;         /* Green (profit, filled orders) */
  --error: #ef4444;           /* Red (loss, rejected orders) */
  --warning: #f59e0b;         /* Yellow (warnings, trial expire) */
  --info: #3b82f6;            /* Blue (info messages) */
  
  /* Borders */
  --border-default: #334155;  /* Default borders */
  --border-focus: var(--accent-primary);
  
  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
  
  /* Fonts */
  --font-primary: 'Inter', system-ui, sans-serif;
  --font-mono: 'Fira Code', 'Courier New', monospace;
  
  /* Border Radius */
  --radius-sm: 0.375rem;  /* 6px */
  --radius-md: 0.5rem;    /* 8px */
  --radius-lg: 0.75rem;   /* 12px */
  --radius-xl: 1rem;      /* 16px */
}
```

### Component UI Types

| Component | UI Type | Description |
|-----------|---------|-------------|
| MetricsGrid | Card Grid | 4-column responsive grid |
| PositionsTable | Table | Sortable, real-time updates |
| OrderDetailsModal | Modal | Dialog with backdrop |
| RiskSlider | Slider | Range input with live value |
| ApiKeyDisplay | Code Block | Monospace with copy button |
| PlanCard | Card | Bordered, hover effects |
| LogsTable | Table | Monospace font, expandable rows |
| StatusBadge | Badge | Color-coded (green/yellow/red) |
| ConfirmDialog | Modal | Yes/No with warning |
| FilterBar | Form | Inline filters with chips |

---

## 🔄 DATA FLOW DIAGRAM (Complete System)

```
┌─────────────────────────────────────────────────────────────────┐
│                        TRADINGVIEW                              │
│                     (Alert Webhook)                             │
└────────────────────────────┬────────────────────────────────────┘
                             │ POST /webhook/{broker}
                             │ Signature: HMAC-SHA256
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API GATEWAY (Edge Function)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Verify HMAC  │→ │ Risk Check   │→ │ Rate Limit   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────────┬────────────────────────────────────┘
                             │ Valid
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BROKER BACKENDS                               │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐        │
│  │ TradeLocker   │ │ Topstep       │ │ TruForex      │        │
│  │ Backend       │ │ Backend       │ │ Backend       │        │
│  └───────┬───────┘ └───────┬───────┘ └───────┬───────┘        │
└──────────┼─────────────────┼─────────────────┼─────────────────┘
           │                 │                 │
           │ Place order     │ Execute         │ Send signal
           │ via API         │ contract        │ to MT4/MT5
           ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SUPABASE DATABASE                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ orders   │  │positions │  │ logs     │  │webhook_  │       │
│  │ table    │  │ table    │  │ table    │  │events    │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┘       │
└───────┼─────────────┼─────────────┼─────────────────────────────┘
        │             │             │
        │ Real-time   │ Real-time   │ Real-time
        │ channel     │ channel     │ channel
        ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    REACT FRONTEND                                │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐        │
│  │ OrdersManager │ │PositionsMonitor│ │ LogsViewer   │        │
│  │ (Table)       │ │ (Live P&L)    │ │ (Tail Mode)  │        │
│  └───────────────┘ └───────────────┘ └───────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 COMPLETE COMPONENT CHECKLIST

### ✅ Existing Components (11)
- [x] App.tsx (Root)
- [x] DashboardOverview
- [x] AccountsManager
- [x] WebhookTemplates
- [x] TradingConfiguration
- [x] RiskControls
- [x] OrdersManager
- [x] PositionsMonitor
- [x] ApiKeyManager
- [x] BillingPortal
- [x] AdminPanel
- [x] LogsViewer

### 🆕 New Components Needed (18)

**Dashboard Enhancements:**
- [ ] HealthStatusBanner
- [ ] RiskHeatmapWidget
- [ ] EquityCurveChart
- [ ] DailyDrawdownChart

**Webhooks:**
- [ ] TestAlertPlayground
- [ ] JSONEditor (Monaco)
- [ ] OrderPreview (Chart)
- [ ] DirectAPIExamples

**Positions:**
- [ ] LivePnLUpdater (Service)
- [ ] PartialCloseModal
- [ ] PositionChartModal

**Billing:**
- [ ] TrialCountdown (Widget)
- [ ] UsageProgressBars

**Admin:**
- [ ] SystemMetricsChart
- [ ] BroadcastMessageForm

**Logs:**
- [ ] TailModeToggle
- [ ] CorrelationIDTracer

**Global:**
- [ ] ThemeToggle (Light/Dark)

---

## 🎯 IMPLEMENTATION PRIORITY

### Phase 1: Core Real-time Features (Sprint 1-2)
1. HealthStatusBanner
2. LivePnLUpdater
3. TailModeToggle
4. Real-time channels setup

### Phase 2: Risk Visualization (Sprint 3-4)
5. RiskHeatmapWidget
6. EquityCurveChart
7. DailyDrawdownChart

### Phase 3: Testing & Validation (Sprint 5-6)
8. TestAlertPlayground
9. OrderPreview
10. Direct API Examples

### Phase 4: Polish & Admin (Sprint 7-8)
11. SystemMetricsChart
12. BroadcastMessageForm
13. ThemeToggle
14. TrialCountdown

---

## 📊 ENDPOINT TO COMPONENT MAPPING (Full List)

| HTTP Method | API Path | Component | UI Type | Data Binding |
|-------------|----------|-----------|---------|--------------|
| GET | /api/unify/v1/health | HealthStatusBanner | Banner | Polling 60s |
| GET | /api/unify/v1/positions | PositionsTable | Table | Real-time |
| POST | /api/unify/v1/order | TestAlertPlayground | Form+Button | On submit |
| PUT | /api/unify/v1/positions/{id} | ModifySLTPModal | Modal+Form | On save |
| DELETE | /api/unify/v1/positions/{id} | ClosePositionButton | Button | On confirm |
| GET | /api/unify/v1/orders | OrdersTable | Table | Real-time |
| DELETE | /api/unify/v1/order/{id} | CancelOrderButton | Button | On confirm |
| GET | /api/unify/v1/risk | RiskControlsForm | Sliders | On load |
| PUT | /api/unify/v1/risk | SaveRiskSettingsButton | Button | On save |
| POST | /api/unify/v1/webhook/{broker} | WebhookEndpoint | N/A (External) | TradingView |
| POST | /api/unify/v1/test-webhook | TestAlertPlayground | Button | On test |
| POST | /api/unify/v1/keys | GenerateKeyButton | Button+Modal | On generate |
| PUT | /api/unify/v1/keys/{id}/rotate | RotateKeyButton | Button+Modal | On rotate |
| DELETE | /api/unify/v1/keys/{id} | RevokeKeyButton | Button | On confirm |
| POST | /api/unify/v1/subscription/checkout | UpgradeButton | Button | Stripe redirect |
| POST | /api/unify/v1/subscription/portal | ManageSubscriptionButton | Button | Stripe redirect |
| GET | /api/unify/v1/metrics | SystemMetricsChart | Chart | Polling 30s |
| POST | /register/{broker} | RegistrationForm | Modal+Form | On submit |
| POST | /sync/{broker}/{account_id} | SyncAccountButton | Button | On click |

---

**End of Component Hierarchy Map**  
**Version**: TradeFlow V5  
**Last Updated**: 2025-10-14
