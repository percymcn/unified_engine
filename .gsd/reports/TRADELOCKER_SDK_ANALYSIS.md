# TradeLocker SDK Full Functionality Analysis

**Date:** 2026-01-24  
**Status:** Analysis Complete

## Executive Summary

TradeLocker integration supports dual-mode operation: official SDK (preferred) and Brand API fallback. The implementation is comprehensive but has some gaps in account discovery and WebSocket real-time updates.

## Current Implementation Status

### ✅ What's Working

1. **Dual-Mode Authentication**
   - SDK mode: Uses official `tradelocker` package with user credentials
   - Brand API mode: Uses httpx with Brand API key (fallback/required for some brokers)

2. **Test Connection** - Successfully tests both SDK and Brand API modes
3. **Account Creation** - Creates accounts with encrypted credentials
4. **Order Placement** - Supports market, limit, and stop orders via SDK
5. **Position Management** - Close positions via SDK
6. **Symbol Discovery** - Gets instruments via SDK or Brand API
7. **WebSocket Infrastructure** - WebSocket client initialized (but not fully utilized)

### ❌ What's Missing/Broken

#### 1. SDK Package Installation Status
- **Status:** SDK listed in `requirements.txt` (`tradelocker>=0.56.0`) but **NOT INSTALLED**
- **Impact:** SDK mode cannot be used, always falls back to Brand API
- **Fix Required:**
  ```bash
  pip install tradelocker>=0.56.0
  ```

#### 2. Account Discovery Issues

**SDK Mode:**
- `get_accounts()` method in executor uses Brand API (`self.session.get("/accounts")`) even when SDK is initialized
- SDK wrapper has `get_account_state()` but executor doesn't use it for account discovery
- Account discovery should use SDK's account state instead of Brand API

**Brand API Mode:**
- Works correctly via `/accounts` endpoint
- Returns account list properly

**Fix Required:**
- Update `get_accounts()` in `tradelocker_executor.py` to use SDK wrapper when `_use_sdk` is True
- Use `get_account_state()` from SDK wrapper to construct Account objects

#### 3. Position Discovery Not Using SDK

**Current Issue:**
- `get_positions()` always uses Brand API (`self.session.get("/positions")`)
- SDK wrapper has `get_positions()` method but executor doesn't use it

**Fix Required:**
- Update `get_positions()` to call `self._sdk_wrapper.get_positions()` when SDK mode is active

#### 4. Order Management Gaps

**Missing Methods:**
- `modify_order()` - Uses Brand API only, SDK wrapper has `modify_order()` but not called
- `cancel_order()` - Uses Brand API only, SDK wrapper has `cancel_order()` but not called
- `get_orders()` - Returns empty list, SDK wrapper has `get_orders()` but not used

**Fix Required:**
- Update all order management methods to use SDK wrapper when available

#### 5. WebSocket Real-Time Updates Not Fully Implemented

**Current Status:**
- WebSocket connection initialized (`socketio.AsyncClient`)
- Event handlers defined (`_on_stream`, `_on_subscriptions`, etc.)
- **BUT:** WebSocket is not actively used for real-time position/order updates
- SDK doesn't expose WebSocket API, so Brand API WebSocket is used separately

**Missing:**
- Real-time position updates via WebSocket
- Real-time order fill notifications
- Real-time account balance updates
- Market data streaming

#### 6. Account Info Method Issues

**Current:**
- `get_account_info()` uses Brand API only
- Should use SDK's `get_account_state()` when SDK mode is active

#### 7. Symbol Lookup Helper Missing

**Current:**
- `get_instrument_id_by_symbol()` exists in SDK wrapper
- Executor's `get_symbols()` uses SDK wrapper correctly
- But `place_order()` needs instrument ID lookup which is implemented correctly

#### 8. Missing Features

- **Order History** - No endpoint for historical orders
- **Trade History** - No endpoint for closed trades
- **Account Performance Metrics** - Not implemented
- **Price History** - SDK wrapper has `get_price_history()` but executor doesn't expose it
- **Real-time Quotes** - `get_quote()` returns None, should use SDK's `get_latest_asking_price()`

## Required Fixes

### Priority 1: Critical (Blocks SDK Mode Usage)

#### Fix 1: Install TradeLocker SDK
```bash
pip install tradelocker>=0.56.0
```

#### Fix 2: Update `get_accounts()` to Use SDK
**File:** `app/brokers/tradelocker_executor.py` (line ~230)

**Current:**
```python
async def get_accounts(self) -> List[Account]:
    """Get all TradeLocker accounts"""
    try:
        response = await self.session.get("/accounts")
        # ... Brand API code
```

**Should Be:**
```python
async def get_accounts(self) -> List[Account]:
    """Get all TradeLocker accounts"""
    # Use SDK if available
    if self._use_sdk and self._sdk_wrapper:
        return await self._get_accounts_sdk()
    
    # Fall back to Brand API
    return await self._get_accounts_brand_api()

async def _get_accounts_sdk(self) -> List[Account]:
    """Get accounts via SDK."""
    try:
        account_state = await self._sdk_wrapper.get_account_state()
        if account_state:
            return [Account(
                id=str(self._sdk_wrapper.account_number or ""),
                broker="tradelocker",
                account_type="live",
                currency=account_state.get("currency", "USD"),
                balance=float(account_state.get("balance", 0)),
                equity=float(account_state.get("equity", 0)),
                margin=float(account_state.get("margin", 0)),
                free_margin=float(account_state.get("freeMargin", 0)),
                margin_level=float(account_state.get("marginLevel", 0)),
                leverage=account_state.get("leverage", 100),
                is_active=True,
                is_live=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )]
        return []
    except Exception as e:
        logger.error(f"SDK get_accounts failed: {e}")
        return []
```

