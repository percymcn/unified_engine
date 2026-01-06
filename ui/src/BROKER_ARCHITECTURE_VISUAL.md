# 🏗️ TradeFlow Broker Switching Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TRADEFLOW DASHBOARD                             │
│                     (React + TypeScript + Tailwind)                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     │     BrokerContext (Global)   │
                     │  ┌────────────────────────┐ │
                     │  │ activeBroker: topstep  │ │
                     │  │ isSyncing: false       │ │
                     │  │ connectedBrokers: [3]  │ │
                     │  └────────────────────────┘ │
                     └──────────────┬──────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌──────────────┐           ┌──────────────┐           ┌──────────────┐
│ TradeLocker  │           │   TopStep    │           │  TruForex    │
│     📈       │           │     🎯       │           │     📊       │
│              │           │              │           │              │
│ #0EA5E9      │           │  #10b981     │           │  #f59e0b     │
└──────┬───────┘           └──────┬───────┘           └──────┬───────┘
       │                          │                          │
       └──────────────────────────┴──────────────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │   API Base URL Router     │
                    │                           │
                    │  /api/tradelocker/*       │
                    │  /api/topstep/*           │
                    │  /api/truforex/*          │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────────┐
        │  Backend: https://unified.fluxeo.net/api/unify  │
        │                      /v1/{broker}/*             │
        └─────────────────────────────────────────────────┘
```

---

## Component Hierarchy

```
App.tsx
 └─ ThemeProvider
     └─ UserProvider
         └─ BrokerProvider ⭐ NEW
             ├─ AppRouter
             │   └─ Dashboard
             │       ├─ Header
             │       │   ├─ Logo
             │       │   ├─ BrokerSwitcher ⭐ NEW
             │       │   └─ SettingsDropdown
             │       │
             │       ├─ BrokerSyncIndicator ⭐ NEW (Floating)
             │       │
             │       └─ Content
             │           ├─ DashboardOverview 🔄 (Broker-aware)
             │           ├─ PositionsMonitor 🔄 (Broker-aware)
             │           ├─ OrdersManager 🔄 (Broker-aware)
             │           ├─ ApiKeyManager 🔄 (Broker-aware + Isolated)
             │           ├─ RiskControls 🔄 (Broker-aware + Isolated)
             │           ├─ TradingConfiguration 🔄 (Broker-aware + Isolated)
             │           ├─ WebhookTemplates 🔄 (Broker-aware + Isolated)
             │           ├─ AccountsManager 🔄 (Broker-aware)
             │           ├─ AnalyticsPage 🔄 (Broker-aware)
             │           ├─ LogsViewer 🔄 (Broker-aware)
             │           └─ BillingPortal (Global - NOT broker-aware)
             │
             └─ Toaster

Legend:
⭐ = New component for broker switching
🔄 = Updated to be broker-aware
Isolated = Settings stored separately per broker
```

---

## Data Flow: Broker Switch Event

```
┌──────────────────────────────────────────────────────────────────────┐
│ Step 1: User Action                                                  │
│ User clicks "TopStep" in BrokerSwitcher dropdown                    │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Step 2: Context Method Called                                        │
│ BrokerContext.switchBroker('topstep', 'account-123')                │
│                                                                       │
│ • Sets isSyncing = true                                             │
│ • Updates activeBroker = 'topstep'                                  │
│ • Updates localStorage                                               │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Step 3: Event Dispatched                                             │
│ window.dispatchEvent(new CustomEvent('broker.switch'))              │
│                                                                       │
│ Payload: { broker: 'topstep', accountId: '...', timestamp: '...' }  │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                ┌────────────────┴────────────────┐
                │                                 │
                ▼                                 ▼
┌──────────────────────────┐      ┌──────────────────────────┐
│ Step 4a: UI Updates      │      │ Step 4b: Data Refresh    │
│                          │      │                          │
│ • Sync indicator shows   │      │ • All subscribed         │
│ • Loading skeletons      │      │   components refetch     │
│ • Disabled buttons       │      │ • API calls switch to:   │
│                          │      │   /api/topstep/*         │
└──────────────────────────┘      └──────────────────────────┘
                │                                 │
                └────────────────┬────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Step 5: Data Loaded                                                  │
│                                                                       │
│ • All components receive new data                                    │
│ • Skeletons replaced with real content                              │
│ • isSyncing set to false                                            │
│ • Success toast displayed                                            │
│ • Sync indicator auto-dismisses after 2s                            │
└──────────────────────────────────────────────────────────────────────┘
```

---

## API Routing Logic

```
┌─────────────────────────────────────────────────────────────┐
│                    Component Code                           │
│                                                             │
│  const { getApiBaseUrl } = useBroker();                    │
│  const url = `${getApiBaseUrl()}/balance`;                │
│  fetch(url);                                                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│               getApiBaseUrl() Function                      │
│                                                             │
│  IF activeBroker === 'tradelocker'                         │
│    RETURN '/api/tradelocker'                               │
│                                                             │
│  ELSE IF activeBroker === 'topstep'                        │
│    RETURN '/api/topstep'                                   │
│                                                             │
│  ELSE IF activeBroker === 'truforex'                       │
│    RETURN '/api/truforex'                                  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Final API Call                             │
│                                                             │
│  TradeLocker: /api/tradelocker/balance                     │
│  TopStep:     /api/topstep/balance                         │
│  TruForex:    /api/truforex/balance                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Backend API Endpoints                          │
│                                                             │
│  https://unified.fluxeo.net/api/unify/v1/tradelocker/*    │
│  https://unified.fluxeo.net/api/unify/v1/topstep/*        │
│  https://unified.fluxeo.net/api/unify/v1/truforex/*       │
└─────────────────────────────────────────────────────────────┘
```

---

## State Management

```
┌──────────────────────────────────────────────────────────────┐
│                    BrokerContext State                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  activeBroker: 'topstep' | 'tradelocker' | 'truforex' | null│
│      ↓                                                       │
│      Determines which broker's data is displayed             │
│      Persisted to localStorage                               │
│                                                              │
│  ───────────────────────────────────────────────────────     │
│                                                              │
│  connectedBrokers: BrokerAccount[]                          │
│      ↓                                                       │
│      Array of all broker accounts user has connected         │
│      Persisted to localStorage                               │
│      Each account has: {                                     │
│        broker: BrokerType,                                   │
│        accountId: string,                                    │
│        accountName: string,                                  │
│        connected: boolean,                                   │
│        lastSync?: string                                     │
│      }                                                       │
│                                                              │
│  ───────────────────────────────────────────────────────     │
│                                                              │
│  isSyncing: boolean                                          │
│      ↓                                                       │
│      True during broker switch or manual refresh             │
│      Used to show loading states across all components       │
│                                                              │
│  ───────────────────────────────────────────────────────     │
│                                                              │
│  isLoading: boolean                                          │
│      ↓                                                       │
│      True during initial context load                        │
│      Prevents flash of wrong broker                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Component Data Dependencies

```
┌────────────────────────────────────────────────────────────────────┐
│                     Component Type Matrix                          │
├──────────────────────┬──────────────┬─────────────┬───────────────┤
│ Component            │ Depends On   │ Updates On  │ Data Isolated │
│                      │ Broker?      │ Switch?     │ Per Broker?   │
├──────────────────────┼──────────────┼─────────────┼───────────────┤
│ DashboardOverview    │ ✅ Yes       │ ✅ Yes      │ ❌ No         │
│ PositionsMonitor     │ ✅ Yes       │ ✅ Yes      │ ❌ No         │
│ OrdersManager        │ ✅ Yes       │ ✅ Yes      │ ❌ No         │
│ ApiKeyManager        │ ✅ Yes       │ ✅ Yes      │ ✅ YES        │
│ RiskControls         │ ✅ Yes       │ ✅ Yes      │ ✅ YES        │
│ TradingConfig        │ ✅ Yes       │ ✅ Yes      │ ✅ YES        │
│ WebhookTemplates     │ ✅ Yes       │ ✅ Yes      │ ✅ YES        │
│ AccountsManager      │ ✅ Yes       │ ✅ Yes      │ ❌ No         │
│ AnalyticsPage        │ ✅ Yes       │ ✅ Yes      │ ❌ No         │
│ LogsViewer           │ ✅ Yes       │ ✅ Yes      │ ❌ No         │
│ BillingPortal        │ ❌ No        │ ❌ No       │ ❌ No         │
│ UserProfile          │ ❌ No        │ ❌ No       │ ❌ No         │
└──────────────────────┴──────────────┴─────────────┴───────────────┘

Legend:
• Depends On Broker: Uses activeBroker state
• Updates On Switch: Refetches data when broker changes
• Data Isolated: Settings stored separately per broker
```

---

## Event System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Event Bus (window)                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
    ┌──────────────────────┐      ┌──────────────────────┐
    │  broker.switch       │      │  broker.refresh      │
    ├──────────────────────┤      ├──────────────────────┤
    │ Payload:             │      │ Payload:             │
    │ • broker: string     │      │ • broker: string     │
    │ • accountId: string  │      │ • timestamp: string  │
    │ • timestamp: string  │      └──────────────────────┘
    └──────────────────────┘
                │
                │ Triggers
                ▼
    ┌──────────────────────────────────────┐
    │  All Subscribed Components           │
    │                                      │
    │  • DashboardOverview.fetchData()    │
    │  • PositionsMonitor.refreshList()   │
    │  • OrdersManager.loadOrders()       │
    │  • ApiKeyManager.loadKeys()         │
    │  • RiskControls.loadSettings()      │
    │  • TradingConfig.loadConfig()       │
    │  • WebhookTemplates.generateURL()   │
    │  • AccountsManager.fetchAccounts()  │
    │  • AnalyticsPage.loadMetrics()      │
    │  • LogsViewer.fetchLogs()           │
    └──────────────────────────────────────┘
```

---

## Data Isolation Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      USER SWITCHES BROKER                      │
│                   TradeLocker → TopStep                        │
└────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┴───────────────────┐
          │                                       │
          ▼                                       ▼
┌──────────────────────┐              ┌──────────────────────┐
│  ISOLATED SETTINGS   │              │  GLOBAL SETTINGS     │
│  (Load fresh for     │              │  (Stay the same)     │
│   new broker)        │              │                      │
├──────────────────────┤              ├──────────────────────┤
│                      │              │                      │
│ • API Keys           │              │ • User Name          │
│   TL: key_abc123    │              │   "John Doe"         │
│   TS: key_xyz789    │              │                      │
│                      │              │ • User Email         │
│ • Risk Settings      │              │   "john@example.com" │
│   TL: 2% max        │              │                      │
│   TS: 1% max        │              │ • Subscription Plan  │
│                      │              │   "Pro - $40/mo"     │
│ • Trading Config     │              │                      │
│   TL: 50 contracts  │              │ • UI Theme           │
│   TS: 25 contracts  │              │   "Dark"             │
│                      │              │                      │
│ • Webhook URLs       │              │ • Language           │
│   TL: /webhook/tl   │              │   "English"          │
│   TS: /webhook/ts   │              │                      │
│                      │              │ • Notifications      │
└──────────────────────┘              │   "Email + Push"     │
                                      │                      │
                                      └──────────────────────┘
```

---

## Loading State Flow

```
┌─────────────────────────────────────────────────────────┐
│                Component Lifecycle                      │
└─────────────────────────────────────────────────────────┘

State: IDLE
├─ No data loaded
├─ activeBroker = null
└─ Show: "No broker connected" message

        │ User connects broker
        ▼

State: LOADING
├─ Initial data fetch
├─ Show: Skeleton loaders
└─ Duration: ~500-800ms

        │ Data received
        ▼

State: SUCCESS
├─ Data displayed
├─ Show: Actual content
└─ Interactive

        │ User switches broker
        ▼

State: SYNCING
├─ Refreshing data
├─ Show: Skeleton loaders + Sync indicator
└─ Duration: ~300-600ms

        │ New data received
        ▼

State: SUCCESS
├─ New broker data displayed
├─ Show: Updated content
└─ Interactive

        │ Error occurs
        ▼

State: ERROR
├─ Failed to load
├─ Show: Error message + Retry button
└─ User can retry
```

---

## Persistence Strategy

```
┌────────────────────────────────────────────────────────┐
│              localStorage Structure                    │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Key: 'activeBroker'                                  │
│  Value: 'topstep'                                     │
│  Purpose: Remember active broker across sessions      │
│                                                        │
│  ────────────────────────────────────────────────      │
│                                                        │
│  Key: 'connectedBrokers'                              │
│  Value: [                                             │
│    {                                                  │
│      broker: 'tradelocker',                          │
│      accountId: 'TL-12345',                          │
│      accountName: 'My TradeLocker',                  │
│      connected: true,                                │
│      lastSync: '2025-10-19T14:30:00Z'                │
│    },                                                 │
│    {                                                  │
│      broker: 'topstep',                              │
│      accountId: 'TS-67890',                          │
│      accountName: 'TopStep Pro',                     │
│      connected: true,                                │
│      lastSync: '2025-10-19T14:32:15Z'                │
│    }                                                  │
│  ]                                                    │
│  Purpose: Remember all connected brokers              │
│                                                        │
└────────────────────────────────────────────────────────┘

On Page Load:
1. Read 'activeBroker' from localStorage
2. Read 'connectedBrokers' from localStorage
3. Set context state
4. Dispatch initial data fetch
5. User sees last active broker's data

On Page Refresh:
• State persists
• No need to reselect broker
• Seamless experience
```

---

## Mobile Responsiveness

```
Desktop (>1024px)
┌──────────────────────────────────────────────────────┐
│ ┌────────┐  ┌─────────────────────┐  ┌──────────┐  │
│ │  Logo  │  │  BrokerSwitcher    │  │ Settings │  │
│ └────────┘  └─────────────────────┘  └──────────┘  │
└──────────────────────────────────────────────────────┘

Tablet (768-1024px)
┌──────────────────────────────────────────────────────┐
│ ┌────┐  ┌───────────────┐  ┌──────────┐            │
│ │Logo│  │BrokerSwitcher │  │ Settings │            │
│ └────┘  └───────────────┘  └──────────┘            │
└──────────────────────────────────────────────────────┘

Mobile (<768px)
┌────────────────────────────┐
│ ┌──┐  ┌──────┐  ┌───────┐ │
│ │≡ │  │ Logo │  │ ⚙️    │ │
│ └──┘  └──────┘  └───────┘ │
├────────────────────────────┤
│ ┌────────────────────────┐ │
│ │  BrokerSwitcher        │ │
│ │  (Full Width Dropdown) │ │
│ └────────────────────────┘ │
└────────────────────────────┘
```

---

## Success Metrics

```
┌─────────────────────────────────────────────────────────┐
│              System Performance Targets                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Broker Switch Time:        < 600ms                    │
│  UI Feedback Delay:         < 50ms                     │
│  Context Load Time:         < 100ms                    │
│  Event Propagation:         < 10ms                     │
│  LocalStorage Read:         < 5ms                      │
│  Component Refetch:         < 500ms (per component)    │
│                                                         │
│  User Experience:                                       │
│  • No flash of wrong broker                            │
│  • Smooth skeleton transitions                         │
│  • Visual feedback for all actions                     │
│  • Error states clearly communicated                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Architecture Complete

This visual architecture provides:
- Clear component hierarchy
- Data flow documentation
- Event system mapping
- State management overview
- Isolation strategy
- Performance targets

All systems operational and ready for production! 🚀
