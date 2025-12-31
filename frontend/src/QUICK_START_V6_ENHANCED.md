# 🚀 TradeFlow v6 - Quick Start Guide

## ⚡ Get Started in 5 Minutes

### 1. Import the Enhanced API Client

```typescript
import { enhancedApiClient } from './utils/api-client-enhanced';

// Set auth token (from login)
enhancedApiClient.setToken(accessToken);

// Start making requests
const overview = await enhancedApiClient.getOverview();
const positions = await enhancedApiClient.getPositions();
```

---

### 2. Add Billing Protection

```tsx
import { BillingGuard } from './components/BillingGuard';

// Wrap trading components
<BillingGuard blockInteraction={true} showBanner={true}>
  <PositionsMonitor />
</BillingGuard>
```

**What it does**: Blocks trading when `status ∈ (past_due, canceled, incomplete)`

---

### 3. Show Trial Status

```tsx
import { TrialBanner } from './components/TrialBanner';

// Add to dashboard
{activeSection === 'overview' && <TrialBanner />}
```

**What it shows**: Remaining trades (of 100) and days (of 3)

---

### 4. Add Emergency Stop

```tsx
import { EmergencyStopButton } from './components/EmergencyStopDialog';

// Add to risk controls
<EmergencyStopButton />
```

**What it does**: Closes all positions + publishes NATS event

---

## 📡 API Quick Reference

### Overview & Positions
```typescript
// Dashboard KPIs
const data = await enhancedApiClient.getOverview();

// Open positions
const positions = await enhancedApiClient.getPositions();

// Close position
const result = await enhancedApiClient.closePosition('pos_123');
```

### Orders
```typescript
// Get orders with filters
const orders = await enhancedApiClient.getOrders({
  limit: 50,
  status: 'FILLED',
  symbol: 'ES'
});

// Delete order
await enhancedApiClient.deleteOrder('ord_456');
```

### Analytics
```typescript
// P&L Report
const report = await enhancedApiClient.getPnLReport(
  '2025-10-01',
  '2025-10-19'
);

// Metrics
const metrics = await enhancedApiClient.getAnalyticsMetrics({
  start_date: '2025-10-01',
  end_date: '2025-10-19',
  broker: 'tradelocker'
});

// Trade history
const trades = await enhancedApiClient.getAnalyticsTrades(
  '2025-10-01',
  '2025-10-19'
);
```

### Broker Management
```typescript
// List brokers
const brokers = await enhancedApiClient.getUserBrokers();

// Connect new broker
const account = await enhancedApiClient.registerBroker('tradelocker', {
  email: 'trader@example.com',
  password: 'SecurePass123!',
  mode: 'live'
});

// Switch account
await enhancedApiClient.switchAccount('acc_123');

// Sync results
const results = await enhancedApiClient.getSyncResults();

// Manual sync
await enhancedApiClient.syncAccount('acc_123');
```

### Configuration
```typescript
// Get config
const config = await enhancedApiClient.getUserConfig();

// Update config
await enhancedApiClient.updateUserConfig({
  stop_loss_pct: 2.0,
  take_profit_pct: 4.5,
  position_size: 2
});

// Risk config
const riskConfig = await enhancedApiClient.getRiskConfig();

// Update risk config
await enhancedApiClient.updateRiskConfig({
  max_risk_per_trade: 1.0,
  max_drawdown: 5.0
});

// Emergency stop
const result = await enhancedApiClient.emergencyStop();
```

### API Keys
```typescript
// List keys
const keys = await enhancedApiClient.getApiKeys();

// Generate new key
const newKey = await enhancedApiClient.generateApiKey({
  name: 'My Trading Bot',
  permissions: ['webhook.receive', 'orders.create']
});

// ⚠️ Save newKey.secret immediately (only shown once!)

// Delete key
await enhancedApiClient.deleteApiKey('key_123');
```

### Billing
```typescript
// Billing status
const status = await enhancedApiClient.getBillingStatus();

// Usage metrics
const usage = await enhancedApiClient.getBillingUsage();

// Create checkout
const checkout = await enhancedApiClient.createCheckout({
  price_id: 'price_1ProMonthly',
  success_url: window.location.href,
  cancel_url: window.location.href
});
window.location.href = checkout.url;

// Cancel subscription
await enhancedApiClient.cancelSubscription();
```

