# STATE CAPSULE - January 2026

**Generated:** 2026-01-23
**Authoritative snapshot of TradeFlow Unified Engine state**

---

## Version Summary

| Component | Version | Status |
|-----------|---------|--------|
| Signal Intelligence Layer | 1.2 | ✅ COMPLETE |
| Secure Webhooks + Theme | 1.2.1 | ✅ COMPLETE |
| DB Reconciliation | 020 | ✅ COMPLETE |
| Alembic Head | 020 | ✅ VERIFIED |

---

## Current Database Target

### Production (Docker Swarm)

```
Database: PostgreSQL
Host: postgres service (internal overlay network)
Port: 5432
Database Name: trading_db
Credentials: Docker secrets (db_user, db_password)
```

**Connection Pattern:**
```python
# app/db/engine.py reads from settings
DATABASE_URL = os.getenv("DATABASE_URL") or settings.DATABASE_URL
```

### Local Development

```
Database: SQLite (fallback) or PostgreSQL
Path: /home/pharma5/unified_engine/trading_db.db (SQLite)
Or: postgresql://trading_user:xxx@localhost:5432/trading_db (Postgres)
```

**Important:** Always set `DATABASE_URL` explicitly in production.

---

## Deployment Method

### Docker Swarm Stack

| Item | Value |
|------|-------|
| Stack Name | `unified` |
| Stack File | `docker-stack.yml` |
| Deploy Command | `docker stack deploy -c docker-stack.yml unified` |

### Key Services

| Service | Port (External:Internal) | Purpose |
|---------|--------------------------|---------|
| api | 8765 | FastAPI backend |
| ui | 3456 | Next.js frontend |
| postgres | - (internal) | PostgreSQL database |
| redis | - (internal) | Cache + sessions |
| nats | 4223:4222 | Event bus (optional) |
| cloudflared | - | Cloudflare tunnel |

### Required Docker Secrets

| Secret Name | Purpose |
|-------------|---------|
| db_password | PostgreSQL password |
| jwt_secret | JWT signing key |
| fernet_key | Credential encryption |
| cloudflare_token | Tunnel auth |

---

## Verification Commands

### Health Check
```bash
curl http://127.0.0.1:8765/health
# Expected: {"status":"healthy","redis":"connected",...}
```

### Alembic State
```bash
export DATABASE_URL="postgresql://trading_user:xxx@localhost:5432/trading_db"
alembic current
# Expected: 020 (head)

alembic heads
# Expected: 020 (head)
```

### DB Audit Script
```bash
./scripts/db_audit.sh
# Checks: DATABASE_URL, alembic current, table existence, column existence
```

### Import Sanity
```bash
python3 -c "from app.main import app; print('OK')"
# Expected: OK (no import errors)
```

### Unit Tests
```bash
# Signal Intelligence
python3 -m pytest tests/test_signal_intelligence_guard.py -q
# Expected: 13 passed

# Connection tests
python3 -m pytest tests/test_connection_test.py -q
# Expected: 25 passed

# Risk converter tests
python3 -m pytest tests/test_risk_unit_converter.py -q
# Expected: 14 passed
```

---

## Smoke Test Scripts

### Signal Intelligence Guard
```bash
./scripts/smoke_signal_intelligence.sh
```

**Pass Criteria:**
- Settings API returns 200
- Counter increment works
- Discard bin logs entries
- Modal action endpoints respond

### Webhook Tests
```bash
# TradingView endpoint
curl -X POST http://localhost:8765/api/v1/webhooks/tradingview \
  -H "Content-Type: application/json" \
  -d '{"ticker":"EURUSD","action":"buy","quantity":0.01,"price":1.1000,"user_id":1}'

# Secure webhook endpoint (requires valid key)
curl -X POST "http://localhost:8765/api/v1/webhooks/incoming?broker=tradelocker&user=1&key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"ticker":"EURUSD","action":"buy","quantity":0.01}'

# Mismatch test (should return 403)
curl -X POST "http://localhost:8765/api/v1/webhooks/incoming?broker=tradelocker&user=1&key=wrong_key" \
  -H "Content-Type: application/json" \
  -d '{"ticker":"EURUSD","action":"buy"}'
```

---

## Known Constraints (DO NOT CHANGE)

### Architecture Rules

1. **Broker-Agnostic Execution**: No broker-specific branches in routing/dispatch logic
2. **Fail-Open Guard Layer**: Guard errors never block execution; log and continue
3. **Migrations-First**: Never use `create_all()` to fix production schema
4. **No New Services**: Only use existing Swarm stack services

### Security Rules

