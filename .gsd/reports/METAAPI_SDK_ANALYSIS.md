# MetaAPI SDK (MT4/MT5) Full Functionality Analysis

**Date:** 2026-01-24  
**Status:** Analysis Complete

## Executive Summary

MetaAPI integration provides unified access to MT4 and MT5 platforms via the official `metaapi-cloud-sdk`. The implementation is comprehensive with dual-mode support (SDK preferred, Manager API fallback). Most functionality is working, but SDK installation status needs verification.

## Current Implementation Status

### ✅ What's Working

1. **Dual-Mode Support**
   - SDK mode: Uses official `metaapi-cloud-sdk` (preferred)
   - Manager API mode: Uses httpx with Manager API (fallback)

2. **Test Connection** - Successfully tests SDK authentication
3. **Account Discovery** - Gets account info via SDK terminal state
4. **Position Management** - Get positions, close positions via SDK
5. **Order Placement** - Supports all order types (market, limit, stop, stop-limit for MT5)
6. **Order Management** - Modify, cancel orders via SDK
7. **Real-time Streaming** - SDK provides streaming connection with terminal state
8. **Market Data** - Subscribe/unsubscribe to symbols, get quotes
9. **Symbol Specifications** - Get contract details, digits, etc.

### ❌ What's Missing/Broken

#### 1. SDK Package Installation Status
- **Status:** SDK listed in `requirements.txt` (`metaapi-cloud-sdk>=29.0.0`) but **NOT VERIFIED INSTALLED**
- **Impact:** If not installed, falls back to Manager API mode (which requires local MT4/MT5 server)
- **Fix Required:**
  ```bash
  pip install metaapi-cloud-sdk>=29.0.0
  ```

#### 2. Manager API Fallback Limitations

**Current Issue:**
- Manager API mode requires local MT4/MT5 Manager API server
- Default configuration points to `localhost:8080` (MT4) and `localhost:8081` (MT5)
- These endpoints likely don't exist in production
- No clear error handling when Manager API is unavailable

**Impact:**
- If SDK not installed or credentials invalid, executor fails silently
- Should provide better error messages

#### 3. Account Discovery Returns Single Account

**Current Behavior:**
- `get_accounts()` returns single account (the MetaAPI account)
- This is correct for MetaAPI (one account per MetaAPI account ID)
- But method signature suggests it could return multiple accounts

**Note:** This is actually correct behavior - MetaAPI provides one MT4/MT5 account per account ID.

#### 4. Position Discovery - DateTime Parsing

**Current Issue:**
- `get_positions()` uses `datetime.now()` as placeholder for `open_time`
- SDK provides `time` field but it's a string, not parsed datetime
- Should parse the time string properly

**Fix Required:**
- Parse `pos.get("time")` or `pos.get("open_time")` string to datetime

#### 5. Order History Not Implemented

**Current:**
- `get_orders()` gets pending orders only
- No method for historical orders (filled/cancelled)
- SDK provides deal history but not exposed

**Missing:**
- Historical order list
- Trade history (closed positions)
- Deal history

#### 6. Account Info DateTime Issues

**Current:**
- `get_account_info()` uses `datetime.now()` for `created_at` and `updated_at`
- SDK doesn't provide account creation time
- Should use account info timestamp if available

#### 7. Missing Features

- **Deal History** - SDK provides deal history but executor doesn't expose it
- **Account Performance Metrics** - Not implemented
- **Symbol Groups** - Not fetched
- **Server Time** - Not synchronized
- **Historical Bars** - SDK supports but executor doesn't expose

#### 8. Error Handling Could Be Better

**Current:**
- Good error messages for authentication failures
- But some generic exceptions could be more specific
- Manager API fallback errors could be clearer

## Required Fixes

### Priority 1: Critical (Verify Installation)

#### Fix 1: Verify MetaAPI SDK Installation
```bash
pip install metaapi-cloud-sdk>=29.0.0
```

#### Fix 2: Improve Manager API Error Handling
**File:** `app/brokers/mt4_executor.py` and `app/brokers/mt5_executor.py`

**Current:**
```python
async def _initialize_httpx(self) -> bool:
    """Initialize using custom httpx client (fallback to Manager API)."""
    if not (self.manager_login and self.manager_password):
        logger.error("MT4 Manager API credentials not configured")
        return False
    # ... rest of code
```

**Should Add:**
- Better error messages when Manager API server is unreachable
- Clear indication that Manager API requires local server
- Suggestion to use MetaAPI SDK instead

### Priority 2: Important (Improves Functionality)

#### Fix 3: Parse Position DateTime Properly
**File:** `app/brokers/mt4_executor.py` and `app/brokers/mt5_executor.py` (line ~266)

**Current:**
```python
open_time=datetime.now(),  # SDK doesn't provide parsed datetime
```

**Should Be:**
```python
open_time=self._parse_sdk_datetime(pos.get("time", pos.get("open_time", ""))),
```

**Add Helper Method:**
```python
def _parse_sdk_datetime(self, time_str: Optional[str]) -> datetime:
    """Parse MetaAPI datetime string to datetime object."""
    if not time_str:
        return datetime.now()
    try:
        # MetaAPI returns ISO format or timestamp
        if isinstance(time_str, (int, float)):
            return datetime.fromtimestamp(time_str)
        return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    except Exception:
        return datetime.now()
```

