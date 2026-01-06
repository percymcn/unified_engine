# TradeFlow v6 - Complete API Sample Payloads

## 📡 All Endpoints with Request/Response Examples

---

## 1. Overview & Analytics

### GET /api/overview
**Description**: Main dashboard KPIs and summary metrics

**Request**:
```http
GET /api/overview
Authorization: Bearer eyJhbGc...
```

**Response** (200 OK):
```json
{
  "total_pnl": 12450.75,
  "total_pnl_pct": 24.9,
  "today_pnl": 385.50,
  "today_trades": 12,
  "win_rate": 68.5,
  "active_positions": 3,
  "total_trades": 245,
  "largest_win": 1250.00,
  "largest_loss": -450.00,
  "avg_win": 215.30,
  "avg_loss": -125.80,
  "sharpe_ratio": 1.85
}
```

**Error** (401):
```json
{
  "error": "Unauthorized",
  "message": "Invalid or expired token"
}
```

---

### GET /api/positions
**Description**: Get all open positions across brokers

**Request**:
```http
GET /api/positions
Authorization: Bearer eyJhbGc...
```

**Response** (200 OK):
```json
[
  {
    "id": "pos_1a2b3c",
    "symbol": "ES",
    "side": "BUY",
    "qty": 2,
    "avg_price": 4825.50,
    "current_price": 4832.25,
    "pnl": 135.00,
    "pnl_percent": 2.8,
    "broker": "tradelocker",
    "opened_at": "2025-10-19T14:23:15Z",
    "stop_loss": 4815.00,
    "take_profit": 4850.00,
    "tag": "ES_Breakout_Long"
  },
  {
    "id": "pos_4d5e6f",
    "symbol": "NQ",
    "side": "SELL",
    "qty": 1,
    "avg_price": 16245.00,
    "current_price": 16260.50,
    "pnl": -155.00,
    "pnl_percent": -0.95,
    "broker": "topstep",
    "opened_at": "2025-10-19T13:45:22Z",
    "stop_loss": 16280.00,
    "take_profit": 16200.00,
    "tag": "NQ_Reversal_Short"
  }
]
```

---

### GET /api/orders
**Description**: Get orders with optional filters

**Request**:
```http
GET /api/orders?limit=50&offset=0&status=FILLED&symbol=ES
Authorization: Bearer eyJhbGc...
```

**Query Parameters**:
- `limit`: number (default: 100)
- `offset`: number (default: 0)
- `status`: PENDING|FILLED|CANCELED|REJECTED (optional)
- `symbol`: string (optional)

**Response** (200 OK):
```json
[
  {
    "id": "ord_7g8h9i",
    "symbol": "ES",
    "side": "BUY",
    "type": "MARKET",
    "qty": 2,
    "price": null,
    "status": "FILLED",
    "broker": "tradelocker",
    "created_at": "2025-10-19T14:23:10Z",
    "filled_at": "2025-10-19T14:23:15Z"
  }
]
```

---

### POST /api/orders/close
**Description**: Close an open position

**Request**:
```http
POST /api/orders/close
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "position_id": "pos_1a2b3c"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "pnl": 135.00,
  "order_id": "ord_abc123",
  "closed_at": "2025-10-19T15:30:45Z"
}
```

**Error** (404):
```json
{
  "error": "Position not found",
  "message": "No position with ID pos_1a2b3c"
}
```

---

### DELETE /api/orders/{order_id}
**Description**: Cancel/delete a pending order

**Request**:
```http
DELETE /api/orders/ord_7g8h9i
Authorization: Bearer eyJhbGc...
```

**Response** (204 No Content)

**Error** (400):
```json
{
  "error": "Cannot delete",
  "message": "Order is already filled"
}
```

---

### GET /api/reports/pnl
**Description**: P&L report for date range

**Request**:
```http
GET /api/reports/pnl?start_date=2025-10-01&end_date=2025-10-19
Authorization: Bearer eyJhbGc...
```

