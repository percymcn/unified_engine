# Tradovate SDK Full Functionality Analysis

**Date:** 2026-01-24  
**Status:** Analysis Complete

## Executive Summary

Tradovate integration supports dual-mode operation: OAuth mode (preferred) and password mode (fallback). The implementation is functional but has gaps in order history, real-time quotes, and some advanced features. OAuth token refresh is implemented but could be improved.

## Current Implementation Status

### ✅ What's Working

1. **Dual-Mode Authentication**
   - OAuth mode: Uses OAuth access token (preferred, production-ready)
   - Password mode: Uses username/password (fallback, for testing)

2. **OAuth Token Refresh** - Automatic token refresh via `TradovateTokenService`
3. **Test Connection** - Successfully tests password authentication
4. **Account Discovery** - Gets accounts via `/account/list`
5. **Position Management** - Get positions, close positions
6. **Order Placement** - Supports market, limit, stop orders
7. **Order Management** - Modify and cancel orders
8. **WebSocket Infrastructure** - WebSocket client initialized (but not fully utilized)

### ❌ What's Missing/Broken

#### 1. No Official SDK Package

**Current Status:**
- No official Tradovate Python SDK exists
- Implementation uses direct REST API calls via `httpx`
- Custom client exists in `broker_sdks/tradovate/tradovate_client.py` but executor doesn't use it

**Impact:**
- All functionality implemented via REST API
- No SDK abstraction layer
- This is acceptable - REST API is well-documented

#### 2. Account Discovery Issues

**Current:**
- `get_accounts()` works correctly via `/account/list`
- But doesn't filter by account type or status
- Returns all accounts without filtering

**Note:** This may be intentional - returns all accounts for user.

#### 3. Position Discovery Filtering

**Current:**
- `get_positions()` filters by `netPos != 0` (correct)
- But doesn't handle multiple accounts well
- Account filtering works but could be more efficient

#### 4. Order History Not Implemented

**Current:**
- `get_orders()` returns empty list (line 647-649)
- Tradovate API has `/order/list` endpoint but executor doesn't use it
- No historical order retrieval

**Missing:**
- Pending orders list
- Filled orders history
- Cancelled orders history

#### 5. Real-time Quotes Not Implemented

**Current:**
- `get_quote()` returns `None` (line 651-653)
- Tradovate API has market data endpoints but executor doesn't use them
- WebSocket supports market data but not implemented

**Missing:**
- Current bid/ask prices
- Market data subscription
- Real-time quote streaming

#### 6. WebSocket Not Fully Utilized

**Current:**
- WebSocket connection initialized (`websockets.connect`)
- Event handlers defined (`_handle_order_update`, `_handle_position_update`, etc.)
- **BUT:** WebSocket is not actively used for real-time updates
- No subscription to market data streams

**Missing:**
- Real-time position updates
- Real-time order fill notifications
- Real-time account balance updates
- Market data streaming

#### 7. Position Modification Not Implemented

**Current:**
- `modify_position()` returns `{"error": "Not implemented"}` (line 655-662)
- Tradovate doesn't support modifying open positions directly
- Positions are modified by placing new orders (opposite side)

**Note:** This may be correct - Tradovate may not support position SL/TP modification.

#### 8. Contract Lookup Inefficient

**Current:**
- `place_order()` calls `/contract/find?symbol={symbol}` for each order
- Should cache contract details or lookup once per symbol
- Could be optimized

#### 9. Missing Features

- **Order History** - No endpoint for historical orders
- **Trade History** - No endpoint for closed trades
- **Account Performance Metrics** - Not implemented
- **Risk Limits** - Not fetched from API
- **Market Data** - Historical bars not implemented
- **Bracket Orders** - Tradovate supports but executor doesn't expose
- **Trailing Stops** - Not implemented

#### 10. OAuth Token Refresh Could Be Improved

**Current:**
- Token refresh happens in `_ensure_valid_token()` before each API call
- This is good but could be optimized
- No proactive token refresh before expiry

## Required Fixes

### Priority 1: Critical (Improves Functionality)

#### Fix 1: Implement Order History
**File:** `app/brokers/tradovate_executor.py` (line ~647)

**Current:**
```python
async def get_orders(self) -> List[Dict[str, Any]]:
    """Get pending orders"""
    return []
```

