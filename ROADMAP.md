# Unified Trading Engine - Roadmap

**Created:** 2026-01-15
**Goal:** Restore full operational status and establish reliable deployment pattern

---

## Phase Overview

| Phase | Name                          | Status      | Dependencies |
|-------|-------------------------------|-------------|--------------|
| 1     | Local Run + Smoke Tests       | NOT STARTED | None         |
| 2     | Restore Workers               | NOT STARTED | Phase 1      |
| 3     | Full Deployment Pattern       | NOT STARTED | Phase 2      |
| 4     | Observability + Autoheal      | NOT STARTED | Phase 3      |

---

## Phase 1: Local Run + Smoke Tests (API + UI)

**Objective:** Get the core application running locally and verify basic functionality.

### Prerequisites
- Docker Swarm mode active
- PostgreSQL, Redis, NATS already running (confirmed in STATE.md)
- Docker images built and pushed to registry

### Tasks

#### 1.1 Scale Up API Service
```bash
docker service scale trading_api=1
```
**Verify:**
```bash
# Wait for service to be ready
sleep 10
curl -s http://localhost:3012/health | jq .
# Expected: {"status": "healthy", ...}
```

#### 1.2 Scale Up UI Service
```bash
docker service scale trading_ui=1
```
**Verify:**
```bash
# Wait for service to be ready
sleep 10
curl -s -o /dev/null -w "%{http_code}" http://localhost:3411/
# Expected: 200
```

#### 1.3 Verify API Endpoints
```bash
# Health check
curl http://localhost:3012/health

# API docs (dev mode)
curl -s -o /dev/null -w "%{http_code}" http://localhost:3012/docs
# Expected: 200 (if ENVIRONMENT=development)

# Auth endpoint exists
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:3012/auth/login
# Expected: 422 (validation error, not 404)
```

#### 1.4 Verify Database Connectivity
```bash
# Via API health (includes DB check)
curl http://localhost:3012/health | jq .database

# Direct postgres check
docker exec $(docker ps -q -f name=trading_postgres) pg_isready -U trading_user -d trading_db
```

#### 1.5 Verify Redis Connectivity
```bash
# Via API health
curl http://localhost:3012/health | jq .redis

# Direct redis check
docker exec $(docker ps -q -f name=trading_redis) redis-cli ping
# Expected: PONG
```

#### 1.6 Test WebSocket Connection
```bash
# Using websocat or wscat
wscat -c ws://localhost:3012/ws/test-user || echo "Install: npm install -g wscat"
```

### Success Criteria
- [ ] `curl http://localhost:3012/health` returns 200 with all components healthy
- [ ] `curl http://localhost:3411/` loads React app
- [ ] API accepts requests (returns 422 on invalid, not 500)
- [ ] No crash loops in `docker service ps trading_api`

### Commit Message
```
feat: Phase 1 - Restore API and UI services

- Scale trading_api to 1 replica
- Scale trading_ui to 1 replica
- Verify health endpoints
- Document verification commands
```

---

## Phase 2: Restore Workers (Celery/Flower/Funnel)

**Objective:** Bring up background workers for async task processing.

### Prerequisites
- Phase 1 complete (API healthy)
- Fix for aioredis import in funnel_automation.py

### Tasks

#### 2.1 Fix Funnel Automation Import Error
```python
# In app/services/funnel_automation.py, replace:
import aioredis

# With:
import redis.asyncio as aioredis
```
**Verify:** Rebuild and deploy image

#### 2.2 Rebuild API Image (includes worker code)
```bash
docker build -t 192.168.1.254:5000/unified-engine/api:latest -f Dockerfile.stack .
docker push 192.168.1.254:5000/unified-engine/api:latest
```

#### 2.3 Scale Up Celery Worker
```bash
docker service scale trading_celery-worker=1
```
**Verify:**
```bash
docker service logs trading_celery-worker --tail 20
# Look for: "celery@... ready"
```

#### 2.4 Scale Up Celery Beat (Scheduler)
```bash
docker service scale trading_celery-beat=1
```
**Verify:**
```bash
docker service logs trading_celery-beat --tail 10
# Look for: "beat: Starting..."
```

#### 2.5 Scale Up Flower (Monitoring)
```bash
docker service scale trading_flower=1
```
**Verify:**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5558/
# Expected: 200 (or 401 if auth enabled)
```

#### 2.6 Scale Up Funnel Automation (After Fix)
```bash
docker service scale trading_funnel-automation=1
```
**Verify:**
```bash
docker service logs trading_funnel-automation --tail 20
# Should NOT see "ModuleNotFoundError"
```

### Success Criteria
- [ ] Celery worker reports "ready" in logs
- [ ] Celery beat starts scheduler
- [ ] Flower UI accessible on port 5558
- [ ] Funnel automation starts without import errors
- [ ] No services in crash-loop

### Commit Message
```
feat: Phase 2 - Restore background workers

