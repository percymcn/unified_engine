# FIX PLAN - Unified Trading Engine
**Generated:** 2026-01-05 19:47 UTC
**Based on:** DISCOVERY_REPORT.md
**Priority:** Critical issues first, then high, medium, low

---

## EXECUTIVE SUMMARY

**Total Issues Identified:** 12
- **CRITICAL:** 2 (blocking all functionality)
- **HIGH:** 4 (blocking major features)
- **MEDIUM:** 4 (impacting UX/monitoring)
- **LOW:** 2 (nice-to-have improvements)

**Estimated Time to GREEN:** 2-3 hours (Critical + High priority issues)
**Estimated Time to 100%:** 4-5 hours (all issues)

---

## ISSUE PRIORITY MATRIX

| Priority | Issue | Impact | Complexity | Est. Time |
|----------|-------|--------|------------|-----------|
| 🔴 **CRITICAL** | #1: NATS Connection Failure | Blocks entire API | Low | 15 min |
| 🔴 **CRITICAL** | #2: Missing aiohttp Dependency | Funnel automation crash | Low | 10 min |
| 🟠 **HIGH** | #3: Database Migrations Not Applied | Core features broken | Low | 10 min |
| 🟠 **HIGH** | #4: Celery Workers Not Running | No background tasks | Medium | 20 min |
| 🟠 **HIGH** | #5: Frontend API URL Not Configured | Frontend-backend disconnect | Low | 15 min |
| 🟠 **HIGH** | #6: TradeLocker Broker Failing | 1 of 5 brokers down | Medium | 30 min |
| 🟡 **MEDIUM** | #7: Flower Monitoring Not Running | No task visibility | Low | 5 min |
| 🟡 **MEDIUM** | #8: Nginx Proxy Not Routing | No unified entry point | Low | 10 min |
| 🟡 **MEDIUM** | #9: Health Check Endpoint Down | No monitoring | Depends on #1 | 0 min |
| 🟡 **MEDIUM** | #10: WebSocket Functionality Unknown | Real-time updates unclear | Medium | 30 min |
| 🟢 **LOW** | #11: Documentation Gaps | User onboarding | Low | 60 min |
| 🟢 **LOW** | #12: Test Suite Not Run | Unknown coverage | Low | 30 min |

---

## CRITICAL ISSUES (MUST FIX IMMEDIATELY)

### Issue #1: NATS Connection Failure Blocking API Startup

**Priority:** 🔴 CRITICAL
**Severity:** BLOCKING
**Service:** trading_api
**Error:** `ConnectionRefusedError: [Errno 111] Connection refused` (NATS)

#### Description
The FastAPI application startup is blocked because `app/core/event_emitter.py` attempts to connect to NATS message bus, which is not running. The health check times out waiting for startup to complete, causing Docker to kill the container (exit 137).

#### Root Cause
```python
# app/core/event_emitter.py expects NATS connection
# But docker-stack.yml does not include NATS service
```

#### Impact
- ❌ API service cannot start
- ❌ All API endpoints unavailable (auth, accounts, trades, signals, webhooks)
- ❌ Frontend cannot authenticate or fetch data
- ❌ Nginx proxy has no backend to route to
- ❌ Entire platform non-functional

#### Proposed Fix (Choose One)

**Option A: Add NATS Service to Stack** (Recommended for full features)
```yaml
# Add to docker-stack.yml
services:
  nats:
    image: nats:2.10-alpine
    command:
      - "--cluster_name=trading"
      - "--http_port=8222"
    ports:
      - "4222:4222"  # Client connections
      - "8222:8222"  # HTTP monitoring
    networks:
      - unified-network
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
      resources:
        limits:
          memory: 128M
        reservations:
          memory: 64M
```

**Option B: Make NATS Optional** (Quick fix)
```python
# Edit app/core/event_emitter.py
async def connect_nats():
    try:
        # ... existing connection code ...
    except Exception as e:
        logger.warning(f"NATS not available, falling back to logging: {e}")
        # Continue without NATS, events will be logged instead
        return None  # Graceful degradation
```

