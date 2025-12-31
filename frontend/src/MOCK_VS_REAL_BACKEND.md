# 🔄 Mock vs Real Backend Toggle Guide

## Quick Fix for API Errors

If you see errors like:
```
API Error [/api/billing/status]: TypeError: Failed to fetch
Failed to load billing status: TypeError: Failed to fetch
```

**Solution**: The app is trying to connect to the real backend which isn't available yet. Use mock mode instead.

---

## How to Toggle Between Mock and Real Backend

### Option 1: Use Mock Backend (Default - Recommended for Development)

**File**: `/utils/api-client-enhanced.ts`

**Line 7-9**:
```typescript
// Toggle between real backend and mock for development
// Set to true for local development until backend is ready
const USE_MOCK = true;  // ✅ Use this for local dev
```

**What this does**:
- All API calls return mock data
- No network requests made
- Fast response times (200-800ms simulated)
- No CORS issues
- Works offline

---

### Option 2: Use Real Backend (Production)

**File**: `/utils/api-client-enhanced.ts`

**Line 7-9**:
```typescript
// Toggle between real backend and mock for development
// Set to false when backend is ready
const USE_MOCK = false;  // ⚠️ Only use when backend is live
```

**Requirements**:
- Backend must be running at `https://unified.fluxeo.net/api/unify/v1`
- All 27 endpoints must be implemented
- CORS must be configured to allow your frontend domain
- Valid auth tokens required

---

## Current Mock Data

The mock backend provides realistic data for:

### ✅ Implemented Mock Endpoints (3/27)

1. **GET /api/overview**
   ```typescript
   {
     total_pnl: 12450.75,
     total_pnl_pct: 24.9,
     today_pnl: 385.50,
     today_trades: 12,
     win_rate: 68.5,
     // ... more KPIs
   }
   ```

2. **GET /api/billing/status**
   ```typescript
   {
     status: 'trialing',
     plan: 'pro',
     trial_end: '2025-10-21T...',
     // ...
   }
   ```

3. **GET /api/billing/usage**
   ```typescript
   {
     trades_count: 65,
     trades_limit: 100,
     trial_trades_remaining: 35,
     days_remaining: 2,
     // ...
   }
   ```

4. **POST /api/user/emergency_stop**
   ```typescript
   {
     success: true,
     positions_closed: 3
   }
   ```

### ⚠️ Not Yet Implemented (Need Mocks)

The following endpoints will still try to hit the real backend:
- GET /api/positions
- GET /api/orders
- POST /api/orders/close
- GET /api/user/brokers
- ... (20+ more endpoints)

**To add mocks for these**, edit `/utils/api-client-enhanced.ts` and add:

```typescript
async getPositions(): Promise<Position[]> {
  if (USE_MOCK) {
    await this.delay(200);
    return [
      // Your mock positions data
    ];
  }
  return this.request<Position[]>('/api/positions');
}
```

---

## Error Handling

Both `BillingGuard.tsx` and `TrialBanner.tsx` now handle API errors gracefully:

```typescript
try {
  const status = await enhancedApiClient.getBillingStatus();
  setBillingStatus(status);
} catch (error) {
  console.error('Failed to load billing status:', error);
  // Don't block on error - assume status is OK
  setBillingStatus(null);
}
```

**What this means**:
- If API fails, app continues to work
- No white screen of death
- Errors logged to console for debugging
- User sees app without billing features

---

## Testing Different Scenarios

### Test Scenario 1: Active Subscription (No Banners)
```typescript
// In api-client-enhanced.ts, modify getBillingStatus():
return {
  status: 'active',  // Change this
  plan: 'pro',
  // ...
};
```

**Expected**: No trial banner, no billing warning

---

### Test Scenario 2: Trial User (Show Banner)
```typescript
return {
  status: 'trialing',  // Change this
  plan: 'pro',
  trial_end: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
};
```

**Expected**: Trial banner visible with progress bars

---

### Test Scenario 3: Payment Failed (Block Trading)
```typescript
return {
  status: 'past_due',  // Change this
  plan: 'pro',
  // ...
};
```

**Expected**: Red warning banner, trading blocked with overlay

---

### Test Scenario 4: Subscription Canceled (Block Trading)
```typescript
return {
  status: 'canceled',  // Change this
  plan: 'pro',
  // ...
};
```

**Expected**: Warning banner with "Reactivate" button

---

## Debugging Tips

### Check Current Mode
```bash
# In browser console:
# The app will log which mode it's using on API calls
```

### Force Reload Mock Data
```bash
# Hard refresh
Ctrl + Shift + R  (Windows/Linux)
Cmd + Shift + R   (Mac)
```

### View Network Requests
```bash
# Open DevTools → Network tab
# If USE_MOCK = true: No XHR requests to fluxeo.net
# If USE_MOCK = false: Will see API calls (and errors if backend down)
```

---

## When to Use Each Mode

### Use Mock Mode When:
- ✅ Developing locally
- ✅ Backend not ready
- ✅ Testing UI without backend team
- ✅ Working offline
- ✅ Rapid prototyping

### Use Real Mode When:
- ✅ Backend is deployed and ready
- ✅ End-to-end testing
- ✅ Staging/production environment
- ✅ Integration testing with real data
- ✅ Load testing

---

## Quick Checklist Before Switching to Real Backend

- [ ] Backend deployed at `https://unified.fluxeo.net/api/unify/v1`
- [ ] All 27 endpoints return 200 OK
- [ ] CORS configured for your domain
- [ ] Auth tokens working
- [ ] Response schemas match TypeScript types
- [ ] Rate limiting configured
- [ ] Error responses match expected format
- [ ] HTTPS certificate valid
- [ ] Database migrations complete
- [ ] Redis cache working

---

## Common Issues & Solutions

### Issue 1: CORS Error
```
Access to fetch at 'https://unified.fluxeo.net/...' has been blocked by CORS
```

**Solution**: Backend must add CORS headers:
```python
# FastAPI example
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### Issue 2: 401 Unauthorized
```
API Error: HTTP 401
```

**Solution**: Check token is being sent:
```typescript
enhancedApiClient.setToken(accessToken);
```

---

### Issue 3: Network Timeout
```
TypeError: Failed to fetch
```

**Solution**: 
1. Check backend is running
2. Check URL is correct
3. Use mock mode: `USE_MOCK = true`

---

## Environment-Based Toggle (Advanced)

For automatic switching based on environment:

```typescript
// In api-client-enhanced.ts
const USE_MOCK = import.meta.env.MODE === 'development' 
  ? true   // Mock in dev
  : false; // Real in prod
```

Then:
```bash
# Development (uses mocks)
npm run dev

# Production (uses real API)
npm run build
```

---

## Summary

**Current Status**: ✅ Mock mode enabled by default
- App works without backend
- No API errors
- Realistic data for testing UI
- Easy to toggle when backend is ready

**To switch to real backend**: Change `USE_MOCK = false` in `/utils/api-client-enhanced.ts`

---

**Last Updated**: 2025-10-19  
**Status**: Mock mode active - ready for local development ✅
