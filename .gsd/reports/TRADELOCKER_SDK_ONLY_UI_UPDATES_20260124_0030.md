# TradeLocker SDK-Only Mode & UI Updates Report

**Date:** 2026-01-24  
**Changes:** Removed Brand API fallback, SDK-only mode + UI account selection updates

## Summary

Removed all Brand API fallback code from TradeLocker executor and updated UI to:
1. Remove Brand API credential option
2. Add refresh accounts functionality
3. Add broker account selection UI

## Backend Changes

### TradeLocker Executor (`app/brokers/tradelocker_executor.py`)

**Removed:**
- All Brand API fallback methods (`_initialize_brand_api`, `_get_accounts_brand_api`, `_get_positions_brand_api`, `_place_order_brand_api`, `_modify_order_brand_api`, `_cancel_order_brand_api`, `_close_position_brand_api`)
- Brand API configuration fields (`api_url`, `ws_url`, `api_key`, `environment`)
- `httpx` import (no longer needed)
- `session` attribute (httpx client)
- All fallback logic that checked `_brand_api_available`

**Updated:**
- `__init__`: Only checks for SDK credentials (username/password/server)
- `initialize()`: SDK-only initialization, no fallback
- All methods (`get_accounts`, `get_positions`, `place_order`, `modify_order`, `cancel_order`, `close_position`, `get_account_info`, `get_quote`, `get_orders`, `get_symbols`): SDK-only, return error if SDK not initialized
- WebSocket connection: Uses SDK environment URL

**Result:**
- TradeLocker executor is now SDK-only
- Requires username, password, and server credentials
- No Brand API support

## Frontend Changes

### Credential Schemas (`ui-next/src/lib/brokers/credentialSchemas.ts`)

**Removed:**
- Brand API mode field (`apiKey` optional field)
- Brand API notes and descriptions
- GATESFX-specific mentions

**Updated:**
- `TRADELOCKER_SCHEMA`: Only includes SDK fields (username, password, server, environment)
- Notes updated to reflect SDK-only mode

### Account Form (`ui-next/src/components/accounts/account-form.tsx`)

**Removed:**
- `requiresBrandAPI` logic
- `backendRequiresBrandAPI` logic
- `effectiveRequiresBrandAPI` logic
- Brand API requirement hints/alerts
- Field hiding logic for Brand API mode
- Brand API field requirement adjustments

**Updated:**
- Simplified credential field rendering (no Brand API checks)
- All fields use standard required/optional logic

### Account Settings Page (`ui-next/src/app/dashboard/settings/accounts/[id]/settings/page.tsx`)

**Added:**
- `refreshBrokerAccounts` function call
- `discoveredAccounts` state
- `selectedAccountIds` state
- `defaultAccountId` state
- `refreshing` state
- `handleRefreshAccounts` function
- `handleAccountToggle` function
- `handleDefaultChange` function
- `handleSaveAccountSelection` function
- Broker Account Selection UI section with:
  - Refresh Accounts button
  - Account list with checkboxes (enabled) and radio buttons (default)
  - Status badges (Active/Inactive)
  - Account type badges (eval/funded/demo)
  - Save Selection button

**Updated:**
- `loadData`: Loads broker account selection fields from account response
- Imports: Added `RefreshCw`, `Checkbox`, `Label`, `refreshBrokerAccounts`, `updateAccount`, `DiscoveredAccount`

### API Client (`ui-next/src/lib/api/accounts.ts`)

**Added:**
- `refreshBrokerAccounts` function to call `/api/accounts/{id}/refresh-accounts`

## Testing

### Backend
```bash
# Verify TradeLocker executor compiles
python3 -m py_compile app/brokers/tradelocker_executor.py
```

### Frontend
1. Navigate to Settings → Accounts → Add New Account
2. Select TradeLocker
3. Verify only username/password/server fields shown (no API key field)
4. Enter credentials and click "Test & Validate"
5. Verify accounts are discovered
6. Select accounts and save

7. Navigate to Settings → Accounts → [Account Name] → Settings
8. Verify "Broker Account Selection" section appears
9. Click "Refresh Accounts" button
10. Verify accounts are refreshed
11. Toggle enabled accounts and set default
12. Click "Save Selection"

## Commands

### Test TradeLocker Connection (SDK Only)
```bash
curl -X POST http://127.0.0.1:8765/api/v1/accounts/test-connection \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "broker": "tradelocker",
    "credentials": {
      "username": "your_email@example.com",
      "password": "your_password",
      "server": "Demo Server"
    }
  }'
```

### Refresh Accounts
```bash
curl -X POST http://127.0.0.1:8765/api/v1/accounts/1/refresh-accounts \
  -H "Authorization: Bearer <token>"
```

## Breaking Changes

⚠️ **BREAKING:** TradeLocker no longer supports Brand API mode.

**Migration:**
- Existing accounts using Brand API will need to be updated with SDK credentials
- Remove `api_key` from TradeLocker account configurations
- Ensure all TradeLocker accounts have `username`, `password`, and `server` configured

## Files Changed

### Backend
- `app/brokers/tradelocker_executor.py` - Removed all Brand API code, SDK-only

### Frontend
- `ui-next/src/lib/brokers/credentialSchemas.ts` - Removed Brand API schema
- `ui-next/src/components/accounts/account-form.tsx` - Removed Brand API logic
- `ui-next/src/app/dashboard/settings/accounts/[id]/settings/page.tsx` - Added refresh/selection UI
- `ui-next/src/lib/api/accounts.ts` - Added refreshBrokerAccounts function

---

**Status:** ✅ Complete - TradeLocker is now SDK-only
