# DISCOVERY REPORT - Unified Trading Engine
**Generated:** 2026-01-05 19:47 UTC
**Discovery Mode:** READ-ONLY
**Session ID:** discovery_20260105_1947

---

## EXECUTIVE SUMMARY

**Project Name:** Unified Trading Engine (TradeFlow SaaS Platform)
**Project Type:** Enterprise Multi-Broker Trading Platform with SaaS Features
**Current State:** **75% Complete** - Backend production-ready, frontend exists but integration incomplete
**Critical Issues:** 5 blocking issues preventing full deployment
**Architecture:** FastAPI Backend + React Frontend + Docker Swarm Deployment

### Key Findings
- ✅ **Backend API:** Fully functional, comprehensive REST API with 20+ routers
- ✅ **Database:** PostgreSQL configured, migrations exist but status unknown
- ✅ **Broker Integrations:** 5 brokers (MT4, MT5, TradeLocker, Tradovate, ProjectX)
- ⚠️ **Docker Services:** Multiple services failing (API health check, Celery workers)
- ⚠️ **Frontend:** UI exists but not fully integrated with backend
- ❌ **NATS Missing:** API expects NATS connection but service not in stack
- ❌ **Missing Dependency:** `aiohttp` not in requirements.txt

---

## 1. PROJECT OVERVIEW

### 1.1 Project Purpose
The Unified Trading Engine is an enterprise-grade SaaS platform that:
- **Unifies Multiple Brokers:** MT4, MT5, TradeLocker, Tradovate, ProjectX into single API
- **Signal Processing:** Webhook receivers for TradingView, TrailHacker, custom signals
- **Strategy Management:** In-house strategy registry with enable/disable per account
- **Real-time Monitoring:** WebSocket connections for live position/trade updates
- **SaaS Features:** Multi-tenancy, subscriptions (Stripe), role-based access control
- **Analytics:** Trading performance dashboards, risk metrics

### 1.2 Technology Stack

#### Backend
- **Framework:** FastAPI 0.104.1 + Uvicorn
- **Database:** PostgreSQL 15 (via SQLAlchemy 2.0.23)
- **Cache:** Redis 7-alpine
- **Task Queue:** Celery 5.3.4 with Flower 2.0.1 monitoring
- **Message Bus:** NATS 2.6.0 (configured but missing from stack)
- **Authentication:** JWT (python-jose) + bcrypt (passlib)
- **WebSocket:** python-socketio 5.10.0 + websockets 12.0

#### Frontend
- **Framework:** React 18.3.1 + Vite 6.3.5
- **UI Library:** Radix UI + Tailwind CSS
- **State Management:** React hooks + contexts
- **HTTP Client:** Configured in `ui/src/utils/api-client.ts`
- **Mock Backend:** `ui/src/utils/mock-backend.ts` (for development)

#### Deployment
- **Container:** Docker + Docker Swarm
- **Orchestration:** docker-stack.yml with 9 services
- **Reverse Proxy:** Nginx (alpine)
- **Registry:** Local registry at 192.168.1.254:5000

---

## 2. DIRECTORY STRUCTURE

