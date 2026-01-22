# Smoke Tests: TradeLocker + ProjectX Wiring

**Date:** 2026-01-22  
**Purpose:** End-to-end verification of TradeLocker and ProjectX broker wiring

---

## Prerequisites

- Backend running on `http://127.0.0.1:8765`
- UI running on `http://127.0.0.1:3456`
- Authentication token required for account endpoints

---

## Backend Health Check

```bash
# Health endpoint (no auth required)
curl http://127.0.0.1:8765/health

# Expected: {"status":"healthy","redis":"connected",...}
```

---

## Account Endpoints Verification

```bash
# List available account endpoints
curl http://127.0.0.1:8765/openapi.json | grep -o '"/api/v1/accounts[^"]*"'

# Expected endpoints:
# - /api/v1/accounts/
# - /api/v1/accounts/test-connection
# - /api/v1/accounts/discover
# - /api/v1/accounts/available/{broker_type}
# - /api/v1/accounts/{account_id}/select
# - /api/v1/accounts/sync-all
# - /api/v1/accounts/{account_id}
# - /api/v1/accounts/{account_id}/sync
# - /api/v1/accounts/{account_id}/balance
# - /api/v1/accounts/{account_id}/settings
```

---

## TradeLocker Test Connection

**Note:** All account endpoints require authentication. Use a valid JWT token in the `Authorization` header.

### Brand API Mode (GATESFX)

```bash
# Test with GATESFX server (requires Brand API)
curl -X POST http://127.0.0.1:8765/api/v1/accounts/test-connection \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "broker": "tradelocker",
    "credentials": {
      "api_key": "your-brand-api-key",
      "server": "GATESFX",
      "environment_url": "https://live.tradelocker.com"
    }
  }'

# Expected success response:
# {
#   "success": true,
#   "status": "connected",
#   "message": "Successfully connected to TradeLocker via Brand API",
#   "details": {"mode": "brand_api", "api_url": "...", "server": "GATESFX"}
# }

# Expected error if username/password provided instead:
# {
#   "success": false,
#   "status": "failed",
#   "message": "Broker 'GATESFX' requires Brand API Key mode; username/password authentication is not supported.",
#   "details": {"mode": "brand_api_required", "server": "GATESFX", ...}
# }
```

### SDK Mode (Other Servers)

```bash
# Test with SDK credentials (username/password/server)
curl -X POST http://127.0.0.1:8765/api/v1/accounts/test-connection \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "broker": "tradelocker",
    "credentials": {
      "username": "your-email@example.com",
      "password": "your-password",
      "server": "Demo Server",
      "environment": "https://demo.tradelocker.com"
    }
  }'

# Expected success response:
# {
#   "success": true,
#   "status": "connected",
#   "message": "Successfully connected to TradeLocker via SDK",
#   "details": {"mode": "sdk", "server": "Demo Server"}
# }
```

---

## ProjectX Test Connection

```bash
# Test ProjectX connection
curl -X POST http://127.0.0.1:8765/api/v1/accounts/test-connection \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "broker": "projectx",
    "credentials": {
      "username": "your-topstep-username",
      "api_key": "your-api-key"
    }
  }'

# Expected success response:
# {
#   "success": true,
#   "status": "connected",
#   "message": "Successfully authenticated with ProjectX/TopStep",
#   "details": {"mode": "httpx"} or {"mode": "sdk"}
# }

# Expected error if missing credentials:
# {
#   "success": false,
#   "status": "failed",
#   "message": "Missing ProjectX/TopStep credentials. Provide username and api_key.",
#   "details": {"required": ["username", "api_key"]}
# }
```

---

## Account Discovery

### TradeLocker Discovery

```bash
# Discover TradeLocker accounts (Brand API mode)
curl -X POST http://127.0.0.1:8765/api/v1/accounts/discover \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "broker": "tradelocker",
    "credentials": {
      "api_key": "your-brand-api-key",
      "server": "GATESFX",
      "environment_url": "https://live.tradelocker.com"
    }
  }'

# Expected response:
# {
#   "accounts": [
#     {
#       "id": "account-id",
#       "name": "Account Name",
#       "account_type": "live",
#       "currency": "USD",
#       "is_live": true,
#       "balance": 10000.0,
#       "equity": 10000.0
#     }
#   ],
#   "message": null
# }
```

### ProjectX Discovery

```bash
# Discover ProjectX accounts
curl -X POST http://127.0.0.1:8765/api/v1/accounts/discover \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "broker": "projectx",
    "credentials": {
      "username": "your-topstep-username",
      "api_key": "your-api-key"
    }
  }'

# Expected response:
# {
#   "accounts": [...],
#   "message": null or "No accounts found. ProjectX/TopStep accounts may need to be added manually..."
# }
```

---

## Unit Tests

```bash
# Run connection test unit tests
python3 -m pytest tests/test_connection_test.py -v

# Expected: All tests pass (25+ tests)
```

---

## UI Build Verification

```bash
cd ui-next
npm ci
npm run build -- --no-lint

# Expected: Build succeeds with no TypeScript errors
# Note: Dynamic route warnings are normal for Next.js
```

---

## Summary

**Backend Health:** ✅ PASS  
**Endpoints Available:** ✅ PASS (test-connection, discover, etc.)  
**Unit Tests:** ✅ PASS (25+ tests)  
**UI Build:** ✅ PASS  

**Note:** Account endpoints require authentication. Use a valid JWT token obtained from `/api/v1/auth/login` endpoint.

---

## Authentication

To get a token for testing:

```bash
# Login (example)
curl -X POST http://127.0.0.1:8765/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "your-password"
  }'

# Response includes access_token - use this in Authorization header
```
