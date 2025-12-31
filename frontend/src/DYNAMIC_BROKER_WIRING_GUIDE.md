# 🔄 Dynamic Broker Switching System - Wiring Guide

## 📋 System Overview

TradeFlow SaaS Dashboard now features a **dynamic broker switching system** that maintains context across three different backend platforms while providing seamless real-time data synchronization.

### Supported Brokers
- **TradeLocker** 📈
- **TopStep / Project X** 🎯  
- **TruForex / MT4 / MT5** 📊

---

## 🏗️ Architecture

### Single Source of Truth: BrokerContext

```typescript
// Central state management for all broker operations
interface BrokerContextType {
  activeBroker: BrokerType | null;          // Currently selected broker
  activeBrokerAccount: BrokerAccount | null; // Active account details
  connectedBrokers: BrokerAccount[];         // All connected accounts
  isLoading: boolean;                        // Initial data loading
  isSyncing: boolean;                        // Active sync operation
  switchBroker: (broker, accountId?) => Promise<void>;
  refreshBrokerData: () => Promise<void>;
  getApiBaseUrl: () => string;
}
```

### Data Flow

```
User Action (Broker Switch)
    ↓
BrokerContext.switchBroker()
    ↓
Dispatch Event: broker.switch
    ↓
All Subscribed Components Re-fetch
    ↓
UI Updates with New Data
```

---

## 🎯 API Routing Logic

### Dynamic Base URL Resolution

```javascript
// Automatic API endpoint mapping
IF activeBroker == "tradelocker":
    baseAPI = "https://unified.fluxeo.net/api/unify/v1/tradelocker"
    
ELIF activeBroker == "topstep":
    baseAPI = "https://unified.fluxeo.net/api/unify/v1/topstep"
    
ELIF activeBroker == "truforex":
    baseAPI = "https://unified.fluxeo.net/api/unify/v1/truforex"
```

### Usage in Components

```typescript
const { getApiBaseUrl, activeBroker } = useBroker();

// All API calls automatically use correct endpoint
const fetchBalance = async () => {
  const url = `${getApiBaseUrl()}/balance`;
  const response = await fetch(url);
  // ...
};
```

---

## 📦 Component Wiring Specifications

### 1️⃣ Dashboard Overview Component

**File:** `/components/DashboardOverview.tsx`

```yaml
wiring:
  data_sources:
    - endpoint: GET {baseAPI}/balance
      depends_on: activeBrokerId
      updates_on: [broker.switch, broker.refresh]
      
    - endpoint: GET {baseAPI}/account/summary
      depends_on: activeBrokerId
      updates_on: [broker.switch, broker.refresh]
      
    - endpoint: GET {baseAPI}/pnl/daily
      depends_on: activeBrokerId
      updates_on: [broker.switch, broker.refresh]
      
  state_management:
    loading_states: [initial, syncing, success, error]
    refresh_interval: 30000  # 30 seconds
    
  events_subscribed:
    - broker.switch
    - broker.refresh
```

**Implementation:**
```typescript
import { useBroker } from '../contexts/BrokerContext';
import { useEffect, useState } from 'react';

export function DashboardOverview() {
  const { activeBroker, getApiBaseUrl, isSyncing } = useBroker();
  const [balance, setBalance] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!activeBroker) return;
    
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`${getApiBaseUrl()}/balance`);
        const data = await response.json();
        setBalance(data);
      } catch (error) {
        console.error('Error fetching balance:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();

    // Listen for broker switch events
    const handleBrokerSwitch = () => fetchData();
    window.addEventListener('broker.switch', handleBrokerSwitch);
    window.addEventListener('broker.refresh', handleBrokerSwitch);

    return () => {
      window.removeEventListener('broker.switch', handleBrokerSwitch);
      window.removeEventListener('broker.refresh', handleBrokerSwitch);
    };
  }, [activeBroker, getApiBaseUrl]);

  if (isLoading || isSyncing) {
    return <SkeletonLoader />;
  }

  return <div>{/* Render balance data */}</div>;
}
```

---

### 2️⃣ Positions Monitor Component

**File:** `/components/PositionsMonitor.tsx`

```yaml
wiring:
  data_sources:
    - endpoint: GET {baseAPI}/positions
      depends_on: activeBrokerId
      updates_on: [broker.switch, broker.refresh]
      poll_interval: 5000  # 5 seconds for live positions
      
  state_management:
    loading_states: [skeleton, updating, live]
    websocket_fallback: true
    
  events_subscribed:
    - broker.switch
    - broker.refresh
    - position.update
```

---

