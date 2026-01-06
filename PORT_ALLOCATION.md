# Port Allocation - TradeFlow Unified Engine

**Generated:** 2026-01-01
**LAN IP:** 192.168.1.254
**System:** Raspberry Pi 5 with Docker Swarm

---

## 🔍 Current Port Usage on System

### Ports Already in Use (AVOID THESE)
```
3000, 3001, 3002, 3004, 3005, 3010, 3100, 3101    # Various web services
4222, 4224, 8222, 8224                             # NATS messaging (other stacks)
5000, 5100, 5101                                   # Other services
5432, 5433, 5434, 5435                             # PostgreSQL instances
5555, 5678                                         # Monitoring/debuggers
6379, 6381, 6382                                   # Redis instances
8000, 8002, 8003, 8080, 8088                       # Backend APIs
8501, 8888, 8889, 8893, 9000, 9001, 9100           # Dashboards/metrics
11434                                              # Ollama LLM
22, 53, 80, 443                                    # System services
```

---

## ✅ TradeFlow Allocated Ports (CURRENT DEPLOYMENT)

### Production Deployment - Docker Stack Ports

| Service | Internal Port | Published Port | Status | LAN Access URL |
|---------|--------------|----------------|--------|----------------|
| **API** | 8000 | 3012 | ✅ Running (1/2 replicas) | http://192.168.1.254:3012 |
| **UI** | 80 | 3411 | ❌ Not Running | http://192.168.1.254:3411 |
| **Nginx** | 80 | 3013 | ❌ Not Running | http://192.168.1.254:3013 |
| **Flower** | 5555 | 5558 | ❌ Not Running | http://192.168.1.254:5558 |
| **PostgreSQL** | 5432 | - | ✅ Running (internal only) | - |
| **Redis** | 6379 | - | ✅ Running (internal only) | - |
| **Celery Worker** | - | - | ❌ Not Running | - |
| **Celery Beat** | - | - | ❌ Not Running | - |
| **Funnel Automation** | - | - | ❌ Not Running | - |

### Additional Ports Available for Future Use
```
3014, 3015, 3016, 3017, 3018, 3019    # Available for additional services
5559, 5560, 5561                       # Available for monitoring
4223, 4225                             # Available for NATS if needed
```

---

## 📊 Port Assignment Strategy

### Why These Ports?
- **3012**: Main API - chosen to avoid conflicts with 3000-3005, 3010, 3100-3101
- **3411**: UI - high port to avoid common ranges
- **3013**: Nginx - next sequential from API
- **5558**: Flower monitoring - next sequential from common 5555

### Port Conflict Resolution
All ports were verified using:
```bash
netstat -tulpn 2>/dev/null | grep LISTEN
```

No conflicts detected with allocated ports.

---

## 🔌 Service Access Endpoints

### Internal (Docker Network)
- API: `http://api:8000`
- PostgreSQL: `postgresql://trading_user:trading_password@postgres:5432/trading_db`
- Redis: `redis://redis:6379/0`

### External (LAN Access)
- API Health: http://192.168.1.254:3012/health
- API Docs: http://192.168.1.254:3012/docs
- Frontend: http://192.168.1.254:3411
- Nginx Proxy: http://192.168.1.254:3013
- Flower Monitor: http://192.168.1.254:5558

### Production (After Cloudflare Tunnel)
- Main App: https://tradeflow.yourdomain.com
- API: https://api.tradeflow.yourdomain.com
- Webhooks: https://api.tradeflow.yourdomain.com/webhooks/tradingview

---

## 🚀 Deployment Configuration

### Docker Stack Configuration
File: `docker-stack.yml`
Stack Name: `unified_engine_stack`

### Environment Variables
All services use consistent environment variables:
- `DATABASE_URL`: PostgreSQL connection
- `REDIS_URL`: Redis connection
- `SECRET_KEY`: Application secret
- `ENVIRONMENT`: production

---

## 📝 Notes

- All ports verified against system-wide listening ports
- No conflicts with existing services
- Ports chosen for logical grouping (3012-3013 for main services, 3411 for UI)
- Internal Docker network services don't require published ports
- Flower monitoring uses high port (5558) to avoid common ranges

---

## 🔄 Port Change History

| Date | Change | Reason |
|------|--------|--------|
| 2026-01-01 | Initial allocation | Fresh deployment |
| - | API: 3012 | Chosen to avoid 3000-3010 conflicts |
| - | UI: 3411 | High port to avoid common ranges |
| - | Nginx: 3013 | Sequential from API |
| - | Flower: 5558 | Avoid conflict with 5555 |

---

**Status:** ✅ All ports verified and allocated
**Last Updated:** 2026-01-01
