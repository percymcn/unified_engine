# ProjectX/TopStep SDK Full Functionality Analysis

**Date:** 2026-01-24  
**Status:** Analysis Complete

## Executive Summary

After examining the full ProjectX/TopStep SDK implementation, several gaps and requirements have been identified to ensure full functionality works correctly.

## Current Implementation Status

### ✅ What's Working
1. **Authentication** - Fixed endpoint path (`/api/Auth/loginKey`)
2. **Test Connection** - Successfully authenticates with TopStepX API
3. **Account Creation** - Creates accounts with encrypted credentials
4. **Dual-Mode Support** - SDK mode (preferred) + httpx fallback

### ❌ What's Missing/Broken

#### 1. SDK Package Not Installed
- **Issue:** `project-x-py` SDK is listed in `requirements.txt` but not installed
- **Impact:** SDK mode cannot be used, always falls back to httpx
- **Fix Required:**
  ```bash
  pip install project-x-py>=3.5.0
  ```

#### 2. Account Discovery Failing
- **Current Error:** "Failed to initialize broker connection"
- **Root Cause:** 
  - httpx mode: API endpoint paths may be incorrect
  - SDK mode: Not available (SDK not installed)
- **API Endpoints Being Used:**
  - `/Account/search` (should be `/api/Account/search` based on base URL structure)
  - `/Contract/Search` (should be `/api/Contract/Search`)
  - `/Position/searchOpen` (should be `/api/Position/searchOpen`)
  - `/Order/searchOpen` (should be `/api/Order/searchOpen`)

#### 3. API Endpoint Path Issues
- **Problem:** Base URL is `https://api.topstepx.com` but endpoints use `/Account/search` instead of `/api/Account/search`
- **Current Code:** Uses relative paths like `/Account/search` 
- **Expected:** Should use `/api/Account/search` OR base_url should be `https://api.topstepx.com/api`
- **Files Affected:**
  - `app/brokers/projectx_executor.py` - Lines 212, 281, 362, 398, 467, 522, 553

#### 4. WebSocket Support Missing
- **Current:** No WebSocket implementation for real-time updates
- **TopStepX API Provides:**
  - Real-time market data streaming
  - Account balance updates
  - Position change notifications
  - Order fill notifications
- **WebSocket URLs:**
  - User Hub: `wss://rtc.topstepx.com/hubs/user`
  - Market Hub: `wss://rtc.topstepx.com/hubs/market`

#### 5. Account Discovery Returns Empty List
- **Issue:** `get_accounts()` returns empty list even after successful authentication
- **Possible Causes:**
  - Wrong API endpoint path
  - Missing account_id parameter
  - API response format mismatch
  - Authentication token not being passed correctly

#### 6. Missing Features
- **Order History** - No endpoint for historical orders
- **Trade History** - No endpoint for closed trades
- **Account Performance Metrics** - Not implemented
- **Risk Limits** - Not fetched from API
- **Real-time Quotes** - `get_quote()` returns None/empty
- **Market Data** - Historical bars not implemented in httpx mode

## Required Fixes

### Priority 1: Critical (Blocks Account Discovery)

#### Fix 1: Correct API Endpoint Paths
**File:** `app/brokers/projectx_executor.py`

**Current:**
```python
base_url = "https://api.topstepx.com"
response = await self._session.post("/Account/search", json={})
```

**Should Be:**
```python
base_url = "https://api.topstepx.com"  # Keep as is
response = await self._session.post("/api/Account/search", json={})  # Add /api prefix
```

**OR:**
```python
base_url = "https://api.topstepx.com/api"  # Add /api to base
response = await self._session.post("/Account/search", json={})  # Keep relative
```

**Endpoints to Fix:**
- `/Account/search` → `/api/Account/search`
- `/Contract/Search` → `/api/Contract/Search`  
- `/Position/searchOpen` → `/api/Position/searchOpen`
- `/Order/searchOpen` → `/api/Order/searchOpen`
- `/Order/place` → `/api/Order/place`
- `/Order/modify` → `/api/Order/modify`
- `/Order/cancel` → `/api/Order/cancel`
- `/Position/closeContract` → `/api/Position/closeContract`

#### Fix 2: Install SDK Package
```bash
pip install project-x-py>=3.5.0
```

### Priority 2: Important (Enables Full Functionality)

