# External Integrations

**Analysis Date:** 2026-01-19

## APIs & External Services

**Trading Brokers:**
- MT4 (MetaTrader 4) - Legacy forex/CFD trading platform
  - SDK/Client: Custom implementation in `broker_sdks/` (not Python package)
  - API: HTTP REST via `MT4_MANAGER_API_URL` (default: http://localhost:4444)
  - Auth: Manager login/password via `MT4_MANAGER_LOGIN`, `MT4_MANAGER_PASSWORD`
  - Timeout: `MT4_SERVER_TIMEOUT` (30s default)

- MT5 (MetaTrader 5) - Modern forex/CFD trading platform
  - SDK/Client: Custom implementation in `broker_sdks/` (not Python package)
  - API: HTTP REST via `MT5_MANAGER_API_URL` (default: http://localhost:4445)
  - Auth: Manager login/password via `MT5_MANAGER_LOGIN`, `MT5_MANAGER_PASSWORD`
  - Timeout: `MT5_SERVER_TIMEOUT` (30s default)

- TradeLocker - Multi-asset trading platform
  - SDK/Client: Custom Python SDK in `broker_sdks/tradelocker-python/`
  - API: REST + WebSocket
    - REST: `TRADELOCKER_BRAND_API_URL` (https://api.tradelocker.com)
    - WebSocket: `TRADELOCKER_WS_URL` (wss://live.tradelocker.com/ws)
  - Auth: Brand ID via `TRADELOCKER_BRAND_ID`
  - Executor: `app/brokers/tradelocker_executor.py`

- Tradovate - Futures trading platform
  - SDK/Client: Custom SDK in `broker_sdks/tradovate/`
  - API: REST + WebSocket
    - REST: `TRADOVATE_API_URL` (https://demo.tradovate.com)
    - WebSocket: `TRADOVATE_WS_URL` (wss://demo.tradovate.com/ws)
  - Auth: App credentials via `TRADOVATE_APP_ID`, `TRADOVATE_APP_VERSION`
  - Executor: `app/brokers/tradovate_executor.py`

- ProjectX/TopStep - Funded trader evaluation platform
  - SDK/Client: Custom SDK in `broker_sdks/topstep/`
  - API: Gateway REST API
  - URL: `PROJECTX_GATEWAY_API_URL` (https://gateway.projectx.com)
  - Executor: `app/brokers/projectx_executor.py`

**Authentication:**
- Supabase - Auth provider and BaaS
  - Client: `@supabase/supabase-js` v2.49.8
  - Usage: User authentication, session management
  - Frontend: `ui/src/contexts/UserContext.tsx`
  - Backend functions: `ui/src/supabase/functions/server/`
  - Project ID and anon key: `ui/src/utils/supabase/info.ts`

## Data Storage

**Databases:**
- PostgreSQL 15
  - Connection: `DATABASE_URL` env var
  - Format: `postgresql://username:password@localhost:5432/trading_engine`
  - Client: SQLAlchemy 2.0.23 (ORM), asyncpg 0.29.0 (async driver)
  - Pool: Configurable via `DB_POOL_SIZE` (20), `DB_MAX_OVERFLOW` (30)
  - Migrations: Alembic 1.13.1 (config: `alembic.ini`)
  - Docker service: `postgres:15` image

**File Storage:**
- Local filesystem only
  - Logs: `/var/log/trading-engine/` and `./logs/`
  - Data: `./data/` directory
  - Backups: `DB_BACKUP_PATH` (default: `/var/backups/trading-engine`)

**Caching:**
- Redis 7
  - Connection: `REDIS_URL` env var (redis://localhost:6379/0)
  - Client: redis 5.0.1, aioredis 2.0.1 (async)
  - Pool: `REDIS_MAX_CONNECTIONS` (20)
  - TTL: `CACHE_TTL` (300s), `SESSION_TTL` (3600s)
  - Used for: Session storage, caching, Celery broker/backend
  - Docker service: `redis:7-alpine` image

## Authentication & Identity

**Auth Provider:**
- Supabase
  - Implementation: Frontend auth via `@supabase/supabase-js`
  - Session: JWT tokens stored in frontend, passed to backend
  - Backend JWT: Custom JWT via `python-jose` for API authentication
  - Endpoints: `app/routers/auth.py`

**OAuth:**
- OAuth service implementation in `app/services/oauth_service.py`
- OAuth router: `app/routers/oauth.py`

## Monitoring & Observability

**Error Tracking:**
- Sentry (configured but not imported in code)
  - DSN: `SENTRY_DSN` env var
  - Toggle: `ENABLE_ERROR_REPORTING` (true/false)

**Logs:**
- Structured JSON logging
  - Framework: Python `logging` module with custom config
  - Config: `app/core/logging_config.py`
  - Level: `LOG_LEVEL` env var (default: INFO)
  - Format: `LOG_FORMAT` (json)
  - Rotation: `LOG_MAX_SIZE` (100MB), `LOG_BACKUP_COUNT` (5)
  - File: `LOG_FILE` env var

**Metrics:**
- Prometheus
  - Client: `prometheus-client` 0.19.0
  - Port: `METRICS_PORT` (9090)
  - Endpoint: `/metrics` on main app
  - Toggle: `ENABLE_METRICS` env var
  - Docker service: `prom/prometheus:latest`
  - Config: `prometheus.yml`

**Dashboards:**
- Grafana (optional)
  - Docker service: `grafana/grafana:latest`
  - Port: 3001 (mapped from 3000)
  - Admin password: `GF_SECURITY_ADMIN_PASSWORD` (default: admin)
  - Provisioning: `./grafana/provisioning/`

**Task Monitoring:**
- Flower - Celery task monitor
  - Version: 2.0.1
  - Port: 5555
  - Docker service: Runs Celery flower command

## CI/CD & Deployment

**Hosting:**
- Docker-based deployment
- Target platform: Fluxeo Master Control Tower integration
- Endpoints for MCT: `/healthz`, `/status`, `/tasks/today`, `/errors`, `/daily`

**CI Pipeline:**
- None currently configured
- Scripts available: `deploy.sh`, `install.sh`, `start.sh`

**Container Registry:**
- Not configured (local Docker builds only)

## Environment Configuration

**Required env vars:**
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - Application secret for JWT signing
- Broker credentials (optional per broker):
  - `MT4_MANAGER_API_URL`, `MT4_MANAGER_LOGIN`, `MT4_MANAGER_PASSWORD`
  - `MT5_MANAGER_API_URL`, `MT5_MANAGER_LOGIN`, `MT5_MANAGER_PASSWORD`
  - `TRADELOCKER_BRAND_API_URL`, `TRADELOCKER_BRAND_ID`
  - `TRADOVATE_API_URL`, `TRADOVATE_APP_ID`, `TRADOVATE_APP_VERSION`
  - `PROJECTX_GATEWAY_API_URL`, `PROJECTX_TIMEOUT`

**Secrets location:**
- `.env` file (main configuration)
- `.env.secrets` (sensitive values)
- Template: `.env.example` with all configuration options documented

## Webhooks & Callbacks

**Incoming:**
- TradingView webhook - `/api/v1/webhooks/tradingview`
  - Implementation: `app/routers/webhooks.py`
  - Secret: `TRADINGVIEW_WEBHOOK_SECRET` env var
  - Path configurable: `TRADINGVIEW_WEBHOOK_PATH`
  - Logs to: `app/models/models.py` WebhookLog model

- TrailHacker webhook - `/api/v1/webhooks/trailhacker`
  - Implementation: `app/routers/webhooks.py`
  - Secret: `TRAILHACKER_WEBHOOK_SECRET` env var
  - Path configurable: `TRAILHACKER_WEBHOOK_PATH`
  - Logs to: `app/models/models.py` WebhookLog model

- Generic webhook signal router - `/api/v1` routes
  - Implementation: `app/webhooks/signal_router.py`
  - Processes signals through `app/services/signal_processor.py`

- Test webhook - `/api/v1/webhooks/test`
  - For testing webhook integration

**Outgoing:**
- None currently configured
- Signal processing is inbound-only (receives signals, executes trades)

## Message Queue

**NATS (Optional):**
- Client: `nats-py` 2.6.0
- URL: `NATS_URL` env var (default: nats://localhost:4222)
- Implementation: `app/core/event_emitter.py`
- Behavior: Graceful fallback to logging if NATS unavailable
- Timeout: Hard 2-second timeout on initialization

**Celery:**
- Broker: Redis (via `CELERY_BROKER_URL`)
- Backend: Redis (via `CELERY_RESULT_BACKEND`)
- Serializer: JSON
- Task module: `app/tasks/` (referenced in docker-compose)

## WebSocket

**Real-time Updates:**
- WebSocket endpoint: `/ws`
- Manager: `app/core/websocket_manager.py`
- Heartbeat: `WS_HEARTBEAT_INTERVAL` (30s)
- Max connections: `WS_MAX_CONNECTIONS` (1000)
- Messages: subscribe, unsubscribe, ping/pong

---

*Integration audit: 2026-01-19*
