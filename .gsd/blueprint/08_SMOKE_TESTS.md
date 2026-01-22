# Smoke Tests: Unified Trading Engine

## Prerequisites

```bash
# Backend running on port 8765
curl http://localhost:8765/health

# UI running on port 3456
curl http://localhost:3456/api/health
```

---

## 1. Health Checks

### Backend Health
```bash
curl -s http://localhost:8765/health | jq
```

**Expected:**
```json
{
  "status": "healthy",
  "redis": "connected",
  "brokers": {
    "mt4": true,
    "mt5": true,
    "tradelocker": false,
    "tradovate": false,
    "projectx": false
  },
  "timestamp": 12345.678
}
```
**HTTP Code:** 200

### UI Health
```bash
curl -s http://localhost:3456/api/health | jq
```

**Expected:**
```json
{
  "status": "ok",
  "service": "unified-ui-next",
  "timestamp": "2026-01-22T12:00:00.000Z"
}
```
**HTTP Code:** 200

---

## 2. Authentication

### Register User
```bash
curl -X POST http://localhost:8765/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "full_name": "Test User"
  }' | jq
```

**Expected:**
```json
{
  "id": 1,
  "email": "test@example.com",
  "full_name": "Test User",
  "is_active": true
}
```
**HTTP Code:** 201

### Login
```bash
curl -X POST http://localhost:8765/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!"
  }' | jq
```

**Expected:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```
**HTTP Code:** 200

### Get Current User
```bash
TOKEN="your-jwt-token-here"
curl -s http://localhost:8765/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected:**
```json
{
  "id": 1,
  "email": "test@example.com",
  "full_name": "Test User",
  "subscription_tier": "free",
  "is_active": true
}
```
**HTTP Code:** 200

---

## 3. Accounts

### List Accounts
```bash
curl -s http://localhost:8765/api/v1/accounts/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected:**
```json
[]
```
**HTTP Code:** 200 (empty array if no accounts)

### Test TradeLocker Connection
```bash
curl -X POST http://localhost:8765/api/v1/accounts/test-connection \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "broker_type": "tradelocker",
    "credentials": {
      "email": "your-tradelocker-email",
      "password": "your-tradelocker-password",
      "server": "Demo Server",
      "environment": "https://demo.tradelocker.com"
    }
  }' | jq
```

**Expected (Success):**
```json
{
  "success": true,
  "accounts": [
    {
      "account_number": "12345",
      "account_name": "Demo Account",
      "balance": 100000.00,
      "currency": "USD"
    }
  ]
}
```
**HTTP Code:** 200

**Expected (Failure):**
```json
{
  "success": false,
  "error": "Authentication failed"
}
```
**HTTP Code:** 200 (with success=false)

### Test ProjectX Connection
```bash
curl -X POST http://localhost:8765/api/v1/accounts/test-connection \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "broker_type": "projectx",
    "credentials": {
      "username": "your-topstep-username",
      "api_key": "your-topstep-api-key"
    }
  }' | jq
```

**Expected (Success):**
```json
{
  "success": true,
  "accounts": [
    {
      "id": "123456",
      "name": "TopStep Funded Account",
      "balance": 50000.00
    }
  ]
}
```

### Create Account
```bash
curl -X POST http://localhost:8765/api/v1/accounts/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "broker": "tradelocker",
    "account_type": "demo",
    "account_number": "12345",
    "account_name": "My Demo Account"
  }' | jq
```

**Expected:**
```json
{
  "id": 1,
  "broker": "tradelocker",
  "account_type": "demo",
  "account_number": "12345",
  "account_name": "My Demo Account",
  "is_active": true,
  "is_signal_enabled": true
}
```
**HTTP Code:** 201

---

## 4. Positions

### List Positions
```bash
curl -s http://localhost:8765/api/v1/positions/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected:**
```json
[]
```
**HTTP Code:** 200 (empty if no open positions)

---

## 5. Webhook Signal

### Send Test Signal
```bash
# First create a webhook config and get the webhook_key
WEBHOOK_KEY="your-webhook-key"

curl -X POST "http://localhost:8765/api/v1/webhooks/signal/$WEBHOOK_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EURUSD",
    "action": "buy",
    "qty": 0.1,
    "price": 1.0850,
    "comment": "Test signal"
  }' | jq
```

**Expected (Success):**
```json
{
  "signal_id": "abc123",
  "status": "executed",
  "executed_accounts": 1,
  "failed_accounts": 0,
  "results": [
    {
      "account_id": 1,
      "broker": "tradelocker",
      "status": "success",
      "order_id": "12345"
    }
  ]
}
```
**HTTP Code:** 200

**Expected (No Accounts):**
```json
{
  "signal_id": "abc123",
  "status": "ignored",
  "message": "No enabled accounts for signal routing"
}
```

---

## 6. Unified API

### System Status
```bash
curl -s http://localhost:8765/api/v1/unified/status \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected:**
```json
{
  "status": "operational",
  "brokers": {
    "tradelocker": "connected",
    "projectx": "disconnected",
    "mt4": "connected",
    "mt5": "connected",
    "tradovate": "disconnected"
  },
  "active_accounts": 1,
  "open_positions": 0,
  "pending_signals": 0
}
```

### List Brokers
```bash
curl -s http://localhost:8765/api/v1/unified/brokers \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected:**
```json
[
  {
    "name": "tradelocker",
    "status": "connected",
    "accounts": 1
  },
  {
    "name": "projectx",
    "status": "disconnected",
    "accounts": 0
  }
]
```

---

## 7. Risk Settings

### Get Risk Settings
```bash
curl -s http://localhost:8765/api/v1/risk/settings \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected:**
```json
{
  "default_max_daily_trades": 10,
  "default_max_positions": 5,
  "default_max_daily_loss_pct": 5.0,
  "default_max_drawdown_pct": 10.0,
  "risk_management_enabled": true
}
```

---

## Quick Test Script

```bash
#!/bin/bash
# smoke_test.sh

BASE_URL="http://localhost:8765"
TOKEN=""

echo "=== Health Check ==="
curl -s $BASE_URL/health | jq -r '.status'

echo ""
echo "=== Login ==="
RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPassword123!"}')
TOKEN=$(echo $RESPONSE | jq -r '.access_token')

if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
  echo "Login successful"

  echo ""
  echo "=== List Accounts ==="
  curl -s $BASE_URL/api/v1/accounts/ \
    -H "Authorization: Bearer $TOKEN" | jq -r '. | length'

  echo ""
  echo "=== System Status ==="
  curl -s $BASE_URL/api/v1/unified/status \
    -H "Authorization: Bearer $TOKEN" | jq -r '.status'
else
  echo "Login failed"
fi
```

---
*Generated: 2026-01-22*