**Option C: Disable NATS in Production**
```python
# Add to .env or docker-stack.yml environment
ENABLE_NATS=false

# app/core/event_emitter.py
if os.getenv("ENABLE_NATS", "true").lower() == "true":
    await connect_nats()
else:
    logger.info("NATS disabled in configuration")
```

#### Implementation Steps
1. Read `app/core/event_emitter.py`
2. Choose fix option (recommend Option B for quickest fix, Option A for production)
3. If Option B:
   - Edit event_emitter.py to handle connection failure gracefully
   - Rebuild API image: `docker build -t 192.168.1.254:5000/unified-engine/api:latest -f Dockerfile.stack .`
   - Push to registry: `docker push 192.168.1.254:5000/unified-engine/api:latest`
4. Redeploy stack: `docker stack deploy -c docker-stack.yml trading`
5. Verify: `docker service ps trading_api`
6. Test health: `curl http://localhost:3012/health`

#### Success Criteria
- ✅ API service starts successfully
- ✅ Health check passes (container stays running)
- ✅ `/health` endpoint returns 200 OK
- ✅ No NATS connection errors in logs

#### Estimated Time
- **Option A:** 20 minutes (add service, redeploy, test)
- **Option B:** 15 minutes (code change, rebuild, deploy, test) ← **Recommended**
- **Option C:** 15 minutes (env var, code change, deploy, test)

#### Dependencies
- None (can be fixed immediately)

---

### Issue #2: Missing Python Dependency (aiohttp)

**Priority:** 🔴 CRITICAL
**Severity:** BLOCKING
**Service:** funnel-automation
**Error:** `ModuleNotFoundError: No module named 'aiohttp'`

#### Description
The funnel-automation service is in a crash loop because `app/services/funnel_automation.py` imports `aiohttp`, which is not listed in `requirements.txt`.

#### Root Cause
```python
# app/services/funnel_automation.py
import aiohttp  # ← This import fails

# requirements.txt
# ... aiohttp is missing
```

#### Impact
- ❌ Funnel automation service constantly restarting
- ❌ Marketing automation features unavailable
- ⚠️ Not blocking core trading functionality (low priority for MVP)

#### Proposed Fix

**Step 1: Add aiohttp to requirements.txt**
```bash
# Add to requirements.txt
aiohttp==3.9.1
```

**Step 2: Rebuild and redeploy**
```bash
docker build -t 192.168.1.254:5000/unified-engine/api:latest -f Dockerfile.stack .
docker push 192.168.1.254:5000/unified-engine/api:latest
docker service update --force trading_funnel-automation
```

#### Implementation Steps
1. Read `requirements.txt`
2. Add line: `aiohttp==3.9.1`
3. Save file
4. Rebuild API image (same image used for funnel-automation)
5. Push to registry
6. Update service
7. Verify: `docker service ps trading_funnel-automation`

#### Success Criteria
- ✅ Funnel-automation service starts without errors
- ✅ Service reaches "Running" state
- ✅ No crash loop

#### Estimated Time
- 10 minutes (add dependency, rebuild, deploy, verify)

#### Dependencies
- None (can be fixed immediately)

---

## HIGH PRIORITY ISSUES

### Issue #3: Database Migrations Not Applied

**Priority:** 🟠 HIGH
**Severity:** HIGH (may cause runtime errors)
**Service:** postgres
**Affected Features:** API keys, strategies, strategy tracking

#### Description
Migration file `alembic/versions/001_add_strategy_support.py` exists but it's unknown if it has been applied to the production database. Missing tables will cause API errors when users try to:
- Generate API keys
- Enable/disable strategies
- View strategy statistics

#### Root Cause
Migrations may not have been run after initial deployment or database reset.

#### Impact
- ⚠️ API key endpoints return errors
- ⚠️ Strategy management endpoints fail
- ⚠️ Signal tracking incomplete (missing strategy_id, strategy_name fields)

#### Proposed Fix

