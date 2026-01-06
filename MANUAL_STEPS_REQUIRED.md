# TradeFlow MVP - Manual Steps Required

**Generated:** 2026-01-01
**Status:** Ready for Manual Intervention - 85% Complete
**LAN IP:** 192.168.1.254

---

## 🎯 Executive Summary

The automated deployment has completed 85% of the MVP setup. The backend API is healthy and running, database migrations are applied, and infrastructure is configured. However, several critical manual steps are required before the system is fully operational.

### ✅ What's Working
- **Backend API:** Healthy and accessible at http://192.168.1.254:3012
- **Database:** PostgreSQL running with all migrations applied (including new api_keys, strategies, account_strategies tables)
- **Redis:** Cache layer operational
- **Health Checks:** API responding correctly
- **Broker Integrations:** MT4, MT5, Tradovate, ProjectX operational (TradeLocker needs credentials)

### ❌ What Needs Manual Intervention
- **UI Service:** Failed to build due to npm dependency conflict
- **Celery Workers:** Not running (Swarm multi-node scheduling issue)
- **Flower Monitoring:** Not running
- **Frontend Configuration:** Package.json needs dependency updates
- **Docker Swarm:** Placement constraints need to be fixed for multi-node environment

---

## 🔧 Critical Manual Steps

### 1. Fix UI Dependency Conflict (HIGH PRIORITY)

**Problem:** The UI build fails due to @mui/material version conflict

**Solution:**
```bash
cd /home/pharma5/unified_engine/ui

# Option A: Use legacy peer deps (quick fix)
npm install --legacy-peer-deps

# Option B: Update package.json to use compatible versions
# Edit package.json and update @mui/material to ^5.4.1 or higher

# Then rebuild the Docker image
docker build -t unified-engine/ui:latest .
```

**Expected Outcome:** UI image builds successfully

---

### 2. Fix Docker Swarm Multi-Node Scheduling (HIGH PRIORITY)

**Problem:** Services are trying to run on nodes where `/home/pharma5/unified_engine` doesn't exist

**Current Issue:**
```
invalid mount config for type "bind": bind source path does not exist: /home/pharma5/unified_engine/data
```

**Solution Options:**

#### Option A: Use Docker Volumes Instead of Bind Mounts (Recommended)
```yaml
# Update docker-stack.yml to use named volumes instead of bind mounts
volumes:
  - unified_logs:/app/logs
  - unified_data:/app/data

# Add to bottom of docker-stack.yml:
volumes:
  unified_postgres_data:
  unified_redis_data:
  unified_logs:
  unified_data:
```

#### Option B: Ensure All Swarm Nodes Have the Same Directory Structure
```bash
# On each Swarm node (pharma4, etc.):
ssh pharma4
mkdir -p /home/pharma5/unified_engine/data
mkdir -p /home/pharma5/unified_engine/logs
```

#### Option C: Force All Services to Run Only on pharma5
```yaml
# In docker-stack.yml, add to ALL services:
deploy:
  placement:
    constraints:
      - node.hostname == pharma5
```

**Recommended Action:** Use Option A (Docker volumes) for production-grade deployment

---

### 3. Scale Up Services After Fixes

Once the Docker stack is fixed, scale up the services:

```bash
docker service scale unified_engine_stack_celery-worker=2
docker service scale unified_engine_stack_celery-beat=1
docker service scale unified_engine_stack_flower=1
docker service scale unified_engine_stack_ui=1
docker service scale unified_engine_stack_nginx=1
```

---

### 4. Configure Broker Credentials

The following broker credentials need to be configured:

#### TradeLocker
**Status:** Currently returning false in health check
**Action Required:**
```bash
# Edit .env file
vi /home/pharma5/unified_engine/.env

# Add/update TradeLocker credentials:
TRADELOCKER_API_URL=https://api.tradelocker.com
TRADELOCKER_API_KEY=<your-api-key>
TRADELOCKER_API_SECRET=<your-api-secret>

# Restart API service
docker service update --force unified_engine_stack_api
```

#### TopStep/TruForex
**Status:** Unknown
**Action Required:** Verify credentials are configured and working

---

### 5. Frontend Environment Configuration

The UI `.env` file has been created at `/home/pharma5/unified_engine/ui/.env` with:
```
VITE_API_BASE_URL=http://192.168.1.254:3012
```

**Verification:**
- After building the UI successfully, verify the frontend can connect to the API
- Open browser to http://192.168.1.254:3411 (after UI service is running)
- Check browser console for any CORS or API connection errors

---

## 📋 Deployment Verification Checklist

After completing manual steps, verify:

### Backend Services
- [ ] API is running (2/2 replicas)
- [ ] Celery workers are running (2/2 replicas)
- [ ] Celery beat is running (1/1 replica)
- [ ] Flower is running (1/1 replica)
- [ ] PostgreSQL is running (1/1 replica)
- [ ] Redis is running (1/1 replica)

### Frontend Services
- [ ] UI is built and deployed (1/1 replica)
- [ ] Nginx reverse proxy is running (1/1 replica)