### 3️⃣ Orders Manager Component

**File:** `/components/OrdersManager.tsx`

```yaml
wiring:
  data_sources:
    - endpoint: GET {baseAPI}/orders
      depends_on: activeBrokerId
      updates_on: [broker.switch, broker.refresh]
      
    - endpoint: DELETE {baseAPI}/orders/{orderId}
      depends_on: activeBrokerId
      triggers: order.cancelled
      
  state_management:
    loading_states: [initial, refreshing, cancelling]
    optimistic_updates: true
    
  events_subscribed:
    - broker.switch
    - broker.refresh
    
  events_dispatched:
    - order.cancelled
```

---

### 4️⃣ API Key Manager Component

**File:** `/components/ApiKeyManager.tsx`

```yaml
wiring:
  data_sources:
    - endpoint: GET {baseAPI}/api-keys
      depends_on: activeBrokerId
      updates_on: broker.switch
      
    - endpoint: POST {baseAPI}/api-keys
      depends_on: activeBrokerId
      
  state_management:
    per_broker_keys: true
    isolation: required
    
  events_subscribed:
    - broker.switch
    
  IMPORTANT: 
    - API keys are ISOLATED per broker
    - Switching brokers loads different keys
    - Keys are NEVER shared across brokers
```

---

### 5️⃣ Risk Controls Component

**File:** `/components/RiskControls.tsx`

```yaml
wiring:
  data_sources:
    - endpoint: GET {baseAPI}/risk-settings
      depends_on: activeBrokerId
      updates_on: broker.switch
      
    - endpoint: PUT {baseAPI}/risk-settings
      depends_on: activeBrokerId
      
  state_management:
    per_broker_settings: true
    isolation: required
    
  settings_isolated:
    - max_position_size
    - risk_percentage
    - auto_close_rules
    - trailing_stop_config
    - daily_loss_limit
    
  events_subscribed:
    - broker.switch
    
  IMPORTANT:
    - Risk settings are ISOLATED per broker
    - Each broker has independent configuration
    - Switching does NOT carry over settings
```

---

### 6️⃣ Trading Configuration Component

**File:** `/components/TradingConfiguration.tsx`

```yaml
wiring:
  data_sources:
    - endpoint: GET {baseAPI}/config
      depends_on: activeBrokerId
      updates_on: broker.switch
      
    - endpoint: PUT {baseAPI}/config
      depends_on: activeBrokerId
      
  state_management:
    per_broker_config: true
    isolation: required
    
  settings_isolated:
    - default_position_size
    - slippage_tolerance
    - execution_mode
    - order_type_preferences
    
  events_subscribed:
    - broker.switch
```

---

### 7️⃣ Webhook Templates Component

**File:** `/components/WebhookTemplates.tsx`

```yaml
wiring:
  data_sources:
    - endpoint: GET {baseAPI}/webhooks/url
      depends_on: activeBrokerId
      updates_on: broker.switch
      
  state_management:
    per_broker_urls: true
    dynamic_generation: true
    
  webhook_format:
    url: "https://unified.fluxeo.net/api/unify/v1/{broker}/webhook"
    auth_header: "X-API-Key: {broker_specific_key}"
    
  events_subscribed:
    - broker.switch
    
  IMPORTANT:
    - Webhook URLs are UNIQUE per broker
    - TradingView alerts must use correct URL
    - API keys in webhooks are broker-specific
```

---

### 8️⃣ Analytics Page Component

**File:** `/components/AnalyticsPage.tsx`

```yaml
wiring:
  data_sources:
    - endpoint: GET {baseAPI}/analytics/performance
      depends_on: activeBrokerId
      updates_on: [broker.switch, broker.refresh]
      
    - endpoint: GET {baseAPI}/analytics/trades
      depends_on: activeBrokerId
      updates_on: broker.switch
      
  state_management:
    loading_states: [skeleton, loading, complete]
    cache_per_broker: true
    
  events_subscribed:
    - broker.switch
    - broker.refresh
```

---

### 9️⃣ Accounts Manager Component

**File:** `/components/AccountsManager.tsx`

```yaml
wiring:
  data_sources:
    - endpoint: GET {baseAPI}/accounts
      depends_on: activeBrokerId
      updates_on: broker.switch
      
  state_management:
    loading_states: [initial, syncing]
    multi_account_support: true
    
  events_subscribed:
    - broker.switch
    
  IMPORTANT:
    - Each broker can have multiple accounts
    - Account list updates when broker switches
    - Account IDs are broker-specific
```

---

## 🎨 UI Components That React to Broker Changes

