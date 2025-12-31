# 🚀 Broker Switching Quick Start Guide

## For Developers Adding New Components

### Step 1: Import the Hook

```typescript
import { useBroker } from '../contexts/BrokerContext';
```

### Step 2: Access Broker State

```typescript
export function YourComponent() {
  const { 
    activeBroker,      // Currently selected broker ('tradelocker' | 'topstep' | 'truforex')
    getApiBaseUrl,     // Function that returns correct API base URL
    isSyncing          // Boolean - true during data refresh
  } = useBroker();
}
```

### Step 3: Fetch Data Using Broker Context

```typescript
const [data, setData] = useState(null);
const [loading, setLoading] = useState(true);

useEffect(() => {
  if (!activeBroker) return;
  
  const fetchData = async () => {
    setLoading(true);
    try {
      // getApiBaseUrl() automatically returns correct endpoint
      const response = await fetch(`${getApiBaseUrl()}/your-endpoint`);
      const json = await response.json();
      setData(json);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  fetchData();

  // IMPORTANT: Listen for broker switch events
  window.addEventListener('broker.switch', fetchData);
  window.addEventListener('broker.refresh', fetchData);

  return () => {
    window.removeEventListener('broker.switch', fetchData);
    window.removeEventListener('broker.refresh', fetchData);
  };
}, [activeBroker, getApiBaseUrl]);
```

### Step 4: Handle Loading States

```typescript
if (loading || isSyncing) {
  return (
    <Card className="bg-[#001f29] border-gray-800">
      <CardContent className="p-6">
        <div className="animate-pulse space-y-2">
          <div className="h-4 bg-gray-700 rounded w-3/4"></div>
          <div className="h-4 bg-gray-700 rounded w-1/2"></div>
        </div>
      </CardContent>
    </Card>
  );
}

if (!activeBroker) {
  return <div className="text-gray-400">No broker connected</div>;
}

return <div>{/* Your component content */}</div>;
```

## Common Patterns

### Pattern 1: Fetch on Mount and Broker Switch

```typescript
useEffect(() => {
  if (!activeBroker) return;
  
  fetchDataFunction();

  const handleBrokerEvent = () => fetchDataFunction();
  window.addEventListener('broker.switch', handleBrokerEvent);
  window.addEventListener('broker.refresh', handleBrokerEvent);

  return () => {
    window.removeEventListener('broker.switch', handleBrokerEvent);
    window.removeEventListener('broker.refresh', handleBrokerEvent);
  };
}, [activeBroker]);
```

### Pattern 2: Auto-Refresh Every N Seconds

```typescript
useEffect(() => {
  if (!activeBroker) return;
  
  fetchDataFunction();

  // Refresh every 30 seconds
  const interval = setInterval(fetchDataFunction, 30000);

  const handleBrokerEvent = () => fetchDataFunction();
  window.addEventListener('broker.switch', handleBrokerEvent);

  return () => {
    clearInterval(interval);
    window.removeEventListener('broker.switch', handleBrokerEvent);
  };
}, [activeBroker]);
```

### Pattern 3: Manual Refresh Button

```typescript
const { refreshBrokerData } = useBroker();
const [isRefreshing, setIsRefreshing] = useState(false);

const handleManualRefresh = async () => {
  setIsRefreshing(true);
  await refreshBrokerData();
  setIsRefreshing(false);
};

return (
  <Button 
    onClick={handleManualRefresh} 
    disabled={isRefreshing}
  >
    <RefreshCw className={isRefreshing ? 'animate-spin' : ''} />
    Refresh
  </Button>
);
```

## API Endpoint Examples

### Current Broker Endpoints

```typescript
// Automatically resolves to correct broker API
GET ${getApiBaseUrl()}/balance          // Account balance
GET ${getApiBaseUrl()}/positions        // Open positions
GET ${getApiBaseUrl()}/orders           // Pending orders
GET ${getApiBaseUrl()}/trades           // Trade history
GET ${getApiBaseUrl()}/api-keys         // API keys (isolated per broker)
GET ${getApiBaseUrl()}/risk-settings    // Risk config (isolated per broker)
GET ${getApiBaseUrl()}/config           // Trading config (isolated per broker)
```

### What getApiBaseUrl() Returns

```javascript
// When activeBroker = 'tradelocker'
getApiBaseUrl() // → "https://unified.fluxeo.net/api/unify/v1/tradelocker"

// When activeBroker = 'topstep'
getApiBaseUrl() // → "https://unified.fluxeo.net/api/unify/v1/topstep"

// When activeBroker = 'truforex'
getApiBaseUrl() // → "https://unified.fluxeo.net/api/unify/v1/truforex"
```

## Important Rules

### ✅ DO

- Always check if `activeBroker` exists before fetching
- Subscribe to `broker.switch` and `broker.refresh` events
- Use `getApiBaseUrl()` for all broker-specific API calls
- Show loading state when `isSyncing === true`
- Clean up event listeners in useEffect return
- Handle errors gracefully with try/catch