**Response** (200 OK):
```json
{
  "start_date": "2025-10-01",
  "end_date": "2025-10-19",
  "total_pnl": 5430.75,
  "total_trades": 87,
  "winning_trades": 58,
  "losing_trades": 29,
  "win_rate": 66.67,
  "profit_factor": 2.15,
  "daily_breakdown": [
    {
      "date": "2025-10-01",
      "pnl": 245.50,
      "trades": 5,
      "volume": 12
    },
    {
      "date": "2025-10-02",
      "pnl": -85.00,
      "trades": 3,
      "volume": 8
    }
  ]
}
```

---

### GET /api/analytics/metrics
**Description**: Advanced metrics for date range and broker

**Request**:
```http
GET /api/analytics/metrics?start_date=2025-10-01&end_date=2025-10-19&broker=tradelocker
Authorization: Bearer eyJhbGc...
```

**Response** (200 OK):
```json
{
  "period": "2025-10-01 to 2025-10-19",
  "broker": "tradelocker",
  "total_volume": 245,
  "total_trades": 87,
  "avg_trade_duration": 125,
  "best_symbol": "ES",
  "worst_symbol": "GC",
  "best_day": "2025-10-15",
  "worst_day": "2025-10-08",
  "metrics_by_symbol": {
    "ES": {
      "trades": 42,
      "pnl": 2450.50,
      "win_rate": 71.4
    },
    "NQ": {
      "trades": 28,
      "pnl": 1850.25,
      "win_rate": 64.3
    },
    "GC": {
      "trades": 17,
      "pnl": -425.00,
      "win_rate": 41.2
    }
  }
}
```

---

### GET /api/analytics/trades
**Description**: Detailed trade history

**Request**:
```http
GET /api/analytics/trades?start_date=2025-10-01&end_date=2025-10-19
Authorization: Bearer eyJhbGc...
```

**Response** (200 OK):
```json
{
  "trades": [
    {
      "id": "trd_123abc",
      "symbol": "ES",
      "side": "BUY",
      "entry_price": 4820.00,
      "exit_price": 4835.50,
      "qty": 2,
      "pnl": 155.00,
      "duration_minutes": 45,
      "opened_at": "2025-10-19T10:15:00Z",
      "closed_at": "2025-10-19T11:00:00Z",
      "broker": "tradelocker"
    }
  ]
}
```

---

## 2. Broker Management

### GET /api/user/brokers
**Description**: List all connected broker accounts

**Request**:
```http
GET /api/user/brokers
Authorization: Bearer eyJhbGc...
```

**Response** (200 OK):
```json
[
  {
    "id": "acc_1a2b3c",
    "broker": "tradelocker",
    "email": "trader@example.com",
    "server": null,
    "mode": "live",
    "status": "active",
    "balance": 50000.00,
    "equity": 51245.75,
    "margin_used": 12500.00,
    "margin_available": 38745.75,
    "created_at": "2025-09-15T08:30:00Z",
    "last_sync": "2025-10-19T15:45:12Z"
  },
  {
    "id": "acc_4d5e6f",
    "broker": "topstep",
    "email": "trader@example.com",
    "server": "Rithmic01",
    "mode": "demo",
    "status": "active",
    "balance": 150000.00,
    "equity": 152385.50,
    "margin_used": 25000.00,
    "margin_available": 127385.50,
    "created_at": "2025-10-01T12:00:00Z",
    "last_sync": "2025-10-19T15:44:58Z"
  }
]
```

---

### POST /register/{broker}
**Description**: Connect a new broker account

**Request** (TradeLocker):
```http
POST /register/tradelocker
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "email": "trader@example.com",
  "password": "SecurePass123!",
  "mode": "live"
}
```

**Request** (Topstep):
```http
POST /register/topstep
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "email": "trader@example.com",
  "password": "SecurePass123!",
  "server": "Rithmic01",
  "mode": "demo"
}
```

**Request** (MT4/MT5):
```http
POST /register/mt4
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "email": "trader@example.com",
  "password": "SecurePass123!",
  "server": "ICMarkets-Demo",
  "mode": "demo"
}
```