- Fix aioredis import in funnel_automation.py
- Scale celery-worker, celery-beat, flower
- Scale funnel-automation service
- All workers healthy and processing
```

---

## Phase 3: Full Deployment Pattern (nginx/routing)

**Objective:** Establish production-ready reverse proxy setup.

### Prerequisites
- Phase 2 complete (workers healthy)
- nginx config verified

### Tasks

#### 3.1 Verify nginx Config
```bash
# Test nginx config syntax
docker run --rm -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro nginx:alpine nginx -t
```

#### 3.2 Scale Up nginx
```bash
docker service scale trading_nginx=1
```
**Verify:**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3013/
# Expected: 200 (proxied to UI)

curl -s -o /dev/null -w "%{http_code}" http://localhost:3013/api/health
# Expected: 200 (proxied to API)
```

#### 3.3 Test Full Request Path
```bash
# Through nginx to API
curl http://localhost:3013/api/health

# Through nginx to UI
curl http://localhost:3013/

# WebSocket through nginx
wscat -c ws://localhost:3013/ws/test-user
```

#### 3.4 Document Access Points
| Endpoint          | Direct Port | Via nginx     |
|-------------------|-------------|---------------|
| API               | :3012       | :3013/api/    |
| UI                | :3411       | :3013/        |
| WebSocket         | :3012/ws/   | :3013/ws/     |
| Flower            | :5558       | (direct only) |
| NATS Monitoring   | :8223       | (direct only) |

### Success Criteria
- [ ] nginx starts without config errors
- [ ] `http://localhost:3013/` serves React UI
- [ ] `http://localhost:3013/api/health` proxies to API
- [ ] WebSocket connections work through nginx

### Commit Message
```
feat: Phase 3 - Full deployment with nginx proxy

- Scale nginx reverse proxy
- Verify proxy routes for UI and API
- Confirm WebSocket proxy working
- Document access endpoints
```

---

## Phase 4: Observability + Autoheal Hooks (NATS Events)

**Objective:** Add monitoring, alerting, and self-healing capabilities.

### Prerequisites
- Phase 3 complete (full stack running)
- NATS already running

### Tasks

#### 4.1 Verify NATS Event Publishing
```bash
# Subscribe to trading events
nats sub "trading.>" --server nats://localhost:4223

# Trigger an event (e.g., health check)
curl http://localhost:3012/health
# Should see event in subscriber (if event_emitter connected)
```

#### 4.2 Add Health Check Probe to Swarm
Already configured in docker-stack.yml:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

#### 4.3 Enable Prometheus Metrics (Optional)
Add to docker-stack.yml:
```yaml
prometheus:
  image: prom/prometheus:latest
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

#### 4.4 Create Autoheal Hook (NATS Subscriber)
Create `scripts/autoheal_listener.py`:
```python
import asyncio
import nats

async def main():
    nc = await nats.connect("nats://localhost:4223")

    async def error_handler(msg):
        data = msg.data.decode()
        print(f"Error event received: {data}")
        # Add autoheal logic here

    await nc.subscribe("trading.error", cb=error_handler)
    print("Autoheal listener running...")
    await asyncio.Event().wait()

asyncio.run(main())
```

#### 4.5 Document NATS Event Subjects
| Subject                    | Payload                    | Publisher |
|----------------------------|----------------------------|-----------|
| trading.signal.received    | Signal JSON                | API       |
| trading.order.executed     | Order result               | Executor  |
| trading.position.updated   | Position state             | Sync task |
| trading.error              | Error details              | Any       |
| trading.health.degraded    | Service name + status      | Monitor   |

### Success Criteria
- [ ] NATS events publishing verified
- [ ] Health checks triggering restarts on failure
- [ ] Prometheus scraping metrics (if deployed)
- [ ] Autoheal listener responding to error events

### Commit Message
```
feat: Phase 4 - Observability and autoheal

- Verify NATS event publishing
- Document event subjects
- Add autoheal listener script
- Configure health check probes
```

---

## Quick Reference: Full Stack Restore

```bash
# From Phase 1-3 complete state:
docker service scale \
  trading_api=1 \
  trading_ui=1 \
  trading_nginx=1 \
  trading_celery-worker=1 \
  trading_celery-beat=1 \
  trading_flower=1

# Verify all running:
docker service ls | grep trading_
```

---

## Risk Register

| Risk                        | Mitigation                           |
|-----------------------------|--------------------------------------|
| Image pull failures         | Pre-pull images, verify registry     |
| Database migration issues   | Run alembic upgrade before scale-up  |
| Memory exhaustion (Rasp Pi) | Monitor with `docker stats`          |
| Port conflicts              | Check `ss -tlnp` before starting     |

---

*Last Updated: 2026-01-15*
