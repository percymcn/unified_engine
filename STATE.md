# Unified Trading Engine - Current State

**Snapshot Date:** 2026-01-15
**Swarm Snapshot:** `~/FREEZE/unified_engine_20260115_194932`

---

## Service Status Overview

| Service                  | Replicas | Status         | Notes                           |
|--------------------------|----------|----------------|---------------------------------|
| trading_postgres         | 1/1      | RUNNING        | Healthy, data persisted         |
| trading_redis            | 1/1      | RUNNING        | Healthy                         |
| trading_nats             | 1/1      | RUNNING        | Port 4223:4222, 8223:8223       |
| trading_api              | 0/0      | SCALED TO 0    | Was 1/1, manually paused        |
| trading_ui               | 0/0      | SCALED TO 0    | Was 1/1, manually paused        |
| trading_nginx            | 0/0      | SCALED TO 0    | Was 1/1, manually paused        |
| trading_celery-worker    | 0/0      | SCALED TO 0    | Was 0/1, crash-looping before   |
| trading_celery-beat      | 0/0      | SCALED TO 0    | Not started                     |
| trading_flower           | 0/0      | SCALED TO 0    | Not started                     |
| trading_funnel-automation| 0/0      | SCALED TO 0    | Crash-looping (missing aioredis)|

---

## What is Working

### Infrastructure (Fully Operational)
- **PostgreSQL**: Running, accepting connections, data intact
- **Redis**: Running, ready for cache/celery
- **NATS**: Running, cluster name `trading`, monitoring on 8223

### API (Was Working Before Pause)
- Health endpoint: `/health` returning 200
- Database connection: Verified working
- Redis connection: Verified working
- NATS connection: Optional, graceful fallback working
- Core routers: Auth, accounts, positions, signals all registered

### Known Working Features (from logs)
- JWT authentication flow
- Database table creation (alembic migrations applied)
- Signal processor initialization
- WebSocket heartbeat task starting
- Health monitoring background task

---

## What is Broken / Has Errors

### 1. TradeLocker Broker Executor (Non-Fatal)
**Error:** `TradeLocker initialization failed: 'NoneType' object has no attribute 'encode'`

**Location:** `app/brokers/tradelocker_executor.py`

**Cause:** Missing or null `TRADELOCKER_API_KEY` in environment. The executor tries to encode a None value.

**Impact:** TradeLocker broker unavailable; other brokers unaffected. This is a recurring warning every 60 seconds but does NOT crash the API.

**Fix:** Either:
- Set valid `TRADELOCKER_API_KEY` environment variable
- Or add null-check in executor to skip initialization if key not configured

---

### 2. Funnel Automation Worker (Fatal)
**Error:** `ModuleNotFoundError: No module named 'aioredis'`

**Location:** `app/services/funnel_automation.py:11`

**Cause:** The `aioredis` package is deprecated and not in `requirements.txt`. Modern redis-py includes async support.

**Impact:** funnel-automation service crashes on startup and enters restart loop.

**Fix:** Replace `import aioredis` with `import redis.asyncio as aioredis` or refactor to use `redis-py` async client.

---

### 3. Celery Worker Root Warning (Non-Fatal)
**Warning:** `You're running the worker with superuser privileges: this is absolutely not recommended!`

**Impact:** Security warning only; worker functions correctly.

**Fix:** Add `--uid` flag to celery command or create non-root user in Dockerfile.

---

### 4. Test Suite (11/101 Passing)
**Status:** Most tests failing, likely due to:
- Services not running during test execution
- Missing test fixtures or database state
- Integration tests requiring full stack

**HARNESS_STATE.json:**
```json
{
  "stage": "fixing",
  "progress": { "passing": 11, "total": 101 },
  "last_completed_step": "session_3_failed"
}
```

---

## What is Missing

### Not Implemented / Incomplete
1. **OAuth flows**: Router exists but service integration may be incomplete
2. **Strategy backtesting**: Models exist, execution unclear
3. **Email notifications**: Service stub exists, SMTP not configured
4. **Admin audit logs**: UI component exists, backend endpoint unclear

### Not Deployed
1. **Prometheus/Grafana**: In docker-compose.yml but not in docker-stack.yml
2. **SSL/TLS**: nginx configured for HTTP only currently
3. **Cloudflare tunnel**: Not configured for this stack

---

## Services Scaled to 0 (Paused)

All application services were intentionally scaled to 0 replicas, leaving only infrastructure running:

```bash
# Services paused (replicas = 0):
trading_api
trading_ui
trading_nginx
trading_celery-worker
trading_celery-beat
trading_flower
trading_funnel-automation
```

**Why paused:** Snapshot taken for debugging/migration work.

**To restore:**
```bash
docker service scale trading_api=1
docker service scale trading_ui=1
docker service scale trading_nginx=1
```

---

## Blockers (Priority Order)

### P0 - Must Fix to Run
1. **funnel_automation aioredis import** - Prevents funnel service from starting
2. *(None others - API runs fine)*

### P1 - Should Fix Soon
1. **TradeLocker null key handling** - Noisy logs, should fail gracefully
2. **Celery root user warning** - Security best practice
3. **Test suite failures** - 90 tests failing

### P2 - Nice to Have
1. **NATS connection resilience** - Currently falls back to logging, could add reconnect
2. **Prometheus metrics** - Not deployed in swarm stack

---

## Environment Variables Status

| Variable              | Required | Set | Notes                              |
|-----------------------|----------|-----|------------------------------------|
| DATABASE_URL          | Yes      | Yes | PostgreSQL connection working      |
| REDIS_URL             | Yes      | Yes | Redis connection working           |
| SECRET_KEY            | Yes      | Yes | Set (should verify strength)       |
| NATS_URL              | No       | No  | Falls back to logging mode         |
| TRADELOCKER_API_KEY   | No       | No  | Causes warning but not fatal       |
| TRADOVATE_USER_ID     | No       | No  | Executor disabled                  |
| PROJECTX_API_TOKEN    | No       | No  | Executor disabled                  |

---

## Ports in Use (When Running)

| Port  | Service       | Protocol | Status      |
|-------|---------------|----------|-------------|
| 3012  | trading_api   | HTTP     | Swarm port  |
| 3411  | trading_ui    | HTTP     | Swarm port  |
| 3013  | trading_nginx | HTTP     | Swarm port  |
| 4223  | trading_nats  | TCP      | ACTIVE      |
| 8223  | trading_nats  | HTTP     | ACTIVE      |
| 5558  | trading_flower| HTTP     | Swarm port  |

---

## Quick Recovery Commands

```bash
# Check current state
docker service ls | grep trading_

# Scale up API + UI
docker service scale trading_api=1 trading_ui=1

# Check API health
curl http://localhost:3012/health

# Check logs
docker service logs trading_api --tail 50

# Scale up full stack (excluding broken funnel)
docker service scale trading_api=1 trading_ui=1 trading_nginx=1 trading_celery-worker=1
```

---

## Next Actions

1. Fix `aioredis` import in `funnel_automation.py`
2. Add null-check for TradeLocker API key
3. Scale up services: api, ui, nginx
4. Verify health endpoints
5. Run smoke tests
6. Fix remaining test failures

---

*Last Updated: 2026-01-15*
