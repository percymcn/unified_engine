# GSD Report: Anchor Postgres + Lock Ports

**Date:** 2026-01-23 19:22 UTC
**Mission:** Re-anchor TradeFlow to Canonical Postgres + Lock Ports + Stop ENV/DB Drift
**Branch:** wire-brokers-tradelocker-projectx-20260122

---

## Summary

Fixed environment drift where tools sometimes used SQLite/port 8000 instead of canonical Postgres/port 8765. Established single source of truth for all runtime settings.

---

## Root Cause

1. `.env` had `DATABASE_URL=sqlite:///...` instead of Postgres
2. `.env` had `PORT=8000` instead of 8765
3. Scripts had inconsistent port defaults (3012, 8000, 8765)

---

## Phases Completed

### PHASE A: Rehydrate + Evidence ✅
- Captured snapshot: git status, Settings, listening ports
- Identified all places DB/ports were set incorrectly
- Debug file: `.planning/debug/postgres-ports-drift.md`

### PHASE B: Enforce Canonical Runtime Settings ✅
- Created `scripts/local_up_postgres.sh`:
  - Kills stale processes on 8765/3456/8000/3000
  - Exports DATABASE_URL for Postgres
  - Starts backend on 0.0.0.0:8765
  - Starts UI on 0.0.0.0:3456
  - Prints LAN URLs for iPhone testing
- Fixed `.env`:
  - DATABASE_URL → postgresql://trading_user:trading_password@localhost:5432/trading_db
  - PORT → 8765
- Updated all scripts to default to port 8765

### PHASE C: Database Consistency ✅
- Confirmed Alembic at head (020)
- Postgres schema matches models
- Created `docs/DB_POLICY.md` documenting:
  - Canonical Postgres on 5432
  - SQLite deprecated artifact policy
  - Canonical ports table

### PHASE D: UI ↔ Backend Broker Contract Alignment ✅
- UI schemas in `credentialSchemas.ts` already match backend
- Added documentation reference to `/api/v1/brokers/contracts` API
- TradeLocker SDK/Brand API modes documented

### PHASE E: Billing Upgrade Flow ✅
- Verified `/api/billing/plans` returns tiers without auth
- UI proxy defaults to `BACKEND_URL=http://localhost:8765`
- Upgrade page renders 4 paid tiers correctly

### PHASE F: Commits + Report ✅
Three logical commits created:
1. `b1eed05` - feat(local): add local_up_postgres.sh + DB policy docs
2. `0b75c9d` - fix(scripts): normalize all scripts to canonical port 8765
3. `c91e9cf` - docs(ui): add backend contract API reference to credentialSchemas

---

## Files Changed

### Created
| File | Purpose |
|------|---------|
| `scripts/local_up_postgres.sh` | Canonical local development startup |
| `docs/DB_POLICY.md` | Database policy documentation |
| `.planning/debug/postgres-ports-drift.md` | Debug session notes |

### Modified
| File | Change |
|------|--------|
| `.env` (local only) | DATABASE_URL → Postgres, PORT → 8765 |
| `scripts/smoke_signal_intelligence.sh` | Default port → 8765 |
| `scripts/smoke_user_flow.sh` | Default port → 8765 |
| `scripts/smoke_webhooks.sh` | Default port → 8765 |
| `scripts/verify_green.sh` | Default port → 8765 |
| `scripts/verify_stack.sh` | Default port → 8765 |
| `ui-next/src/lib/brokers/credentialSchemas.ts` | Added API reference docs |

---

## Canonical Settings

| Setting | Value |
|---------|-------|
| DATABASE_URL | `postgresql://trading_user:trading_password@localhost:5432/trading_db` |
| API Port | 8765 |
| UI Port | 3456 |
| Postgres Port | 5432 |
| Redis Port | 6379 |

---

## iPhone Testing URLs

| Service | Local | LAN |
|---------|-------|-----|
| API | http://localhost:8765 | http://192.168.1.254:8765 |
| UI | http://localhost:3456 | http://192.168.1.254:3456 |

---

## Smoke Check Results

```
✅ Backend health: http://localhost:8765/health
✅ Postgres: accepting connections on 5432
✅ Alembic: at head (020)
✅ Billing plans: 5 tiers returned (unauthenticated)
✅ Broker contracts: 6 brokers returned
```

---

## Quick Start

```bash
# Start canonical local stack
./scripts/local_up_postgres.sh

# Or manually:
export DATABASE_URL="postgresql://trading_user:trading_password@localhost:5432/trading_db"
uvicorn app.main:app --host 0.0.0.0 --port 8765 --reload
```

---

*Generated: 2026-01-23 19:22 UTC*
