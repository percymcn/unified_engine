# 🎯 Broker Navigation Bar - Dynamic Switching Guide

## Overview

The **BrokerNavigationBar** component provides a top-level, always-visible interface for switching between connected brokers (TradeLocker, Topstep, TruForex). All dashboard data, settings, and configurations automatically sync and update when switching brokers.

---

## 🎨 Visual Design

```
┌─────────────────────────────────────────────────────────────────┐
│  [📈 TradeLocker]  [🎯 Topstep]  [📊 TruForex]   Syncing data... │
│       ✓ Active        • Connected      (Not Connected)           │
└─────────────────────────────────────────────────────────────────┘
```

### Features:
- **Active Tab**: Blue underline + green checkmark + bold text
- **Connected Tab**: Small colored dot indicator + hover effect
- **Disconnected Tab**: Grayed out + cursor disabled
- **Syncing State**: Spinning loader icon + "Syncing data..." text

---

## 📍 Location in Dashboard

```tsx
<Dashboard>
  <Header>
    <Logo /> <BrokerSwitcher (compact) /> <UserInfo /> <Settings />
  </Header>
  
  <BrokerNavigationBar /> ← Top-level switcher
  
  <MainContent>
    <Sidebar />
    <DynamicContent /> ← Updates based on active broker
  </MainContent>
</Dashboard>
```

---

## 🔄 How Dynamic Switching Works

### 1. **User Clicks Broker Tab**
```tsx
onClick={() => handleBrokerClick('tradelocker')}
```

### 2. **BrokerContext Updates**
```tsx
const handleBrokerClick = async (brokerId: BrokerType) => {
  // Find connected account for this broker
  const brokerAccount = connectedBrokers.find(b => b.broker === brokerId);
  
  if (brokerAccount) {
    // Switch active broker in context
    await switchBroker(brokerId, brokerAccount.accountId);
  }
};
```

### 3. **Context Dispatches Events**
```tsx
// In BrokerContext.switchBroker()
const event = new CustomEvent('broker.switch', {
  detail: { 
    broker: 'tradelocker',
    accountId: 'acc-123456',
    timestamp: '2025-10-19T10:30:00Z'
  }
});
window.dispatchEvent(event);
```

### 4. **All Components React**
All components that use `useBroker()` automatically re-render with new data:

```tsx
// In any component
const { activeBroker, activeBrokerAccount } = useBroker();

// This automatically updates when broker switches
useEffect(() => {
  fetchDataForBroker(activeBroker);
}, [activeBroker]);
```

---

## 🎯 Components That Auto-Update

When you switch brokers, these components automatically sync:

### Dashboard Components
✅ **DashboardOverview** - Balance, equity, P&L, active positions
✅ **AccountsManager** - Shows accounts for selected broker
✅ **PositionsMonitor** - Displays positions for active broker
✅ **OrdersManager** - Shows orders for active broker
✅ **TradingConfiguration** - Loads settings for active broker
✅ **RiskControls** - Shows risk settings for active broker
✅ **WebhookTemplates** - Generates webhooks for active broker
✅ **ApiKeyManager** - Shows API keys for active broker
✅ **LogsViewer** - Filters logs by active broker
✅ **AnalyticsPage** - Shows analytics for active broker

### Example: DashboardOverview Auto-Update
```tsx
export function DashboardOverview() {
  const { activeBroker, activeBrokerAccount } = useBroker();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    // This runs automatically when activeBroker changes
    async function fetchStats() {
      const data = await api.getStats(activeBroker);
      setStats(data);
    }
    
    if (activeBroker) {
      fetchStats();
    }
  }, [activeBroker]); // ← Dependency triggers re-fetch

  return (
    <div>
      <h2>{getBrokerDisplayName(activeBroker)} Dashboard</h2>
      <p>Balance: ${stats?.balance}</p>
      <p>Equity: ${stats?.equity}</p>
    </div>
  );
}
```

---

## 🔧 Implementation Details

### BrokerNavigationBar Component

