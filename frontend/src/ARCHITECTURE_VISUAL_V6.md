# 🏗️ TradeFlow v6 - Visual Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         TRADEFLOW v6                             │
│                  Unified Trading SaaS Dashboard                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
         ┌────────────────────────────────────────┐
         │         Frontend Layer (React)          │
         │    - Dark/Light Theme                   │
         │    - Responsive (Mobile/Desktop)        │
         │    - Tailwind CSS v4                    │
         └────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌──────────┐    ┌──────────┐    ┌──────────┐
       │  Guards  │    │Components│    │ Widgets  │
       │  Layer   │    │   Layer  │    │  Layer   │
       └──────────┘    └──────────┘    └──────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
         ┌────────────────────────────────────────┐
         │      Enhanced API Client                │
         │   - 27 REST Endpoints                   │
         │   - Bearer Token Auth                   │
         │   - API Key Auth (Webhooks)             │
         │   - Error Handling                      │
         │   - Request/Response Logging            │
         └────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌──────────┐    ┌──────────┐    ┌──────────┐
       │   REST   │    │   NATS   │    │WebSocket │
       │   API    │    │  Events  │    │  (Future)│
       └──────────┘    └──────────┘    └──────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
         ┌────────────────────────────────────────┐
         │    Backend Server (FastAPI)             │
         │   https://unified.fluxeo.net            │
         │   - Request Validation                  │
         │   - Business Logic                      │
         │   - Auth Middleware                     │
         │   - Rate Limiting                       │
         └────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌──────────┐    ┌──────────┐    ┌──────────┐
       │PostgreSQL│    │  Redis   │    │   NATS   │
       │ Database │    │  Cache   │    │  Queue   │
       └──────────┘    └──────────┘    └──────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
         ┌────────────────────────────────────────┐
         │       External Integrations             │
         │   - TradeLocker API                     │
         │   - Topstep API (ProjectX)              │
         │   - TruForex API                        │
         │   - MetaTrader 4/5                      │
         │   - Stripe (Billing)                    │
         │   - TradingView (Webhooks)              │
         └────────────────────────────────────────┘
```

---

## Component Architecture

```
App.tsx (Main Router)
│
├── UserProvider (Auth Context)
│   ├── user: { id, email, name, plan, role }
│   ├── login(email, password)
│   ├── logout()
│   └── isAdmin boolean
│
├── ThemeProvider (Theme Context)
│   ├── theme: 'dark' | 'light'
│   └── toggleTheme()
│
└── Routes
    │
    ├── /landing → LandingPage.tsx
    │
    ├── /login → LoginPage.tsx
    │
    ├── /signup → SignupPage.tsx
    │
    ├── /password-reset → PasswordResetPage.tsx
    │
    ├── /dashboard → Dashboard.tsx ⭐
    │   │
    │   ├── Header
    │   │   ├── TradeFlowLogo
    │   │   ├── Broker Tabs (Desktop)
    │   │   ├── Mobile Menu (Mobile)
    │   │   └── SettingsDropdown
    │   │
    │   ├── Sidebar Navigation
    │   │   ├── Overview
    │   │   ├── Positions
    │   │   ├── Orders
    │   │   ├── Analytics
    │   │   ├── Accounts
    │   │   ├── Configuration
    │   │   ├── Risk Controls
    │   │   ├── API Keys
    │   │   ├── Billing
    │   │   ├── Logs
    │   │   └── Webhooks
    │   │
    │   └── Main Content (with Guards)
    │       │
    │       ├── TrialBanner (if trialing) ⭐ NEW
    │       │   ├── Trades Progress Bar
    │       │   ├── Days Remaining
    │       │   └── Upgrade CTA
    │       │
    │       ├── BillingGuard ⭐ NEW
    │       │   ├── Warning Banner (if blocked)
    │       │   ├── Reactivate Button
    │       │   └── Content Overlay (blocks interaction)
    │       │
    │       └── Section Content
    │           │
    │           ├── DashboardOverview
    │           │   ├── KPI Cards
    │           │   ├── Quick Actions Panel
    │           │   └── Recent Activity
    │           │
    │           ├── PositionsMonitor
    │           │   ├── Summary Cards
    │           │   ├── Positions Table
    │           │   ├── Close Button
    │           │   └── Modify SL/TP Dialog
    │           │
    │           ├── OrdersManager
    │           │   ├── Orders Table
    │           │   ├── Filters
    │           │   └── Cancel/Delete Actions
    │           │
    │           ├── AnalyticsPage
    │           │   ├── P&L Chart (recharts)
    │           │   ├── Volume Chart
    │           │   ├── Metrics Cards
    │           │   └── Trade History
    │           │
    │           ├── AccountsManager
    │           │   ├── Broker List
    │           │   ├── Connect Button
    │           │   ├── Test Connection
    │           │   └── Sync Actions
    │           │
    │           ├── TradingConfiguration
    │           │   ├── SL/TP Sliders
    │           │   ├── Position Size
    │           │   ├── Max Daily Loss
    │           │   └── Save Button
    │           │
    │           ├── RiskControls
    │           │   ├── Risk Settings Form
    │           │   ├── Emergency Stop Button ⭐
    │           │   └── Drawdown Limits
    │           │
    │           ├── ApiKeyManager
    │           │   ├── API Keys List
    │           │   ├── Generate Button
    │           │   ├── Copy Key Modal
    │           │   └── Delete Actions
    │           │
    │           ├── BillingPortal
    │           │   ├── Current Plan Card
    │           │   ├── Usage Metrics
    │           │   ├── Upgrade Options
    │           │   └── Billing History
    │           │
    │           ├── LogsViewer
    │           │   ├── Webhook Logs Table
    │           │   ├── Pagination
    │           │   └── Filter Options
    │           │
    │           └── WebhookTemplates
    │               ├── TradingView Code
    │               ├── Pine Script Examples
    │               └── Copy Buttons
    │
    ├── /account-selection → AccountSelectionPage
    │   ├── Sync Results Table
    │   └── Activate Buttons
    │
    ├── /change-account → ChangeAccountPage
    │   ├── Account Selector
    │   └── Switch Button
    │
    ├── /sync-results → SyncResultsPage
    │   ├── Results Table
    │   └── Retry Buttons
    │
    └── /404 → NotFoundPage