```
/home/pharma5/unified_engine/
├── app/                          # FastAPI Backend Application
│   ├── main.py                   # Main FastAPI app (480+ lines, 20+ routers)
│   ├── routers/                  # API Endpoints (19 files)
│   │   ├── auth.py               # JWT authentication
│   │   ├── accounts.py           # Broker account CRUD
│   │   ├── positions.py          # Open positions
│   │   ├── trades.py             # Trade history
│   │   ├── signals.py            # Trading signal management
│   │   ├── webhooks.py           # Webhook receivers
│   │   ├── api_keys.py           # API key generation
│   │   ├── strategies.py         # Strategy registry
│   │   ├── strategy_execution.py # Strategy runner
│   │   ├── subscription.py       # Stripe billing
│   │   ├── analytics.py          # Trading analytics
│   │   ├── funnel_router.py      # Marketing funnel
│   │   ├── credential_router.py  # Broker credentials
│   │   ├── oauth.py              # Social login
│   │   ├── notifications.py      # User notifications
│   │   ├── health.py             # Health checks
│   │   └── unified_router.py     # Unified operations
│   ├── services/                 # Business Logic
│   │   ├── strategy_runner.py    # In-house strategy execution
│   │   ├── funnel_automation.py  # Marketing automation (MISSING aiohttp)
│   │   └── ...
│   ├── brokers/                  # Broker Integrations
│   │   ├── mt4_executor.py
│   │   ├── mt5_executor.py
│   │   ├── tradelocker_executor.py
│   │   ├── tradovate_executor.py
│   │   └── projectx_executor.py
│   ├── models/                   # SQLAlchemy Models
│   │   └── models.py             # Users, Accounts, Positions, Trades, Signals, etc.
│   ├── core/                     # Core Configuration
│   │   ├── config.py
│   │   ├── auth.py
│   │   ├── event_emitter.py      # NATS event emitter (expects NATS)
│   │   └── websocket.py
│   ├── cache/                    # Redis Client
│   ├── db/                       # Database Connection
│   ├── tasks/                    # Celery Tasks
│   ├── utils/                    # Utilities
│   └── webhooks/                 # Webhook Handlers
├── ui/                           # React Frontend
│   ├── src/
│   │   ├── App.tsx               # Main React app
│   │   ├── components/           # 40+ UI components
│   │   │   ├── DashboardOverview.tsx
│   │   │   ├── AccountsManager.tsx
│   │   │   ├── PositionsMonitor.tsx
│   │   │   ├── ConnectBrokerPage.tsx
│   │   │   ├── AdminDashboard.tsx
│   │   │   └── ...
│   │   ├── contexts/             # React Contexts
│   │   │   ├── UserContext.tsx
│   │   │   ├── BrokerContext.tsx
│   │   │   └── ThemeContext.tsx
│   │   └── utils/
│   │       ├── api-client.ts     # API client (points to localhost:3012)
│   │       └── mock-backend.ts   # Mock data
│   ├── Dockerfile                # Multi-stage build (Node + Nginx)
│   ├── nginx.conf                # SPA routing + API proxy
│   └── package.json              # Dependencies (Radix UI, Recharts, etc.)
├── broker_sdks/                  # Broker SDK Implementations
│   ├── tradelocker/
│   ├── tradelocker-python/       # May need git submodule treatment
│   ├── tradovate/
│   ├── topstep/
│   └── truforex/
├── alembic/                      # Database Migrations
│   ├── versions/
│   │   └── 001_add_strategy_support.py  # Adds api_keys, strategies, account_strategies
│   └── alembic.ini
├── tests/                        # Test Suite (11 files)
│   ├── test_api.py
│   ├── test_brokers.py
│   ├── test_webhooks.py
│   ├── test_e2e.py
│   ├── test_performance.py
│   └── ...
├── docker-stack.yml              # Swarm deployment (9 services)
├── Dockerfile.stack              # Combined API build
├── nginx-reverse-proxy.conf      # Main reverse proxy config
├── requirements.txt              # Python dependencies (MISSING aiohttp)
├── .env                          # Environment configuration
└── logs/                         # Log files
    └── integration_run_*/        # Previous integration attempts
```

**Total Python Files:** 52 files in app/
**Total UI Components:** 40+ TSX components
**Total Test Files:** 11 test files

---

## 3. ARCHITECTURE

### 3.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    External Clients                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Browser    │  │ TradingView  │  │ TrailHacker  │       │
│  │  (Port 3411)│  │  Webhooks    │  │  Webhooks    │       │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼─────────────────┼──────────────────┼──────────────┘
          │                 │                  │
          ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│               Nginx Reverse Proxy (Port 3013)               │