**Should Be:**
```python
async def get_orders(self, account_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get pending orders"""
    if not await self._ensure_valid_token():
        logger.error("Token refresh failed, cannot get orders")
        return []
    
    try:
        params = {}
        if account_id:
            params["accountId"] = int(account_id)
        
        response = await self.session.get("/order/list", params=params)
        if response.status_code == 200:
            orders_data = response.json()
            return [
                {
                    "id": str(order.get("orderId", "")),
                    "account_id": str(order.get("accountId", "")),
                    "contract_id": str(order.get("contractId", "")),
                    "symbol": order.get("contract", {}).get("symbol", ""),
                    "order_type": order.get("orderType", ""),
                    "side": order.get("side", ""),
                    "quantity": order.get("orderQty", 0),
                    "price": order.get("price", 0),
                    "stop_price": order.get("stopPrice", 0),
                    "status": order.get("status", ""),
                    "filled_quantity": order.get("filledQty", 0),
                    "timestamp": order.get("timestamp", ""),
                }
                for order in orders_data
            ]
        else:
            logger.error(f"Failed to get Tradovate orders: {response.text}")
            return []
    except Exception as e:
        logger.error(f"Error getting Tradovate orders: {e}")
        return []
```

#### Fix 2: Implement Real-time Quotes
**File:** `app/brokers/tradovate_executor.py` (line ~651)

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
    if not await self._ensure_valid_token():
        logger.error("Token refresh failed, cannot get quote")
        return None
    
    try:
        # First get contract ID
        contract_response = await self.session.get(
            f"/contract/find?symbol={symbol}"
        )
        if contract_response.status_code != 200:
            return None
        
        contracts = contract_response.json()
        if not contracts:
            return None
        
        contract_id = contracts[0].get("contractId")
        
        # Get market data
        md_response = await self.session.get(
            "/md/getquotes",
            params={"contractId": contract_id}
        )
        if md_response.status_code == 200:
            quote_data = md_response.json()
            return {
                "symbol": symbol,
                "bid": float(quote_data.get("bid", 0)),
                "ask": float(quote_data.get("ask", 0)),
                "last": float(quote_data.get("last", 0)),
                "volume": int(quote_data.get("volume", 0)),
                "time": quote_data.get("time", ""),
            }
        return None
    except Exception as e:
        logger.error(f"Error getting Tradovate quote for {symbol}: {e}")
        return None
```

### Priority 2: Important (Enhances Real-time Features)

#### Fix 3: Enhance WebSocket Usage
**File:** `app/brokers/tradovate_executor.py` (line ~213)

**Current:**
- WebSocket connects but doesn't subscribe to streams

**Should Add:**
```python
async def _init_websocket(self):
    """Initialize WebSocket connection"""
    try:
        self.ws_connection = await websockets.connect(
            self.ws_url,
            extra_headers={"Authorization": f"Bearer {self.access_token}"}
        )
        
        # Subscribe to account updates
        await self.ws_connection.send(json.dumps({
            "e": "subscribe",
            "d": {"account": True}
        }))
        
        # Subscribe to position updates
        await self.ws_connection.send(json.dumps({
            "e": "subscribe",
            "d": {"position": True}
        }))
        
        # Subscribe to order updates
        await self.ws_connection.send(json.dumps({
            "e": "subscribe",
            "d": {"order": True}
        }))
        
        # Start WebSocket message handler
        asyncio.create_task(self._handle_websocket_messages())
        
    except Exception as e:
        logger.error(f"Failed to initialize Tradovate WebSocket: {e}")
```

#### Fix 4: Implement Bracket Orders
**File:** `app/brokers/tradovate_executor.py`

**Add Method:**
```python
async def place_bracket_order(
    self,
    account_id: str,
    symbol: str,
    side: str,
    quantity: float,
    entry_price: Optional[float] = None,
    profit_target: Optional[float] = None,
    stop_loss: Optional[float] = None
) -> OrderResponse:
    """Place bracket order (OCO) with Tradovate"""
    if not await self._ensure_valid_token():
        return OrderResponse(
            success=False,
            error="Token expired and refresh failed"
        )
    
    try:
        # Get contract details
        contract_response = await self.session.get(
            f"/contract/find?symbol={symbol}"
        )
        if contract_response.status_code != 200:
            return OrderResponse(
                success=False,
                error=f"Symbol {symbol} not found"
            )
        
        contract = contract_response.json()[0]
        
        # Build bracket orders
        bracket_orders = []
        if profit_target:
            bracket_orders.append({
                "orderType": "Limit",
                "side": "Sell" if side.lower() == "buy" else "Buy",
                "orderQty": quantity,
                "price": profit_target
            })
        if stop_loss:
            bracket_orders.append({
                "orderType": "StopMarket",
                "side": "Sell" if side.lower() == "buy" else "Buy",
                "orderQty": quantity,
                "stopPrice": stop_loss
            })
        
        order_data = {
            "accountId": int(account_id),
            "contractId": contract["contractId"],
            "orderType": "Market" if not entry_price else "Limit",
            "side": side.capitalize(),
            "orderQty": quantity,
            "price": entry_price,
            "bracketOrders": bracket_orders,
            "isAutomated": True
        }
        
        response = await self.session.post("/order/placeorder", json=order_data)
        
        if response.status_code == 200:
            result = response.json()
            return OrderResponse(
                success=True,
                order_id=str(result.get("orderId", "")),
                broker="tradovate",
                status=result.get("status", "submitted"),
                filled_quantity=result.get("filledQty", 0),
                filled_price=result.get("avgFillPrice", 0),
                commission=result.get("commission", 0),
                timestamp=datetime.now()
            )
        else:
            error_msg = response.text
            logger.error(f"Tradovate bracket order failed: {error_msg}")
            return OrderResponse(
                success=False,
                error=error_msg
            )
    except Exception as e:
        logger.error(f"Error placing Tradovate bracket order: {e}")
        return OrderResponse(
            success=False,
            error=str(e)
        )
