# TradeFlow System Architecture Diagram

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  Dashboard   │  │   Accounts   │  │   Webhooks   │             │
│  │  Overview    │  │   Manager    │  │   Templates  │   + 10 more │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                     │
│  Contexts: UserContext | BrokerContext | ThemeContext              │
│  Utils: api-client-enhanced.ts (API calls)                         │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
                    HTTPS / Authorization: Bearer {token}
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│               UNIFIED API GATEWAY (Optional)                        │
│           https://unified.fluxeo.net/api/unify/v1                   │
│                                                                     │
│  Routes requests to appropriate backend based on path              │
│  - /register/{broker} → Broker-specific backend                    │
│  - /webhook/{broker} → Broker-specific backend                     │
│  - /api/* → Unified backend (accounts, billing, analytics)         │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
                    ┌──────────────┴───────────────┐
                    ↓                              ↓
┌─────────────────────────────┐  ┌─────────────────────────────┐
│  BROKER-SPECIFIC BACKENDS   │  │   UNIFIED BACKEND (FastAPI) │
│                             │  │                             │
│ ┌─────────────────────────┐ │  │ Handles:                    │
│ │ TradeLocker Backend     │ │  │ • User accounts             │
│ │ (FastAPI)               │ │  │ • API key management        │
│ │                         │ │  │ • Billing (Stripe)          │
│ │ /register/tradelocker   │ │  │ • Analytics & reports       │
│ │ /webhook/tradelocker    │ │  │ • Risk configuration        │
│ │ /api/positions (TL)     │ │  │ • Admin panel               │
│ └─────────────────────────┘ │  │ • Cross-broker aggregation  │
│                             │  └─────────────────────────────┘
│ ┌─────────────────────────┐ │                  ↓
│ │ Topstep Backend         │ │         ┌────────────────┐
│ │ (FastAPI)               │ │         │   PostgreSQL   │
│ │                         │ │         │   Database     │
│ │ /register/projectx      │ │         │                │
│ │ /webhook/topstep        │ │         │ Tables:        │
│ │ /api/positions (TS)     │ │         │ • users        │
│ └─────────────────────────┘ │         │ • accounts     │
│                             │         │ • api_keys     │
│ ┌─────────────────────────┐ │         │ • positions    │
│ │ MT4/MT5 Backend         │ │         │ • orders       │
│ │ (FastAPI)               │ │         │ • webhooks_log │
│ │                         │ │         │ • billing      │
│ │ /register/mtx           │ │         │ • risk_config  │
│ │ /webhook/truforex       │ │         └────────────────┘
│ │ /api/ea/heartbeat       │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
          ↓                              ↓
  ┌───────────────┐              ┌────────────────┐
  │ Broker APIs   │              │ Stripe API     │
  │               │              │                │
  │ • TradeLocker │              │ • Checkout     │
  │ • Topstep API │              │ • Webhooks     │
  │ • MT4/MT5 EA  │              │ • Portal       │
  └───────────────┘              └────────────────┘
```

---

## 🔄 Data Flow: User Registration → First Trade

### Step 1: User Signs Up
```
User (Browser)
    ↓ POST /auth/signup { email, password, name }
Supabase Auth
    ↓ Returns { user_id, access_token }
Frontend
    ↓ Store token in localStorage
    ↓ Update UserContext
Dashboard (logged in)
```

### Step 2: User Connects Broker
```
User clicks "Connect Broker" → TradeLocker
    ↓ Fills form: { email, password, server, mode: 'demo' }
Frontend
    ↓ POST /register/tradelocker
    ↓ Headers: { Authorization: Bearer {access_token} }
TradeLocker Backend
    ↓ Validates credentials with TradeLocker API
    ↓ Creates account in database
    ↓ Generates API key: tradelocker_acc123_xyz789
    ↓ Returns { id, broker, email, status, balance, api_key }
Frontend
    ↓ Displays API key with copy button
    ↓ Updates BrokerContext (adds account to connectedBrokers)
    ↓ Shows "Account Connected" success message
```

### Step 3: User Configures TradingView Webhook
```
User navigates to Webhooks tab
    ↓ Selects account from dropdown
Frontend
    ↓ Generates webhook URL: https://unified.fluxeo.net/api/unify/v1/webhook/tradelocker
    ↓ Fills JSON template with account's API key
    ↓ User copies JSON template
User (TradingView)
    ↓ Creates alert → Pastes JSON into message
    ↓ Sets webhook URL in alert settings
TradingView Alert triggers when condition met
```

### Step 4: TradingView Sends Webhook
```
TradingView Alert
    ↓ POST https://unified.fluxeo.net/api/unify/v1/webhook/tradelocker
    ↓ Headers: { Authorization: Bearer tradelocker_acc123_xyz789 }
    ↓ Body: {
    ↓   version: "unify.v1",
    ↓   intent: {
    ↓     broker: "tradelocker",
    ↓     side: "buy",
    ↓     type: "market",
    ↓     symbol: "EURUSD",
    ↓     qty: 1,
    ↓     sl: { mode: "price", value: 1.0850 },
    ↓     tp: { mode: "rr", value: 2.0 }
    ↓   }
    ↓ }
TradeLocker Backend Webhook Handler
    ↓ 1. Extract API key from Authorization header
    ↓ 2. Query database: SELECT * FROM accounts WHERE api_key = ?
    ↓ 3. Validate account exists and enabled = TRUE
    ↓ 4. Fetch user's risk_config
    ↓ 5. Check risk limits:
    ↓      - Daily loss not exceeded
    ↓      - Within trading hours
    ↓      - Symbol not in denied list
    ↓      - Max open positions not exceeded
    ↓ 6. Execute trade via TradeLocker API
    ↓ 7. Create order record in database
    ↓ 8. Increment user's trades_count (for trial tracking)
    ↓ 9. Log webhook event (webhooks_log table)
    ↓ 10. Return { success: true, order_id: "ord_456" }
TradingView
    ↓ Receives 200 OK response
    ↓ Alert marked as successfully triggered
```

### Step 5: User Monitors Position
```
User (Dashboard)
    ↓ Navigates to Positions tab
Frontend
    ↓ GET /api/positions?broker=tradelocker
    ↓ Headers: { Authorization: Bearer {access_token} }
TradeLocker Backend
    ↓ Queries TradeLocker API for open positions
    ↓ Returns [{
    ↓   id: "pos_789",
    ↓   symbol: "EURUSD",
    ↓   side: "BUY",
    ↓   qty: 1,
    ↓   avg_price: 1.0900,
    ↓   current_price: 1.0920,
    ↓   pnl: 20.00,
    ↓   pnl_percent: 0.18,
    ↓   opened_at: "2025-10-19T14:30:00Z"
    ↓ }]
Frontend
    ↓ Displays position in table
    ↓ Shows real-time P&L (green +$20.00)
```

### Step 6: User Closes Position
```
User clicks "Close Position" button
Frontend
    ↓ POST /api/orders/close { position_id: "pos_789" }
TradeLocker Backend
    ↓ Calls TradeLocker API to close at market price
    ↓ Updates position status in database
    ↓ Returns { success: true, pnl: 20.00, order_id: "ord_999" }
Frontend
    ↓ Shows success toast: "Position closed with +$20.00 profit"
    ↓ Refreshes positions list (position removed)
    ↓ Updates dashboard P&L metrics
```

---

## 🔑 API Key Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                    API Key Lifecycle                             │
└──────────────────────────────────────────────────────────────────┘

1. GENERATION (on account registration)
   POST /register/tradelocker
        ↓
   Backend generates: api_key = f"{broker}_{account_id[:8]}_{random()}"
        ↓
   Stored in database: INSERT INTO api_keys (account_id, key, created_at)
        ↓
   Returned to frontend: { api_key: "tradelocker_acc12345_xyz789" }
        ↓
   User copies API key

2. USAGE (in TradingView webhook)
   User pastes API key into TradingView alert
        ↓
   TradingView sends: Authorization: Bearer tradelocker_acc12345_xyz789
        ↓
   Backend validates: SELECT account_id FROM api_keys WHERE key = ?
        ↓
   If valid and account enabled → Execute trade
   If invalid → Return 401 Unauthorized

3. DISPLAY (in UI)
   GET /api/user/brokers
        ↓
   Returns accounts with masked API keys: "trader****xyz789"
        ↓
   User clicks "Show" → Full key displayed
   User clicks "Copy" → Copied to clipboard

4. REGENERATION (if compromised)
   User clicks "Regenerate API Key"
        ↓
   POST /api/accounts/{id}/regenerate-api-key
        ↓
   Backend:
     - Invalidates old key: DELETE FROM api_keys WHERE account_id = ?
     - Generates new key
     - Returns new key
        ↓
   Frontend warns: "Update TradingView webhooks with new API key"
```

---

## 💳 Billing & Trial Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                    Trial & Subscription Flow                     │
└──────────────────────────────────────────────────────────────────┘

NEW USER SIGNUP
    ↓
User plan = 'trial'
Trial start = NOW()
Trades count = 0
    ↓
┌──────────────────────────────────────────────────────────┐
│  Trial Conditions (whichever comes first)                │
│  • 3 days from signup                                    │
│  • 100 trades executed                                   │
└──────────────────────────────────────────────────────────┘
    ↓
EVERY WEBHOOK EXECUTION
    ↓
Backend checks:
    if user.plan == 'trial':
        trades_count = GET /api/billing/usage
        days_elapsed = NOW() - user.created_at
        
        if trades_count >= 100:
            BLOCK TRADE → "Trial limit: 100 trades reached. Upgrade to continue."
        
        if days_elapsed >= 3 days:
            BLOCK TRADE → "Trial expired: 3 days elapsed. Upgrade to continue."
        
        else:
            EXECUTE TRADE
            INCREMENT trades_count
    ↓
USER DECIDES TO UPGRADE
    ↓
User clicks "Upgrade to Pro" ($40/mo)
    ↓
POST /api/billing/checkout { price_id: "price_pro", success_url, cancel_url }
    ↓
Backend creates Stripe checkout session
    ↓
Returns { url: "https://checkout.stripe.com/..." }
    ↓
Frontend redirects to Stripe
    ↓
USER COMPLETES PAYMENT
    ↓
Stripe webhook → POST /api/billing/webhook
    ↓
Event: checkout.session.completed
    ↓
Backend:
    UPDATE users SET plan = 'pro', trial_end = NOW() WHERE id = ?
    INSERT INTO billing_status (user_id, stripe_customer_id, ...)
    ↓
User redirected back to app
    ↓
GET /api/billing/status
    ↓
Returns { status: 'active', plan: 'pro' }
    ↓
User can now:
    • Connect 2 brokers (was 1)
    • Add 2 accounts per broker (was 1)
    • Activate 1 Fluxeo strategy
    • Unlimited trades (no 100 trade limit)
```

---

## 🛡️ Risk Control Enforcement

```
┌──────────────────────────────────────────────────────────────────┐
│              Webhook Risk Control Middleware                     │
└──────────────────────────────────────────────────────────────────┘

TradingView sends webhook
    ↓
POST /api/unify/v1/webhook/tradelocker
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Authenticate                                        │
│   - Extract Authorization: Bearer {api_key}                 │
│   - Validate API key exists in database                     │
│   - Check account.enabled = TRUE                            │
│   ✗ If failed → 401 Unauthorized                           │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Fetch Risk Config                                   │
│   risk_config = GET /api/user/risk_config                   │
│   if risk_config.enabled == FALSE:                          │
│       SKIP ALL CHECKS → Execute trade                       │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Check Daily Loss Limit                              │
│   today_pnl = SUM(pnl) WHERE date = TODAY()                 │
│   if today_pnl <= -risk_config.max_daily_loss:              │
│       ✗ REJECT → "Daily loss limit reached: $500"          │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Check Trading Hours                                 │
│   if risk_config.trading_hours_enabled:                     │
│       current_time = NOW() in risk_config.timezone          │
│       if NOT (start_time <= current_time <= end_time):      │
│           ✗ REJECT → "Outside trading hours: 09:30-16:00"  │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Check Max Trades Per Day                            │
│   today_trades = COUNT(trades) WHERE date = TODAY()         │
│   if today_trades >= risk_config.max_trades_per_day:        │
│       ✗ REJECT → "Daily trade limit reached: 10 trades"    │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: Check Max Open Positions                            │
│   open_positions = COUNT(positions) WHERE status = 'OPEN'   │
│   if open_positions >= risk_config.max_open_trades:         │
│       ✗ REJECT → "Max open positions: 5"                   │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 7: Check Denied Instruments                            │
│   if symbol IN risk_config.denied_instruments:              │
│       ✗ REJECT → "Symbol BTCUSD is denied"                 │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 8: Check News Lockout (if enabled)                     │
│   if risk_config.news_lockout_enabled:                      │
│       upcoming_events = GET /api/calendar/events            │
│       if high_impact_event_within(5 minutes):               │
│           ✗ REJECT → "News lockout: FOMC in 3 minutes"     │
└─────────────────────────────────────────────────────────────┘
    ↓
ALL CHECKS PASSED ✓
    ↓
Execute trade via broker API
    ↓
Log event in webhooks_log table
    ↓
Return { success: true, order_id: "ord_123" }
```

---

## 🚨 Emergency Stop Flow

```
User clicks "Emergency Stop" button (red panic button)
    ↓
Frontend shows confirmation dialog:
    "⚠️ This will immediately close ALL open positions across ALL accounts.
     Are you sure?"
    ↓
User confirms
    ↓
POST /api/user/emergency_stop
    ↓
Backend:
    1. Fetch all open positions for user (all brokers)
         SELECT * FROM positions WHERE user_id = ? AND status = 'OPEN'
    
    2. For each position:
         - Call broker API to close at market price
         - Update position status = 'CLOSED'
         - Record final P&L
    
    3. Disable all accounts temporarily
         UPDATE accounts SET enabled = FALSE WHERE user_id = ?
    
    4. Log emergency stop event
         INSERT INTO logs (user_id, type, message, ...)
    
    5. Send notification
         "Emergency stop executed. 7 positions closed. Re-enable accounts to resume trading."
    ↓
Return {
    success: true,
    positions_closed: 7,
    total_pnl: -245.50,
    errors: []  // or ["Failed to close position pos_123"]
}
    ↓
Frontend:
    - Shows success toast with summary
    - Refreshes positions list (all positions gone)
    - Shows warning banner: "All accounts disabled. Re-enable to resume trading."
    - Updates dashboard metrics
```

---

## 🔄 Real-Time Updates (Optional Enhancement)

```
Current: Polling (GET /api/positions every 5 seconds)
    ↓
Better: WebSocket

┌──────────────────────────────────────────────────────────────┐
│                 WebSocket Architecture                       │
└──────────────────────────────────────────────────────────────┘

Frontend connects:
    ws://unified.fluxeo.net/ws/positions?token={access_token}
        ↓
Backend validates token → Opens WebSocket connection
        ↓
Backend sends initial snapshot:
    { type: "snapshot", positions: [...] }
        ↓
Backend subscribes to position updates from broker APIs
        ↓
When position price changes:
    Broker API → Backend → WebSocket → Frontend
    { type: "update", position_id: "pos_123", current_price: 1.0925, pnl: 25.00 }
        ↓
Frontend updates UI in real-time (no polling)

Benefits:
    • Lower latency (instant updates vs 5s delay)
    • Less server load (no repeated GET requests)
    • Better UX (live P&L updates)
```

---

## 📊 Database Schema (Simplified)

```sql
-- Users table (Supabase Auth handles this)
users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE,
    name TEXT,
    plan TEXT,  -- 'trial', 'starter', 'pro', 'elite'
    role TEXT,  -- 'user', 'admin'
    created_at TIMESTAMP,
    trial_start TIMESTAMP,
    trades_count INT DEFAULT 0
)

-- Broker accounts
accounts (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    broker TEXT,  -- 'tradelocker', 'topstep', 'truforex'
    email TEXT,
    server TEXT,
    mode TEXT,  -- 'demo', 'live'
    status TEXT,  -- 'active', 'inactive', 'error'
    enabled BOOLEAN DEFAULT TRUE,
    balance DECIMAL,
    equity DECIMAL,
    created_at TIMESTAMP,
    last_sync TIMESTAMP
)

-- API keys (for webhook authentication)
api_keys (
    id UUID PRIMARY KEY,
    account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
    key TEXT UNIQUE,  -- e.g., "tradelocker_acc12345_xyz789"
    created_at TIMESTAMP,
    last_used TIMESTAMP
)

-- Positions
positions (
    id UUID PRIMARY KEY,
    account_id UUID REFERENCES accounts(id),
    symbol TEXT,
    side TEXT,  -- 'BUY', 'SELL'
    qty DECIMAL,
    avg_price DECIMAL,
    current_price DECIMAL,
    pnl DECIMAL,
    status TEXT,  -- 'OPEN', 'CLOSED'
    opened_at TIMESTAMP,
    closed_at TIMESTAMP,
    stop_loss DECIMAL,
    take_profit DECIMAL
)

-- Orders
orders (
    id UUID PRIMARY KEY,
    account_id UUID REFERENCES accounts(id),
    symbol TEXT,
    side TEXT,
    type TEXT,  -- 'MARKET', 'LIMIT', 'STOP'
    qty DECIMAL,
    price DECIMAL,
    status TEXT,  -- 'PENDING', 'FILLED', 'CANCELED', 'REJECTED'
    created_at TIMESTAMP,
    filled_at TIMESTAMP,
    reject_reason TEXT
)

-- Webhook logs
webhooks_log (
    id UUID PRIMARY KEY,
    account_id UUID REFERENCES accounts(id),
    timestamp TIMESTAMP,
    method TEXT,
    path TEXT,
    status INT,  -- HTTP status code
    payload JSONB,
    response JSONB,
    latency_ms INT,
    error TEXT
)

-- Risk configuration
risk_config (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    enabled BOOLEAN DEFAULT TRUE,
    risk_mode TEXT,
    max_daily_loss DECIMAL,
    max_trades_per_day INT,
    max_open_trades INT,
    denied_instruments TEXT[],
    trading_hours_enabled BOOLEAN,
    trading_hours_start TIME,
    trading_hours_end TIME,
    trading_hours_timezone TEXT,
    news_lockout_enabled BOOLEAN
)

-- Billing status
billing_status (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    status TEXT,  -- 'active', 'trialing', 'past_due', 'canceled'
    plan TEXT,
    price_id TEXT,
    current_period_end TIMESTAMP,
    trial_end TIMESTAMP
)
```

---

## 🎯 Summary

**Frontend**:
- React components for all screens
- Contexts for state management (User, Broker, Theme)
- API client for backend communication

**Backend(s)**:
- **Broker-specific**: TradeLocker, Topstep, MT4/MT5 (registration + webhooks)
- **Unified**: Accounts, billing, analytics, risk, admin

**Database**:
- PostgreSQL (users, accounts, positions, orders, webhooks_log, billing)

**External Services**:
- Supabase (authentication)
- Stripe (billing)
- Broker APIs (TradeLocker, Topstep, MT4/MT5)

**Critical Path**:
Signup → Connect Broker → Get API Key → Configure TradingView → Webhook Executes Trade → View Position → Close Position

**Priority 1**: Webhook execution + API key generation  
**Priority 2**: Billing & trial tracking  
**Priority 3**: Account management + risk controls  
**Priority 4**: Analytics + admin panel

---

**Last Updated**: 2025-10-19  
**Version**: 6.0  
**Author**: AI Assistant (Figma Make)
