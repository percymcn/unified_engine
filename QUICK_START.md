# TradeFlow MVP - Quick Start Guide

**Status:** 85% Complete - 2 fixes needed before production

---

## ⚡ TL;DR - What You Need to Do

### Step 1: Fix UI Build (5 minutes)
```bash
cd /home/pharma5/unified_engine/ui
npm install --legacy-peer-deps
cd ..
docker build -t unified-engine/ui:latest ./ui
```

### Step 2: Fix Docker Swarm (10 minutes)
**Option A (Recommended):** Edit `docker-stack.yml` and replace all `./logs:/app/logs` and `./data:/app/data` with named volumes

**OR Option B (Quick):** Force everything to run on pharma5:
```bash
# Add to ALL services in docker-stack.yml under deploy.placement.constraints:
- node.hostname == pharma5
```

### Step 3: Deploy Services (5 minutes)
```bash
cd /home/pharma5/unified_engine
docker service scale unified_engine_stack_celery-worker=2
docker service scale unified_engine_stack_celery-beat=1
docker service scale unified_engine_stack_flower=1
docker service scale unified_engine_stack_ui=1
docker service scale unified_engine_stack_nginx=1
```

### Step 4: Verify (2 minutes)
```bash
curl http://192.168.1.254:3012/health
curl http://192.168.1.254:3411
docker service ls | grep unified_engine_stack
```

---

## 📊 Current Status

| Component | Status | Action Needed |
|-----------|--------|---------------|
| Backend API | ✅ Working | None |
| Database | ✅ Working | None |
| Redis | ✅ Working | None |
| Migrations | ✅ Applied | None |
| Frontend UI | ❌ Failed Build | Fix npm deps |
| Celery Workers | ❌ Not Running | Fix Swarm placement |
| Flower Monitor | ❌ Not Running | Fix Swarm placement |

---

## 🔗 Service URLs (After Fixes)

- API: http://192.168.1.254:3012
- API Docs: http://192.168.1.254:3012/docs
- Health: http://192.168.1.254:3012/health
- Frontend: http://192.168.1.254:3411
- Nginx: http://192.168.1.254:3013
- Flower: http://192.168.1.254:5558

---

## 📖 Full Documentation

For detailed instructions, see:
- `MANUAL_STEPS_REQUIRED.md` - Complete manual steps guide
- `RALPH_LOOP_COMPLETION_SUMMARY.md` - Full automation summary
- `deploy.sh` - Automated deployment script

---

## ❓ Quick Troubleshooting

**UI won't build?**
```bash
cd ui
rm -rf node_modules package-lock.json
npm cache clean --force
npm install --legacy-peer-deps
```

**Services won't start?**
```bash
docker service logs unified_engine_stack_celery-worker
docker service ps unified_engine_stack_celery-worker --no-trunc
```

**Need to restart everything?**
```bash
docker stack rm unified_engine_stack
sleep 10
docker stack deploy -c docker-stack.yml unified_engine_stack
```

---

**Total Time to Production:** ~20 minutes if you follow the steps above
