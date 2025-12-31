# Unified Engine Audit Report
**Generated:** 2025-11-30  
**Purpose:** Production readiness assessment for TradeFlow system

---

## 1. CURRENT ARCHITECTURE

### 1.1 Deployment Method
- **Primary:** Docker Swarm (`docker-stack.yml`)
- **Alternative:** Docker Compose (`docker-compose.yml`) for local dev
- **Stack Name:** `unified_engine_stack`
- **Network:** `unified-network` (overlay)

### 1.2 Services & Status

| Service | Replicas | Port | Status | Notes |
|---------|----------|------|--------|-------|
| `api` | 1/2 | 3012:8000 | ⚠️ Partial | Only 1 replica running (should be 2) |
| `postgres` | 1/1 | Internal | ✅ Running | Database healthy |
| `redis` | 1/1 | Internal | ✅ Running | Cache healthy |
| `ui` | 0/1 | 3411:80 | ❌ Not Running | Frontend not deployed |
| `celery-worker` | 0/2 | Internal | ❌ Not Running | Background tasks disabled |
| `celery-beat` | 0/1 | Internal | ❌ Not Running | Scheduled tasks disabled |
| `flower` | 0/1 | 5558:5555 | ❌ Not Running | Monitoring disabled |
| `funnel-automation` | 0/1 | Internal | ❌ Not Running | Automation disabled |
| `nginx` | 0/1 | 3013:80 | ❌ Not Running | Reverse proxy not running |

### 1.3 Port Mapping
- **API:** `3012` → `8000` (internal)
- **UI:** `3411` → `80` (internal, not running)
- **Flower:** `5558` → `5555` (internal, not running)
- **Nginx:** `3013` → `80` (not running)

### 1.4 Environment Variables

**Present in `.env.example`:**
- Database: `DATABASE_URL`, `POSTGRES_*`
- Redis: `REDIS_URL`
- Security: `SECRET_KEY`, `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- Brokers: `MT4_*`, `MT5_*`, `TRADELOCKER_*`, `TRADOVATE_*`, `PROJECTX_*`
- Celery: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`

**Missing/Unclear:**
- `VITE_API_BASE_URL` (UI needs this)
- `NATS_URL` (NATS integration not present)
- `ENVIRONMENT` (production/development flag)
- API key management env vars

---

## 2. BACKEND API ENDPOINTS

### 2.1 Authentication (`/api/v1/auth`)
- ✅ `POST /register` - User registration
- ✅ `POST /login` - User login (returns JWT)
- ✅ `GET /me` - Get current user
- ✅ `POST /logout` - Logout (client-side)
- ✅ `POST /refresh` - Refresh token
- ✅ `PUT /change-password` - Change password
- ✅ `GET /sessions` - List user sessions
- ✅ `DELETE /sessions/{id}` - Revoke session
- ⚠️ `verify_api_key()` - Exists but uses hardcoded test key

### 2.2 Accounts (`/api/v1/accounts`)
- ✅ `GET /` - List user accounts
- ✅ `POST /` - Create account
- ✅ `GET /{id}` - Get account details
- ✅ `PUT /{id}` - Update account
- ✅ `DELETE /{id}` - Delete account
- ✅ `POST /{id}/sync` - Sync with broker
- ✅ `GET /{id}/balance` - Get account balance

### 2.3 Positions (`/api/v1/positions`)
- ✅ `GET /` - List positions
- ✅ `POST /` - Create position
- ✅ `GET /{id}` - Get position
- ✅ `POST /{id}/close` - Close position
- ✅ `GET /account/{account_id}` - Get account positions

### 2.4 Trades (`/api/v1/trades`)
- ✅ `GET /` - List trades
- ✅ `POST /` - Create trade
- ✅ `GET /{id}` - Get trade
- ✅ `GET /account/{account_id}` - Get account trades

### 2.5 Signals (`/api/v1/signals`)
- ✅ `GET /` - List signals
- ✅ `POST /` - Create signal
- ✅ `GET /{id}` - Get signal
- ✅ `POST /{id}/cancel` - Cancel signal
- ✅ `GET /history` - Signal history
- ✅ `GET /active` - Active signals
- ✅ `POST /execute` - Execute signal

### 2.6 Webhooks (`/api/v1/webhooks`)
- ✅ `POST /tradingview` - TradingView webhook
- ✅ `POST /trailhacker` - TrailHacker webhook
- ✅ `GET /logs` - Webhook logs
- ✅ `GET /logs/{id}` - Get webhook log
- ✅ `POST /test` - Test webhook