```tsx
export function BrokerNavigationBar() {
  const { 
    activeBroker,      // Currently active broker
    connectedBrokers,  // Array of connected broker accounts
    switchBroker,      // Function to switch brokers
    isSyncing          // Loading state during switch
  } = useBroker();

  const brokerOptions = [
    { id: 'tradelocker', name: 'TradeLocker', icon: <TradeLockerIcon />, color: '#0EA5E9' },
    { id: 'topstep', name: 'Topstep', icon: '🎯', color: '#10b981' },
    { id: 'truforex', name: 'TruForex', icon: '📊', color: '#f59e0b' }
  ];

  const isBrokerConnected = (brokerId) => {
    return connectedBrokers.some(b => b.broker === brokerId);
  };

  const isBrokerActive = (brokerId) => {
    return activeBroker === brokerId;
  };

  const handleBrokerClick = async (brokerId) => {
    const brokerAccount = connectedBrokers.find(b => b.broker === brokerId);
    if (brokerAccount) {
      await switchBroker(brokerId, brokerAccount.accountId);
    }
  };

  return (
    <div className="broker-nav-bar">
      {brokerOptions.map((broker) => {
        const isConnected = isBrokerConnected(broker.id);
        const isActive = isBrokerActive(broker.id);
        
        return (
          <button
            onClick={() => isConnected && handleBrokerClick(broker.id)}
            disabled={!isConnected || isSyncing}
            className={cn(
              isActive && "active",
              !isConnected && "disabled"
            )}
            style={{ borderBottomColor: isActive ? broker.color : 'transparent' }}
          >
            {broker.icon}
            <span>{broker.name}</span>
            {isActive && isSyncing && <Loader2 className="animate-spin" />}
            {isActive && !isSyncing && <CheckCircle />}
          </button>
        );
      })}
    </div>
  );
}
```

---

## 🎨 Styling & States

### Tab States

#### 1. **Active & Connected**
```css
background: #002b36
border: 1px solid #374151
border-bottom: 2px solid {broker.color}
color: white
font-weight: 500
icon: ✓ CheckCircle (green)
```

#### 2. **Connected (Not Active)**
```css
background: transparent
color: gray-400
hover:background: #002b36/50
icon: • colored dot
cursor: pointer
```

#### 3. **Not Connected**
```css
opacity: 0.4
cursor: not-allowed
disabled: true
```

#### 4. **Syncing (Active)**
```css
opacity: 0.7
icon: ⟳ Loader2 (spinning)
additional: "Syncing data..." text on right
```

---

## 📊 Data Flow Diagram

```
User Click
    ↓
handleBrokerClick('topstep')
    ↓
BrokerContext.switchBroker()
    ↓
┌─────────────────────────────────┐
│ 1. Update activeBroker state   │
│ 2. Update activeBrokerAccount   │
│ 3. Save to localStorage         │
│ 4. Dispatch 'broker.switch'     │
└─────────────────────────────────┘
    ↓
All Components with useBroker() Re-render
    ↓
┌────────────────────────────────────────────┐
│ • DashboardOverview fetches new data       │
│ • AccountsManager loads Topstep accounts   │
│ • PositionsMonitor shows Topstep positions │
│ • Settings load Topstep configuration      │
│ • API calls use Topstep endpoints          │
└────────────────────────────────────────────┘
    ↓
toast.success("Switched to Topstep")
```

---

## 🧪 Testing the Dynamic Updates

### Test Scenario 1: Switch from TradeLocker to Topstep

1. **Initial State**: TradeLocker active, showing balance $52,430
2. **User Action**: Click "Topstep" tab
3. **Expected Result**:
   - Topstep tab becomes active (blue underline)
   - "Syncing data..." appears briefly
   - Dashboard balance updates to Topstep account balance
   - Positions list shows Topstep positions
   - Settings reflect Topstep configuration
   - Toast: "Switched to Topstep"

### Test Scenario 2: Click on Disconnected Broker

