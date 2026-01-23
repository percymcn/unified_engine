# PATCH 1.2.1 STATUS REPORT

**Date:** January 22, 2026  
**Milestone:** TradeFlow VSD Patch 1.2.1 — Secure Broker Webhooks + Theme Isolation  
**Status:** ✅ **COMPLETE**

## Executive Summary

Patch 1.2.1 implements per-broker secure webhooks and theme isolation for the dashboard. Each broker connection now has its own unique webhook key, preventing cross-broker signal routing. Theme preferences apply only to dashboard routes; the landing page always remains dark.

## Features Completed

### ✅ Per-Broker Secure Webhooks

1. **Database Migration (019)**
   - Added `users.theme` column (VARCHAR(10), default 'system')
   - Added `trading_accounts.webhook_key` column (TEXT, unique, nullable)
   - Created unique index on `webhook_key` (allows NULL)

2. **Webhook Key Generation**
   - Auto-generates webhook key on account creation: `webhook_<broker>_user<userId>_<random>`
   - Auto-generates on account connect/reconnect if missing
   - Format: `webhook_tradelocker_user1234_a8f3c1`

3. **Secure Webhook Endpoint (`/api/v1/webhooks/incoming`)**
   - Requires: `broker` (query), `user` (query), `key` (query or header `X-TradeFlow-Webhook-Key`)
   - Validates broker + user + key match against `TradingAccount` table
   - Routes signal ONLY to matching broker account
   - Mismatched keys return 403 and log to `discard_bin` with reason `broker_mismatch`
   - Fail-closed for key mismatches (no execution)

4. **UI: Copy Webhook Button**
   - Added to account cards in Dashboard → Settings → Accounts
   - Shows truncated webhook URL
   - Copy button copies full URL: `{BASE_URL}/api/v1/webhooks/incoming?broker={broker}&user={userId}&key={webhook_key}`
   - Tooltip: "Paste this only in TradingView for {broker}"

### ✅ Theme Isolation

1. **Database**
   - `users.theme` column stores preference (system/dark/light)

2. **Theme Provider (`ui-next/src/providers/theme-provider.tsx`)**
   - Checks route pathname
   - Dashboard routes (`/dashboard/*` or `/app/*`): Uses theme provider with cookie support
   - Landing/public routes: Forces dark theme, ignores cookie

3. **UI: Appearance Settings**
   - Added to Dashboard → Settings → Preferences
   - Theme selector: Light / Dark / System
   - Saves to `users.theme` via API
   - Updates cookie immediately
   - Note: "Landing page always remains dark"

4. **API Endpoints**
   - `GET /api/users/me/preferences` - Returns theme
   - `PUT /api/users/me/preferences` - Updates theme (validates: system/dark/light)

## Files Changed

### Backend
- `alembic/versions/019_add_per_broker_webhooks_and_theme.py` (NEW)
- `app/models/models.py` - Added `theme` column to User model
- `app/models/database_models.py` - Added `webhook_key` column to TradingAccount model
- `app/models/schemas.py` - Added `theme` to PreferencesResponse/Update
- `app/routers/webhooks_secure.py` (NEW) - Secure per-broker webhook endpoint
- `app/routers/accounts.py` - Added webhook_key to account responses, webhook key generation helper
- `app/routers/users.py` - Added theme handling to preferences endpoints
- `app/application/use_cases/manage_accounts.py` - Webhook key generation on create/connect
- `app/main.py` - Registered `webhooks_secure_router`

### Frontend
- `ui-next/src/providers/theme-provider.tsx` - Route-based theme isolation
- `ui-next/src/app/dashboard/settings/preferences/page.tsx` - Added Appearance section
- `ui-next/src/components/accounts/account-card.tsx` - Added Copy Webhook button
- `ui-next/src/types/account.ts` - Added `webhook_key` and `user_id` to Account interface

## Verification Commands

```bash
# 1. Check migration status
alembic current
alembic upgrade head

# 2. Test import sanity
python3 -c "from app.main import app; print('OK')"

# 3. Test webhook endpoint (requires valid broker/user/key)
curl -X POST "http://localhost:8765/api/v1/webhooks/incoming?broker=tradelocker&user=1&key=webhook_tradelocker_user1_abc123" \
  -H "Content-Type: application/json" \
  -d '{"ticker":"EURUSD","action":"buy","quantity":0.01}'

# 4. Test webhook mismatch (should return 403)
curl -X POST "http://localhost:8765/api/v1/webhooks/incoming?broker=tradelocker&user=1&key=wrong_key" \
  -H "Content-Type: application/json" \
  -d '{"ticker":"EURUSD","action":"buy"}'

# 5. Test theme preference API
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8765/api/v1/users/me/preferences

curl -X PUT -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"theme":"dark"}' \
  http://localhost:8765/api/v1/users/me/preferences
```

## Rollback Instructions

```bash
# Rollback migration
alembic downgrade 018

# Remove files
rm alembic/versions/019_add_per_broker_webhooks_and_theme.py
rm app/routers/webhooks_secure.py

# Revert code changes
git revert <commit-hash>
```

## Deployment Checklist

- [ ] Apply migration: `alembic upgrade head`
- [ ] Restart backend service
- [ ] Verify webhook endpoint accessible
- [ ] Test webhook key generation on account create/connect
- [ ] Verify theme isolation (dashboard changes, landing stays dark)
- [ ] Test webhook mismatch returns 403
- [ ] Verify discard_bin logs broker_mismatch entries

## Notes

- Webhook keys are auto-generated on account creation/connection
- Old accounts without webhook keys will generate them on next connect
- Theme preference persists across sessions via database + cookie
- Landing page theme is hardcoded dark and cannot be changed
