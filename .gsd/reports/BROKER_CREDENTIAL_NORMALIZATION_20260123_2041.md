# Broker Credential Normalization Report

**Date:** 2026-01-23 20:41  
**Mission:** Normalize platform so GET /api/v1/brokers/contracts is the single source of truth

## Summary

Normalized broker credential requirements across UI, ENV docs, and doctor script to match the canonical contract at `/api/v1/brokers/contracts`.

## Changes Made

### 1. UI Alignment (`ui-next/src/lib/brokers/credentialSchemas.ts`)

**Removed:**
- `environment_url` field from TradeLocker schema (not present in contract)

**Fixed:**
- TradeLocker `environment` field type: changed from `string` to `select` with options (demo/live) to match contract

### 2. ENV Doctor Script (`scripts/doctor_env.sh`)

**Removed:**
- `MT4_MANAGER_HOST` and `MT4_MANAGER_PORT` from MT4 Manager API check (platform defaults, not user credentials)
- `MT5_MANAGER_HOST` and `MT5_MANAGER_PORT` from MT5 Manager API check (platform defaults, not user credentials)
- `TRADOVATE_CLIENT_ID` and `TRADOVATE_CLIENT_SECRET` from Tradovate OAuth check (platform config, not user-provided credentials)

**Updated:**
- Tradovate section now only checks Password mode (OAuth doesn't require user-provided credentials)

### 3. ENV Reference Documentation (`docs/ENV_REFERENCE.md`)

**Updated:**
- MT4/MT5 Manager API section: Removed HOST/PORT, added note that these are platform-level defaults
- Tradovate section: Clarified that OAuth mode doesn't require user-provided credentials (handled via redirect), removed OAuth env var requirements

## Contract Analysis

The contract (`app/contracts/brokers.json`) defines user-provided credentials only:

- **TradeLocker**: SDK mode requires `username`, `password`, `server`; Brand API requires `api_key`; `environment` is optional
- **ProjectX**: Requires `username`, `api_key`
- **Tradovate**: OAuth mode (no user fields), Password mode requires `user_id`, `password`; optional: `environment`, `app_id`, `cid`, `sec`
- **MT4/MT5**: MetaAPI mode requires `metaapi_token`, `metaapi_account_id`; Manager mode requires `manager_login`, `manager_password`

## Verification

### Commands Run

1. **Preflight Gate:**
   ```bash
   ./scripts/gsd_preflight_gate.sh
   ```
   ✅ Passed - All invariants verified

2. **Contract Analysis:**
   ```bash
   python3 -c "import json; ..." # Analyzed contract structure
   ```
   ✅ Contract structure verified

3. **Postflight Gate:**
   ```bash
   ./scripts/gsd_postflight_gate.sh
   ```
   ✅ Passed - Backend healthy, contracts endpoint working

4. **ENV Doctor:**
   ```bash
   ./scripts/doctor_env.sh
   ```
   ✅ Updated structure verified - no HOST/PORT for Manager API, no OAuth check for Tradovate

### Results

- ✅ Contracts endpoint returns expected structure
- ✅ UI schemas match contract (after fixes)
- ✅ ENV doctor matches contract (after fixes)
- ✅ ENV reference docs match contract (after fixes)
- ✅ Backend health check passed
- ✅ All critical endpoints responding

## Files Modified

1. `ui-next/src/lib/brokers/credentialSchemas.ts` - Removed `environment_url`, fixed `environment` type
2. `scripts/doctor_env.sh` - Removed platform-level config checks
3. `docs/ENV_REFERENCE.md` - Updated to match contract exactly

## Commit

```
feat(gsd): normalize broker credential requirements to contract
```

## Next Steps

The platform now has a single source of truth for broker credential requirements:
- UI forms should use `/api/v1/brokers/contracts` to dynamically render fields
- ENV docs reference the contract for user-provided credentials
- Platform-level config (hosts, ports, OAuth client IDs) is separate from user credentials

---

*Report generated: 2026-01-23 20:41*
