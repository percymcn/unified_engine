# Deployment Checklist - Database Migration Fix
**Created:** 2026-01-11 04:40 UTC
**Priority:** HIGH - Blocks 10-20 tests
**Issue:** FIX_PLAN.md #3 - Database Migrations Not Applied

---

## Summary

A critical fix has been applied to `app/main.py` that will enable database table creation and unlock authentication endpoints. The fix is code-complete but cannot be deployed due to operational restrictions.

**Expected Impact:** 10-20 additional tests passing (from 11/101 to 20-30/101)

---

## Pre-Deployment Steps

### Step 1: Clear Git Lock
```bash
cd /home/pharma5/unified_engine
rm -f .git/index.lock
```

**Verification:**
```bash
git status  # Should not show "fatal: Unable to create index.lock"
```

### Step 2: Review Changes
```bash
git diff app/main.py
```

**Expected Diff:**
```diff
# Core imports
from app.core.config import settings
from app.core.websocket_manager import ws_manager as websocket_manager
from app.services.signal_processor import signal_processor
from app.cache.redis_client import redis_client
from app.db.database import engine, Base

+# Import models so SQLAlchemy can create tables
+# This must be imported before Base.metadata.create_all()
+from app.models import models, enhanced_models  # noqa: F401
+
# Router imports
```

### Step 3: Commit Changes
```bash
git add app/main.py
git commit -m "Fix database migrations: Import models before create_all()

- Import app.models.models and app.models.enhanced_models in main.py
- Ensures SQLAlchemy knows about all tables when Base.metadata.create_all() is called
- Fixes Issue #3 from FIX_PLAN.md: Database Migrations Not Applied
- Should resolve 500 errors on /api/v1/auth/register and other endpoints

Impact: Expected to enable 10-20 additional passing tests

Tables that will be created:
From models.py:
  - users, user_sessions, accounts, trades, positions, orders
  - signals, webhook_logs, execution_logs, system_configs
  - alerts, api_keys, strategies, account_strategies

From enhanced_models.py:
  - organizations, roles, permissions, user_subscriptions
  - oauth_accounts, notifications, notification_preferences
  - audit_logs, usage_metrics
"
```

---

## Deployment Steps

### Step 4: Rebuild Docker Image
```bash
docker build -t 192.168.1.254:5000/unified-engine/api:latest -f Dockerfile.stack .
```

**This build includes TWO fixes:**
1. ✅ aiohttp==3.9.1 dependency (from requirements.txt - previous session)
2. ✅ Model imports (from app/main.py - this session)

**Expected Duration:** 30-60 minutes (context size is 315MB)

**Monitor Progress:**
```bash
# In another terminal:
docker images | grep unified-engine/api
# Watch for new image SHA
```

### Step 5: Push to Registry
```bash
docker push 192.168.1.254:5000/unified-engine/api:latest
```

### Step 6: Update Services
```bash
# Update API service first
docker service update --force trading_api

# Wait for API to stabilize (check logs)
docker service logs trading_api --tail 50 --follow

# Look for these log messages:
# "✅ Database tables created"
# "✅ Redis connected"
# "✅ Signal processor initialized"
# "🎉 Unified Trading Engine started successfully!"
```

### Step 7: Update Dependent Services
```bash
# Update funnel-automation (needs aiohttp fix)
docker service update --force trading_funnel-automation

# Update celery workers
docker service update --force trading_celery-worker

# Update celery beat
docker service update --force trading_celery-beat

# Update flower
docker service update --force trading_flower
```

---

## Verification Steps

### Test 1: Check Service Health
```bash
docker service ls | grep trading
```

**Expected Output:**
```
trading_api                 1/1    (was 1/1)
trading_funnel-automation   1/1    (was 0/1) ← SHOULD START NOW
trading_celery-worker       1/1    (was 0/1) ← MAY STILL NEED FIX
trading_celery-beat         1/1    (was 0/1)
trading_flower              1/1    (was 0/1)
trading_postgres            1/1
trading_redis               1/1
trading_nats                1/1
trading_nginx               1/1
trading_ui                  1/1
```

### Test 2: Verify Database Tables Created
```bash
# Check API logs for table creation
docker service logs trading_api --tail 100 | grep -i "table\|database"
```

**Expected:** Should see SQLAlchemy CREATE TABLE statements or "Database tables created"

### Test 3: Test Authentication Endpoint
```bash
# Test user registration
curl -X POST http://192.168.1.254:3012/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "username": "testuser"
  }'
```