```

### Priority 3: Nice to Have

#### Fix 5: Add Trade History
- Implement endpoint to get historical trades
- Use `/order/list` with status filter for filled orders

#### Fix 6: Optimize Contract Lookup
- Cache contract details per symbol
- Reduce API calls for repeated symbol lookups

#### Fix 7: Improve Position Modification
- Document that Tradovate doesn't support direct position modification
- Or implement via opposite order placement

## API Endpoint Reference

### Tradovate REST API
- **Base URL (Demo):** `https://demo.tradovate.com/v1`
- **Base URL (Live):** `https://live.tradovate.com/v1`
- **Authentication:** OAuth Bearer token or password auth

### Endpoints Used
- `POST /auth/accesstokenrequest` - Authenticate (password mode)
- `GET /account/list` - List accounts
- `GET /account/item?id={id}` - Get account details
- `GET /position/list` - Get open positions
- `GET /position/item?id={id}` - Get position details
- `GET /contract/find?symbol={symbol}` - Find contract by symbol
- `GET /contract/list` - List all contracts
- `POST /order/placeorder` - Place order
- `POST /order/modifyorder` - Modify order
- `POST /order/cancelorder` - Cancel order
- `GET /order/list` - List orders (NOT IMPLEMENTED)
- `GET /md/getquotes?contractId={id}` - Get market data (NOT IMPLEMENTED)

### WebSocket API
- **Base URL:** `wss://demo.tradovate.com/v1/websocket` or `wss://live.tradovate.com/v1/websocket`
- **Authentication:** Bearer token in headers
- **Events:**
  - `order` - Order updates
  - `position` - Position updates
  - `account` - Account updates
  - `fill` - Fill notifications

## Testing Checklist

- [ ] Test OAuth authentication with real credentials
- [ ] Test password authentication (fallback mode)
- [ ] Test account discovery (`get_accounts()`)
- [ ] Test position discovery (`get_positions()`)
- [ ] Test order placement for all order types
- [ ] Test order modification (`modify_order()`)
- [ ] Test order cancellation (`cancel_order()`)
- [ ] Test position closing (`close_position()`)
- [ ] Test order history (`get_orders()` - after fix)
- [ ] Test quote retrieval (`get_quote()` - after fix)
- [ ] Test WebSocket connection and subscriptions
- [ ] Test OAuth token refresh mechanism
- [ ] Test bracket orders (after implementation)
- [ ] Test error handling for invalid credentials
- [ ] Test error handling for network failures

## Implementation Recommendations

1. **Immediate Actions:**
   - Implement `get_orders()` to retrieve pending orders
   - Implement `get_quote()` to get real-time quotes
   - Enhance WebSocket subscriptions

2. **Short-term:**
   - Implement bracket orders
   - Add trade history endpoint
   - Optimize contract lookup caching

3. **Long-term:**
   - Add account performance metrics
   - Implement trailing stops
   - Enhance WebSocket event handling
   - Add market data historical bars

## Notes

- Tradovate has no official Python SDK - REST API is well-documented
- OAuth mode is preferred for production (more secure, token refresh)
- Password mode is useful for testing but less secure
- WebSocket API provides real-time updates but requires proper subscription
- Tradovate uses futures contracts (not spot forex like MT4/MT5)
- Contract symbols are different (e.g., "MES", "MNQ" instead of "EURUSD")
- Position modification may not be supported - check Tradovate API docs
- Bracket orders (OCO) are supported via `bracketOrders` parameter