### 2.7 Unified Router (`/api/v1/unified`)
- ✅ `GET /health` - Health check
- ✅ `GET /status` - System status
- ✅ `GET /accounts` - All accounts
- ✅ `GET /accounts/{id}` - Account details
- ✅ `GET /positions` - All positions
- ✅ `GET /positions/{id}` - Position details
- ✅ `DELETE /positions/{id}` - Close position
- ✅ `POST /orders` - Place order
- ⚠️ `GET /orders` - Returns empty array (TODO)
- ✅ `PUT /orders/{id}` - Modify order
- ✅ `DELETE /orders/{id}` - Cancel order
- ✅ `POST /signals` - Create signal
- ✅ `GET /signals` - Signal history
- ⚠️ `GET /trades` - Returns empty array (TODO)
- ✅ `GET /symbols` - Available symbols
- ✅ `GET /brokers` - Broker list
- ✅ `GET /brokers/{name}/status` - Broker status

### 2.8 Missing Endpoints (Required)
- ❌ `GET /api/strategies/top` - Top strategies
- ❌ `GET /api/strategies` - List strategies
- ❌ `GET /api/strategies/{id}/stats` - Strategy statistics
- ❌ `POST /api/strategies/{id}/enable` - Enable strategy
- ❌ `GET /api/v1/api-keys` - List API keys
- ❌ `POST /api/v1/api-keys` - Create API key
- ❌ `DELETE /api/v1/api-keys/{id}` - Revoke API key

---

## 3. DATABASE SCHEMA

### 3.1 Current Models (`app/models/models.py`)

**User Management:**
- ✅ `User` - Users table with email, username, password
- ✅ `UserSession` - Session tracking

**Trading:**
- ✅ `Account` - Trading accounts (linked to User)
- ✅ `Trade` - Trade history
- ✅ `Position` - Open positions
- ✅ `Order` - Order management
- ✅ `Signal` - Signal tracking

**System:**
- ✅ `WebhookLog` - Webhook audit trail
- ✅ `ExecutionLog` - Execution audit trail
- ✅ `SystemConfig` - System configuration
- ✅ `Alert` - User alerts

### 3.2 Missing Fields (Required)

**Signal Model:**
- ❌ `strategy_id` (string) - Strategy identifier
- ❌ `strategy_version` (string) - Strategy version
- ❌ `strategy_name` (string) - Human-readable name
- ❌ `strategy_source` (enum: tradingview|inhouse|manual) - Source type

**New Models Needed:**
- ❌ `Strategy` - Strategy registry table
  - id, name, version, source, enabled, params, created_at, updated_at
- ❌ `ApiKey` - API key management
  - id, user_id, key_hash, name, permissions, expires_at, created_at, last_used_at

---

## 4. UI COMPONENTS

### 4.1 Existing Pages
- ✅ `App.jsx` - Main app with routing
- ✅ `pages/Launchpad.jsx` - Education launchpad (uses API)
- ✅ `pages/FreeGuide.jsx` - Funnel page
- ✅ `pages/Apply.jsx` - Funnel page
- ✅ `pages/PremiumOffer.jsx` - Funnel page
- ✅ `pages/VSL.jsx` - Funnel page

### 4.2 Missing Pages (Referenced but don't exist)
- ❌ `pages/Dashboard.jsx` - Main dashboard
- ❌ `pages/Accounts.jsx` - Account management
- ❌ `pages/Positions.jsx` - Position management
- ❌ `pages/Trades.jsx` - Trade history
- ❌ `pages/Signals.jsx` - Signal management
- ❌ `pages/Admin.jsx` - Admin panel

### 4.3 UI Mock Data Status
**Current State:** UI pages don't exist, so no mock data to replace yet.  
**Action Required:** Create all missing pages with real API integration.

### 4.4 UI Configuration
- ❌ Missing: `VITE_API_BASE_URL` environment variable
- ❌ Missing: API client configuration
- ❌ Missing: Auth store integration with backend

---

## 5. STRATEGY SUPPORT

### 5.1 Current State
- ❌ No strategy tracking in signals
- ❌ No strategy registry
- ❌ No in-house strategy runner
- ⚠️ Webhook handler exists but doesn't extract strategy info

### 5.2 Required Implementation