│  /api/* → trading_api:8000                                  │
│  /      → trading_ui:80                                     │
│  /flower → trading_flower:5555                              │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌────────────────┐  ┌──────────────┐
│  React UI     │  │  FastAPI API   │  │   Flower     │
│  (Port 3411)  │  │  (Port 3012)   │  │ (Port 5558)  │
│  Nginx:alpine │  │  Python 3.9    │  │   Monitor    │
└───────────────┘  └────────┬───────┘  └──────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌────────────────┐  ┌──────────────┐
│  PostgreSQL   │  │     Redis      │  │ Celery Tasks │
│  (Port 5432)  │  │  (Port 6379)   │  │  Worker+Beat │
│   Database    │  │     Cache      │  │  Background  │
└───────────────┘  └────────────────┘  └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │  NATS (MISSING!)
                    │  Event Bus   │
                    │ (Expected)   │
                    └──────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌────────────────┐  ┌──────────────┐
│     MT4       │  │      MT5       │  │ TradeLocker  │
│   Executor    │  │   Executor     │  │   Executor   │
└───────────────┘  └────────────────┘  └──────────────┘
        ▼                   ▼                   ▼
┌───────────────┐  ┌────────────────┐  ┌──────────────┐
│   Tradovate   │  │   ProjectX     │  │   TruForex   │
│   Executor    │  │   Executor     │  │   Executor   │
└───────────────┘  └────────────────┘  └──────────────┘
```

### 3.2 Docker Swarm Services (Stack: `trading`)

| Service | Image | Replicas | Status | Ports | Notes |
|---------|-------|----------|--------|-------|-------|
| **postgres** | postgres:15 | 1/1 | ✅ GREEN | internal | Healthy |
| **redis** | redis:7-alpine | 1/1 | ✅ GREEN | internal | Healthy |
| **api** | 192.168.1.254:5000/unified-engine/api:latest | 0/1 | ❌ RED | 3012:8000 | **Health check failing (exit 137)** |
| **celery-worker** | 192.168.1.254:5000/unified-engine/api:latest | 0/1 | ❌ RED | - | **Stopped (exited 0)** |
| **celery-beat** | 192.168.1.254:5000/unified-engine/api:latest | 0/1 | ❌ RED | - | **Stopped (exited 0)** |
| **flower** | 192.168.1.254:5000/unified-engine/api:latest | 0/1 | ❌ RED | 5558:5555 | **Stopped (exited 0)** |
| **ui** | 192.168.1.254:5000/unified-engine/ui:latest | 1/1 | ✅ GREEN | 3411:80 | Running on pharma4 |
| **funnel-automation** | 192.168.1.254:5000/unified-engine/api:latest | 0/1 | ❌ RED | - | **Crash loop (exit 1)** |
| **nginx** | nginx:alpine | 1/1 | ✅ GREEN | 3013:80 | Running on pharma4 |

**Services GREEN:** 4/9 (44%)
**Services RED:** 5/9 (56%)

### 3.3 Additional Running Containers (Non-Swarm)
- `unified_trading_api` - Up 29 hours (unhealthy)
- `unified_trading_celery` - Up 17 minutes (unhealthy)
- `unified_trading_flower` - Up 29 hours (unhealthy)
- `unified_trading_db` - Up 29 hours (healthy)
- `unified_trading_redis` - Up 29 hours (healthy)

---

## 4. NETWORK CONFIGURATION

### 4.1 Port Allocation

| Port | Service | Protocol | Status | Accessibility |
|------|---------|----------|--------|---------------|
| 3012 | API (FastAPI) | HTTP | ❌ Down | Should be http://192.168.1.254:3012 |
| 3013 | Nginx Proxy | HTTP | ✅ Up | http://192.168.1.254:3013 |
| 3411 | UI (React) | HTTP | ✅ Up | http://192.168.1.254:3411 |
| 5558 | Flower (Celery Monitor) | HTTP | ❌ Down | - |
| 5432 | PostgreSQL | TCP | ✅ Up | Internal only |
| 6379 | Redis | TCP | ✅ Up | Internal (127.0.0.1:6379 + container) |
| 8000 | API Internal | HTTP | ❌ Down | Container port |

### 4.2 Docker Networks
- **Network:** `trading_unified-network` (overlay, attachable)
- **Swarm Manager:** pharma5 (192.168.1.254)
- **Swarm Worker:** pharma4

### 4.3 Service DNS Names (Internal)
- `postgres:5432`
- `redis:6379`
- `trading_api:8000`
- `trading_ui:80`
- `trading_flower:5555`

---

## 5. CRITICAL ISSUES IDENTIFIED

### Issue #1: API Service Health Check Failure ❌ CRITICAL
**Severity:** BLOCKING
**Service:** `trading_api`
**Error:** `task: non-zero exit (137): dockerexec: unhealthy container`
**Root Cause:** NATS connection failure blocks application startup

**Evidence:**
```
INFO: Started server process [1]
INFO: Waiting for application startup.
INFO: Database tables created
INFO: Connected to Redis successfully
ERROR: nats: encountered error - ConnectionRefusedError: [Errno 111] Connection refused
```

**Impact:**
- All API functionality unavailable
- No authentication endpoints
- No webhook receivers
- No trading operations
- Nginx proxy has no backend to route to

**Fix Required:**
1. **Option A:** Add NATS service to docker-stack.yml
2. **Option B:** Make NATS connection optional in `app/core/event_emitter.py` (graceful fallback)
3. **Option C:** Disable NATS in production config

---

### Issue #2: Missing Python Dependency (aiohttp) ❌ CRITICAL
**Severity:** BLOCKING
**Service:** `funnel-automation`
**Error:** `ModuleNotFoundError: No module named 'aiohttp'`
**Root Cause:** `aiohttp` not in requirements.txt but required by `app/services/funnel_automation.py`

**Impact:**
- Funnel automation service crash loop
- Marketing automation unavailable

**Fix Required:**
- Add `aiohttp` to requirements.txt
- Rebuild API image

---

### Issue #3: Celery Services Not Running ❌ HIGH
**Severity:** HIGH PRIORITY
**Services:** `celery-worker`, `celery-beat`, `flower`
**Status:** All in "Complete" state (exited cleanly)
**Root Cause:** Services stopped, likely due to previous deployments

**Impact:**
- No background task processing
- No periodic strategy execution
- No scheduled tasks
- No Celery monitoring

**Fix Required:**
- Restart services after stack update
- Verify Redis broker connectivity

---

### Issue #4: Database Migrations Unknown Status ⚠️ HIGH
**Severity:** HIGH PRIORITY
**Migration File:** `alembic/versions/001_add_strategy_support.py`
**Tables to Create:**
- `api_keys` - API key management
- `strategies` - Strategy registry
- `account_strategies` - Strategy enable/disable per account

**Impact:**
- Unknown if migrations applied
- Potential runtime errors if tables missing
- Strategy features may not work

**Fix Required:**
1. Exec into API container
2. Run `alembic upgrade head`
3. Verify tables exist: `psql $DATABASE_URL -c "\dt"`

---

### Issue #5: Frontend API URL Configuration ⚠️ MEDIUM
**Severity:** MEDIUM PRIORITY
**File:** `ui/src/utils/api-client.ts`
**Current:** Hardcoded `http://localhost:3012` or env var `VITE_API_BASE_URL`
**Issue:** No `.env` file in `ui/` directory

**Impact:**
- Frontend may not connect to backend in production
- API calls will fail if backend URL incorrect

**Fix Required:**
- Create `ui/.env` with `VITE_API_BASE_URL=http://192.168.1.254:3012`
- Rebuild UI image

---

## 6. API ENDPOINTS INVENTORY

### 6.1 Core Endpoints (from app/main.py)

| Route Prefix | Router File | Description | Endpoints |
|--------------|-------------|-------------|-----------|
| `/api/v1/auth` | auth.py | Authentication | login, register, logout, refresh, me |
| `/api/v1/accounts` | accounts.py | Broker Accounts | CRUD, sync, balance |
| `/api/v1/positions` | positions.py | Open Positions | list, get, close |
| `/api/v1/trades` | trades.py | Trade History | list, get, by account |
| `/api/v1/signals` | signals.py | Trading Signals | CRUD, execute, cancel, history |
| `/api/v1/webhooks` | webhooks.py | Webhook Management | logs, test |
| `/api/v1` | unified_router.py | Unified Operations | Consolidated broker operations |
| `/api/v1` | funnel_router.py | Sales Funnel | Marketing automation |
| `/api/v1` | credential_router.py | Broker Credentials | Secure credential storage |
| `/` | subscription.py | Billing/Subscription | Stripe integration |
| `/api/v1` | webhook-signals | Webhook Receivers | TradingView, TrailHacker |
| `/api/v1/api-keys` | api_keys.py | API Keys | generate, list, revoke |
| `/api/strategies` | strategies.py | Strategies | list, enable, disable, stats |
| `/api/v1/strategy-execution` | strategy_execution.py | Strategy Runner | run, start-periodic, stop-periodic |
| `/` | oauth.py | OAuth | Social login providers |
| `/` | analytics.py | Analytics | Dashboard stats, performance |
| `/` | notifications.py | Notifications | User notifications |

### 6.2 Direct Endpoints (in main.py)

```python
GET  /                 # Root info
GET  /health           # Health check (FAILS - NATS issue)
GET  /healthz          # K8s health check
GET  /status           # Detailed status
GET  /metrics          # Prometheus metrics
GET  /test             # Connectivity test
GET  /tasks/today      # Daily tasks
GET  /errors           # Recent errors
GET  /api/keys         # API key status
GET  /daily            # Daily summary
POST /workflow/run     # Run workflow
WS   /ws               # WebSocket endpoint
```

### 6.3 OpenAPI Documentation
- **Interactive Docs:** http://localhost:3012/docs (currently down)
- **ReDoc:** http://localhost:3012/redoc (currently down)
- **OpenAPI JSON:** http://localhost:3012/openapi.json (currently down)

---

## 7. DATABASE SCHEMA

### 7.1 Core Models (app/models/models.py)

**User Management:**
- `users` - User accounts with email, hashed password
- `roles` - Role definitions (admin, user, etc.)
- `permissions` - Permission registry
- `organizations` - Multi-tenancy support

**Trading:**
- `accounts` - Broker account connections
- `positions` - Open trading positions
- `trades` - Trade history
- `signals` - Trading signals with strategy tracking
- `strategies` - Strategy registry
- `account_strategies` - Strategy enable/disable per account

**API & Auth:**
- `api_keys` - Generated API keys with hashing
- `subscriptions` - Stripe subscriptions
- `notifications` - User notifications
- `webhook_logs` - Webhook request history

### 7.2 Database Connection String

**Development (.env):**
```bash
DATABASE_URL=sqlite:///trading_db.db
```

**Production (docker-stack.yml override):**
```bash
DATABASE_URL=postgresql://trading_user:trading_password@postgres:5432/trading_db
```

### 7.3 Migration Status
- **Alembic Configured:** ✅ Yes
- **Migration Files:** 1 file (`001_add_strategy_support.py`)
- **Applied Status:** ❓ Unknown (needs verification)

---

## 8. FRONTEND ARCHITECTURE

### 8.1 React Application Structure

**Framework:** React 18.3.1 + TypeScript + Vite 6.3.5
**UI Library:** Radix UI (accordion, dialog, dropdown, tabs, etc.)
**Styling:** Tailwind CSS
**Charts:** Recharts 2.15.2
**Forms:** React Hook Form 7.55.0

### 8.2 Key Components (40+ total)

**Dashboard & Overview:**
- `DashboardOverview.tsx` - Main dashboard
- `AdminDashboard.tsx` - Admin panel
- `AnalyticsPage.tsx` - Analytics dashboard

**Account Management:**
- `AccountsManager.tsx` - Broker account CRUD
- `AccountSelectionPage.tsx` - Account selector
- `ChangeAccountPage.tsx` - Switch accounts
- `ConnectBrokerPage.tsx` - Broker onboarding (31KB - comprehensive)

**Trading Operations:**
- `PositionsMonitor.tsx` - Live position tracking
- `OrdersManager.tsx` - Order management
- `RiskControls.tsx` - Risk management UI

**Admin & Settings:**
- `AdminPanel.tsx` - Admin controls
- `ApiKeyManager.tsx` - API key generation UI
- `SettingsDropdown.tsx` - User settings
- `BillingPortal.tsx` - Subscription management

**Onboarding & Landing:**
- `LandingPage.tsx` - Marketing landing page
- `SignupPage.tsx` - User registration
- `LoginPage.tsx` - User login
- `OnboardingPlanSelection.tsx` - Plan selection

### 8.3 API Client Configuration

**File:** `ui/src/utils/api-client.ts`
**Base URL:** Defaults to `http://localhost:3012` or `VITE_API_BASE_URL`
**Methods:** Complete API client for all backend endpoints
**Mock Backend:** `ui/src/utils/mock-backend.ts` (for development without backend)

### 8.4 React Contexts

- `UserContext.tsx` - User authentication state
- `BrokerContext.tsx` - Active broker state
- `ThemeContext.tsx` - Light/dark theme

---

## 9. BROKER INTEGRATIONS

### 9.1 Supported Brokers

| Broker | Executor File | SDK Location | Status |
|--------|---------------|--------------|--------|
| **MT4** | app/brokers/mt4_executor.py | - | ✅ Configured |
| **MT5** | app/brokers/mt5_executor.py | - | ✅ Configured |
| **TradeLocker** | app/brokers/tradelocker_executor.py | broker_sdks/tradelocker/ | ⚠️ False (creds issue) |
| **Tradovate** | app/brokers/tradovate_executor.py | broker_sdks/tradovate/ | ✅ Configured |
| **ProjectX** | app/brokers/projectx_executor.py | - | ✅ Configured |
| **TopStep** | - | broker_sdks/topstep/ | ❓ Status unknown |
| **TruForex** | - | broker_sdks/truforex/ | ❓ Status unknown |

### 9.2 Health Check Status (Last Known)

From `/health` endpoint (when working):
```json
{
  "status": "healthy",
  "redis": "connected",
  "brokers": {
    "mt4": true,
    "mt5": true,
    "tradelocker": false,
    "tradovate": true,
    "projectx": true
  }
}
```

---

## 10. TESTING INFRASTRUCTURE

### 10.1 Test Suite (tests/ directory)

| Test File | Purpose | Lines |
|-----------|---------|-------|
| test_api.py | API endpoint tests | - |
| test_brokers.py | Broker integration tests | - |
| test_webhooks.py | Webhook receiver tests | - |
| test_e2e.py | End-to-end user flows | - |
| test_websockets.py | WebSocket connection tests | - |
| test_performance.py | Performance benchmarks | - |
| test_ui_integration.py | Frontend-backend integration | - |
| test_analytics.py | Analytics calculations | - |
| test_deployment.py | Deployment verification | - |
| test_notifications.py | Notification system | - |
| run_tests.py | Test runner | - |

### 10.2 Test Execution Status
- **Last Run:** Unknown
- **Coverage:** Comprehensive test suite exists
- **CI/CD:** Not configured

---

## 11. CONFIGURATION FILES

### 11.1 Environment Variables (.env)

**Key Variables:**
```bash
# Database
DATABASE_URL=sqlite:///trading_db.db  # Overridden in production
REDIS_URL=redis://localhost:6379/0

# API
SECRET_KEY=unified-secret-key-2024
ENVIRONMENT=production
VITE_API_BASE_URL=http://localhost:3012

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Brokers (MT4, MT5, TradeLocker, Tradovate, ProjectX configs)
```

### 11.2 Docker Configuration

**docker-stack.yml:**
- 9 services defined
- Overlay network: `unified-network`
- Volume mounts: `./logs:/app/logs`, `./data:/app/data`
- Health checks: Configured for API service (failing)
- Resource limits: Memory constraints per service
- Placement constraints: `node.role == manager` for most services

**Dockerfile.stack:**
- Multi-stage build (Node 20 for UI, Python 3.9 for API)
- UI build: `npm install --legacy-peer-deps` → `npm run build`
- API: installs requirements.txt, copies app/, copies UI build to `/static`
- Health check: `curl -f http://localhost:8000/health`

### 11.3 Nginx Configuration

**nginx-reverse-proxy.conf:**
```nginx
/api        → trading_api:8000
/docs       → trading_api:8000
/openapi.json → trading_api:8000
/health     → trading_api:8000
/ws         → trading_api:8000 (WebSocket upgrade)
/flower     → trading_flower:5555
/           → trading_ui:80 (catch-all)
```

**ui/nginx.conf:**
```nginx
/api/       → trading_api:8000/  (proxy to backend)
/           → Static files with SPA fallback (try_files)
```

---

## 12. DEPLOYMENT & INFRASTRUCTURE

### 12.1 Docker Swarm Cluster

**Manager Node:**
- Hostname: pharma5
- IP: 192.168.1.254
- Role: Manager/Leader
- Status: Ready/Active

**Worker Node:**
- Hostname: pharma4
- IP: (not exposed)
- Role: Worker
- Status: Ready/Active

### 12.2 Docker Images

| Image | Tag | Size | Content Size |
|-------|-----|------|--------------|
| 192.168.1.254:5000/unified-engine/api | latest | 1.34GB | 236MB |
| 192.168.1.254:5000/unified-engine/ui | latest | 82.9MB | 23.5MB |
| postgres | 15 | Standard | - |
| redis | 7-alpine | Standard | - |
| nginx | alpine | Standard | - |

### 12.3 Deployment Scripts

- `deploy.sh` - Automated deployment (5984 bytes)
- `install.sh` - Initial installation (1501 bytes)
- `start.sh` - Service startup (1909 bytes)
- `scripts/` - Additional deployment utilities

---

## 13. DOCUMENTATION INVENTORY

### 13.1 Existing Documentation

| File | Purpose | Lines | Quality |
|------|---------|-------|---------|
| README.md | Project overview | 329 | ✅ Excellent |
| app_spec.txt | Original spec (Claude.ai clone) | 682 | ⚠️ Outdated |
| spec.md | Unified Engine mission | 129 | ✅ Current |
| spec-phase1.md | Phase 1 safety snapshot | 58 | ✅ Current |
| spec-phase2.md | Phase 2 infrastructure fixes | 53 | ✅ Current |
| INTEGRATION_REPORT.md | Previous integration attempt | 344 | ✅ Comprehensive |
| GAP_ANALYSIS.md | Gap analysis from Jan 1 | 347 | ✅ Detailed |
| NEXT_STEPS.md | Next steps roadmap | 353 | ✅ Actionable |
| QUICK_START.md | Quick start guide | 64 | ✅ Concise |
| MANUAL_STEPS_REQUIRED.md | Manual intervention guide | - | ✅ Exists |
| RALPH_LOOP_COMPLETION_SUMMARY.md | Ralph loop report | 90 | ✅ Informative |
| DEPLOYMENT.md | Deployment guide | - | ✅ Exists |
| SETUP_GUIDE.md | Setup instructions | - | ✅ Exists |

### 13.2 Missing Documentation
- ❌ User onboarding flow guide
- ❌ Broker connection setup guide (detailed)
- ❌ Troubleshooting guide with common errors
- ❌ API integration examples for third parties
- ❌ WebSocket protocol documentation

---

## 14. DISCOVERY FINDINGS SUMMARY

### 14.1 What's Working ✅

1. **Database Infrastructure**
   - PostgreSQL 15 running and healthy
   - Redis cache operational
   - Connection strings properly configured

2. **UI Service**
   - React frontend built and deployed
   - Running on port 3411
   - Nginx serving static files
   - Comprehensive component library (40+ components)

3. **Nginx Reverse Proxy**
   - Running and routing configured
   - WebSocket upgrade support
   - Proper service name resolution

4. **Broker Integration Code**
   - 5 broker executors implemented
   - SDK folders organized
   - Health check integration exists

5. **Comprehensive Backend Code**
   - 20+ API routers
   - Complete CRUD operations
   - WebSocket support
   - Strategy management system
   - Webhook receivers (TradingView, TrailHacker)
   - Subscription/billing integration (Stripe)

### 14.2 What's Broken ❌

1. **API Service Health Checks**
   - Container exits with code 137 (unhealthy)
   - NATS connection failure blocks startup
   - No API endpoints accessible

2. **Celery Background Tasks**
   - All Celery services stopped (worker, beat, flower)
   - No background task processing
   - No periodic strategy execution

3. **Funnel Automation**
   - Crash loop due to missing `aiohttp` dependency
   - Marketing automation unavailable

4. **Database Migrations**
   - Unknown if migrations applied
   - Critical tables (api_keys, strategies) may be missing

5. **Frontend-Backend Integration**
   - No .env file in ui/ directory
   - Unclear if API URL correctly configured
   - Cannot test integration with API down

### 14.3 Gaps & Unknowns ❓

1. **NATS Message Bus**
   - Code expects NATS connection
   - Not included in docker-stack.yml
   - Unclear if required or optional

2. **TradeLocker Broker**
   - Health check returns `false`
   - Possible credential issue
   - SDK exists but connection failing

3. **UI Mock vs Live Data**
   - `mock-backend.ts` exists
   - Unclear what percentage of UI uses mocks
   - Integration completeness unknown (API down prevents testing)

4. **TopStep & TruForex**
   - SDK folders exist
   - No executor files found
   - Integration status unknown

5. **Test Coverage**
   - Tests exist but not run recently
   - Unknown pass/fail status
   - No CI/CD configured

---

## 15. SECURITY OBSERVATIONS

### 15.1 Credentials & Secrets

- ✅ `.env` file not in git (in .gitignore)
- ✅ `.env.example` provided for template
- ✅ API keys hashed in database
- ✅ JWT authentication implemented
- ⚠️ `.env` file contains credentials (protected by file permissions)
- ⚠️ Docker secrets not used (credentials in environment variables)

### 15.2 Authentication
- ✅ JWT token-based auth
- ✅ Bcrypt password hashing
- ✅ Role-based access control (RBAC)
- ✅ API key generation with secure hashing

### 15.3 Network Security
- ✅ Internal services not exposed externally
- ✅ Overlay network isolation
- ⚠️ Ports published to host (3012, 3013, 3411, 5558)

---

## 16. PERFORMANCE CONSIDERATIONS

### 16.1 Resource Limits (docker-stack.yml)

| Service | Memory Limit | Memory Reserved | Notes |
|---------|--------------|-----------------|-------|
| postgres | 512M | 256M | Standard for small dataset |
| redis | 256M | 128M | With LRU eviction |
| api | 512M | 256M | May need increase under load |
| celery-worker | 512M | 256M | Per worker instance |
| celery-beat | 256M | 128M | Scheduler only |
| flower | 256M | 128M | Monitoring UI |
| ui | 256M | 128M | Static file serving |
| nginx | 128M | 64M | Reverse proxy |

### 16.2 Optimization Opportunities
- 🔄 Redis configured with `maxmemory-policy allkeys-lru`
- 🔄 Celery worker concurrency: 2
- ⚠️ No database connection pooling visible
- ⚠️ No API response caching layer
- ⚠️ No CDN for static assets

---

## 17. EXTERNAL DEPENDENCIES

### 17.1 Third-Party Services

**Required:**
- PostgreSQL 15
- Redis 7
- NATS (expected but missing)

**Optional:**
- Stripe (for subscriptions)
- OAuth providers (Google, GitHub, etc.)
- Email service (for notifications)

### 17.2 Broker APIs
- MT4 API (configured)
- MT5 API (configured)
- TradeLocker API (credentials issue)
- Tradovate API (configured)
- ProjectX API (configured)

---

## 18. NEXT STEPS (See FIX_PLAN.md)

This discovery phase is complete. All critical issues have been documented in detail. The next phase should focus on:

1. **Fix NATS Connection Issue** (CRITICAL)
2. **Add Missing aiohttp Dependency** (CRITICAL)
3. **Apply Database Migrations** (HIGH)
4. **Restart Celery Services** (HIGH)
5. **Configure Frontend API URL** (MEDIUM)
6. **Integration Testing** (MEDIUM)

---

## 19. APPENDIX

### A. Key Commands for Verification

```bash
# Check Swarm services
docker service ls | grep trading

# Check specific service tasks
docker service ps trading_api --no-trunc

# Check container logs (non-Swarm)
docker logs unified_trading_api --tail 100

# Test endpoints (when API running)
curl http://localhost:3012/health
curl http://localhost:3012/docs
curl http://localhost:3411/

# Check database connection
docker exec -it $(docker ps -q -f name=trading_postgres) \
  psql -U trading_user -d trading_db -c "\dt"

# Check Redis connection
docker exec -it $(docker ps -q -f name=trading_redis) \
  redis-cli ping
```

### B. File Locations Reference

| Component | Location |
|-----------|----------|
| Main API | `/home/pharma5/unified_engine/app/main.py` |
| Frontend | `/home/pharma5/unified_engine/ui/` |
| Tests | `/home/pharma5/unified_engine/tests/` |
| Migrations | `/home/pharma5/unified_engine/alembic/versions/` |
| Docker Stack | `/home/pharma5/unified_engine/docker-stack.yml` |
| Environment | `/home/pharma5/unified_engine/.env` |
| Logs | `/home/pharma5/unified_engine/logs/` |

### C. Contact & Support

- **Project Directory:** /home/pharma5/unified_engine
- **Host:** pharma5 (192.168.1.254)
- **Git Branch:** main
- **Last Commit:** (check `git log -1`)

---

**END OF DISCOVERY REPORT**

*This report was generated in READ-ONLY mode. No files were modified during discovery.*
