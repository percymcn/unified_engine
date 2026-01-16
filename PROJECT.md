# Unified Trading Engine - Project Specification

## Overview

The Unified Trading Engine is a comprehensive multi-broker trading system built with FastAPI backend and React frontend. It supports real-time signal processing, WebSocket connections, risk management, and a modern dashboard for trading operations.

---

## Architecture

```
unified_engine/
├── app/                          # FastAPI Backend (Python)
│   ├── main.py                   # Application entry point + lifespan
│   ├── brokers/                  # Broker executors
│   │   ├── base_executor.py      # Abstract base class
│   │   ├── mt4_executor.py       # MetaTrader 4
│   │   ├── mt5_executor.py       # MetaTrader 5
│   │   ├── tradelocker_executor.py
│   │   ├── tradovate_executor.py
│   │   └── projectx_executor.py
│   ├── cache/                    # Redis client
│   ├── core/                     # Config, security, middleware, websocket
│   │   ├── config.py             # Settings (pydantic-settings)
│   │   ├── security.py           # JWT auth
│   │   ├── websocket_manager.py  # WS connection manager
│   │   ├── event_emitter.py      # NATS event bus (optional)
│   │   └── logging_config.py
│   ├── db/                       # SQLAlchemy database
│   ├── models/                   # ORM + Pydantic schemas
│   │   ├── models.py             # SQLAlchemy models
│   │   ├── database_models.py
│   │   ├── enhanced_models.py
│   │   ├── schemas.py
│   │   └── pydantic_schemas.py
│   ├── routers/                  # API endpoints
│   │   ├── auth.py               # /auth/*
│   │   ├── accounts.py           # /accounts/*
│   │   ├── positions.py          # /positions/*
│   │   ├── trades.py             # /trades/*
│   │   ├── signals.py            # /signals/*
│   │   ├── webhooks.py           # /webhooks/*
│   │   ├── analytics.py          # /analytics/*
│   │   ├── notifications.py      # /notifications/*
│   │   ├── subscription.py       # /subscription/*
│   │   ├── api_keys.py           # /api-keys/*
│   │   ├── strategies.py         # /strategies/*
│   │   ├── strategy_execution.py
│   │   ├── oauth.py              # OAuth flows
│   │   ├── unified_router.py     # Unified broker operations
│   │   ├── funnel_router.py      # Marketing funnel
│   │   └── credential_router.py  # Broker credentials
│   ├── services/                 # Business logic
│   │   ├── signal_processor.py   # Signal routing + execution
│   │   ├── funnel_automation.py  # Lead funnel worker
│   │   ├── subscription_service.py
│   │   ├── notification_service.py
│   │   ├── oauth_service.py
│   │   └── strategy_runner.py
│   ├── tasks/                    # Celery tasks
│   │   ├── celery_app.py
│   │   └── trading_tasks.py
│   └── webhooks/
│       └── signal_router.py      # Inbound signal webhooks
│
├── ui/                           # React Frontend
│   └── src/
│       ├── App.tsx               # Main router
│       ├── main.tsx              # Entry point
│       ├── components/           # 40+ React components
│       │   ├── Dashboard.tsx
│       │   ├── AdminDashboard.tsx
│       │   ├── ConnectBrokerPage.tsx
│       │   ├── PositionsMonitor.tsx
│       │   ├── OrdersManager.tsx
│       │   ├── AccountsManager.tsx
│       │   ├── TradingConfiguration.tsx
│       │   ├── RiskControls.tsx
│       │   ├── AnalyticsPage.tsx
│       │   ├── BillingPortal.tsx
│       │   ├── WebhookTemplates.tsx
│       │   └── ... (see full list below)
│       ├── contexts/             # React contexts
│       └── utils/
│
├── alembic/                      # Database migrations
├── tests/                        # Test suite (12 test files)
├── broker_sdks/                  # External SDK wrappers
├── scripts/                      # Utility scripts
└── docker-stack.yml              # Swarm deployment
```

---

## Deployment Configuration (Swarm)

### Published Ports

| Service       | External Port | Internal Port | Protocol |
|---------------|---------------|---------------|----------|
| trading_api   | 3012          | 8000          | HTTP     |
| trading_ui    | 3411          | 80            | HTTP     |
| trading_nginx | 3013          | 80            | HTTP     |
| trading_nats  | 4223          | 4222          | TCP      |
| trading_nats  | 8223          | 8223          | HTTP (monitoring) |
| trading_flower| 5558          | 5555          | HTTP     |

### Infrastructure Services (Internal Only)

| Service           | Image               | Notes                     |
|-------------------|---------------------|---------------------------|
| trading_postgres  | postgres:15         | Volume: unified_postgres_data |
| trading_redis     | redis:7-alpine      | Volume: unified_redis_data    |

### Application Services