**Response** (201 Created):
```json
{
  "id": "acc_new123",
  "broker": "tradelocker",
  "email": "trader@example.com",
  "mode": "live",
  "status": "pending",
  "balance": 0,
  "equity": 0,
  "margin_used": 0,
  "margin_available": 0,
  "created_at": "2025-10-19T16:00:00Z"
}
```

**Error** (400):
```json
{
  "error": "Invalid credentials",
  "message": "Failed to authenticate with broker"
}
```

---

### POST /api/accounts/switch
**Description**: Switch active broker account

**Request**:
```http
POST /api/accounts/switch
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "account_id": "acc_4d5e6f"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Switched to Topstep account",
  "active_account_id": "acc_4d5e6f"
}
```

**Error** (404):
```json
{
  "error": "Account not found",
  "message": "No account with ID acc_4d5e6f"
}
```

---

### GET /api/accounts/sync_results
**Description**: Get latest sync results for all accounts

**Request**:
```http
GET /api/accounts/sync_results
Authorization: Bearer eyJhbGc...
```

**Response** (200 OK):
```json
[
  {
    "account_id": "acc_1a2b3c",
    "broker": "tradelocker",
    "status": "success",
    "positions_synced": 3,
    "orders_synced": 12,
    "balance_updated": true,
    "errors": [],
    "synced_at": "2025-10-19T15:45:12Z"
  },
  {
    "account_id": "acc_4d5e6f",
    "broker": "topstep",
    "status": "partial",
    "positions_synced": 2,
    "orders_synced": 8,
    "balance_updated": true,
    "errors": ["Failed to fetch order history for symbol GC"],
    "synced_at": "2025-10-19T15:44:58Z"
  }
]
```

---

### POST /api/accounts/sync/{id}
**Description**: Manually trigger account sync

**Request**:
```http
POST /api/accounts/sync/acc_1a2b3c
Authorization: Bearer eyJhbGc...
```

**Response** (200 OK):
```json
{
  "account_id": "acc_1a2b3c",
  "broker": "tradelocker",
  "status": "success",
  "positions_synced": 3,
  "orders_synced": 12,
  "balance_updated": true,
  "errors": [],
  "synced_at": "2025-10-19T16:05:30Z"
}
```

---

## 3. User Configuration

### GET /api/user/config
**Description**: Get user trading configuration

**Request**:
```http
GET /api/user/config
Authorization: Bearer eyJhbGc...
```

**Response** (200 OK):
```json
{
  "stop_loss_pct": 2.5,
  "take_profit_pct": 5.0,
  "position_size": 1,
  "max_daily_loss": 1000.00,
  "max_daily_trades": 20,
  "allow_weekend_trading": false
}
```

---

### PUT /api/user/config
**Description**: Update user trading configuration

**Request**:
```http
PUT /api/user/config
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "stop_loss_pct": 2.0,
  "take_profit_pct": 4.5,
  "position_size": 2,
  "max_daily_loss": 800.00,
  "max_daily_trades": 15,
  "allow_weekend_trading": true
}
```

**Response** (200 OK):
```json
{
  "stop_loss_pct": 2.0,
  "take_profit_pct": 4.5,
  "position_size": 2,
  "max_daily_loss": 800.00,
  "max_daily_trades": 15,
  "allow_weekend_trading": true,
  "updated_at": "2025-10-19T16:10:00Z"
}
```

---

### GET /api/user/risk_config
**Description**: Get risk management configuration

**Request**:
```http
GET /api/user/risk_config
Authorization: Bearer eyJhbGc...
```

**Response** (200 OK):
```json
{
  "max_risk_per_trade": 1.0,
  "max_drawdown": 5.0,
  "max_correlation": 0.7,
  "max_open_positions": 5,
  "emergency_stop_enabled": true,
  "emergency_stop_loss": 2000.00
}
```

---

### PUT /api/user/risk_config
**Description**: Update risk management configuration