### Components That MUST Update

| Component | Updates On Switch? | Data Source | Refresh Rate |
|-----------|-------------------|-------------|--------------|
| **Balance Widget** | ✅ Yes | `{baseAPI}/balance` | 30s |
| **Equity Widget** | ✅ Yes | `{baseAPI}/account/summary` | 30s |
| **PnL Chart** | ✅ Yes | `{baseAPI}/pnl/daily` | On demand |
| **Trade History** | ✅ Yes | `{baseAPI}/trades` | On switch |
| **Open Positions** | ✅ Yes | `{baseAPI}/positions` | 5s |
| **Pending Orders** | ✅ Yes | `{baseAPI}/orders` | 10s |
| **API Keys Panel** | ✅ Yes | `{baseAPI}/api-keys` | On switch |
| **Risk Settings** | ✅ Yes | `{baseAPI}/risk-settings` | On switch |
| **Webhook URLs** | ✅ Yes | `{baseAPI}/webhooks/url` | On switch |
| **Account Selector** | ✅ Yes | `{baseAPI}/accounts` | On switch |
| **Broker Logo** | ✅ Yes | Context | Instant |
| **Analytics** | ✅ Yes | `{baseAPI}/analytics/*` | On switch |

### Components That DO NOT Update

| Component | Updates On Switch? | Reason |
|-----------|-------------------|--------|
| **Billing/Subscription** | ❌ No | Global per user |
| **User Profile** | ❌ No | Global per user |
| **Plan/Pricing** | ❌ No | Global per user |
| **Support Chat** | ❌ No | Global feature |
| **Navigation Menu** | ❌ No | UI structure |

---

## 🔔 Event System

### Events Dispatched

```typescript
// When user switches broker
event: 'broker.switch'
payload: {
  broker: 'topstep',
  accountId: 'TSX-12345',
  timestamp: '2025-10-19T14:23:00Z'
}

// When user refreshes data
event: 'broker.refresh'
payload: {
  broker: 'tradelocker',
  timestamp: '2025-10-19T14:24:00Z'
}

// When data sync completes
event: 'broker.sync.complete'
payload: {
  broker: 'truforex',
  success: true,
  timestamp: '2025-10-19T14:25:00Z'
}
```

### Subscribing to Events

```typescript
useEffect(() => {
  const handleBrokerSwitch = (event) => {
    console.log('Broker switched:', event.detail);
    // Refetch component data
    fetchData();
  };

  window.addEventListener('broker.switch', handleBrokerSwitch);
  
  return () => {
    window.removeEventListener('broker.switch', handleBrokerSwitch);
  };
}, []);
```

---

## 🎭 UI State Management

### Loading States

```typescript
// Component state machine
type LoadingState = 
  | 'idle'           // Not loaded yet
  | 'loading'        // Initial load
  | 'syncing'        // Refreshing data
  | 'success'        // Data loaded
  | 'error';         // Failed to load

// UI rendering based on state
if (state === 'loading' || state === 'syncing') {
  return <SkeletonLoader />;
}

if (state === 'error') {
  return <ErrorMessage onRetry={refetch} />;
}

return <DataDisplay data={data} />;
```

### Skeleton Loaders

```typescript
// Show skeleton during broker switch (300-600ms)
export function BalanceWidget() {
  const { isSyncing } = useBroker();
  
  if (isSyncing) {
    return (
      <Card className="bg-[#001f29] border-gray-800">
        <CardContent className="p-6">
          <div className="animate-pulse">
            <div className="h-4 bg-gray-700 rounded w-24 mb-2"></div>
            <div className="h-8 bg-gray-700 rounded w-32"></div>
          </div>
        </CardContent>
      </Card>
    );
  }
  
  return <ActualBalance />;
}
```

---

## 🔒 Data Isolation Rules

### ⚠️ CRITICAL: Per-Broker Settings

These settings **MUST** be isolated per broker:

1. **API Keys**
   - Each broker has unique keys
   - NEVER share keys between brokers
   - Load/save independently

2. **Risk Settings**
   - Position size limits
   - Risk percentage
   - Auto-close rules
   - Trailing stops
   - Daily loss limits

3. **Trading Configuration**
   - Default order sizes
   - Slippage tolerance
   - Execution preferences

4. **Webhook URLs**
   - Unique URL per broker
   - Broker-specific authentication

### ✅ Global Settings

These settings are **shared** across all brokers:

1. **User Account**
   - Email, name, password
   - User ID

2. **Subscription/Billing**
   - Plan tier (Starter/Pro/Elite)
   - Payment method
   - Trial status