### Logs
```typescript
// Webhook logs
const logs = await enhancedApiClient.getWebhookLogs({
  limit: 100,
  offset: 0
});
```

### Auth
```typescript
// Password reset
await enhancedApiClient.resetPassword('user@example.com');
```

---

## 🎨 UI Components Cheat Sheet

### Import Components
```tsx
// Pages
import { Dashboard } from './components/Dashboard';
import { PositionsMonitor } from './components/PositionsMonitor';
import { OrdersManager } from './components/OrdersManager';
import { AnalyticsPage } from './components/AnalyticsPage';
import { AccountsManager } from './components/AccountsManager';
import { ApiKeyManager } from './components/ApiKeyManager';
import { BillingPortal } from './components/BillingPortal';
import { LogsViewer } from './components/LogsViewer';

// Functional Components
import { ChangeAccountPage } from './components/ChangeAccountPage';
import { SyncResultsPage } from './components/SyncResultsPage';
import { AccountSelectionPage } from './components/AccountSelectionPage';
import { PasswordResetPage } from './components/PasswordResetPage';

// Guards & Widgets
import { BillingGuard } from './components/BillingGuard';
import { TrialBanner } from './components/TrialBanner';
import { EmergencyStopDialog } from './components/EmergencyStopDialog';
```

### Use Toasts
```tsx
import { toast } from 'sonner@2.0.3';

// Success
toast.success('Position closed successfully!');

// Error
toast.error('Failed to connect broker');

// Info
toast.info('Syncing positions...');

// Warning
toast.warning('Low trade count remaining');
```

---

## 🛡️ Guards Implementation

### 1. Billing Guard Pattern
```tsx
// pages/Positions.tsx
import { BillingGuard } from '../components/BillingGuard';

export function PositionsPage() {
  return (
    <BillingGuard blockInteraction={true} showBanner={true}>
      <PositionsMonitor broker="tradelocker" />
    </BillingGuard>
  );
}
```

### 2. Trial Banner Pattern
```tsx
// components/Dashboard.tsx
import { TrialBanner } from './TrialBanner';

export function Dashboard() {
  return (
    <div>
      <TrialBanner />
      {/* Rest of dashboard */}
    </div>
  );
}
```

### 3. Check Billing Status Programmatically
```tsx
import { useBillingStatus } from './components/BillingGuard';

export function MyComponent() {
  const { status, isBlocked, isActive, isTrialing } = useBillingStatus();
  
  if (isBlocked) {
    return <div>Please update payment</div>;
  }
  
  return <div>Trading enabled</div>;
}
```

---

## 🔥 Common Patterns

### Error Handling
```tsx
try {
  const positions = await enhancedApiClient.getPositions();
  toast.success('Positions loaded');
} catch (error) {
  console.error('Failed to load positions:', error);
  toast.error(`Error: ${error.message}`);
}
```

### Loading States
```tsx
const [loading, setLoading] = useState(false);

const handleSync = async () => {
  setLoading(true);
  try {
    await enhancedApiClient.syncAccount('acc_123');
    toast.success('Sync complete');
  } catch (error) {
    toast.error('Sync failed');
  } finally {
    setLoading(false);
  }
};

return (
  <Button disabled={loading}>
    {loading ? 'Syncing...' : 'Sync Now'}
  </Button>
);
```

### Confirmation Dialogs
```tsx
const handleDelete = async () => {
  if (!window.confirm('Are you sure?')) return;
  
  await enhancedApiClient.deleteOrder('ord_123');
  toast.success('Order deleted');
};
```

---

## 📱 Responsive Patterns

### Mobile Menu
```tsx
import { Sheet, SheetTrigger, SheetContent } from './components/ui/sheet';
import { Menu } from 'lucide-react';

<Sheet>
  <SheetTrigger asChild>
    <Button variant="ghost" className="md:hidden">
      <Menu className="w-5 h-5" />
    </Button>
  </SheetTrigger>
  <SheetContent side="left">
    {/* Navigation items */}
  </SheetContent>
</Sheet>
```