**Request**:
```http
PUT /api/user/risk_config
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "max_risk_per_trade": 0.5,
  "max_drawdown": 3.0,
  "max_correlation": 0.6,
  "max_open_positions": 3,
  "emergency_stop_enabled": true,
  "emergency_stop_loss": 1500.00
}
```

**Response** (200 OK):
```json
{
  "max_risk_per_trade": 0.5,
  "max_drawdown": 3.0,
  "max_correlation": 0.6,
  "max_open_positions": 3,
  "emergency_stop_enabled": true,
  "emergency_stop_loss": 1500.00,
  "updated_at": "2025-10-19T16:15:00Z"
}
```

---

### POST /api/user/emergency_stop
**Description**: Close all positions immediately (kill switch)

**Request**:
```http
POST /api/user/emergency_stop
Authorization: Bearer eyJhbGc...
```

**Response** (200 OK):
```json
{
  "success": true,
  "positions_closed": 3,
  "orders_canceled": 5,
  "total_pnl": -245.50,
  "executed_at": "2025-10-19T16:20:00Z"
}
```

**NATS Event Published**:
```json
{
  "subject": "ai.ops.health.sweep",
  "payload": {
    "op": "kill_switch",
    "user_id": "usr_abc123",
    "timestamp": "2025-10-19T16:20:00Z",
    "positions_closed": 3
  }
}
```

---

## 4. API Keys

### GET /api/user/api_keys
**Description**: List all API keys

**Request**:
```http
GET /api/user/api_keys
Authorization: Bearer eyJhbGc...
```

**Response** (200 OK):
```json
[
  {
    "id": "key_1a2b3c",
    "key": "tf_live_4d5e6f7g8h9i0j",
    "name": "TradingView Webhook",
    "permissions": ["webhook.receive", "orders.create"],
    "created_at": "2025-10-15T10:00:00Z",
    "last_used": "2025-10-19T14:30:00Z",
    "expires_at": null
  }
]
```

---

### POST /api/user/api_keys/generate
**Description**: Generate a new API key

**Request**:
```http
POST /api/user/api_keys/generate
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "name": "My Strategy Bot",
  "permissions": ["webhook.receive", "orders.create", "positions.read"]
}
```

**Response** (201 Created):
```json
{
  "id": "key_new456",
  "key": "tf_live_k1l2m3n4o5p6q7",
  "secret": "sk_live_r8s9t0u1v2w3x4y5z6",
  "name": "My Strategy Bot",
  "permissions": ["webhook.receive", "orders.create", "positions.read"],
  "created_at": "2025-10-19T16:25:00Z"
}
```

**⚠️ Warning**: Secret is only shown once!

---

### DELETE /api/user/api_keys/{key_id}
**Description**: Revoke an API key

**Request**:
```http
DELETE /api/user/api_keys/key_1a2b3c
Authorization: Bearer eyJhbGc...
```

**Response** (204 No Content)

---

## 5. Billing

### GET /api/billing/status
**Description**: Get subscription status

**Request**:
```http
GET /api/billing/status
Authorization: Bearer eyJhbGc...
```

**Response** (200 OK):
```json
{
  "status": "active",
  "plan": "pro",
  "price_id": "price_1ProMonthly",
  "current_period_end": "2025-11-19T00:00:00Z",
  "cancel_at_period_end": false,
  "trial_end": null,
  "customer_id": "cus_abc123xyz"
}
```

**Possible statuses**:
- `active`: Subscription active and paid
- `trialing`: In trial period
- `past_due`: Payment failed
- `canceled`: Subscription canceled
- `incomplete`: Payment setup incomplete

---

### GET /api/billing/usage
**Description**: Get usage metrics for current period

**Request**:
```http
GET /api/billing/usage
Authorization: Bearer eyJhbGc...
```

**Response** (200 OK):
```json
{
  "trades_count": 45,
  "trades_limit": null,
  "days_remaining": null,
  "trial_trades_remaining": null,
  "brokers_connected": 2,
  "brokers_limit": 2,
  "strategies_active": 1,
  "strategies_limit": 1
}
```

