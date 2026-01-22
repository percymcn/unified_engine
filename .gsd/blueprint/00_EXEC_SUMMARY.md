# Executive Summary: Unified Trading Engine (Tradeflow)

## What This System Is

**Tradeflow** is a unified trading signal routing engine that:
1. Receives trading signals from TradingView, Trailhacker, or custom webhooks
2. Routes signals to multiple broker accounts simultaneously
3. Executes trades via broker APIs (TradeLocker, ProjectX/TopStep, MT4, MT5, Tradovate)
4. Provides risk management, position tracking, and trade logging

**Tech Stack:**
- Backend: FastAPI (Python 3.13) with hexagonal architecture
- Frontend: Next.js 14 (React 18, TypeScript)
- Database: PostgreSQL 15 (SQLAlchemy 2.0.23)
- Cache: Redis 7
- Message Bus: NATS (optional, graceful fallback)

## Git State

```
Branch: main
Tag: v1.1-7-g8fe4681
Latest commits:
  8fe4681 docs: research v1.2 broker integration patterns
  e26c9f0 docs: start milestone v1.2 Full Broker Integration
  11ce370 fix: resolve auth cookie, risk page, and WebSocket issues
```

## What "Shipped v1.1" Means

v1.1 (Production Ready) includes:
- Complete FastAPI backend with 30+ API routes
- Multi-broker support (TradeLocker, TopStep/ProjectX, MT4, MT5, Tradovate)
- Hexagonal architecture (domain/application/infrastructure layers)
- Dual-mode broker auth (SDK + API fallback)
- Next.js 14 dashboard UI with shadcn/ui
- Stripe billing integration
- Risk management with daily limits, drawdown tracking
- WebSocket real-time updates
- Alembic migrations (17 migration files)

## How to Run Locally

### 1. Start Infrastructure (DB + Redis)

```bash
cd /home/pharma5/unified_engine
docker compose up -d postgres redis
# Ports: PostgreSQL 5432, Redis 6379
```

### 2. Start Backend

```bash
# Activate venv
source venv/bin/activate

# Set environment
export DATABASE_URL="postgresql://trading_user:trading_password@localhost:5432/trading_db"

# Run migrations
python -m alembic upgrade head

# Start API server
python run_backend.py
# OR
uvicorn app.main:app --host 0.0.0.0 --port 8765 --reload
```

**Backend runs on: http://localhost:8765**

### 3. Start Frontend (UI)

```bash
cd ui-next
npm install
PORT=3456 npm run start  # Production mode
# OR
PORT=3456 npm run dev    # Development mode
```

**UI runs on: http://localhost:3456** (Cloudflare tunnel expects 3456)

### 4. Health Checks

```bash
# Backend health
curl http://localhost:8765/health

# UI health
curl http://localhost:3456/api/health
```

## Key Entry Points

| Component | File | Purpose |
|-----------|------|---------|
| Backend Main | `app/main.py` | FastAPI app, lifespan, router includes |
| Signal Processor | `app/services/signal_processor.py` | Webhook → broker routing |
| Broker Adapters | `app/infrastructure/adapters/` | BrokerPort implementations |
| Broker Executors | `app/brokers/` | Low-level broker API calls |
| UI App | `ui-next/src/app/` | Next.js App Router pages |
| UI API Routes | `ui-next/src/app/api/` | BFF (Backend-for-Frontend) routes |

## External URLs

| Service | URL |
|---------|-----|
| UI (Cloudflare) | https://tradeflow.fluxeo.net |
| API (Cloudflare) | https://api.tradeflow.fluxeo.net |
| Webhook Endpoint | https://api.tradeflow.fluxeo.net/api/v1/webhooks/signal/{key} |

---
*Generated: 2026-01-22*
