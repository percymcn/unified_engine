# Project Discovery Summary

## Project Information
- **Project Name:** Unified Trading Engine
- **Slug:** unified-trading-engine
- **Absolute Path:** `/home/pharma5/unified_engine`
- **Type:** Business Application

## Detected Tech Stack

### Backend
- **Framework:** FastAPI (Python)
- **Entry Point:** `app/main.py`
- **Database:** PostgreSQL (via SQLAlchemy)
- **Cache:** Redis
- **Task Queue:** Celery with Redis broker
- **API Documentation:** Available at `/docs` (Swagger UI)

### Frontend
- **Framework:** React with Vite
- **Location:** `/home/pharma5/unified_engine/ui`
- **Entry File:** `index.html`
- **Build System:** Vite

## Important Files

### Backend Entrypoints
- `app/main.py` - Main FastAPI application
- `app/main_demo.py` - Demo version
- `simple_backend.py` - Simplified backend

### Frontend Entrypoints
- `ui/index.html` - Frontend entry point
- `ui/src/` - React source files

### Docker/Deployment Files
- `Dockerfile` - Standard Docker build
- `Dockerfile.stack` - Docker Swarm optimized build
- `docker-compose.yml` - Local development
- `docker-stack.yml` - Docker Swarm deployment

### Configuration Files
- `.env` - Environment variables (if exists)
- `requirements.txt` - Python dependencies
- `nginx.conf` - Nginx configuration

### Documentation
- `README.md` - Main documentation
- `docs/README.md` - Additional docs

## Relation to Other Empire Components

- **Master Dashboard:** Should be monitored via master dashboard
- **NATS:** Not currently integrated (potential enhancement)
- **n8n:** Has onboarding automation workflow at `n8n/onboarding_automation.json`
- **MCP:** Has connector at `mcp/connector.json`

## Docker Swarm Configuration

**Stack Name:** `unified_engine_stack`

**Services:**
- `api` - Main FastAPI application (2 replicas)
- `celery-worker` - Background task processing (2 replicas)
- `celery-beat` - Scheduled tasks (1 replica)
- `flower` - Celery monitoring (1 replica)
- `ui` - React frontend (1 replica)
- `postgres` - PostgreSQL database (1 replica)
- `redis` - Redis cache (1 replica)
- `funnel-automation` - Funnel automation service (1 replica)
- `nginx` - Reverse proxy (1 replica)

**Network:** `unified-network` (overlay)

**Ports:**
- API: 8000
- Flower: 5555
- UI: Via nginx

## Current Status

- ✅ Backend API functional
- ✅ Frontend UI exists
- ✅ Docker Swarm stack file exists
- ✅ Database models defined
- ✅ Broker integrations (MT4, MT5, TradeLocker, Tradovate, ProjectX)
- ⚠️ Health check endpoint exists but status unknown
- ❌ No documented signup/login flow
- ❌ Missing user onboarding documentation

## Key Features

1. Multi-broker support (MT4, MT5, TradeLocker, Tradovate, ProjectX)
2. Signal processing and execution
3. Risk management
4. Portfolio management
5. Real-time WebSocket connections
6. Webhook integration
7. Celery background tasks
8. Monitoring with Flower

## Dependencies

- PostgreSQL 12+
- Redis 6+
- Python 3.9+
- Node.js 18+ (for frontend)