**Response** (Trialing):
```json
{
  "trades_count": 65,
  "trades_limit": 100,
  "days_remaining": 2,
  "trial_trades_remaining": 35,
  "brokers_connected": 1,
  "brokers_limit": 1,
  "strategies_active": 0,
  "strategies_limit": 0
}
```

---

### POST /api/billing/checkout
**Description**: Create Stripe checkout session

**Request**:
```http
POST /api/billing/checkout
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "price_id": "price_1ProMonthly",
  "success_url": "https://app.tradeflow.com/dashboard?checkout=success",
  "cancel_url": "https://app.tradeflow.com/billing?checkout=canceled"
}
```

**Response** (200 OK):
```json
{
  "url": "https://checkout.stripe.com/c/pay/cs_live_abc123...",
  "session_id": "cs_live_abc123xyz"
}
```

---

### POST /api/billing/cancel
**Description**: Cancel subscription at period end

**Request**:
```http
POST /api/billing/cancel
Authorization: Bearer eyJhbGc...
```

**Response** (200 OK):
```json
{
  "success": true,
  "effective_date": "2025-11-19T23:59:59Z",
  "message": "Subscription will cancel on 2025-11-19"
}
```

---

## 6. Logs

### GET /api/logs/webhooks
**Description**: Get webhook request logs

**Request**:
```http
GET /api/logs/webhooks?limit=50&offset=0
Authorization: Bearer eyJhbGc...
```

**Response** (200 OK):
```json
[
  {
    "id": "log_1a2b3c",
    "timestamp": "2025-10-19T14:30:15Z",
    "method": "POST",
    "path": "/webhook",
    "status": 200,
    "payload": {
      "symbol": "ES",
      "action": "BUY",
      "price": 4825.50,
      "sl": 4815.00,
      "tp": 4850.00
    },
    "response": {
      "success": true,
      "order_id": "ord_abc123"
    },
    "latency_ms": 145,
    "error": null
  },
  {
    "id": "log_4d5e6f",
    "timestamp": "2025-10-19T13:15:22Z",
    "method": "POST",
    "path": "/webhook",
    "status": 401,
    "payload": {
      "symbol": "NQ",
      "action": "SELL"
    },
    "response": {
      "error": "Invalid API key"
    },
    "latency_ms": 12,
    "error": "Authentication failed"
  }
]
```

---

## 7. Auth

### POST /api/auth/reset-password
**Description**: Send password reset email

**Request**:
```http
POST /api/auth/reset-password
Content-Type: application/json

{
  "email": "trader@example.com"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Password reset email sent to trader@example.com"
}
```

**Error** (404):
```json
{
  "error": "User not found",
  "message": "No account exists with that email"
}
```

---

## 8. Webhook (TradingView → Backend)

### POST /webhook
**Description**: Receive TradingView alerts (backend only, no UI)

**Request**:
```http
POST /webhook
X-API-Key: tf_live_4d5e6f7g8h9i0j
Content-Type: application/json

{
  "symbol": "ES",
  "action": "BUY",
  "price": 4825.50,
  "sl": 4815.00,
  "tp": 4850.00,
  "qty": 2,
  "tag": "ES_Breakout_Long"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "order_id": "ord_abc123",
  "message": "Order placed successfully"
}
```

**Error** (401):
```json
{
  "error": "Unauthorized",
  "message": "Invalid or missing API key"
}
```

**Error** (400):
```json
{
  "error": "Validation error",
  "message": "Missing required field: symbol"
}
```

---

## 📊 Quick Reference

### Success Codes
- `200 OK`: Request successful
- `201 Created`: Resource created
- `204 No Content`: Successful deletion

### Error Codes
- `400 Bad Request`: Validation error
- `401 Unauthorized`: Auth failure
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource doesn't exist
- `429 Too Many Requests`: Rate limited
- `500 Internal Server Error`: Server error

### Rate Limits
- Default: 100 requests/minute
- Webhook: 300 requests/minute
- Burst: 20 requests/second

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-19  
**Base URL**: https://unified.fluxeo.net/api/unify/v1
