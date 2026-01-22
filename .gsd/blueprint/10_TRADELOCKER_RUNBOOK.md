# TradeLocker Setup RUNBOOK

## Overview

This runbook guides you through connecting a TradeLocker account to Tradeflow.

**Auth Mode:** SDK (email/password/server) - NOT Brand API

## Prerequisites

1. Backend running on port 8765
2. Valid TradeLocker demo or live account credentials
3. HTTP client (curl, Postman, or browser console)

---

## Step 1: Register a User (if needed)

```bash
curl -X POST http://localhost:8765/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "password": "YourPassword123!",
    "full_name": "Your Name"
  }'
```

**Expected:** 201 Created with user object

---

## Step 2: Login

```bash
curl -X POST http://localhost:8765/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "password": "YourPassword123!"
  }' | jq

# Save the access_token
export TOKEN="<paste_access_token_here>"
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

---

## Step 3: Test TradeLocker Connection

**Important:** The backend expects these credential fields for SDK mode:
- `username` (your TradeLocker email)
- `password` (your TradeLocker password)
- `server` (e.g., "Demo Server" or exact server name)
- `environment` (optional, defaults to "https://demo.tradelocker.com")

```bash
curl -X POST http://localhost:8765/api/v1/accounts/test-connection \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "broker": "tradelocker",
    "credentials": {
      "username": "YOUR_TRADELOCKER_EMAIL",
      "password": "YOUR_TRADELOCKER_PASSWORD",
      "server": "Demo Server",
      "environment": "https://demo.tradelocker.com"
    }
  }' | jq
```

**Expected Success:**
```json
{
  "success": true,
  "status": "connected",
  "message": "Successfully connected to TradeLocker via SDK",
  "details": { "mode": "sdk", "server": "Demo Server" },
  "detected_format": { ... },
  "symbol_map": { ... },
  "sample_symbols": ["EURUSD", "GBPUSD", ...]
}
```

**Expected Failure:**
```json
{
  "success": false,
  "status": "failed",
  "message": "TradeLocker SDK authentication failed. Please verify your username, password, and server.",
  "details": { "mode": "sdk" }
}
```

---

## Step 4: Create Account

After successful test connection, create the account:

```bash
curl -X POST http://localhost:8765/api/v1/accounts/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "YOUR_TL_ACCOUNT_NUMBER",
    "broker": "tradelocker",
    "account_type": "demo",
    "currency": "USD",
    "leverage": 100
  }' | jq
```

**Note:** The `account_id` is your TradeLocker account number (visible in TradeLocker platform).

**Expected:**
```json
{
  "id": 1,
  "account_id": "YOUR_TL_ACCOUNT_NUMBER",
  "broker": "tradelocker",
  "account_type": "demo",
  "is_active": true,
  "is_connected": true
}
```

---

## Step 5: Sync Account Balance

```bash
ACCOUNT_DB_ID=1  # Use the id from Step 4 response

curl -X POST "http://localhost:8765/api/v1/accounts/$ACCOUNT_DB_ID/sync" \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected:**
```json
{
  "balance": 100000.00,
  "equity": 100000.00,
  "margin": 0.00,
  "free_margin": 100000.00,
  "last_sync": "2026-01-22T..."
}
```

---

## Step 6: Fetch Positions

```bash
curl -s http://localhost:8765/api/v1/positions/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected:** Empty array `[]` if no open positions, or array of position objects.

---

## Step 7: List Your Accounts

```bash
curl -s http://localhost:8765/api/v1/accounts/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## Troubleshooting

### "TradeLocker SDK authentication failed"

1. **Wrong server name:** Server must match exactly (e.g., "Demo Server" not "demo server")
2. **Wrong environment:** For live accounts, use `https://live.tradelocker.com`
3. **Credentials expired:** Re-check email/password in TradeLocker web platform

### "Missing TradeLocker credentials"

The backend error response lists required fields:
```json
{
  "required_sdk": ["username", "password", "server"],
  "required_brand": ["api_key"]
}
```

Ensure you're sending `username` (not `email`) in the credentials object.

### Connection timeout

- Check network connectivity to TradeLocker servers
- Verify environment URL is reachable
- Backend timeout is 10 seconds

---

## TradeLocker Server Names (Common)

| Environment | Server Name |
|-------------|-------------|
| Demo | "Demo Server" |
| Live | (varies by broker) |

To find your exact server name:
1. Open TradeLocker web platform
2. Check the server dropdown on login
3. Use the exact string shown

---

## Quick Test Script

```bash
#!/bin/bash
# test_tradelocker.sh

BASE_URL="http://localhost:8765"
EMAIL="your@email.com"
PASSWORD="YourPassword123!"

TL_EMAIL="your-tradelocker@email.com"
TL_PASSWORD="your-tradelocker-password"
TL_SERVER="Demo Server"
TL_ENV="https://demo.tradelocker.com"

echo "=== Login ==="
RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo $RESPONSE | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo "Login failed: $RESPONSE"
  exit 1
fi
echo "Login OK"

echo ""
echo "=== Test TradeLocker Connection ==="
curl -s -X POST $BASE_URL/api/v1/accounts/test-connection \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"broker\": \"tradelocker\",
    \"credentials\": {
      \"username\": \"$TL_EMAIL\",
      \"password\": \"$TL_PASSWORD\",
      \"server\": \"$TL_SERVER\",
      \"environment\": \"$TL_ENV\"
    }
  }" | jq
```

---

*Generated: 2026-01-22*
