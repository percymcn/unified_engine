# PROJECT MVP PLAN

## Project Name
Unified Trading Engine

## Code Root
`/home/pharma5/unified_engine`

## One-Sentence Description
Multi-broker trading platform that integrates MT4, MT5, TradeLocker, Tradovate, and TopStep into a unified API for signal processing, trade execution, and portfolio management.

## CURRENT STATUS

### Backend: ✅ Ready
- FastAPI application fully functional
- All broker integrations implemented
- Database models complete
- API endpoints documented
- Celery workers configured
- Health check endpoint exists

### Frontend/UI: ✅ Ready
- React frontend exists
- UI components built
- Connected to backend API

### Onboarding (signup/login): ⚠️ Partial
- Authentication endpoints exist (`app/routers/auth.py`)
- Login/register routes implemented
- No documented onboarding flow
- Missing user documentation

### Dashboard: ✅ Ready
- Frontend dashboard exists
- Real-time data display
- Monitoring via Flower

## GAPS TO MVP

1. **No documented signup/login flow**
   - Auth endpoints exist but no user-facing flow documented
   - Need to verify frontend auth integration

2. **Missing user onboarding documentation**
   - No guide for new users
   - No setup instructions for broker connections
   - Missing API key management UI

3. **Health check status unknown**
   - Endpoint exists at `/health` but not verified
   - Need to test health check functionality

4. **No Docker Swarm deployment verification**
   - Stack file exists but deployment status unknown
   - Need to verify all services are running

5. **Missing environment variable documentation**
   - `.env.example` may be missing
   - Need to document all required env vars

## SUGGESTED MVP SCOPE

### Phase 1: Core Functionality (Current State)
- ✅ Multi-broker API integration
- ✅ Signal processing
- ✅ Trade execution
- ✅ Portfolio management
- ✅ Real-time WebSocket updates

### Phase 2: User Onboarding (MVP Gap)
- Add user registration flow
- Add login flow
- Add broker connection setup wizard
- Add API key management UI
- Create user documentation

### Phase 3: Production Readiness
- Verify health checks
- Add monitoring dashboards
- Add error handling and logging
- Add rate limiting
- Add API documentation for end users

## ENVIRONMENT & SECRETS

### Expected Environment Variables

**Database:**
- `DATABASE_URL` - PostgreSQL connection string
- `POSTGRES_DB` - Database name
- `POSTGRES_USER` - Database user
- `POSTGRES_PASSWORD` - Database password

**Redis:**
- `REDIS_URL` - Redis connection string

**Security:**
- `SECRET_KEY` - JWT secret key
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiration time

**Brokers:**
- `MT4_API_URL` - MT4 API endpoint
- `MT5_API_URL` - MT5 API endpoint
- `TRADELOCKER_API_URL` - TradeLocker API endpoint
- `TRADOVATE_API_URL` - Tradovate API endpoint
- `PROJECTX_API_URL` - ProjectX API endpoint

**Broker Credentials:**
- `MT4_API_KEY` - MT4 API key
- `MT5_API_KEY` - MT5 API key
- `TRADELOCKER_API_KEY` - TradeLocker API key
- `TRADOVATE_API_KEY` - Tradovate API key
- `PROJECTX_API_KEY` - ProjectX API key

**Application:**
- `ENVIRONMENT` - Environment (development/production)
- `LOG_LEVEL` - Logging level
- `LOG_FILE` - Log file path

**Celery:**
- `CELERY_BROKER_URL` - Celery broker URL
- `CELERY_RESULT_BACKEND` - Celery result backend

## SWARM / DEPLOYMENT NOTES

### Current Deployment
- **Stack Name:** `unified_engine_stack`
- **Stack File:** `docker-stack.yml`
- **Status:** File exists, deployment status unknown

### Services
- `api` - Main API (2 replicas)
- `celery-worker` - Background workers (2 replicas)
- `celery-beat` - Scheduler (1 replica)
- `flower` - Monitoring (1 replica)
- `ui` - Frontend (1 replica)
- `postgres` - Database (1 replica)
- `redis` - Cache (1 replica)
- `funnel-automation` - Automation service (1 replica)
- `nginx` - Reverse proxy (1 replica)

### Ports
- **API:** 8000 (internal), exposed via nginx
- **Flower:** 5555 (monitoring)
- **UI:** Via nginx reverse proxy

### Network
- **Network Name:** `unified-network`
- **Type:** Overlay network

### Deployment Command
```bash
docker stack deploy -c docker-stack.yml unified_engine_stack
```

### Health Check
- **Endpoint:** `http://localhost:8000/health`
- **Status:** Unknown - needs verification

### Next Steps
1. Verify Docker Swarm deployment
2. Test health check endpoint
3. Document user onboarding flow
4. Create `.env.example` file
5. Add user documentation
