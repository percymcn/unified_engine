# PASTE BACK TO CHATGPT

## Repository Info

```
Repository: unified_engine (Tradeflow)
Branch: main
Tag: v1.1-7-g8fe4681
Last Commit: 8fe4681 docs: research v1.2 broker integration patterns
Date: 2026-01-22
LOC: ~60k+ (500+ commits)
```

---

## Top 10 Important Paths

| Path | Purpose |
|------|---------|
| `app/main.py` | FastAPI entry point, router includes, lifespan |
| `app/services/signal_processor.py` | Webhook → broker signal routing |
| `app/infrastructure/adapters/tradelocker_adapter.py` | TradeLocker BrokerPort implementation |
| `app/infrastructure/adapters/topstep_adapter.py` | ProjectX/TopStep BrokerPort implementation |
| `app/brokers/tradelocker_executor.py` | TradeLocker low-level API (SDK + Brand API) |
| `app/brokers/projectx_executor.py` | ProjectX Gateway API calls (httpx) |
| `app/models/database_models.py` | ORM models (TradingAccount, Credential, etc.) |
| `app/routers/accounts.py` | Account CRUD + test-connection endpoint |
| `ui-next/src/app/dashboard/` | Next.js dashboard pages |
| `docker-stack.yml` | Production Docker Swarm deployment |

---

## Top 10 Important Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/auth/login` | JWT authentication |
| `GET /api/v1/auth/me` | Current user info |
| `POST /api/v1/accounts/test-connection` | Test broker credentials |
| `POST /api/v1/accounts/` | Create/save broker account |
| `GET /api/v1/accounts/` | List user's accounts |
| `POST /api/v1/accounts/{id}/sync` | Refresh account balance |
| `POST /api/v1/webhooks/signal/{key}` | Receive trading signal |
| `GET /api/v1/positions/` | List open positions |
| `GET /api/v1/unified/status` | System status |
| `GET /health` | Health check |

---

## TradeLocker Credential Fields

### Where Stored

**Database:** `trading_accounts` table
```sql
broker = 'tradelocker'
api_key = <encrypted>           -- Brand API mode
access_token = <encrypted>      -- JWT token
refresh_token = <encrypted>
token_expires_at = <timestamp>
```

**Credentials table:** (Fernet encrypted JSON)
```json
{
  "email": "user@tradelocker.com",
  "password": "...",
  "server": "Demo Server",
  "environment": "https://demo.tradelocker.com"
}
```

### Environment Variables (Fallback)
```bash
TRADELOCKER_USERNAME=user@example.com
TRADELOCKER_PASSWORD=password
TRADELOCKER_SERVER=Demo Server
TRADELOCKER_ENVIRONMENT=https://demo.tradelocker.com
```

### Used In
- `app/brokers/tradelocker_executor.py:__init__()` - Loads from settings
- `app/brokers/tradelocker_sdk_wrapper.py:initialize()` - SDK auth
- `app/routers/accounts.py:test_connection()` - Connection test

---

## ProjectX/TopStep Credential Fields

### Where Stored

**Database:** `trading_accounts` table
```sql
broker = 'projectx' OR 'topstep'
account_number = <TopStep account ID>
api_key = <encrypted API key>
access_token = <encrypted JWT>
token_expires_at = <24h from auth>
```

### Environment Variables
```bash
PROJECT_X_USERNAME=topstep-username
PROJECT_X_API_KEY=api-key-here
PROJECTX_GATEWAY_API_URL=https://gateway-api-demo.s2f.projectx.com
```

### Used In
- `app/brokers/projectx_executor.py:__init__()` - Loads credentials
- `app/brokers/projectx_executor.py:_initialize_httpx()` - Auth call
- `app/routers/accounts.py:test_connection()` - Connection test

### Gateway API Auth Flow
```
POST /api/Auth/loginKey
Body: { "userName": "...", "apiKey": "..." }
Response: JWT token (text/plain or JSON)
Header: Authorization: Bearer <token>
Expiry: 24 hours
```

---

## Quick Start Commands

```bash
# Start infrastructure
docker compose up -d postgres redis

# Backend
export DATABASE_URL="postgresql://trading_user:trading_password@localhost:5432/trading_db"
python -m alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8765 --reload

# Frontend
cd ui-next
PORT=3456 npm run start

# Health check
curl http://localhost:8765/health
curl http://localhost:3456/api/health
```

---

## Files Generated

```
.gsd/blueprint/
├── 00_EXEC_SUMMARY.md      - What, how to run, shipped v1.1
├── 01_SYSTEM_MAP.md        - Architecture diagram, ports, structure
├── 02_DOMAIN_MODEL.md      - Entities, tables, migrations
├── 03_API_SURFACE.md       - All API endpoints grouped
├── 04_BROKER_WIRING.md     - Broker auth, happy paths, credentials
├── 05_DATA_FLOWS.md        - Signal flow, caching, WebSocket
├── 06_DEPLOYMENT_MAP.md    - Docker, env vars, ports
├── 07_GAPS_AND_BLOCKERS.md - What prevents live trading
├── 08_SMOKE_TESTS.md       - curl tests for core flows
└── 09_PASTE_BACK.md        - This summary
```

---
*Generated: 2026-01-22*