**Before Fix:**
```json
{
  "error": "Internal server error",
  "status_code": 500,
  "path": "/api/v1/auth/register"
}
```

**After Fix (Expected):**
```json
{
  "id": 1,
  "email": "test@example.com",
  "username": "testuser",
  "created_at": "2026-01-11T04:45:00Z"
}
```
OR at minimum, a different error (like "email already exists") proving the database is working.

### Test 4: Test Login Endpoint
```bash
curl -X POST http://192.168.1.254:3012/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

**Expected:** Should return JWT token or auth error (not 500)

### Test 5: Check Funnel-Automation Service
```bash
docker service ps trading_funnel-automation --no-trunc
docker service logs trading_funnel-automation --tail 30
```

**Before Fix:**
```
ModuleNotFoundError: No module named 'aiohttp'
```

**After Fix (Expected):**
No aiohttp errors, service should stay running

---

## Expected Test Results

### Tests That Should Pass After Deployment

**Authentication (Tests #12-17):**
- ✅ #12: User registration endpoint functional
- ✅ #13: User login returns JWT token
- ✅ #14: JWT token authentication works
- ✅ #15: Token refresh extends session
- ✅ #16: Logout invalidates session
- ✅ #17: Protected endpoints reject unauthenticated requests

**Database (Test #12):**
- ✅ #12: Database has core tables created

**Funnel-Automation (Test #10):**
- ✅ #10: Funnel-automation service running without crashes

**Total Expected:**
- Before: 11/101 tests passing
- After: 20-30/101 tests passing
- Gain: +9 to +19 tests

---

## Rollback Plan (If Deployment Fails)

### If API Fails to Start
```bash
# Roll back to previous image SHA
docker service update --image 192.168.1.254:5000/unified-engine/api@sha256:95550960294a trading_api

# Or roll back git commit
git revert HEAD
# Then rebuild and redeploy
```

### If Database Issues Persist
```bash
# Check what tables exist
docker exec $(docker ps -q -f name=trading_postgres) \
  psql -U trading_user -d trading_db -c "\dt"

# If tables exist but queries fail, may need to:
# 1. Check Alembic migration state
# 2. Manually run migrations
# 3. Check for schema conflicts
```

---

## Known Issues to Monitor

### Issue 1: Alembic Multiple Heads
The alembic migrations have a branching issue (both start with down_revision=None):
- 001_add_strategy_support.py
- 002_add_strategy_support_manual.py

**Action After Tables Created:**
```bash
# Mark current state as migration head
docker exec $(docker ps -q -f name=trading_api) alembic stamp head
# This may still fail, but tables will already exist from create_all()
```

### Issue 2: Celery Worker May Still Exit
The celery-worker service may still exit with "Complete" status. This is a separate issue from the database fix and can be addressed in next session.

**Investigation Needed:**
- Check if tasks are registered correctly
- Try `--pool=solo` flag
- Check Celery logs for startup errors

### Issue 3: OpenAPI Docs Still Disabled
The /docs and /redoc endpoints will still return 404 because ENVIRONMENT=production.

**Optional Fix:**
```yaml
# In docker-stack.yml, change:
environment:
  - ENVIRONMENT=development  # was: production
```
Then redeploy. But this is low priority.

---

## Success Criteria

✅ API service starts without errors
✅ Database tables created (23+ tables)
✅ Authentication endpoints return 200/201/400 (not 500)
✅ Funnel-automation service running (no aiohttp error)
✅ At least 5 new tests passing

**Target:** 20-30/101 tests passing

---

## Next Steps After Successful Deployment

1. Run full test suite to update feature_list.json
2. Mark passing tests as "passes": true
3. Update SESSION_SUMMARY.md with results
4. Commit updated feature_list.json
5. Address next priority issue from FIX_PLAN.md:
   - Issue #4: Celery Workers (if still failing)
   - Issue #5: Frontend API URL
   - Issue #6: TradeLocker Broker

---

## Contact Information

**Code Fix By:** Claude (Autonomous Session 2026-01-11)
**Session Documentation:** SESSION_2026-01-11.md
**Modified Files:** app/main.py (3 lines added)
**Git Status:** Uncommitted (blocked by index.lock)

---

**IMPORTANT:** This fix is correct and ready. The only barrier is deployment mechanics. Once deployed, this unlocks significant progress toward the 101-test goal.