```

---

## Data Flow

### 1. User Login Flow
```
LoginPage.tsx
    │
    ├─> login(email, password)
    │       │
    │       └─> Supabase Auth
    │               │
    │               ├─> Success → setUser({ id, email, plan })
    │               │                  │
    │               │                  └─> Navigate to /dashboard
    │               │
    │               └─> Error → toast.error('Invalid credentials')
    │
    └─> UserContext updates
            │
            └─> All components re-render with user data
```

### 2. API Request Flow
```
Component (e.g., PositionsMonitor.tsx)
    │
    ├─> const positions = await enhancedApiClient.getPositions()
    │       │
    │       ├─> Check cache (5s TTL)
    │       │       │
    │       │       ├─> Cache hit → return cached data
    │       │       │
    │       │       └─> Cache miss → make HTTP request
    │       │
    │       ├─> HTTP Request
    │       │       │
    │       │       ├─> Headers: { Authorization: Bearer ${token} }
    │       │       │
    │       │       └─> GET https://unified.fluxeo.net/api/unify/v1/api/positions
    │       │
    │       ├─> Backend validates token
    │       │       │
    │       │       ├─> Valid → query database
    │       │       │       │
    │       │       │       └─> Return positions array
    │       │       │
    │       │       └─> Invalid → return 401 Unauthorized
    │       │
    │       └─> Response
    │               │
    │               ├─> Success (200) → cache data → return to component
    │               │
    │               └─> Error (4xx/5xx) → throw Error → catch block
    │
    ├─> Success → setState(positions) → UI updates
    │
    └─> Error → toast.error(message) → show error state
```

### 3. Emergency Stop Flow
```
EmergencyStopButton clicked
    │
    └─> EmergencyStopDialog opens
            │
            ├─> User confirms checkbox
            │
            ├─> handleEmergencyStop()
            │       │
            │       └─> POST /api/user/emergency_stop
            │               │
            │               ├─> Backend closes all positions
            │               │       │
            │               │       ├─> Position 1 closed
            │               │       ├─> Position 2 closed
            │               │       └─> Position 3 closed
            │               │
            │               ├─> Backend publishes NATS event
            │               │       │
            │               │       └─> Subject: ai.ops.health.sweep
            │               │           Payload: {
            │               │             op: 'kill_switch',
            │               │             user_id: 'usr_123',
            │               │             positions_closed: 3
            │               │           }
            │               │
            │               └─> Response: { positions_closed: 3, pnl: -245.50 }
            │
            ├─> toast.success('3 positions closed')
            │
            ├─> Dialog closes
            │
            └─> Dashboard refreshes