#### Fix 3: Implement Account Discovery Properly
- Add account_id parameter handling
- Parse API response correctly
- Handle multiple accounts
- Map account fields correctly (id, account_number, name, etc.)

#### Fix 4: Add WebSocket Support
- Implement WebSocket connection to `wss://rtc.topstepx.com/hubs/user`
- Subscribe to account updates
- Subscribe to position changes
- Subscribe to order fills
- Handle reconnection logic

#### Fix 5: Implement Missing Endpoints
- Order history: `/api/Order/search` with date filters
- Trade history: `/api/Trade/search` or similar
- Account performance: `/api/Account/{id}/performance`
- Risk limits: `/api/Account/{id}/riskLimits`
- Real-time quotes: WebSocket or `/api/MarketData/quote/{symbol}`

### Priority 3: Nice to Have (Enhancements)

#### Fix 6: Improve Error Handling
- Better error messages for authentication failures
- Handle rate limiting (429 responses)
- Handle token expiration and refresh
- Network error recovery

#### Fix 7: Add Market Data Support
- Historical bars/candles
- Real-time quotes via WebSocket
- Symbol search with contract details

## API Endpoint Reference

Based on TopStepX API documentation and current implementation:

### Authentication
- `POST /api/Auth/loginKey` ✅ Fixed
  - Body: `{"userName": "username", "apiKey": "api_key"}`
  - Returns: JWT token (24h expiry)

### Accounts
- `POST /api/Account/search` ❌ Path needs fixing
  - Body: `{}` or `{"accountId": "..."}`
  - Returns: List of accounts

### Contracts/Instruments
- `POST /api/Contract/Search` ❌ Path needs fixing
  - Body: `{"symbol": "MNQ"}` or `{}`
  - Returns: List of contracts

### Positions
- `POST /api/Position/searchOpen` ❌ Path needs fixing
  - Body: `{}` or `{"accountId": "...", "symbol": "..."}`
  - Returns: List of open positions

### Orders
- `POST /api/Order/place` ❌ Path needs fixing
  - Body: `{"accountId": "...", "contractId": "...", "side": "buy|sell", "type": "market|limit", "size": 1, "price": 21050.0, "stopLoss": 21000.0, "takeProfit": 21100.0}`
- `POST /api/Order/modify` ❌ Path needs fixing
  - Body: `{"orderId": "...", "price": 21051.0, "stopLoss": 21001.0, "takeProfit": 21101.0}`
- `POST /api/Order/cancel` ❌ Path needs fixing
  - Body: `{"orderId": "..."}`
- `POST /api/Order/searchOpen` ❌ Path needs fixing
  - Body: `{}` or `{"accountId": "..."}`
  - Returns: List of open orders

### Position Management
- `POST /api/Position/closeContract` ❌ Path needs fixing
  - Body: `{"accountId": "...", "contractId": "...", "size": 1}` (size optional for full close)

## Testing Checklist

- [ ] Install `project-x-py` SDK
- [ ] Fix all API endpoint paths
- [ ] Test account discovery with real credentials
- [ ] Test account creation
- [ ] Test position fetching
- [ ] Test order placement
- [ ] Test order modification
- [ ] Test order cancellation
- [ ] Test position closing
- [ ] Test WebSocket connection (if implemented)
- [ ] Test error handling with invalid credentials
- [ ] Test token expiration handling

## Recommended Implementation Order

1. **Fix API endpoint paths** (Priority 1) - Quick fix, high impact
2. **Install SDK** (Priority 1) - Enables SDK mode
3. **Fix account discovery** (Priority 2) - Critical for UX
4. **Add WebSocket support** (Priority 2) - Real-time updates
5. **Add missing endpoints** (Priority 2) - Complete functionality
6. **Improve error handling** (Priority 3) - Better UX
7. **Add market data** (Priority 3) - Enhanced features

## Files to Modify

1. `app/brokers/projectx_executor.py` - Fix API paths, improve discovery
2. `app/services/projectx_sdk_service.py` - Enhance SDK wrapper (if SDK installed)
3. `requirements.txt` - Ensure SDK is listed (already there)
4. `app/core/config.py` - Verify WebSocket URLs are configured

## Next Steps

1. Fix API endpoint paths immediately
2. Install SDK: `pip install project-x-py>=3.5.0`
3. Test account discovery with real credentials
4. Implement WebSocket support for real-time updates
5. Add comprehensive error handling
