# Deploy and Verify Plan

**Date:** 2026-01-23
**Status:** Ready for Execution (after schema reconciliation)

## Prerequisites

Before deploying, ensure:
- [ ] Schema reconciliation complete (bridge migration 020 applied)
- [ ] ORM models match database schema
- [ ] No API containers are processing requests (or accept brief downtime)

## Phase 1: Pre-Deploy Verification (Read-Only)

### 1.1 Run Database Audit
```bash
cd /home/pharma5/unified_engine
./scripts/db_audit.sh
```

**Expected output:**
- Alembic version: 020 (or 019 if bridge migration not yet applied)
- All tables present
- Signal Intelligence columns correct

### 1.2 Check Docker Services
```bash
docker service ls
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "api|postgres|redis"
```

**Expected:**
- postgres: 1/1 running
- redis: 1/1 running
- api: 1/1 running (or 0/1 if not deployed yet)

### 1.3 Verify Configuration
```bash
# Check docker-stack.yml has correct DATABASE_URL
grep DATABASE_URL docker-stack.yml

# Expected: DATABASE_URL=postgresql://trading_user@postgres:5432/trading_db
```

## Phase 2: Safe Rebuild/Redeploy

### 2.1 Build New API Image
```bash
cd /home/pharma5/unified_engine

# Build the image
docker build -t 192.168.1.254:5000/unified-engine/api:latest -f Dockerfile.stack .

# Push to registry
docker push 192.168.1.254:5000/unified-engine/api:latest
```

### 2.2 Update Stack (Rolling Update)
```bash
# This performs a rolling update - no downtime
docker stack deploy -c docker-stack.yml unified --with-registry-auth

# Or for specific service update:
docker service update --force unified_api
```

### 2.3 Monitor Deployment
```bash
# Watch service update progress
docker service ps unified_api --no-trunc

# Check logs for startup errors
docker service logs unified_api --tail 100 -f
```

## Phase 3: Post-Deploy Smoke Tests

### 3.1 Health Check
```bash
# Direct health check
curl -s http://localhost:3012/health | jq .

# Expected: {"status": "healthy", ...}
```

### 3.2 API Endpoint Tests
```bash
# Root endpoint
curl -s http://localhost:3012/ | jq .

# Docs available
curl -s -o /dev/null -w "%{http_code}" http://localhost:3012/docs
# Expected: 200

# Signal Intelligence endpoint (requires auth)
curl -s http://localhost:3012/api/v1/signal-intelligence/settings | jq .
# Expected: 401 Unauthorized (auth required) - confirms endpoint exists
```

### 3.3 Database Connectivity Test
```bash
# Run from API container
docker exec $(docker ps -q -f "name=api" | head -1) python3 -c "
from app.db.database import engine
from sqlalchemy import text
conn = engine.connect()
result = conn.execute(text('SELECT version_num FROM alembic_version'))
print(f'Alembic version: {result.scalar()}')
conn.close()
"
```

### 3.4 Signal Intelligence Smoke Test
```bash
# Test momentum settings endpoint (requires auth token)
# Replace YOUR_TOKEN with a valid JWT

curl -s -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:3012/api/v1/signal-intelligence/settings | jq .

# Test discard bin (requires auth)
curl -s -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:3012/api/v1/signal-intelligence/discard-bin | jq .
```

### 3.5 Webhook Smoke Test
```bash
# Use existing smoke_webhooks.sh script
./scripts/smoke_webhooks.sh
```

## Phase 4: Rollback Plan

### 4.1 If Deployment Fails

**Immediate rollback:**
```bash
# Rollback to previous image
docker service update --rollback unified_api

# Or deploy previous version
docker service update --image 192.168.1.254:5000/unified-engine/api:previous unified_api
```

### 4.2 If Schema Migration Causes Issues

**Rollback migration:**
```bash
docker exec $(docker ps -q -f "name=api" | head -1) alembic downgrade -1
```

**Manual schema revert (if alembic fails):**
```sql
-- Reverse signal_counters changes
ALTER TABLE signal_counters RENAME COLUMN current_bias TO directional_bias;
ALTER TABLE signal_counters RENAME COLUMN opposite_momentum TO total_signals;
ALTER TABLE signal_counters RENAME COLUMN last_signal_ts TO last_signal_at;
ALTER TABLE signal_counters DROP COLUMN IF EXISTS last8_pattern;
ALTER TABLE signal_counters DROP COLUMN IF EXISTS chop_mode;

-- Reverse discard_bin changes
ALTER TABLE discard_bin RENAME COLUMN raw_signal_json TO raw_payload;
ALTER TABLE discard_bin ALTER COLUMN raw_payload TYPE text;
ALTER TABLE discard_bin RENAME COLUMN normalized_signal_json TO normalized_payload;

-- Re-stamp version
DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num) VALUES ('019');
```

### 4.3 If Redis/NATS Issues
```bash
# Restart services
docker service update --force unified_redis
docker service update --force unified_nats
```

## Verification Checklist

### Must Pass Before Production Use
- [ ] `/health` returns 200 with "healthy" status
- [ ] `/docs` loads Swagger UI
- [ ] Database connection working (alembic version query succeeds)
- [ ] No ERROR logs in api service startup
- [ ] Signal Intelligence endpoints return 401 (auth required) not 500

### Nice to Have
- [ ] Full webhook flow test passes
- [ ] Signal processing works end-to-end
- [ ] Celery workers connected and processing

## Emergency Contacts

If critical issues arise:
1. Check logs: `docker service logs unified_api --tail 500`
2. Check DB: `docker exec <postgres_container> psql -U trading_user -d trading_db`
3. Rollback: `docker service update --rollback unified_api`

## Timeline

| Step | Duration | Cumulative |
|------|----------|------------|
| Pre-deploy verification | 5 min | 5 min |
| Build image | 5-10 min | 15 min |
| Deploy (rolling) | 2-5 min | 20 min |
| Smoke tests | 5 min | 25 min |
| **Total** | | **~25-30 min** |