| Service                  | Image                                        | Purpose              |
|--------------------------|----------------------------------------------|----------------------|
| trading_api              | 192.168.1.254:5000/unified-engine/api:latest | FastAPI backend      |
| trading_ui               | 192.168.1.254:5000/unified-engine/ui:latest  | React frontend       |
| trading_nginx            | nginx:alpine                                 | Reverse proxy        |
| trading_celery-worker    | (same as api)                                | Background tasks     |
| trading_celery-beat      | (same as api)                                | Scheduled tasks      |
| trading_flower           | (same as api)                                | Celery monitoring    |
| trading_funnel-automation| (same as api)                                | Lead funnel worker   |

### Network

- Overlay network: `trading_unified-network`
- All services attached with internal DNS aliases

---

## Major Features & Modules

### 1. Authentication & Authorization (`app/routers/auth.py`)
- JWT token authentication (access + refresh tokens)
- User registration, login, logout
- Password reset flow
- Role-based access (user/admin)

**Acceptance Tests:**
- [ ] `POST /auth/register` creates user, returns tokens
- [ ] `POST /auth/login` validates credentials, returns tokens
- [ ] `POST /auth/refresh` issues new access token
- [ ] `GET /auth/me` returns current user with valid token
- [ ] Expired token returns 401

### 2. Broker Management (`app/routers/accounts.py`, `credential_router.py`)
- Multi-broker support: MT4, MT5, TradeLocker, Tradovate, ProjectX
- Credential storage (encrypted)
- Account sync and validation
- Broker health monitoring

**Acceptance Tests:**
- [ ] `POST /credentials` stores broker credentials
- [ ] `GET /accounts` lists connected accounts
- [ ] `POST /accounts/sync` syncs positions from broker
- [ ] Broker connection errors handled gracefully

### 3. Signal Processing (`app/services/signal_processor.py`)
- Inbound webhook signals (TradingView, custom)
- Signal validation and normalization
- Multi-account distribution
- Execution tracking

**Acceptance Tests:**
- [ ] `POST /webhooks/signal` accepts valid signal payload
- [ ] Signal routes to correct broker executor
- [ ] Failed execution triggers retry logic
- [ ] Signal history persisted to database

### 4. Position Management (`app/routers/positions.py`)
- Real-time position tracking
- P&L calculation
- Position close/modify operations
- Cross-broker position aggregation

**Acceptance Tests:**
- [ ] `GET /positions` returns current positions
- [ ] `POST /positions/{id}/close` closes position
- [ ] WebSocket broadcasts position updates

### 5. Order Execution (`app/routers/trades.py`)
- Market/limit/stop orders
- Order validation against risk rules
- Execution status tracking

**Acceptance Tests:**
- [ ] `POST /trades` creates order
- [ ] Order respects risk limits
- [ ] Order status updates via WebSocket

### 6. Risk Management (`app/core/config.py`, UI: `RiskControls.tsx`)
- Max position size limits
- Daily loss limits
- Leverage restrictions
- Emergency stop functionality

**Acceptance Tests:**
- [ ] Order rejected when exceeding position limit
- [ ] Trading halted when daily loss exceeded
- [ ] Emergency stop closes all positions

### 7. WebSocket Real-Time Updates (`app/core/websocket_manager.py`)
- Position updates
- Order status changes
- Price ticks (when connected)
- System notifications

**Acceptance Tests:**
- [ ] `WS /ws/{user_id}` establishes connection
- [ ] Heartbeat maintains connection
- [ ] Position changes broadcast to user

### 8. Analytics & Reporting (`app/routers/analytics.py`)
- Trade history analysis
- P&L reports
- Performance metrics
- Export functionality

**Acceptance Tests:**
- [ ] `GET /analytics/performance` returns metrics
- [ ] `GET /analytics/trades` returns trade history
- [ ] Date range filtering works

### 9. Subscription & Billing (`app/routers/subscription.py`, `subscription_service.py`)
- Plan management (Free/Pro/Enterprise)
- Usage tracking
- Trial management

**Acceptance Tests:**
- [ ] `GET /subscription` returns current plan
- [ ] `POST /subscription/upgrade` processes upgrade
- [ ] Feature gates enforced by plan

### 10. Notifications (`app/routers/notifications.py`, `notification_service.py`)
- In-app notifications
- Email notifications (configurable)
- Trade alerts
- System announcements

**Acceptance Tests:**
- [ ] `GET /notifications` returns user notifications
- [ ] `POST /notifications/mark-read` updates status
- [ ] Trade execution triggers notification

### 11. API Key Management (`app/routers/api_keys.py`)
- Generate/revoke API keys
- Key-based authentication for webhooks
- Usage tracking

**Acceptance Tests:**
- [ ] `POST /api-keys` generates new key
- [ ] `DELETE /api-keys/{id}` revokes key
- [ ] Webhook with API key authenticates