### ❌ DON'T

- Hardcode API base URLs
- Forget to unsubscribe from events
- Share settings between brokers (API keys, risk config)
- Assume activeBroker is always defined
- Make API calls when `activeBroker === null`

## Component Template

Copy this template for new broker-aware components:

```typescript
import { useEffect, useState } from 'react';
import { useBroker } from '../contexts/BrokerContext';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { RefreshCw } from 'lucide-react';
import { toast } from 'sonner@2.0.3';

export function YourNewComponent() {
  const { activeBroker, getApiBaseUrl, isSyncing } = useBroker();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!activeBroker) {
      setData(null);
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      try {
        const response = await fetch(`${getApiBaseUrl()}/your-endpoint`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('apiKey')}`
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch data');
        }

        const json = await response.json();
        setData(json);
      } catch (error) {
        console.error('Error fetching data:', error);
        toast.error('Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    // Subscribe to broker events
    const handleBrokerEvent = () => fetchData();
    window.addEventListener('broker.switch', handleBrokerEvent);
    window.addEventListener('broker.refresh', handleBrokerEvent);

    return () => {
      window.removeEventListener('broker.switch', handleBrokerEvent);
      window.removeEventListener('broker.refresh', handleBrokerEvent);
    };
  }, [activeBroker, getApiBaseUrl]);

  // Loading state
  if (loading || isSyncing) {
    return (
      <Card className="bg-[#001f29] border-gray-800">
        <CardContent className="p-6">
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-gray-700 rounded w-3/4"></div>
            <div className="h-4 bg-gray-700 rounded w-1/2"></div>
            <div className="h-4 bg-gray-700 rounded w-5/6"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // No broker selected
  if (!activeBroker) {
    return (
      <Card className="bg-[#001f29] border-gray-800">
        <CardContent className="p-6">
          <p className="text-gray-400 text-center">
            No broker connected. Please connect a broker to view data.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Main content
  return (
    <Card className="bg-[#001f29] border-gray-800">
      <CardHeader>
        <CardTitle className="text-white">Your Component Title</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Render your data here */}
          <pre className="text-gray-300 text-sm">
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      </CardContent>
    </Card>
  );
}
```

## Testing Your Component

### 1. Test with No Broker Connected

```typescript
// Should show "No broker connected" message
// Should not make any API calls
```

### 2. Test Broker Switching

```typescript
// 1. Connect to TradeLocker
// 2. Verify component loads TradeLocker data
// 3. Switch to TopStep
// 4. Verify component shows loading state
// 5. Verify component loads TopStep data
// 6. Switch to TruForex
// 7. Verify component shows loading state
// 8. Verify component loads TruForex data
```

### 3. Test Manual Refresh

```typescript
// 1. Load component with active broker
// 2. Click refresh button
// 3. Verify loading state appears
// 4. Verify fresh data loads
```

### 4. Test Error Handling

```typescript
// 1. Disconnect network
// 2. Try to load component
// 3. Verify error message shows
// 4. Verify retry mechanism works
```

## Debugging Tips

### Check Active Broker

```typescript
console.log('Active broker:', activeBroker);
console.log('API base URL:', getApiBaseUrl());
```

### Monitor Events

```typescript
window.addEventListener('broker.switch', (e) => {
  console.log('Broker switched:', e.detail);
});

window.addEventListener('broker.refresh', (e) => {
  console.log('Data refreshed:', e.detail);
});
```

### Verify Event Listeners

```typescript
useEffect(() => {
  const handler = () => console.log('Event fired!');
  window.addEventListener('broker.switch', handler);
  
  return () => {
    console.log('Cleaning up event listener');
    window.removeEventListener('broker.switch', handler);
  };
}, []);
```

## Common Issues & Solutions

### Issue: Component doesn't update when switching brokers

**Solution:** Make sure you're listening to `broker.switch` event

```typescript
window.addEventListener('broker.switch', fetchData);
```

### Issue: Multiple unnecessary API calls

**Solution:** Add activeBroker to dependency array

```typescript
useEffect(() => {
  fetchData();
}, [activeBroker]); // ← Important!
```

### Issue: Memory leaks

**Solution:** Always clean up event listeners

```typescript
return () => {
  window.removeEventListener('broker.switch', handler);
};
```

### Issue: Stale data showing

**Solution:** Also listen to `broker.refresh` event

```typescript
window.addEventListener('broker.refresh', fetchData);
```

## Need Help?

- 📖 Full Documentation: `/DYNAMIC_BROKER_WIRING_GUIDE.md`
- 🗺️ Wiring Map: `/BROKER_CONTEXT_WIRING_MAP.json`
- 📊 Implementation Summary: `/DYNAMIC_BROKER_IMPLEMENTATION_SUMMARY.md`
- 💬 Support: support@fluxeo.net

---

**Happy coding! 🚀**