```

---

## Guard System

### Billing Guard Flow
```
Dashboard renders
    │
    └─> BillingGuard component mounts
            │
            ├─> useEffect → loadBillingStatus()
            │       │
            │       └─> GET /api/billing/status
            │               │
            │               └─> Response: { status: 'past_due', ... }
            │
            ├─> isBlocked = status ∈ (past_due, canceled, incomplete)
            │
            └─> Render:
                    │
                    ├─> Warning Banner
                    │   ├─> AlertTriangle icon
                    │   ├─> "Payment Past Due" message
                    │   └─> "Update Payment Method" button
                    │
                    ├─> Content (wrapped)
                    │   └─> Opacity: 60%, pointer-events: none
                    │
                    └─> Overlay (blocks clicks)
```

### Trial Banner Flow
```
Dashboard Overview section
    │
    └─> TrialBanner component
            │
            ├─> GET /api/billing/status → { status: 'trialing', ... }
            ├─> GET /api/billing/usage → { trades_count: 65, trades_limit: 100, ... }
            │
            ├─> Calculate:
            │   ├─> tradesRemaining = 100 - 65 = 35
            │   ├─> daysRemaining = 2
            │   └─> showWarning = tradesRemaining <= 20 || daysRemaining <= 1
            │
            └─> Render:
                    │
                    ├─> Banner (orange if warning, blue otherwise)
                    │
                    ├─> Progress Bars
                    │   ├─> Trades: 65/100 (35 remaining)
                    │   └─> Days: 1/3 (2 days left)
                    │
                    └─> Upgrade Button
```

---

## API Endpoint Mapping

```
┌──────────────────────────────────────────────────────────────┐
│                    27 REST ENDPOINTS                          │
└──────────────────────────────────────────────────────────────┘

Overview & Trading (7)
├── GET  /api/overview              → DashboardOverview.tsx
├── GET  /api/positions             → PositionsMonitor.tsx
├── GET  /api/orders                → OrdersManager.tsx
├── POST /api/orders/close          → PositionsMonitor (close button)
├── DEL  /api/orders/{order_id}     → OrdersManager (delete button)
├── GET  /api/reports/pnl           → AnalyticsPage
├── GET  /api/analytics/metrics     → AnalyticsPage
└── GET  /api/analytics/trades      → AnalyticsPage

Broker Management (5)
├── GET  /api/user/brokers          → AccountsManager.tsx
├── POST /register/{broker}         → ConnectBrokerPage.tsx
├── POST /api/accounts/switch       → ChangeAccountPage.tsx
├── GET  /api/accounts/sync_results → SyncResultsPage.tsx
└── POST /api/accounts/sync/{id}    → SyncResultsPage.tsx (retry)

Configuration (5)
├── GET  /api/user/config           → TradingConfiguration.tsx
├── PUT  /api/user/config           → TradingConfiguration.tsx (save)
├── GET  /api/user/risk_config      → RiskControls.tsx
├── PUT  /api/user/risk_config      → RiskControls.tsx (save)
└── POST /api/user/emergency_stop   → EmergencyStopDialog.tsx

API Keys (3)
├── GET  /api/user/api_keys         → ApiKeyManager.tsx
├── POST /api/user/api_keys/generate→ ApiKeyManager.tsx (generate)
└── DEL  /api/user/api_keys/{key_id}→ ApiKeyManager.tsx (delete)

Billing (4)
├── GET  /api/billing/status        → BillingPortal + Guards
├── GET  /api/billing/usage         → BillingPortal + TrialBanner
├── POST /api/billing/checkout      → BillingPortal (upgrade)
└── POST /api/billing/cancel        → BillingPortal (cancel)

Logs & Auth (3)
├── GET  /api/logs/webhooks         → LogsViewer.tsx
├── POST /api/auth/reset-password   → PasswordResetPage.tsx
└── POST /webhook                   → Backend only (TradingView)
```

---

## NATS Event System

```
Frontend Events (Published)
    │
    ├─> ai.trade.exec.order
    │   ├─> Trigger: Close position button
    │   └─> Payload: { op: 'close', position_id, user_id, timestamp }
    │
    ├─> ai.hub.kpi.ingest
    │   ├─> Trigger: Broker connection success
    │   └─> Payload: { event: 'broker_connected', user_id, broker, timestamp }
    │
    └─> ai.ops.health.sweep
        ├─> Trigger: Emergency stop confirmed
        └─> Payload: { op: 'kill_switch', user_id, timestamp, positions_closed }

Backend Events (Subscribed)
    │
    └─> ai.user.billing.status
        ├─> Published by: Stripe webhook handler
        ├─> Consumed by: Frontend (via WebSocket future)
        └─> Action: Refresh billing guards
