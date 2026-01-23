# BROKER UI CONTRACT REPORT

**Date:** 2026-01-23
**Phase:** PHASE 4 - Broker UI ↔ Backend Contract Alignment

---

## Summary

Broker "Add Account" UI and backend endpoints are aligned. Backend accepts multiple field name variations (non-breaking), and error responses are structured.

---

## Backend Endpoints

### 1. Test Connection

**Endpoint:** `POST /api/v1/accounts/test-connection`

**Request Body:**
```json
{
  "broker": "tradelocker",
  "credentials": {
    "username": "...",
    "password": "...",
    "server": "..."
  }
}
```

**Response (Success):**
```json
{
  "success": true,
  "status": "connected",
  "message": "Connection successful",
  "details": {},
  "detected_format": "pips",
  "symbol_map": {},
  "sample_symbols": []
}
```

**Response (Failure):**
```json
{
  "success": false,
  "status": "failed",
  "message": "Authentication failed: Invalid credentials",
  "details": {}
}
```

### 2. Discover Accounts

**Endpoint:** `POST /api/v1/accounts/discover`

**Request Body:**
```json
{
  "broker": "tradelocker",
  "credentials": {
    "username": "...",
    "password": "...",
    "server": "..."
  }
}
```

**Response:**
```json
{
  "accounts": [
    {
      "id": "12345",
      "name": "My Account",
      "account_type": "live",
      "currency": "USD",
      "is_live": true,
      "balance": 10000.0,
      "equity": 10000.0
    }
  ],
  "message": null
}
```

### 3. Connect Account

**Endpoint:** `POST /api/v1/accounts/connect`

**Request Body:**
```json
{
  "broker": "tradelocker",
  "credentials": {
    "username": "...",
    "password": "...",
    "server": "..."
  },
  "account_ids": ["12345"],
  "default_account_id": "12345"
}
```

**Response:**
```json
{
  "success": true,
  "accounts": [...],
  "message": "Accounts connected successfully"
}
```

---

## Field Name Variations (Non-Breaking)

### Backend Accepts Multiple Field Names

**TradeLocker:**
- `username` OR `email` (for Brand API)
- `password`
- `server`
- `api_key` OR `apiKey` (for Brand API)
- `environment` OR `sdk_environment`

**ProjectX/TopStep:**
- `username`
- `api_key` OR `api_token`
- `apiKey` (camelCase)

**MT4/MT5:**
- `metaapi_token` OR `metaApiToken`
- `metaapi_account_id` OR `metaApiAccountId`
- `manager_login` OR `login`
- `manager_password` OR `password`

**Tradovate:**
- `access_token` OR `accessToken`
- `environment` (demo/live)
- `user_id` (for password mode)
- `password` (for password mode)

---

## Error Response Format

### Structured Errors

**HTTPException (400/500):**
```json
{
  "detail": "Error message or validation errors"
}
```

**Use Case Errors:**
```json
{
  "success": false,
  "status": "failed",
  "message": "Human-readable error message",
  "details": {
    "code": "AUTH_FAILED",
    "reason": "Invalid credentials"
  }
}
```

### Error Codes (Proposed Standard)

- `AUTH_FAILED` - Authentication failed
- `CONNECTION_TIMEOUT` - Connection timeout
- `INVALID_BROKER` - Invalid broker type
- `MISSING_CREDENTIALS` - Required credentials missing
- `ACCOUNT_NOT_FOUND` - Account not found
- `DISCOVERY_FAILED` - Account discovery failed

---

## UI Payload Mapping

### Credential Mapping Function

**File:** `ui-next/src/lib/brokers/credentialSchemas.ts`

**Function:** `mapCredentialsToBackend(broker, credentials)`

**Purpose:** Maps UI field names (camelCase) to backend field names (snake_case)

**Example:**
```typescript
// UI sends:
{
  apiKey: "123",
  userName: "user@example.com"
}

// Backend receives:
{
  api_key: "123",
  username: "user@example.com"
}
```

---

## UI Error Handling

### Current Implementation

**File:** `ui-next/src/components/accounts/account-form.tsx`

**Error Display:**
- Test connection errors shown in `testResult.message`
- Form submission errors shown in `formError`
- Discovery errors logged but don't block form

**Improvements Made:**
- Errors are caught and displayed to user
- Error messages are user-readable
- Non-blocking errors (discovery) don't prevent account creation

---

## Contract Verification

### Field Name Compatibility

✅ **Backend accepts both:**
- `api_key` and `apiKey`
- `manager_login` and `login`
- `api_token` and `api_key` (ProjectX)

✅ **UI maps correctly:**
- CamelCase → snake_case
- Handles all broker-specific variations

### Error Structure

✅ **Backend returns structured errors:**
- `success` boolean
- `status` string
- `message` string
- `details` object (optional)

✅ **UI handles errors:**
- Displays error messages
- Shows connection status
- Handles network errors gracefully

---

## Smoke Test Script

**File:** `scripts/ui_broker_contract_smoke.sh`

**Purpose:** Test UI ↔ Backend contract alignment

**Tests:**
1. Test connection endpoint accepts UI payload format
2. Error responses are structured correctly
3. Field name variations are accepted
4. Discover accounts returns expected format

---

## Files Involved

### Backend

| File | Purpose |
|------|---------|
| `app/routers/accounts.py` | Account endpoints (test-connection, discover, connect) |
| `app/application/use_cases/test_connection.py` | Test connection use case |
| `app/brokers/*_executor.py` | Broker executors (accept various field names) |

### Frontend

| File | Purpose |
|------|---------|
| `ui-next/src/components/accounts/account-form.tsx` | Account form UI |
| `ui-next/src/lib/api/accounts.ts` | API client functions |
| `ui-next/src/lib/brokers/credentialSchemas.ts` | Credential mapping |

---

## Non-Breaking Changes

### Backend Compatibility

✅ **Accepts old field names:**
- `login` → `manager_login` (MT4/MT5)
- `password` → `manager_password` (MT4/MT5)
- `api_token` → `api_key` (ProjectX)

✅ **Accepts new field names:**
- `apiKey` → `api_key` (all brokers)
- `userName` → `username` (TradeLocker)
- `accessToken` → `access_token` (Tradovate)

### UI Compatibility

✅ **Maps correctly:**
- All UI field names mapped to backend format
- Handles missing fields gracefully
- Shows clear error messages

---

## Testing Checklist

- [x] Backend accepts UI payload format
- [x] Backend accepts field name variations
- [x] Error responses are structured
- [x] UI displays errors correctly
- [x] Discovery works after successful connection test
- [x] Account creation works after discovery

---

## Conclusion

- ✅ Contract aligned
- ✅ Non-breaking changes (accepts both old/new field names)
- ✅ Structured error responses
- ✅ UI error handling improved
- ✅ Smoke script created

**Status:** ✅ COMPLETE

---

*Generated: 2026-01-23*
