# GSD Report: Broker Contracts & Billing Fix

**Date:** 2026-01-23 18:35 UTC
**Mission:** v1.2 Rehydrate + Normalize Broker Contracts + Fix Upgrade/Billing Drift
**Branch:** wire-brokers-tradelocker-projectx-20260122

---

## Summary

This session established a single source of truth for broker credential schemas and fixed the billing plans endpoint that was blocking unauthenticated users from viewing pricing.

---

## Phases Completed

### PHASE 0: Rehydrate Snapshot ✅
- Verified git status (clean working tree)
- Confirmed DB at Alembic migration 020
- Reviewed existing broker executors

### PHASE 1: Broker Contracts Source of Truth ✅
- Created `docs/BROKER_CONTRACTS.md` - human-readable documentation with official API citations
- Created `app/contracts/brokers.json` - machine-readable contract for 6 brokers:
  - TradeLocker (SDK + Brand API modes)
  - ProjectX (API key auth)
  - TopStep (alias of ProjectX)
  - Tradovate (OAuth + password modes)
  - MT4 (MetaAPI + Manager modes)
  - MT5 (MetaAPI + Manager modes)

### PHASE 2: Contracts Endpoint ✅
- Created `app/routers/broker_contracts.py`:
  - `GET /api/v1/brokers/contracts` - Public endpoint returning all credential schemas
  - `GET /api/v1/brokers/status` - Auth-required endpoint for config status
- Registered router in `app/main.py`

### PHASE 3: Billing Plans Fix ✅
- Added `get_current_user_optional()` to `app/routers/auth.py`
- Updated `GET /api/billing/plans` to work without authentication
- Pricing page now loads for unauthenticated users

### PHASE 4: Local Verification ✅
- Backend running on port 8765
- Verified `/api/v1/brokers/contracts` returns all 6 brokers
- Verified `/api/billing/plans` returns 5 tiers without auth
- Verified `/api/v1/brokers/status` properly requires auth (401)

### PHASE 5: Commits ✅
Three logical commits created:
1. `a508b6c` - docs(brokers): add canonical broker contracts documentation
2. `8098324` - feat(api): add /api/v1/brokers/contracts endpoint
3. `6cbf86a` - fix(billing): allow unauthenticated access to /api/billing/plans

---

## Files Changed

### Created
| File | Purpose |
|------|---------|
| `docs/BROKER_CONTRACTS.md` | Human-readable credential documentation |
| `app/contracts/brokers.json` | Machine-readable broker schemas |
| `app/routers/broker_contracts.py` | New API router for broker contracts |

### Modified
| File | Change |
|------|--------|
| `app/main.py` | Import + register broker_contracts_router |
| `app/routers/auth.py` | Add get_current_user_optional() |
| `app/routers/billing.py` | Use optional auth for /plans endpoint |

---

## API Endpoints Added

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /api/v1/brokers/contracts` | None | Returns broker credential schemas |
| `GET /api/v1/brokers/status` | Required | Returns broker configuration status |

---

## Verification Results

```
✅ /health                    → healthy
✅ /api/v1/brokers/contracts  → 6 brokers returned (public)
✅ /api/v1/brokers/status     → 401 Unauthorized (correct)
✅ /api/billing/plans         → 5 tiers returned (public)
```

---

## Next Steps

1. UI can now fetch `/api/v1/brokers/contracts` to dynamically render broker forms
2. Pricing page should fetch `/api/billing/plans` on mount (no auth required)
3. Consider migrating `ui-next/src/lib/brokers/credentialSchemas.ts` to fetch from API

---

*Generated: 2026-01-23 18:35 UTC*