### Touch-Friendly Buttons
```tsx
// Minimum 44px height for mobile
<Button className="min-h-[44px] touch-manipulation">
  Trade Now
</Button>
```

---

## 🎯 Key Files Reference

| Purpose | File Path |
|---------|-----------|
| **API Client** | `/utils/api-client-enhanced.ts` |
| **Wiring Manifest** | `/WIRING_MANIFEST_V6.json` |
| **API Examples** | `/API_SAMPLE_PAYLOADS_V6.md` |
| **Implementation Guide** | `/COMPLETE_V6_IMPLEMENTATION_GUIDE.md` |
| **Main Router** | `/App.tsx` |
| **Styles** | `/styles/globals.css` |
| **User Context** | `/contexts/UserContext.tsx` |

---

## 🔍 Debugging Tips

### Enable API Logging
```typescript
// In api-client-enhanced.ts, requests are already logged
// Check browser console for:
// - Request URLs
// - Response data
// - Error messages
```

### Mock Backend
```typescript
// In api-client-enhanced.ts
const USE_MOCK = true; // Toggle this for local dev
```

### Check Billing Status
```typescript
const status = await enhancedApiClient.getBillingStatus();
console.log('Billing status:', status);
// Look for: active, trialing, past_due, canceled
```

### Test Emergency Stop
```typescript
// CAUTION: This closes ALL positions!
const result = await enhancedApiClient.emergencyStop();
console.log('Positions closed:', result.positions_closed);
```

---

## 📊 Environment Variables

```bash
# .env.local
VITE_API_BASE_URL=https://unified.fluxeo.net/api/unify/v1
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_STRIPE_PUBLIC_KEY=pk_live_...
```

---

## 🎁 Pro Tips

### 1. Batch API Calls
```typescript
// Use Promise.all for parallel requests
const [overview, positions, orders] = await Promise.all([
  enhancedApiClient.getOverview(),
  enhancedApiClient.getPositions(),
  enhancedApiClient.getOrders({ limit: 10 })
]);
```

### 2. Cache Awareness
```typescript
// Positions update every 5s
// No need to refresh more frequently
useEffect(() => {
  const interval = setInterval(loadPositions, 5000);
  return () => clearInterval(interval);
}, []);
```

### 3. NATS Publishing
```typescript
// After closing position, publish event
const result = await enhancedApiClient.closePosition('pos_123');

// Frontend should log this (backend handles actual NATS)
console.log('NATS publish: ai.trade.exec.order', {
  op: 'close',
  position_id: 'pos_123',
  user_id: currentUserId,
  timestamp: new Date().toISOString()
});
```

### 4. Error Recovery
```typescript
// Retry pattern for transient errors
const retryRequest = async (fn, retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === retries - 1) throw error;
      await new Promise(r => setTimeout(r, 1000 * (i + 1)));
    }
  }
};

const positions = await retryRequest(() => 
  enhancedApiClient.getPositions()
);
```

---

## ✅ Quick Validation Checklist

Before going live:
- [ ] All 27 endpoints return 200
- [ ] Billing guard blocks when past_due
- [ ] Trial banner shows correct counts
- [ ] Emergency stop closes positions
- [ ] Toast notifications appear
- [ ] Loading states work
- [ ] Mobile menu opens
- [ ] Forms validate
- [ ] Errors show helpful messages
- [ ] Dark theme applies

---

## 📞 Need Help?

1. **Check Documentation**:
   - `/COMPLETE_V6_IMPLEMENTATION_GUIDE.md`
   - `/API_SAMPLE_PAYLOADS_V6.md`
   - `/WIRING_MANIFEST_V6.json`

2. **Inspect Components**:
   - All components have inline comments
   - TypeScript types document parameters
   - Props are clearly defined

3. **Contact Support**:
   - Email: support@fluxeo.net
   - Include: Error message, browser console logs, request payload

---

## 🚀 Ready to Build!

You now have everything needed to:
- ✅ Build new features on TradeFlow
- ✅ Integrate with backend APIs
- ✅ Add new components
- ✅ Test locally with mocks
- ✅ Deploy to production

**Start coding and happy trading!** 📈

---

**Version**: 1.0  
**Last Updated**: 2025-10-19  
**Status**: Production Ready ✅
