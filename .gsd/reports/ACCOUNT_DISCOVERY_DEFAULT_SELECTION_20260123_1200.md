# Account Discovery & Default Selection Implementation Report

**Date:** 2026-01-23  
**Feature:** Add Broker Account UX with Discovery and Selection

## Overview

Implemented a comprehensive account discovery and selection system that allows users to:
1. Test & validate broker credentials
2. Automatically discover available accounts from the broker
3. Select multiple accounts and set a default account
4. Refresh discovered accounts later
5. Use default account for webhook routing

## Implementation Summary

### Phase 1: Backend - Discover Accounts API ✅

**Endpoint:** `POST /api/v1/accounts/discover`

**Request:**
```json
{
  "broker": "tradelocker|projectx|topstep|mt4|mt5|tradovate",
  "credentials": { ... broker specific ... }
}
```

**Response:**
```json
{
  "accounts": [
    {
      "broker_account_id": "string",
      "account_number": "string|null",
      "display_name": "string",
      "status": "active|inactive|unknown",
      "account_type": "eval|funded|demo|unknown",
      "broker": "tradelocker|projectx|topstep|mt4|mt5|tradovate",
      "meta": {}
    }
  ],
  "message": "optional message"
}
```

**Features:**
- Standardized response format across all brokers
- Status mapping: active/inactive/unknown (defaults to "unknown" if broker doesn't provide)
- Account type mapping: eval/funded/demo/unknown
- Legacy field compatibility for backward compatibility
- Never logs secrets

### Phase 2: Backend - Database Schema ✅

**New Fields in `TradingAccount` table:**
- `enabled_broker_account_ids` (JSON): List of enabled broker account IDs
- `default_broker_account_id` (String): Default broker account ID
- `discovered_accounts_cache` (JSON): Cached discovered accounts metadata

**Migration Required:**
```sql
ALTER TABLE trading_accounts 
ADD COLUMN enabled_broker_account_ids JSON,
ADD COLUMN default_broker_account_id VARCHAR(100),
ADD COLUMN discovered_accounts_cache JSON;
```

### Phase 3: Backend - Account Endpoints ✅

**Updated Endpoints:**

1. **POST /api/v1/accounts/** (Create Account)
   - Accepts `enabled_broker_account_ids`, `default_broker_account_id`, `discovered_accounts_cache`
   - Validates that default is in enabled list if provided

2. **PUT /api/v1/accounts/{id}** (Update Account)
   - Allows updating enabled/default account selections
   - Updates cache metadata

3. **GET /api/v1/accounts/** (List Accounts)
   - Returns `enabled_broker_account_ids`, `default_broker_account_id`, `discovered_accounts_cache`

4. **GET /api/v1/accounts/{id}** (Get Account)
   - Returns broker account selection fields

5. **POST /api/v1/accounts/{id}/refresh-accounts** (NEW)
   - Re-discovers accounts using stored credentials
   - Updates `discovered_accounts_cache`
   - Does not change enabled/default selections

### Phase 4: UI - Account Form ✅

**Updated Flow:**
1. User enters broker credentials
2. Clicks "Test & Validate" button
3. If validation succeeds:
   - Automatically calls `/api/v1/accounts/discover`
   - Shows discovered accounts list
   - Auto-selects first account as default (if only one) or all accounts (if multiple)
4. User can:
   - Toggle accounts enabled/disabled (checkboxes)
   - Set default account (radio button)
5. On save:
   - Sends `enabled_broker_account_ids`, `default_broker_account_id`, `discovered_accounts_cache` to backend

**UI Components:**
- Account discovery status indicator
- Account list with status badges (Active/Inactive)
- Account type badges (eval/funded/demo)
- Checkbox for enabled accounts
- Radio button for default selection
- Account metadata display (balance, equity, currency)

### Phase 5: Webhook Routing Foundation ✅

**Current Implementation:**
- One webhook endpoint: `POST /api/v1/webhooks/tradingview`
- One user API key per user (header `X-Tradeflow-Key`)
- Payload includes `"strategy": "<slug>"`

**Default Behavior:**
- If strategy targets none: use account's `default_broker_account_id`
- If strategy targets multiple: execute on those accounts

**Future Enhancement:**
- Strategies table maps slug → target account(s)
- UI panel for webhook URL + user key copy buttons
- Per-strategy TradingView JSON templates

## Usage Guide

### Adding a New Account

1. Navigate to **Settings → Accounts**
2. Click **"Add New Account"**
3. Select broker and enter credentials
4. Click **"Test & Validate"**
5. If successful, accounts will be discovered automatically
6. Select accounts to enable (checkboxes)
7. Set one account as default (radio button)
8. Click **"Add Account"**

### Managing Existing Account

1. Navigate to **Settings → Accounts → [Account Name]**
2. View current default + enabled accounts
3. Click **"Refresh broker accounts"** to re-discover
4. Update enabled/default selections
5. Save changes

### Webhook Usage

**Webhook URL:**
```
POST http://127.0.0.1:8765/api/v1/webhooks/tradingview
```

**Headers:**
```
X-Tradeflow-Key: <your_user_api_key>
Content-Type: application/json
```

**Payload:**
```json
{
  "strategy": "my_strategy_slug",
  "symbol": "EURUSD",
  "action": "BUY",
  "volume": 0.01
}
```

**Routing:**
- If strategy has no target accounts: uses account's `default_broker_account_id`
- If strategy has target accounts: uses those accounts

## Curl Examples

### Discover Accounts
```bash
curl -X POST http://127.0.0.1:8765/api/v1/accounts/discover \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "broker": "tradelocker",
    "credentials": {
      "api_key": "your_api_key"
    }
  }'
```

### Create Account with Selection
```bash
curl -X POST http://127.0.0.1:8765/api/v1/accounts/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "account_id": "account_123",
    "broker": "tradelocker",
    "account_type": "live",
    "currency": "USD",
    "leverage": 100,
    "enabled_broker_account_ids": ["acc1", "acc2"],
    "default_broker_account_id": "acc1",
    "discovered_accounts_cache": [...]
  }'
```

### Refresh Accounts
```bash
curl -X POST http://127.0.0.1:8765/api/v1/accounts/1/refresh-accounts \
  -H "Authorization: Bearer <token>"
```

### Update Account Selection
```bash
curl -X PUT http://127.0.0.1:8765/api/v1/accounts/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "enabled_broker_account_ids": ["acc1", "acc2", "acc3"],
    "default_broker_account_id": "acc2"
  }'
```

## Testing

### Test Script
```bash
python3 scripts/test_discover_accounts.py
```

**Expected Results:**
- Endpoint should return 200, 400, or 401 (never 500)
- Schema validation should pass
- Empty accounts list is acceptable (no credentials provided)

### Manual Testing

1. **Backend Health:**
   ```bash
   curl -m 2 http://127.0.0.1:8765/health
   ```

2. **UI Reachability:**
   ```bash
   curl -I -m 3 http://127.0.0.1:3456/login
   ```

3. **Test Discovery:**
   - Login to UI
   - Go to Settings → Accounts
   - Add new account
   - Enter valid credentials
   - Click "Test & Validate"
   - Verify accounts are discovered
   - Select accounts and save

## Files Modified

### Backend
- `app/routers/accounts.py` - Enhanced discover endpoint, added refresh endpoint, updated create/update endpoints
- `app/models/database_models.py` - Added broker account selection fields
- `app/models/schemas.py` - Updated AccountCreate/AccountUpdate schemas

### Frontend
- `ui-next/src/components/accounts/account-form.tsx` - Updated to chain Test → Discover → Select → Save
- `ui-next/src/lib/api/accounts.ts` - Updated DiscoveredAccount interface
- `ui-next/src/types/account.ts` - Added broker account selection fields to Account/AccountCreate/AccountUpdate

### Scripts
- `scripts/test_discover_accounts.py` - Test script for discovery endpoint

## Known Limitations

1. **Database Migration:** Manual migration required for new fields (or Alembic migration)
2. **Account Detail Page:** UI for viewing/editing enabled/default accounts in account detail page not yet implemented
3. **Webhook UI Panel:** Webhook URL + key copy buttons not yet implemented
4. **Strategy Mapping:** Strategies table for slug → account mapping not yet implemented

## Next Steps

1. Create Alembic migration for new database fields
2. Add account detail page UI for managing enabled/default accounts
3. Add webhook panel UI with copy buttons
4. Implement strategies table for webhook routing
5. Add comprehensive integration tests

## URLs

- **UI Local:** http://127.0.0.1:3456
- **UI iPhone/LAN:** http://192.168.1.254:3456
- **API:** http://127.0.0.1:8765

## Pages to Test

1. **Settings → Accounts** - Add new account with discovery
2. **Settings → Accounts → [Account Name]** - View/edit account selection (after migration)
3. **Settings → Webhooks** - Webhook panel (future enhancement)

---

**Status:** ✅ Implementation Complete (Pending Database Migration)