3. **UI Preferences**
   - Theme (dark/light)
   - Language
   - Notifications

---

## 📊 Broker Context Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    BrokerContext (Global State)              │
│                                                              │
│  activeBroker: "topstep"                                    │
│  activeBrokerAccount: { broker: "topstep", accountId: "..." }│
│  connectedBrokers: [TradeLocker, TopStep, TruForex]         │
│  isSyncing: false                                           │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┬──────────────┬──────────────┐
        │                     │              │              │
        ▼                     ▼              ▼              ▼
┌──────────────┐    ┌──────────────┐  ┌──────────────┐  ┌────────────┐
│ Dashboard    │    │ Positions    │  │ Orders       │  │ Risk       │
│ Overview     │    │ Monitor      │  │ Manager      │  │ Controls   │
│              │    │              │  │              │  │            │
│ GET /balance │    │ GET /positions│  │ GET /orders │  │ GET /risk  │
└──────────────┘    └──────────────┘  └──────────────┘  └────────────┘
        │                     │              │              │
        └─────────────────────┴──────────────┴──────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  API Base URL      │
                    │  /api/{broker}/*   │
                    └────────────────────┘
```

---

## 🚀 Quick Integration Checklist

For engineers integrating new components:

- [ ] Import `useBroker()` hook
- [ ] Subscribe to `broker.switch` event
- [ ] Use `getApiBaseUrl()` for API calls
- [ ] Show loading state when `isSyncing === true`
- [ ] Refetch data when `activeBroker` changes
- [ ] Handle `activeBroker === null` (no broker connected)
- [ ] Add skeleton/loading UI for smooth transitions
- [ ] Test switching between all three brokers
- [ ] Verify data isolation (settings don't leak)
- [ ] Add error handling for failed API calls

---

## 📝 Example: Complete Component Implementation

```typescript
import { useEffect, useState } from 'react';
import { useBroker } from '../contexts/BrokerContext';
import { Card, CardContent } from './ui/card';
import { Skeleton } from './ui/skeleton';
import { toast } from 'sonner@2.0.3';

export function AccountBalance() {
  const { activeBroker, getApiBaseUrl, isSyncing } = useBroker();
  const [balance, setBalance] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!activeBroker) {
      setBalance(null);
      setIsLoading(false);
      return;
    }

    const fetchBalance = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`${getApiBaseUrl()}/balance`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('apiKey')}`
          }
        });

        if (!response.ok) throw new Error('Failed to fetch balance');

        const data = await response.json();
        setBalance(data.balance);
      } catch (error) {
        console.error('Error fetching balance:', error);
        toast.error('Failed to load balance');
      } finally {
        setIsLoading(false);
      }
    };

    fetchBalance();

    // Listen for broker events
    const handleBrokerEvent = () => fetchBalance();
    window.addEventListener('broker.switch', handleBrokerEvent);
    window.addEventListener('broker.refresh', handleBrokerEvent);

    return () => {
      window.removeEventListener('broker.switch', handleBrokerEvent);
      window.removeEventListener('broker.refresh', handleBrokerEvent);
    };
  }, [activeBroker, getApiBaseUrl]);

  if (isLoading || isSyncing) {
    return (
      <Card className="bg-[#001f29] border-gray-800">
        <CardContent className="p-6">
          <Skeleton className="h-4 w-24 mb-2" />
          <Skeleton className="h-8 w-32" />
        </CardContent>
      </Card>
    );
  }

  if (!activeBroker) {
    return (
      <Card className="bg-[#001f29] border-gray-800">
        <CardContent className="p-6">
          <p className="text-gray-400">No broker connected</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-[#001f29] border-gray-800">
      <CardContent className="p-6">
        <p className="text-sm text-gray-400 mb-1">Balance</p>
        <p className="text-2xl text-white">
          ${balance?.toLocaleString() || '0.00'}
        </p>
      </CardContent>
    </Card>
  );
}
```

---

## ✅ Dynamic Broker Switching + Backend Mapping Complete

This system provides:
- ✔️ Dynamic broker context switching
- ✔️ Real-time data synchronization
- ✔️ Per-broker setting isolation
- ✔️ Event-driven architecture
- ✔️ Smooth UI transitions
- ✔️ Complete wiring documentation
- ✔️ Production-ready error handling
- ✔️ Engineer-friendly integration guide

**Backend API Integration Point:** `https://unified.fluxeo.net/api/unify/v1/{broker}/*`

All components are now broker-aware and will seamlessly sync data when users switch between TradeLocker, TopStep, and TruForex platforms.