### 12. Strategies (`app/routers/strategies.py`, `strategy_runner.py`)
- Strategy configuration
- Automated execution rules
- Backtesting support

**Acceptance Tests:**
- [ ] `POST /strategies` creates strategy
- [ ] `PUT /strategies/{id}/activate` starts strategy
- [ ] Strategy executes on signal match

### 13. Marketing Funnel (`app/routers/funnel_router.py`, `funnel_automation.py`)
- Lead capture
- Email sequences
- VSL delivery
- Guide downloads

**Acceptance Tests:**
- [ ] `POST /funnel/lead` captures lead
- [ ] `GET /funnel/guide/download` serves PDF
- [ ] Lead progresses through funnel stages

### 14. Admin Panel (UI: `AdminDashboard.tsx`, `AdminPanel.tsx`)
- User management
- System monitoring
- Configuration management
- Audit logs

**Acceptance Tests:**
- [ ] Admin can view all users
- [ ] Admin can modify user plans
- [ ] System health visible in dashboard

### 15. NATS Event Bus (`app/core/event_emitter.py`)
- Async event publishing
- Service decoupling
- Graceful fallback to logging if NATS unavailable

**NATS Subjects:**
- `trading.signal.received` - Inbound signals
- `trading.order.executed` - Order completions
- `trading.position.updated` - Position changes
- `trading.error` - System errors

**Acceptance Tests:**
- [ ] Events publish to NATS when connected
- [ ] System operates normally without NATS
- [ ] Event subscribers receive messages

### 16. Background Workers (Celery)
- `celery-worker`: Async task execution
- `celery-beat`: Scheduled tasks (position sync, cleanup)
- `flower`: Web-based monitoring (port 5558)

**Acceptance Tests:**
- [ ] Tasks execute in worker
- [ ] Scheduled tasks run on time
- [ ] Flower UI accessible

---

## UI Components (React)

### Public Pages
- `LandingPage.tsx` - Marketing homepage
- `LoginPage.tsx` - User login
- `SignupPage.tsx` - Registration
- `PasswordResetPage.tsx`

### Dashboard Pages
- `Dashboard.tsx` - Main dashboard shell
- `DashboardOverview.tsx` - Summary widgets
- `PositionsMonitor.tsx` - Live positions
- `OrdersManager.tsx` - Order management
- `AccountsManager.tsx` - Broker accounts
- `AnalyticsPage.tsx` - Reports & charts

### Configuration Pages
- `ConnectBrokerPage.tsx` - Broker setup wizard
- `TradingConfiguration.tsx` - Trading settings
- `RiskControls.tsx` - Risk parameters
- `WebhookTemplates.tsx` - Signal templates
- `ApiKeyManager.tsx` - API key management
- `BillingPortal.tsx` - Subscription management

### Admin Pages
- `AdminDashboard.tsx` - Admin overview
- `AdminPanel.tsx` - User management
- `AdminLoginPage.tsx` - Admin auth
- `AdminAccountsViewer.tsx` - Account inspection
- `LogsViewer.tsx` - System logs

---

## Environment Variables

Key configuration (see `.env.example` for full list):

```bash
# Core
DATABASE_URL=postgresql://trading_user:trading_password@postgres:5432/trading_db
REDIS_URL=redis://redis:6379/0
SECRET_KEY=<change-in-production>
ENVIRONMENT=production

# NATS (optional)
NATS_URL=nats://nats:4222

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Broker APIs (configure per broker)
TRADELOCKER_API_KEY=
TRADOVATE_USER_ID=
TRADOVATE_PASSWORD=
PROJECTX_API_TOKEN=
```

---

## Test Suite

Located in `tests/`:

| File                    | Coverage Area                |
|-------------------------|------------------------------|
| test_api.py             | REST API endpoints           |
| test_brokers.py         | Broker executor logic        |
| test_webhooks.py        | Signal webhook processing    |
| test_websockets.py      | WebSocket connections        |
| test_e2e.py             | End-to-end flows             |
| test_deployment.py      | Container/service health     |
| test_performance.py     | Load testing                 |
| test_ui_integration.py  | Frontend-backend integration |
| test_analytics.py       | Analytics endpoints          |
| test_notifications.py   | Notification system          |

Run tests:
```bash
pytest tests/ -v
pytest tests/test_api.py -v  # Single file
```

---

## Quick Reference

### Health Check
```bash
curl http://localhost:3012/health
```

### API Documentation
- Swagger UI: http://localhost:3012/docs (dev only)
- ReDoc: http://localhost:3012/redoc (dev only)

### Logs
- API logs: `./logs/trading_engine.log`
- Container logs: `docker service logs trading_api`

---

## Version

- App Version: 2.0.0
- Last Updated: 2026-01-15