```

---

## Caching Strategy

```
Realtime (No Cache)
├── /api/positions
├── /api/orders
├── /api/user/api_keys
├── /api/logs/webhooks
└── /api/accounts/sync_results

5 Second TTL
├── /api/overview
└── /api/analytics/trades

30 Second TTL
├── /api/user/config
├── /api/user/risk_config
├── /api/billing/status
└── /api/billing/usage

60 Second TTL
├── /api/reports/pnl
└── /api/analytics/metrics
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Production Stack                          │
└─────────────────────────────────────────────────────────────┘

Frontend (Vercel/Netlify)
├── Domain: app.tradeflow.com
├── CDN: Cloudflare
├── SSL: Auto (Let's Encrypt)
└── Environment Variables:
    ├── VITE_API_BASE_URL=https://unified.fluxeo.net/api/unify/v1
    ├── VITE_SUPABASE_URL
    ├── VITE_SUPABASE_ANON_KEY
    └── VITE_STRIPE_PUBLIC_KEY

Backend (Fluxeo Infrastructure)
├── Domain: unified.fluxeo.net
├── Framework: FastAPI (Python)
├── Server: Uvicorn
├── Load Balancer: nginx
└── Environment Variables:
    ├── DATABASE_URL (PostgreSQL)
    ├── REDIS_URL
    ├── NATS_URL
    ├── STRIPE_SECRET_KEY
    ├── TRADELOCKER_API_KEY
    ├── TOPSTEP_API_KEY
    └── TRUFOREX_API_KEY

Database (Supabase/Postgres)
├── Hosted: Supabase
├── Backup: Daily @ 2 AM UTC
├── Replication: Enabled
└── Tables:
    ├── users
    ├── broker_accounts
    ├── positions
    ├── orders
    ├── api_keys
    ├── billing_subscriptions
    └── webhook_logs

Cache (Redis)
├── Hosted: Redis Cloud
├── TTL: Per endpoint (5s/30s/60s)
└── Keys:
    ├── overview::<userId>
    ├── pos::<userId>
    ├── orders::<userId>::<status>
    └── config::<userId>

Message Queue (NATS)
├── Hosted: NATS Cloud
├── Subjects:
    ├── ai.trade.exec.order
    ├── ai.hub.kpi.ingest
    ├── ai.ops.health.sweep
    └── ai.user.billing.status
└── Persistence: Enabled

Monitoring
├── Frontend: Vercel Analytics
├── Backend: Sentry
├── Uptime: Pingdom
└── Logs: Datadog
```

---

## Security Architecture

```
Authentication Flow
├── User Login → Supabase Auth
│   ├── Email/Password validation
│   ├── JWT token issued (expires 1h)
│   └─> Access token stored in memory (not localStorage)
│
├── API Requests → Bearer Token
│   ├── Header: Authorization: Bearer ${accessToken}
│   ├── Backend validates with Supabase
│   └─> User context attached to request
│
└── Webhook Requests → API Key
    ├── Header: X-API-Key: ${apiKey}
    ├── Backend validates against database
    └─> Rate limited (300 req/min)

Authorization Rules
├── User Role
│   ├── Can view: Own data only
│   ├── Can modify: Own settings
│   └─> Cannot access: Other users' data
│
└── Admin Role (excluded from UI)
    ├── Can view: All users
    ├── Can modify: User roles, system settings
    └─> Access via separate admin dashboard

Data Protection
├── Passwords: Bcrypt hashed
├── API Keys: Encrypted at rest
├── Secrets: Environment variables
├── HTTPS: Enforced (redirect HTTP)
└── CORS: Restricted to app.tradeflow.com
```

---

## Mobile Responsive Strategy

```
Breakpoints
├── Mobile:  < 768px  → Single column, hamburger menu
├── Tablet:  768-1024 → 2 columns, collapsible sidebar
└── Desktop: > 1024px → Full layout, permanent sidebar

Mobile Optimizations
├── Navigation
│   ├── Hamburger menu (Sheet component)
│   ├── Bottom broker selector
│   └─> Collapsible sections
│
├── Tables
│   ├── Horizontal scroll
│   ├── Sticky first column
│   └─> Card view for narrow screens
│
├── Forms
│   ├── Full-width inputs
│   ├── Larger touch targets (44px min)
│   └─> Stacked button groups
│
└── Charts
    ├── Simplified legends
    ├── Touch-friendly tooltips
    └─> Responsive aspect ratios
```

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-19  
**Complexity**: Production-Grade Architecture 🏗️