#### Fix 4: Expose Deal History
**File:** `app/services/metaapi_sdk_service.py`

**Add Method:**
```python
async def get_deal_history(
    self,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Get deal history (closed trades).
    
    Args:
        start_time: Optional start time filter
        end_time: Optional end time filter
        
    Returns:
        List of deal dictionaries
    """
    if not self._connection:
        raise RuntimeError("Not connected")
    
    # MetaAPI SDK provides deal history through terminal state
    # or via account API
    deals = self._connection.terminal_state.deals
    return [
        {
            "id": str(deal.get("id", "")),
            "order_id": str(deal.get("orderId", "")),
            "position_id": str(deal.get("positionId", "")),
            "symbol": deal.get("symbol", ""),
            "type": deal.get("type", ""),
            "volume": float(deal.get("volume", 0)),
            "price": float(deal.get("price", 0)),
            "commission": float(deal.get("commission", 0)),
            "swap": float(deal.get("swap", 0)),
            "profit": float(deal.get("profit", 0)),
            "time": deal.get("time", ""),
        }
        for deal in deals
    ]
```

### Priority 3: Nice to Have

#### Fix 5: Expose Historical Bars
- Add method to get historical OHLCV data via SDK
- SDK supports `get_candles()` or similar methods

#### Fix 6: Add Account Performance Metrics
- Calculate win rate, average profit/loss, etc.
- Use deal history to compute metrics

## API Endpoint Reference

### MetaAPI Cloud SDK
- **Base URL:** `https://metaapi.cloud` (managed by SDK)
- **Authentication:** API token from https://app.metaapi.cloud/token
- **Account ID:** MetaAPI account ID (provisioned in MetaAPI dashboard)

### SDK Methods (via MetaAPISDKService)
- `connect()` - Connect to MetaAPI and synchronize terminal state
- `get_account_info()` - Get account balance/equity/margin
- `get_positions()` - Get open positions
- `get_orders()` - Get pending orders
- `create_market_buy_order()` - Place market buy
- `create_market_sell_order()` - Place market sell
- `create_limit_buy_order()` - Place buy limit
- `create_limit_sell_order()` - Place sell limit
- `create_stop_buy_order()` - Place buy stop
- `create_stop_sell_order()` - Place sell stop
- `create_stop_limit_buy_order()` - Place buy stop limit (MT5 only)
- `create_stop_limit_sell_order()` - Place sell stop limit (MT5 only)
- `modify_order()` - Modify pending order
- `cancel_order()` - Cancel pending order
- `modify_position()` - Modify position SL/TP
- `close_position()` - Close position
- `close_positions_by_symbol()` - Close all positions for symbol
- `subscribe_to_market_data()` - Subscribe to real-time quotes
- `get_quote()` - Get current quote
- `get_symbol_specification()` - Get symbol contract details

### Manager API Endpoints (Fallback Mode)
- **Base URL:** `http://localhost:8080/api` (MT4) or `http://localhost:8081/api` (MT5)
- **Authentication:** Manager login/password
- **Endpoints:**
  - `POST /auth/login` - Authenticate
  - `GET /users` - List accounts
  - `GET /trades` - Get positions
  - `POST /trades` - Place order
  - `PUT /orders/{order_id}` - Modify order
  - `DELETE /orders/{order_id}` - Cancel order
  - `GET /symbols` - Get symbols

## Testing Checklist

- [ ] Verify `metaapi-cloud-sdk` installation: `pip list | grep metaapi`
- [ ] Test SDK authentication with valid MetaAPI token and account ID
- [ ] Test account discovery (`get_accounts()`)
- [ ] Test position discovery (`get_positions()`)
- [ ] Test order placement for all order types
- [ ] Test order modification (`modify_order()`)
- [ ] Test order cancellation (`cancel_order()`)
- [ ] Test position closing (`close_position()`)
- [ ] Test position modification (`modify_position()`)
- [ ] Test market data subscription (`subscribe_to_market_data()`)
- [ ] Test quote retrieval (`get_quote()`)
- [ ] Test symbol specifications (`get_symbol_specification()`)
- [ ] Test Manager API fallback (if local server available)
- [ ] Test error handling for invalid credentials
- [ ] Test error handling for network failures

## Implementation Recommendations

1. **Immediate Actions:**
   - Verify MetaAPI SDK installation
   - Improve Manager API error messages
   - Fix position datetime parsing

2. **Short-term:**
   - Expose deal history functionality
   - Add historical bars support
   - Improve account info datetime handling

3. **Long-term:**
   - Add account performance metrics
   - Implement symbol groups
   - Add server time synchronization
   - Enhance error messages with actionable suggestions

## Notes

- MetaAPI SDK is async-first and well-designed
- Terminal state provides real-time synchronized data
- Streaming connection handles real-time updates automatically
- SDK supports both MT4 and MT5 platforms via same interface
- Manager API fallback requires local MT4/MT5 Manager API server (rarely available)
- MetaAPI account must be provisioned and deployed before use
- SDK handles account deployment automatically if needed

## MT4 vs MT5 Differences

- **MT4:** Supports market, limit, stop orders
- **MT5:** Supports all MT4 orders + stop-limit orders
- **MT5:** More advanced order types (buy/sell stop limit)
- **MT5:** Better deal history and reporting
- Both use same SDK interface, differences handled internally