**A) TradingView Webhook Enhancement:**
- Extract `strategy.id`, `strategy.version`, `strategy.name` from payload
- Store in Signal model
- Validate schema

**B) In-House Strategy Runner:**
- Create `app/services/strategy_runner.py`
- Implement MA cross "toy strategy"
- Gate behind enable flag per account
- Emit signals using same schema as webhooks

**C) Strategy Registry:**
- Database table for strategies
- Enable/disable per account
- Parameter management
- Statistics tracking

---

## 6. NATS INTEGRATION

### 6.1 Current State
- ❌ NATS not present in codebase
- ❌ No NATS client configuration
- ❌ No event emission

### 6.2 Required Implementation
- Add NATS client library
- Emit events for:
  - User signup/login
  - Account creation/connection
  - Signal received/executed
  - Order placed/filled
  - Position opened/closed
- Fallback to local logging if NATS unavailable

---

## 7. API KEY MANAGEMENT

### 7.1 Current State
- ⚠️ `verify_api_key()` exists but uses hardcoded test key
- ❌ No API key generation endpoint
- ❌ No API key storage in database
- ❌ No API key revocation

### 7.2 Required Implementation
- Create `ApiKey` model
- Add endpoints:
  - `GET /api/v1/api-keys` - List keys
  - `POST /api/v1/api-keys` - Generate key
  - `DELETE /api/v1/api-keys/{id}` - Revoke key
- Update `verify_api_key()` to check database
- Add key hashing (bcrypt)

---

## 8. GAPS TO IMPLEMENT

### 8.1 Critical (Blocking Production)
1. **UI Pages Missing** - Dashboard, Accounts, Positions, Trades, Signals, Admin
2. **Strategy Tracking** - Add fields to Signal model, create Strategy registry
3. **API Key Management** - Full CRUD for API keys
4. **In-House Strategy Runner** - Service to run strategies and emit signals
5. **TradingView Webhook Enhancement** - Extract strategy info from payload

### 8.2 Important (Required for MVP)
6. **UI API Integration** - Connect all pages to real backend
7. **NATS Integration** - Event emission for all major actions
8. **Service Health** - Fix services not running (UI, Celery, etc.)
9. **Environment Variables** - Add `VITE_API_BASE_URL` and document all vars

### 8.3 Nice to Have
10. **Logs Endpoint** - GET /api/v1/logs for execution logs
11. **Strategy Statistics** - Performance metrics per strategy
12. **Dashboard KPIs** - Real-time metrics aggregation

---

## 9. TESTING & VERIFICATION

### 9.1 Existing Tests
- ✅ `tests/test_api.py` - API tests
- ✅ `tests/test_brokers.py` - Broker tests
- ✅ `tests/test_webhooks.py` - Webhook tests
- ✅ `tests/test_websockets.py` - WebSocket tests

### 9.2 Missing Tests
- ❌ End-to-end user flow tests
- ❌ Strategy execution tests
- ❌ API key management tests
- ❌ Integration tests for UI → Backend

### 9.3 Verification Scripts Needed
- ❌ `scripts/verify_green.sh` - Health check script
- ❌ `scripts/smoke_user_flow.sh` - User flow smoke test
- ❌ `scripts/deploy_one.sh` - One-command deploy
- ❌ `scripts/verify_one.sh` - One-command verify

---

## 10. DEPLOYMENT & OPERATIONS

### 10.1 Current Deployment
- ✅ `deploy.sh` - Deployment script exists
- ✅ `start.sh` - Startup script exists
- ✅ `docker-stack.yml` - Swarm stack file
- ⚠️ Many services not running (UI, Celery, etc.)

### 10.2 Required Improvements
- Fix service startup issues
- Ensure all services healthy
- Add health check endpoints verification
- Create one-command deploy/verify scripts

---

## 11. MONETIZATION & PROJECTIONS

### 11.1 Current State
- ❌ No monetization flow documented
- ❌ No pricing tiers
- ❌ No subscription management endpoints

### 11.2 Required (Per Requirements)
- Document monetization flow
- Add $/day projections
- Map functions to Empire NATS events

---

## 12. NEXT STEPS (PHASE ORDER)

### Phase 1: Discovery ✅
- [x] Parse all key files
- [x] Identify architecture
- [x] List gaps
- [x] Create audit report