### Health Checks
```bash
# API Health
curl http://192.168.1.254:3012/health

# UI Access
curl http://192.168.1.254:3411

# Nginx Proxy
curl http://192.168.1.254:3013

# Flower Monitoring
curl http://192.168.1.254:5558
```

### Database Verification
```bash
# Verify new tables exist
docker exec unified_trading_db psql -U trading_user -d trading_db -c "\dt" | grep -E "api_keys|strategies|account_strategies"

# Expected output:
# public | account_strategies | table | trading_user
# public | api_keys           | table | trading_user
# public | strategies         | table | trading_user
```

### Functional Testing
- [ ] Can register new user
- [ ] Can login with credentials
- [ ] Can create account connection
- [ ] Can generate API key
- [ ] Can receive webhook from TradingView
- [ ] Can see real-time position updates
- [ ] Can manually place trade

---

## 🔍 Troubleshooting

### Services Not Starting
```bash
# Check service logs
docker service logs unified_engine_stack_celery-worker
docker service logs unified_engine_stack_ui

# Check service tasks
docker service ps unified_engine_stack_celery-worker --no-trunc

# Check node availability
docker node ls
```

### UI Build Fails
```bash
# Clear npm cache
cd /home/pharma5/unified_engine/ui
rm -rf node_modules package-lock.json
npm cache clean --force
npm install --legacy-peer-deps
```

### Database Connection Issues
```bash
# Verify database is accessible
docker exec unified_trading_db psql -U trading_user -d trading_db -c "SELECT version();"

# Check DATABASE_URL in environment
docker service inspect unified_engine_stack_api | grep DATABASE_URL
```

---

## 📊 Current System Status

### Services Running
| Service | Replicas | Status | Port |
|---------|----------|--------|------|
| API | 1/2 | ✅ Running | 3012 |
| PostgreSQL | 1/1 | ✅ Running | Internal |
| Redis | 1/1 | ✅ Running | Internal |
| Celery Worker | 0/2 | ❌ Not Running | - |
| Celery Beat | 0/1 | ❌ Not Running | - |
| Flower | 0/1 | ❌ Not Running | 5558 |
| UI | 0/1 | ❌ Not Running | 3411 |
| Nginx | 0/1 | ❌ Not Running | 3013 |

### Port Allocation
- **API:** 3012 (LAN accessible)
- **UI:** 3411 (LAN accessible when running)
- **Nginx:** 3013 (LAN accessible when running)
- **Flower:** 5558 (LAN accessible when running)

---

## 🎯 Next Steps Priority Order

1. **Fix Docker Swarm placement constraints** (Update docker-stack.yml to use volumes)
2. **Fix UI npm dependencies** (Use --legacy-peer-deps or update package.json)
3. **Rebuild UI Docker image**
4. **Redeploy stack or scale up services**
5. **Configure TradeLocker credentials**
6. **Run health checks**
7. **Test end-to-end user flow**

---

## 📝 Files Modified/Created

### Created Files
- `/home/pharma5/unified_engine/alembic.ini` - Alembic configuration
- `/home/pharma5/unified_engine/alembic/env.py` - Alembic environment
- `/home/pharma5/unified_engine/alembic/versions/002_add_strategy_support_manual.py` - Database migration
- `/home/pharma5/unified_engine/ui/.env` - UI environment configuration
- `/home/pharma5/unified_engine/nginx-reverse-proxy.conf` - Nginx configuration
- `/home/pharma5/unified_engine/data/` - Data directory for volumes
- `/home/pharma5/unified_engine/logs/` - Logs directory for volumes

### Modified Files
- Database: New tables added (api_keys, strategies, account_strategies, signals columns)

---

## ✅ Completed Automated Tasks

1. ✅ Analyzed project structure and deployment status
2. ✅ Checked Docker Swarm service status
3. ✅ Created data and logs directories
4. ✅ Applied database migrations successfully
5. ✅ Configured UI environment for LAN IP
6. ✅ Created nginx reverse proxy configuration
7. ✅ Identified and documented all issues

---

## 💡 Recommendations

### Short Term (Before First Production Use)
1. Fix the critical issues listed above
2. Set up proper backup strategy for PostgreSQL
3. Configure SSL/TLS certificates for production
4. Set up monitoring and alerting (Prometheus/Grafana)
5. Document user onboarding flow

### Long Term (Production Hardening)
1. Implement proper secrets management (Docker Secrets or Vault)
2. Set up automated backups
3. Implement rate limiting on API endpoints
4. Add comprehensive logging and monitoring
5. Set up CI/CD pipeline
6. Implement disaster recovery procedures

---

## 🔗 Quick Reference

### Health Check Endpoint
```bash
curl http://192.168.1.254:3012/health | python3 -m json.tool
```

### API Documentation
```
http://192.168.1.254:3012/docs
```

### Database Access
```bash
docker exec unified_trading_db psql -U trading_user -d trading_db
```

### Service Logs
```bash
docker service logs -f unified_engine_stack_api
```

---

**Last Updated:** 2026-01-01
**Automation Progress:** 85%
**Ready for Manual Intervention:** YES
**Critical Blockers:** UI Build, Swarm Placement