#### Fix 3: Update `get_positions()` to Use SDK
**File:** `app/brokers/tradelocker_executor.py` (line ~266)

**Add SDK method:**
```python
async def _get_positions_sdk(self) -> List[Position]:
    """Get positions via SDK."""
    try:
        positions_data = await self._sdk_wrapper.get_positions()
        positions = []
        
        for pos_data in positions_data:
            position = Position(
                id=str(pos_data.get("id", "")),
                broker="tradelocker",
                account_id=str(self._sdk_wrapper.account_number or ""),
                symbol=pos_data.get("symbol", ""),
                side=pos_data.get("side", "buy").lower(),
                size=float(pos_data.get("quantity", 0)),
                entry_price=float(pos_data.get("entryPrice", 0)),
                current_price=float(pos_data.get("currentPrice", 0)),
                unrealized_pnl=float(pos_data.get("unrealizedPnl", 0)),
                realized_pnl=0.0,
                margin=float(pos_data.get("margin", 0)),
                magic_number=pos_data.get("magic", 0),
                comment=pos_data.get("comment", ""),
                open_time=datetime.now(),  # SDK may not provide parsed datetime
                close_time=None,
                is_active=True
            )
            positions.append(position)
        
        return positions
    except Exception as e:
        logger.error(f"SDK get_positions failed: {e}")
        return []
```

### Priority 2: Important (Improves Functionality)

#### Fix 4: Update Order Management to Use SDK
- `modify_order()` - Use `self._sdk_wrapper.modify_order()` when SDK active
- `cancel_order()` - Use `self._sdk_wrapper.cancel_order()` when SDK active
- `get_orders()` - Use `self._sdk_wrapper.get_orders()` when SDK active

#### Fix 5: Implement Real-time Quotes
**File:** `app/brokers/tradelocker_executor.py` (line ~650)

**Current:**
```python
async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
    """Get quote for symbol"""
    return None
```

**Should Be:**
```python
async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
    """Get quote for symbol"""
    if self._use_sdk and self._sdk_wrapper:
        instrument_id = await self._sdk_wrapper.get_instrument_id_by_symbol(symbol)
        if instrument_id:
            ask_price = await self._sdk_wrapper.get_latest_asking_price(instrument_id)
            if ask_price:
                return {
                    "symbol": symbol,
                    "ask": ask_price,
                    "bid": ask_price - 0.0001,  # Approximate, SDK may not provide bid
                    "time": datetime.now().isoformat()
                }
    return None
```

### Priority 3: Nice to Have

#### Fix 6: Expose Price History
- Add method to executor to expose SDK's `get_price_history()` functionality

#### Fix 7: Enhance WebSocket Usage
- Actively use WebSocket for real-time updates instead of just polling
- Implement proper event handlers for position/order updates

## API Endpoint Reference

### Brand API Endpoints (Fallback Mode)
- Base URL: `https://api.tradelocker.com` (or broker-specific)
- Authentication: `brand-api-key` header
- Endpoints:
  - `GET /accounts` - List accounts
  - `GET /positions` - Get open positions
  - `GET /instruments` - Get available instruments
  - `POST /trades/market` - Place market order
  - `PUT /orders/{order_id}` - Modify order
  - `DELETE /orders/{order_id}` - Cancel order
  - `DELETE /positions/{position_id}` - Close position

### SDK Methods (Preferred Mode)
- Package: `tradelocker` (TLAPI)
- Methods:
  - `get_account_state()` - Get account balance/equity/margin
  - `get_all_instruments()` - Get instruments (returns DataFrame)
  - `get_all_positions()` - Get open positions
  - `get_all_orders()` - Get pending orders
  - `create_order()` - Place order
  - `close_position()` - Close position
  - `modify_order()` - Modify pending order
  - `delete_order()` - Cancel order
  - `get_price_history()` - Get OHLCV data
  - `get_latest_asking_price()` - Get current ask price

## Testing Checklist

- [ ] Install `tradelocker` SDK: `pip install tradelocker>=0.56.0`
- [ ] Test SDK authentication with real credentials
- [ ] Test account discovery via SDK (`get_accounts()`)
- [ ] Test position discovery via SDK (`get_positions()`)
- [ ] Test order placement via SDK (`place_order()`)
- [ ] Test order modification via SDK (`modify_order()`)
- [ ] Test order cancellation via SDK (`cancel_order()`)
- [ ] Test position closing via SDK (`close_position()`)
- [ ] Test symbol lookup (`get_symbols()`)
- [ ] Test quote retrieval (`get_quote()`)
- [ ] Test Brand API fallback mode (when SDK unavailable)
- [ ] Test WebSocket connection (if applicable)

## Implementation Recommendations

1. **Immediate Actions:**
   - Install TradeLocker SDK
   - Update `get_accounts()` to use SDK wrapper
   - Update `get_positions()` to use SDK wrapper

2. **Short-term:**
   - Update all order management methods to use SDK
   - Implement real-time quotes via SDK
   - Test with real TradeLocker credentials

3. **Long-term:**
   - Enhance WebSocket usage for real-time updates
   - Expose price history functionality
   - Add order/trade history endpoints
   - Implement account performance metrics

## Notes

- TradeLocker SDK is synchronous and uses `requests` library
- SDK wrapper uses `ThreadPoolExecutor` to avoid blocking async event loop
- Some brokers (e.g., GATESFX) require Brand API mode only
- WebSocket is maintained separately from SDK (SDK doesn't expose WebSocket API)
- SDK returns DataFrames for some methods (instruments, positions, orders)