**Step 1: Check current migration status**
```bash
# Option 1: If you can exec into API container
docker exec -it $(docker ps -q -f name=trading_api) alembic current

# Option 2: Check database directly
docker exec -it $(docker ps -q -f name=trading_postgres) \
  psql -U trading_user -d trading_db -c "\dt" | grep -E "api_keys|strategies|account_strategies"
```

**Step 2: Apply migrations if needed**
```bash
# Exec into API container
docker exec -it $(docker ps -q -f name=trading_api) bash

# Run migrations
alembic upgrade head

# Verify tables created
psql $DATABASE_URL -c "\dt"
```

**Step 3: Verify tables exist**
```sql
-- Expected tables:
-- api_keys
-- strategies
-- account_strategies
-- AND signals table has new columns: strategy_id, strategy_name, strategy_version, strategy_source
```

#### Implementation Steps
1. Wait for API service to be running (fix Issue #1 first)
2. Exec into API container
3. Run `alembic current` to check status
4. If not on latest, run `alembic upgrade head`
5. Verify tables with `\dt` in psql
6. Test API key creation: `curl -X POST http://localhost:3012/api/v1/api-keys?name=Test -H "Authorization: Bearer <token>"`

#### Success Criteria
- ✅ `alembic current` shows migration 001 applied
- ✅ Tables exist: api_keys, strategies, account_strategies
- ✅ Signals table has strategy columns
- ✅ API key creation endpoint works

#### Estimated Time
- 10 minutes (check status, run migrations, verify)

#### Dependencies
- **Requires:** Issue #1 fixed (API must be running to exec into container)

---

### Issue #4: Celery Workers Not Running

**Priority:** 🟠 HIGH
**Severity:** HIGH (no background processing)
**Services:** celery-worker, celery-beat, flower
**Status:** All 0/1 replicas (stopped)

#### Description
All Celery-related services (worker, beat, flower) are in "Complete" state, meaning they exited cleanly but are not restarting. This prevents:
- Background task processing
- Periodic strategy execution
- Scheduled health checks
- Async trade operations

#### Root Cause
Services may have stopped during previous stack updates and need manual restart.

#### Impact
- ❌ No background task processing
- ❌ Strategy periodic execution not working
- ❌ Scheduled tasks not running (daily reports, etc.)
- ⚠️ Synchronous operations still work (API can execute trades directly)

#### Proposed Fix

**Step 1: Verify Redis broker is accessible**
```bash
# Test Redis connection
docker exec -it $(docker ps -q -f name=trading_redis) redis-cli ping
# Expected: PONG
```

**Step 2: Scale up Celery services**
```bash
# Scale worker to 2 instances
docker service scale trading_celery-worker=2

# Scale beat to 1 instance
docker service scale trading_celery-beat=1

# Scale flower to 1 instance
docker service scale trading_flower=1
```

**Step 3: Monitor startup**
```bash
# Watch services come up
watch -n 2 'docker service ls | grep celery'

# Check logs (if docker service logs is allowed)
# docker service logs trading_celery-worker
```

**Step 4: Verify Flower UI**
```bash
curl http://localhost:5558/
# Should return Flower dashboard HTML
```

#### Implementation Steps
1. Verify Redis is running and accessible
2. Scale celery-worker to 2 replicas
3. Scale celery-beat to 1 replica
4. Scale flower to 1 replica
5. Wait 30 seconds for services to start
6. Check service status: `docker service ls | grep celery`
7. Verify Flower UI loads: http://localhost:5558 (credentials: admin/Unified2024!)

#### Success Criteria
- ✅ celery-worker: 2/2 replicas running
- ✅ celery-beat: 1/1 replicas running
- ✅ flower: 1/1 replicas running
- ✅ Flower UI accessible with task list
- ✅ No crash loops

#### Estimated Time
- 20 minutes (scale services, monitor startup, verify)

#### Dependencies
- **Requires:** Redis running (already healthy)
- **Optional:** Issue #1 fixed (if Celery tasks need to call API)

---

### Issue #5: Frontend API URL Not Configured

**Priority:** 🟠 HIGH
**Severity:** HIGH (frontend cannot connect to backend)
**Service:** ui
**File:** `ui/.env` (missing)

#### Description
The React frontend is configured to call the backend API, but the base URL is not properly set. The code likely defaults to `http://localhost:3012`, which may not work in production or from the browser.

#### Root Cause
No `.env` file exists in the `ui/` directory to set `VITE_API_BASE_URL`.

#### Impact
- ⚠️ Frontend may not connect to backend API
- ⚠️ Authentication may fail
- ⚠️ Data fetching may use mock backend instead of live data

#### Proposed Fix

**Step 1: Create ui/.env file**
```bash
# For local development
echo "VITE_API_BASE_URL=http://localhost:3012" > ui/.env

# For production (browser access from LAN)
echo "VITE_API_BASE_URL=http://192.168.1.254:3012" > ui/.env

# OR route through nginx proxy
echo "VITE_API_BASE_URL=http://192.168.1.254:3013/api" > ui/.env
```

**Step 2: Rebuild UI image**
```bash
cd ui/
docker build -t 192.168.1.254:5000/unified-engine/ui:latest .
docker push 192.168.1.254:5000/unified-engine/ui:latest
```

**Step 3: Update service**
```bash
docker service update --force trading_ui
```

**Step 4: Verify in browser**
```javascript
// In browser console at http://192.168.1.254:3411
localStorage.getItem('api_base_url')
// OR check network tab for API calls
```

#### Implementation Steps
1. Create `ui/.env` with appropriate API URL
2. Rebuild UI image
3. Push to registry
4. Force update UI service
5. Wait for new container to start
6. Open browser to http://192.168.1.254:3411
7. Open DevTools Network tab
8. Try to login or load dashboard
9. Verify API calls go to correct URL

#### Success Criteria
- ✅ `.env` file exists in ui/ directory
- ✅ UI image rebuilt with new config
- ✅ Browser network tab shows API calls to correct backend
- ✅ Login works (if backend is up)
- ✅ Dashboard loads live data (not mocks)

#### Estimated Time
- 15 minutes (create env, rebuild, deploy, test)

#### Dependencies
- **Requires:** Issue #1 fixed (backend API must be running to test)

---

### Issue #6: TradeLocker Broker Connection Failing

**Priority:** 🟠 HIGH
**Severity:** MEDIUM-HIGH (1 of 5 brokers down)
**Service:** api (TradeLocker executor)
**Health Check:** Returns `"tradelocker": false`

#### Description
The TradeLocker broker executor is returning `false` in health checks, meaning it cannot connect to TradeLocker API. This may be due to:
- Missing or invalid credentials
- Incorrect API endpoint
- TradeLocker API being down

#### Root Cause
Credentials issue (most likely) or API configuration error.

#### Impact
- ⚠️ Users cannot connect TradeLocker accounts
- ⚠️ TradeLocker signals will fail
- ✅ Other 4 brokers still working (MT4, MT5, Tradovate, ProjectX)

#### Proposed Fix

**Step 1: Check TradeLocker configuration**
```bash
# Check environment variables
grep -i tradelocker .env

# Expected variables:
# TRADELOCKER_API_URL=...
# TRADELOCKER_API_KEY=...
# TRADELOCKER_API_SECRET=...
```

**Step 2: Verify TradeLocker SDK**
```bash
# Check SDK exists
ls -la broker_sdks/tradelocker/
ls -la broker_sdks/tradelocker-python/
```

**Step 3: Test connection manually**
```python
# In Python REPL or test script
from app.brokers.tradelocker_executor import TradeLockerExecutor

executor = TradeLockerExecutor()
status = await executor.health_check()
print(f"Health: {status}")
```

**Step 4: If credentials missing, update .env**
```bash
# Add to .env (DO NOT COMMIT REAL CREDENTIALS)
TRADELOCKER_API_URL=https://api.tradelocker.com
TRADELOCKER_API_KEY=your_test_key_here
TRADELOCKER_API_SECRET=your_test_secret_here
```

**Step 5: Restart API service**
```bash
docker service update --force trading_api
```

#### Implementation Steps
1. Check `.env` for TradeLocker credentials
2. If missing, add placeholder or real test credentials
3. Verify `broker_sdks/tradelocker-python/` exists and is functional
4. Restart API service to reload environment
5. Wait for service to start
6. Test health endpoint: `curl http://localhost:3012/health`
7. Verify `"tradelocker": true` in response

#### Success Criteria
- ✅ TradeLocker credentials present in .env
- ✅ Health check returns `"tradelocker": true`
- ✅ Can connect TradeLocker account via UI
- ✅ TradeLocker signals execute successfully

#### Estimated Time
- **If credentials available:** 10 minutes
- **If credentials need to be obtained:** 30 minutes + waiting for TradeLocker support

#### Dependencies
- **Requires:** Issue #1 fixed (API must be running)
- **May require:** Manual credential acquisition from TradeLocker

---

## MEDIUM PRIORITY ISSUES

### Issue #7: Flower Monitoring Not Running

**Priority:** 🟡 MEDIUM
**Severity:** MEDIUM (monitoring only)
**Service:** flower
**Status:** 0/1 replicas

#### Description
Flower (Celery monitoring UI) is not running, preventing visibility into background task status.

#### Proposed Fix
Included in Issue #4 (Celery Workers). Scale flower service:
```bash
docker service scale trading_flower=1
```

#### Estimated Time
5 minutes (part of Issue #4 fix)

---

### Issue #8: Nginx Proxy Not Fully Utilized

**Priority:** 🟡 MEDIUM
**Severity:** LOW-MEDIUM (convenience feature)
**Service:** nginx
**Status:** Running but backend (API) is down

#### Description
Nginx reverse proxy is configured and running, but cannot route to backend API because API service is down.

#### Proposed Fix
No action needed - will work automatically once Issue #1 is fixed.

#### Verification Steps
```bash
# After API is running
curl http://localhost:3013/api/health
# Should proxy to trading_api:8000/health
```

#### Estimated Time
0 minutes (no action needed, just verify after API fix)

---

### Issue #9: Health Check Endpoint Down

**Priority:** 🟡 MEDIUM
**Severity:** MEDIUM (monitoring)
**Endpoint:** /health
**Status:** Unreachable (API down)

#### Description
The `/health` endpoint is unreachable because the API service is down (Issue #1).

#### Proposed Fix
No action needed - will work automatically once Issue #1 is fixed.

#### Expected Response
```json
{
  "status": "healthy",
  "redis": "connected",
  "brokers": {
    "mt4": true,
    "mt5": true,
    "tradelocker": false,  // Until Issue #6 fixed
    "tradovate": true,
    "projectx": true
  }
}
```

#### Estimated Time
0 minutes (automatic after Issue #1 fix)

---

### Issue #10: WebSocket Functionality Unknown

**Priority:** 🟡 MEDIUM
**Severity:** MEDIUM (real-time features)
**Endpoint:** /ws
**Status:** Unknown (API down prevents testing)

#### Description
The application has WebSocket support (`app/core/websocket.py`) for real-time position and trade updates, but functionality is untested.

#### Proposed Fix

**Step 1: Verify WebSocket endpoint**
```bash
# After API is running
wscat -c ws://localhost:3012/ws
# Or use browser WebSocket client
```

**Step 2: Test real-time updates**
```javascript
// In browser console
const ws = new WebSocket('ws://localhost:3012/ws');
ws.onmessage = (event) => {
  console.log('Received:', event.data);
};
ws.onopen = () => {
  console.log('WebSocket connected');
};
```

**Step 3: Trigger position update**
```bash
# Execute a trade via API
curl -X POST http://localhost:3012/api/v1/signals \
  -H "Authorization: Bearer <token>" \
  -d '{...signal data...}'

# WebSocket should receive position update message
```

#### Implementation Steps
1. Wait for API to be running (Issue #1 fixed)
2. Connect WebSocket client to ws://localhost:3012/ws
3. Execute a test trade
4. Verify WebSocket receives update message
5. Check UI components use WebSocket for live updates

#### Success Criteria
- ✅ WebSocket connection established
- ✅ Receives messages on position/trade changes
- ✅ UI components reflect real-time updates

#### Estimated Time
30 minutes (test WebSocket, verify UI integration)

#### Dependencies
- **Requires:** Issue #1 fixed (API must be running)

---

## LOW PRIORITY ISSUES

### Issue #11: Documentation Gaps

**Priority:** 🟢 LOW
**Severity:** LOW (onboarding/support)
**Missing Docs:** User guides, troubleshooting

#### Description
While comprehensive technical documentation exists, user-facing documentation is missing:
- User onboarding flow
- Broker connection setup guide (step-by-step)
- Troubleshooting common errors
- API integration examples for third-party developers

#### Proposed Fix

Create the following documentation files:

**USER_ONBOARDING.md:**
- Account registration
- First broker connection
- First trade signal
- Dashboard navigation

**BROKER_SETUP_GUIDE.md:**
- MT4 connection steps
- MT5 connection steps
- TradeLocker connection steps
- Tradovate connection steps
- ProjectX connection steps
- Common connection errors

**TROUBLESHOOTING.md:**
- API not responding
- Login failures
- Broker connection errors
- Trade execution failures
- WebSocket disconnections

**API_INTEGRATION_GUIDE.md:**
- Authentication flow
- Webhook setup (TradingView)
- Signal execution
- Position monitoring
- Code examples (Python, JavaScript)

#### Estimated Time
60 minutes total (15 minutes per document)

---

### Issue #12: Test Suite Not Run Recently

**Priority:** 🟢 LOW
**Severity:** LOW (quality assurance)
**Tests:** 11 test files exist
**Status:** Unknown (not run recently)

#### Description
A comprehensive test suite exists in `tests/` directory but there's no evidence of recent test runs. Running tests would:
- Verify all API endpoints work
- Catch regression bugs
- Validate broker integrations
- Test WebSocket functionality

#### Proposed Fix

**Step 1: Set up test environment**
```bash
# Activate venv
cd /home/pharma5/unified_engine
source venv/bin/activate

# Install test dependencies (should be in requirements.txt)
pip install pytest pytest-asyncio httpx
```

**Step 2: Run test suite**
```bash
# Run all tests
pytest tests/ -v

# Run specific test files
pytest tests/test_api.py -v
pytest tests/test_brokers.py -v
pytest tests/test_webhooks.py -v
pytest tests/test_e2e.py -v
```

**Step 3: Review results**
```bash
# Generate coverage report
pytest tests/ --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

#### Implementation Steps
1. Wait for API to be running (Issue #1 fixed)
2. Activate Python venv
3. Run `pytest tests/ -v`
4. Document any failing tests
5. Fix failing tests or update tests if API changed
6. Re-run until all pass
7. Create CI/CD configuration (optional)

#### Success Criteria
- ✅ All tests pass or documented failures explained
- ✅ Coverage report generated
- ✅ No critical test failures

#### Estimated Time
30 minutes (run tests, review results, document findings)

#### Dependencies
- **Requires:** Issue #1 fixed (API must be running)
- **Requires:** Issue #3 fixed (migrations applied)

---

## IMPLEMENTATION SEQUENCE

### Phase 1: CRITICAL (Get System Running)
**Goal:** API running, basic functionality working
**Time:** 30 minutes

1. Fix Issue #1 (NATS connection) - **15 min**
2. Fix Issue #2 (aiohttp dependency) - **10 min**
3. Verify API health endpoint - **5 min**

**Checkpoint:** API service running, /health returns 200 OK

---

### Phase 2: HIGH PRIORITY (Core Features)
**Goal:** Full backend functionality, frontend integration
**Time:** 1 hour

4. Fix Issue #3 (database migrations) - **10 min**
5. Fix Issue #4 (Celery workers) - **20 min**
6. Fix Issue #5 (frontend API URL) - **15 min**
7. Test frontend-backend integration - **15 min**

**Checkpoint:** Frontend loads, users can login, dashboard shows data

---

### Phase 3: MEDIUM PRIORITY (Full Features)
**Goal:** All features working, monitoring in place
**Time:** 1 hour

8. Fix Issue #6 (TradeLocker broker) - **30 min**
9. Verify Issue #7 (Flower) - **5 min** (part of Issue #4)
10. Verify Issue #8 (Nginx proxy) - **5 min** (automatic)
11. Verify Issue #9 (health endpoint) - **5 min** (automatic)
12. Test Issue #10 (WebSocket) - **30 min**

**Checkpoint:** All 5 brokers working, real-time updates working, monitoring in place

---

### Phase 4: LOW PRIORITY (Documentation & Quality)
**Goal:** Production-ready documentation and testing
**Time:** 1.5 hours

13. Fix Issue #11 (documentation) - **60 min**
14. Fix Issue #12 (run tests) - **30 min**

**Checkpoint:** Comprehensive documentation, all tests passing

---

## VERIFICATION CHECKLIST

After completing all fixes, verify the following:

### Backend Health
- [ ] API service running (1/1 replicas)
- [ ] `/health` endpoint returns 200 OK
- [ ] Database connection working
- [ ] Redis connection working
- [ ] All 5 broker executors initialized
- [ ] No NATS errors in logs

### Background Tasks
- [ ] celery-worker running (2/2 replicas)
- [ ] celery-beat running (1/1 replicas)
- [ ] flower running (1/1 replicas)
- [ ] Flower UI accessible at :5558
- [ ] Tasks visible in Flower dashboard

### Frontend
- [ ] UI service running (1/1 replicas)
- [ ] Frontend accessible at :3411
- [ ] Login works
- [ ] Dashboard loads live data
- [ ] No console errors

### Integration
- [ ] API calls from frontend succeed
- [ ] Authentication flow works
- [ ] Broker connection flow works
- [ ] Signal execution works
- [ ] WebSocket real-time updates work

### Monitoring
- [ ] Health checks passing
- [ ] Nginx proxy routing correctly
- [ ] Logs clean (no errors)
- [ ] All services green in `docker service ls`

---

## ROLLBACK PLAN

If issues occur during fixes:

### Rollback Issue #1 (NATS Fix)
```bash
# If Option B code change causes issues
git checkout app/core/event_emitter.py
docker build -t 192.168.1.254:5000/unified-engine/api:latest -f Dockerfile.stack .
docker push 192.168.1.254:5000/unified-engine/api:latest
docker service update --force trading_api
```

### Rollback Issue #2 (aiohttp)
```bash
# Remove aiohttp from requirements.txt
# Rebuild and redeploy
# Scale funnel-automation to 0 to stop crash loop
docker service scale trading_funnel-automation=0
```

### Rollback Issue #3 (Migrations)
```bash
# Downgrade migrations
docker exec -it $(docker ps -q -f name=trading_api) alembic downgrade -1
```

### Rollback Issue #4 (Celery)
```bash
# Scale down if causing issues
docker service scale trading_celery-worker=0
docker service scale trading_celery-beat=0
docker service scale trading_flower=0
```

---

## SUCCESS METRICS

**System is GREEN when:**
- ✅ All CRITICAL issues fixed
- ✅ All HIGH priority issues fixed
- ✅ API responds to health checks
- ✅ Frontend can authenticate users
- ✅ At least 1 end-to-end trade flow tested successfully

**System is 100% when:**
- ✅ All issues fixed (including MEDIUM and LOW)
- ✅ All tests passing
- ✅ Documentation complete
- ✅ All 5 brokers connected
- ✅ Real-time updates working

---

## NOTES

- All Docker image rebuilds require push to local registry (192.168.1.254:5000)
- Services may take 30-60 seconds to start after update
- Health checks have 30s interval, 10s timeout, 3 retries
- Keep `.env` file backed up before making changes
- Document any manual configuration steps in MANUAL_STEPS_REQUIRED.md

---

**END OF FIX PLAN**

*Next Step: Execute Phase 1 (Critical Issues) to get the system running.*