### Phase 2: Boot + Health
- [x] Check current service status
- [x] Create `scripts/verify_green.sh`
- [x] Run health checks
- [x] Log results to `logs/healthcheck_<timestamp>.log`
- [x] Create logs/data directories
- [ ] Fix port mapping issues (API port 3012 not exposed)
- [ ] Start missing services (UI, Celery workers)
- [ ] Verify all services healthy

### Phase 3: Auth + Onboarding (COMPLETE)
- [x] Add ApiKey model to database
- [x] Create API key management endpoints (GET, POST, DELETE)
- [x] Update verify_api_key() to use database
- [x] Create `scripts/smoke_user_flow.sh`
- [x] Test end-to-end user flow (script ready)
- [x] Log results to `logs/smoke_user_flow_<timestamp>.log` (script ready)

### Phase 6: NATS Integration (COMPLETE)
- [x] Create event emitter with NATS support (`app/core/event_emitter.py`)
- [x] Add logging fallback if NATS unavailable
- [x] Add NATS to requirements.txt (optional dependency)
- [x] Emit events for: signup, login, account creation
- [x] Event subjects follow Empire pattern: `empire.{resource}.{action}`

### Phase 5: Dual Strategy Mode (COMPLETE)
- [x] Add strategy tracking fields to Signal model
- [x] Create Strategy registry table
- [x] Create AccountStrategy junction table
- [x] Enhance TradingView webhook to extract strategy info
- [x] Create in-house strategy runner service (`app/services/strategy_runner.py`)
- [x] Implement MA cross toy strategy
- [x] Add strategy enable/disable endpoints
- [x] Add strategy execution endpoints (`/api/v1/strategy-execution/run`, `/start-periodic`, `/stop-periodic`)
- [x] Update SignalRequest schema with strategy fields

### Phase 3: Auth + Onboarding
- [ ] Verify signup/login works
- [ ] Implement API key CRUD
- [ ] Create `scripts/smoke_user_flow.sh`
- [ ] Test end-to-end user flow
- [ ] Log results to `logs/smoke_user_flow_<timestamp>.log`

### Phase 4: Remove Demo UI Data
- [ ] Create missing UI pages (Dashboard, Accounts, Positions, Trades, Signals, Admin)
- [ ] Add `VITE_API_BASE_URL` env var
- [ ] Connect all pages to real backend APIs
- [ ] Verify no mock data remains

### Phase 5: Dual Strategy Mode
- [ ] Add strategy fields to Signal model
- [ ] Create Strategy registry table
- [ ] Enhance TradingView webhook to extract strategy info
- [ ] Create in-house strategy runner service
- [ ] Implement MA cross toy strategy
- [ ] Add strategy enable/disable endpoints

### Phase 6: Final Verification
- [ ] Create `scripts/deploy_one.sh`
- [ ] Create `scripts/verify_one.sh`
- [ ] Run full verification
- [ ] Update README.md
- [ ] Create FINAL_GREEN_REPORT.md

---

## 13. ARCHITECTURE DIAGRAM (TEXT)

```
┌─────────────────────────────────────────────────────────────┐
│                    NGINX (Port 3013)                        │
│                  Reverse Proxy / Load Balancer               │
└──────────────────────┬───────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────┐          ┌────────▼────────┐
│   UI (3411)    │          │  API (3012)    │
│   React App    │          │  FastAPI       │
│                │          │                │
│  - Dashboard   │◄─────────┤  - Auth        │
│  - Accounts    │  HTTP    │  - Accounts    │
│  - Positions   │          │  - Positions   │
│  - Trades      │          │  - Trades      │
│  - Signals     │          │  - Signals     │
│  - Admin       │          │  - Webhooks    │
└────────────────┘          └───────┬────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
            ┌───────▼────┐   ┌──────▼─────┐   ┌─────▼──────┐
            │ PostgreSQL │   │   Redis    │   │   NATS     │
            │  Database  │   │   Cache    │   │  Events    │
            └────────────┘   └────────────┘   └────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
            ┌───────▼────┐   ┌──────▼─────┐   ┌─────▼──────┐
            │  Celery    │   │   Celery   │   │  Flower    │
            │  Worker    │   │   Beat     │   │  Monitor   │
            └────────────┘   └────────────┘   └────────────┘

External:
  - TradingView Webhooks → /api/v1/webhooks/tradingview
  - In-House Strategies → Strategy Runner Service
  - Broker APIs (MT4, MT5, TradeLocker, Tradovate, ProjectX)
```

---

**END OF AUDIT REPORT**