1. **Initial State**: Only TradeLocker connected
2. **User Action**: Click "TruForex" tab (not connected)
3. **Expected Result**:
   - Button is disabled (cursor: not-allowed)
   - No action occurs
   - Tab remains grayed out

### Test Scenario 3: Rapid Switching

1. **User Action**: Quickly click TradeLocker → Topstep → TradeLocker
2. **Expected Result**:
   - Each switch queues properly
   - No race conditions
   - Final state matches last clicked broker
   - Data is consistent

---

## 🔐 Persistence

### LocalStorage Keys
```typescript
// Saved automatically by BrokerContext
localStorage.setItem('activeBroker', 'tradelocker');
localStorage.setItem('connectedBrokers', JSON.stringify([
  { broker: 'tradelocker', accountId: 'acc-123', accountName: 'Main' },
  { broker: 'topstep', accountId: 'acc-456', accountName: 'Funded' }
]));
```

### On Page Reload
1. BrokerContext reads localStorage
2. Restores last active broker
3. Restores all connected brokers
4. Dashboard loads with correct broker data

---

## 🎯 API Endpoint Routing

When broker switches, all API calls automatically route to correct endpoints:

```typescript
// In api-client-enhanced.ts
const API_BASE = 'https://unified.fluxeo.net/api/unify/v1';

// Active Broker: tradelocker
GET /api/positions → Returns TradeLocker positions

// After switching to topstep
GET /api/positions → Returns Topstep positions

// Query params or headers identify the broker
headers: {
  'X-Active-Broker': activeBroker,
  'X-Account-Id': activeBrokerAccount.accountId
}
```

---

## 🚀 Best Practices

### 1. Always Use useBroker() Hook
```tsx
// ✅ Good
const { activeBroker } = useBroker();
useEffect(() => fetchData(activeBroker), [activeBroker]);

// ❌ Bad - hardcoded broker
useEffect(() => fetchData('tradelocker'), []);
```

### 2. Handle Loading States
```tsx
const { activeBroker, isSyncing } = useBroker();

if (isSyncing) {
  return <Skeleton />;
}

return <DataDisplay broker={activeBroker} />;
```

### 3. Listen to Broker Events
```tsx
useEffect(() => {
  const handleBrokerSwitch = (e) => {
    console.log('Broker switched to:', e.detail.broker);
    // Perform additional actions
  };

  window.addEventListener('broker.switch', handleBrokerSwitch);
  return () => window.removeEventListener('broker.switch', handleBrokerSwitch);
}, []);
```

### 4. Show Broker-Specific UI
```tsx
const { activeBroker } = useBroker();

return (
  <div>
    <h2>{getBrokerDisplayName(activeBroker)} Dashboard</h2>
    {activeBroker === 'truforex' && (
      <Alert>TruForex requires EA installation</Alert>
    )}
  </div>
);
```

---

## 📱 Mobile Responsiveness

The BrokerNavigationBar adapts to mobile:

```css
/* Desktop: Full width with padding */
@media (min-width: 768px) {
  .broker-nav-bar {
    padding: 12px 24px;
  }
}

/* Mobile: Compact with horizontal scroll */
@media (max-width: 767px) {
  .broker-nav-bar {
    padding: 8px 16px;
    overflow-x: auto;
    white-space: nowrap;
  }
  
  button {
    padding: 8px 12px;
    font-size: 12px;
  }
}
```

---

## 🎉 Summary

The **BrokerNavigationBar** provides:

✅ **Visual Clarity** - Clear indication of active broker
✅ **One-Click Switching** - Instant broker changes
✅ **Auto-Sync** - All components update automatically
✅ **State Persistence** - Remembers selection across sessions
✅ **Loading States** - Visual feedback during sync
✅ **Disabled States** - Clear indication of disconnected brokers
✅ **Mobile Friendly** - Responsive design
✅ **Accessible** - Keyboard navigation support

**Result**: Users can seamlessly switch between brokers with confidence that all data, settings, and configurations dynamically update to match their selection. 🚀