1. **Webhook Key Validation**: Secure endpoint is fail-closed (403 on mismatch)
2. **Theme Isolation**: Landing page always dark; never reads user preference
3. **Credential Encryption**: All broker credentials use Fernet encryption

### Database Rules

1. **Alembic is source of truth**: All schema changes via migrations
2. **No destructive ops**: No DROP TABLE, DROP DATABASE in migrations
3. **Bridge migrations for drift**: Use additive changes only

---

## File References

### Status Reports
- `STATUS_REPORT_1_2.md` - Signal Intelligence Layer complete status
- `.planning/PATCH_1_2_1_STATUS.md` - Secure webhooks + theme status

### Planning Artifacts
- `.planning/CHANGESET_INDEX.md` - All changes indexed by feature area
- `.planning/DB_AUDIT_REPORT.md` - DB target documentation
- `.planning/ALEMBIC_RECONCILIATION_PLAN.md` - Migration reconciliation steps
- `.planning/DEPLOY_VERIFY_PLAN.md` - Deployment verification commands

### Blueprint
- `.gsd/blueprint/01_SYSTEM_MAP.md` - System architecture with guard layer
- `.gsd/blueprint/05_DATA_FLOWS.md` - Data flows with guard evaluation

### Migrations
- `alembic/versions/018_add_signal_intelligence_tables.py`
- `alembic/versions/019_add_per_broker_webhooks_and_theme.py`
- `alembic/versions/020_bridge_schema_drift_reconciliation.py`

### Scripts
- `scripts/db_audit.sh` - Read-only DB verification
- `scripts/redeploy_unified_engine.sh` - Safe stack redeploy
- `scripts/smoke_signal_intelligence.sh` - Guard layer smoke tests

---

## Quick Recovery Commands

### Restart Backend (Local)
```bash
pkill -f "uvicorn app.main" || true
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8765 > /tmp/unified-backend.log 2>&1 &
```

### Restart UI (Local)
```bash
cd ui-next && PORT=3456 npm run start &
```

### Redeploy Swarm Stack
```bash
./scripts/redeploy_unified_engine.sh
docker stack services unified
```

### Check Logs
```bash
tail -100 /tmp/unified-backend.log | grep -i error
docker service logs unified_api --tail 100
```

---

## Commit History (Relevant)

| Hash | Message |
|------|---------|
| `af1d12c` | chore: reconcile DB + alembic to 020 |
| `2d264e8` | chore: DB alignment + redeploy verification |
| `5d10064` | feat: Patch 1.2.1 secure webhooks + theme |
| `4acc73e` | feat: Complete Signal Intelligence Layer v1.2 |

---

---

## Latest Verification (2026-01-23 18:40 UTC)

### Session: Cursor Agent Phase 0-2
- **Commit:** `aa17b39` phase0: baseline snapshot + session log
- **Branch:** `wire-brokers-tradelocker-projectx-20260122`

### Database & Migrations
- ✅ Alembic current: `020 (head)`
- ✅ Backend import: `from app.main import app` - OK

### Frontend Build
- ✅ Build: `npm run build` - PASSES
- ✅ Server: Port 3456 - VERIFIED (HTTP 200)
- ✅ Script: `ui-next/scripts/run_3456.sh` exists

### Documentation
- ✅ `.planning/GSD_HANDOFF_BUNDLE.md` - Created
- ✅ `.planning/CHANGESET_INDEX.md` - Updated
- ✅ `.planning/CURSOR_SESSION_LOG.md` - Created

### Next Steps
- PHASE 3: Remove broken SSO buttons from auth UI
- PHASE 4: Create broker auth smoke test harness

---

## Previous Verification (2026-01-23 18:06 UTC)

### Database Alignment
- **Alembic Version:** 020 ✅
- **Signal Intelligence Tables:** momentum_settings, signal_counters, discard_bin ✅
- **New Columns:** users.theme, accounts.webhook_key ✅

### Test Results
| Test Suite | Result |
|------------|--------|
| Signal Intelligence Guard | 13/13 passed ✅ |
| Connection Tests | 25/25 passed ✅ |
| Risk Unit Converter | 14/14 passed ✅ |
| **Total** | **52/52 passed** |

### Backend Health
```json
{"status":"healthy","redis":"connected","brokers":{"mt4":true,"mt5":true,"tradelocker":false,"tradovate":false,"projectx":false}}
```

### Known Issues (Pre-existing)
- `SessionFactory` object issue in webhook logging (not introduced by 1.2/1.2.1)
- Broker executors disabled until credentials configured

---

*This capsule represents the authoritative state as of 2026-01-23. Any changes to milestones, patches, or database schema should update this document.*
