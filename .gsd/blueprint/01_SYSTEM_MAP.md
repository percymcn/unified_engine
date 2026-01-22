# System Map: Unified Trading Engine

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL CLIENTS                                │
│  TradingView Webhooks    Browser/Mobile    Trailhacker    Custom Webhooks   │
└──────────────┬──────────────────┬───────────────────┬───────────────────────┘
               │                  │                   │
               ▼                  ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CLOUDFLARE TUNNEL                                   │
│  tradeflow.fluxeo.net (UI)     api.tradeflow.fluxeo.net (API)               │
└──────────────┬──────────────────────────────────────┬───────────────────────┘
               │                                      │
               ▼                                      ▼
┌──────────────────────────────┐    ┌────────────────────────────────────────┐
│      NEXT.JS UI (3456)       │    │         FASTAPI BACKEND (8765)         │
│  ui-next/src/app/            │    │  app/main.py                           │
│  ├── dashboard/              │◄──►│  ├── routers/   (30+ API routes)       │
│  ├── api/ (BFF routes)       │    │  ├── services/  (business logic)       │
│  └── login, register         │    │  ├── domain/    (entities, ports)      │
└──────────────────────────────┘    │  └── infrastructure/ (adapters)        │
                                    └──────────────┬─────────────────────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────────────┐
                    │                              │                          │
                    ▼                              ▼                          ▼
┌───────────────────────────┐  ┌───────────────────────────┐  ┌─────────────────────┐
│    POSTGRESQL (5432)      │  │      REDIS (6379)         │  │    NATS (4222)      │
│  unified_trading_db       │  │  unified_trading_redis    │  │  (optional)         │
│  - users                  │  │  - Session cache          │  │  - Event bus        │
│  - trading_accounts       │  │  - Rate limiting          │  │  - Pub/sub          │
│  - webhook_configs        │  │  - Signal dedup           │  └─────────────────────┘
│  - signals, trades        │  │                           │
│  - credentials (encrypted)│  └───────────────────────────┘
└───────────────────────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────────────┐
                    │                              │                          │
                    ▼                              ▼                          ▼
┌───────────────────────────┐  ┌───────────────────────────┐  ┌─────────────────────┐
│      BROKER ADAPTERS      │  │      BROKER ADAPTERS      │  │   BROKER ADAPTERS   │
│  ┌─────────────────────┐  │  │  ┌─────────────────────┐  │  │ ┌─────────────────┐ │
│  │ TradeLocker         │  │  │  │ TopStep/ProjectX    │  │  │ │ MT4/MT5         │ │
│  │ - SDK mode          │  │  │  │ - Gateway API       │  │  │ │ - Manager API   │ │
│  │ - Brand API mode    │  │  │  │ - httpx client      │  │  │ │ - REST bridge   │ │
│  └─────────────────────┘  │  │  └─────────────────────┘  │  │ └─────────────────┘ │
│  ┌─────────────────────┐  │  │                           │  │ ┌─────────────────┐ │
│  │ Tradovate           │  │  │                           │  │ │                 │ │
│  │ - OAuth flow        │  │  │                           │  │ │                 │ │
│  │ - REST + WebSocket  │  │  │                           │  │ │                 │ │
│  └─────────────────────┘  │  │                           │  │ └─────────────────┘ │
└───────────────────────────┘  └───────────────────────────┘  └─────────────────────┘
```

## Network / Port Allocation

### Local Development

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| PostgreSQL | unified_trading_db | 5432 | Primary database |
| Redis | unified_trading_redis | 6379 | Cache & sessions |
| FastAPI | - | 8765 | Backend API (run_backend.py) |
| Next.js | - | 3456 | Frontend UI (npm run start) |
| NATS | - | 4222 | Event bus (optional) |

### Docker Compose Services

File: `docker-compose.yml`

```yaml
services:
  postgres:     # Port 5432
  redis:        # Port 6379
  api:          # Port 8000 (inside container)
  celery:       # No external port
```

### Docker Stack (Swarm) Services

File: `docker-stack.yml`

```yaml
services:
  postgres:     # Internal only (overlay network)
  redis:        # Internal only
  nats:         # Port 4223:4222 (external:internal)
  api:          # Port 8765 (published)
  ui:           # Port 3456 (published)
  cloudflared:  # Tunnel to Cloudflare
```

## Runtime Entry Points

### Backend Entry Point

```
app/main.py
├── FastAPI app creation
├── Lifespan manager (startup/shutdown)
├── Router includes (30+ routers)
├── CORS, TrustedHost middleware
├── WebSocket endpoint at /ws
└── Health endpoint at /health
```

Key initialization flow:
1. `Base.metadata.create_all()` - DB tables
2. `redis_client._connect()` - Redis
3. `Container.initialize()` - DI container
4. `event_emitter.initialize()` - NATS (optional)
5. `signal_processor.initialize()` - Broker connections

### UI Entry Point

```
ui-next/src/app/
├── layout.tsx          # Root layout with providers
├── page.tsx            # Landing page
├── login/page.tsx      # Login form
├── register/page.tsx   # Registration
├── dashboard/          # Protected dashboard
│   ├── page.tsx        # Main dashboard
│   └── settings/       # Settings pages
└── api/                # BFF (backend-for-frontend)
    ├── auth/           # Auth proxy routes
    ├── accounts/       # Account proxy routes
    └── risk/           # Risk settings proxy
```

## Directory Structure Overview

```
/home/pharma5/unified_engine/
├── app/                          # Backend application
│   ├── main.py                   # FastAPI entry point
│   ├── core/                     # Config, settings, websocket
│   ├── db/                       # Database session, engine
│   ├── models/                   # SQLAlchemy ORM models
│   ├── routers/                  # API route handlers (30+)
│   ├── services/                 # Business logic services
│   ├── domain/                   # Hexagonal domain layer
│   │   ├── entities/             # Domain entities
│   │   ├── ports/                # Interface definitions
│   │   ├── services/             # Domain services
│   │   └── value_objects.py      # Value objects
│   ├── infrastructure/           # Hexagonal infra layer
│   │   └── adapters/             # Broker adapters (BrokerPort impls)
│   ├── brokers/                  # Broker executors (low-level)
│   └── tasks/                    # Background tasks (Celery)
├── ui-next/                      # Next.js frontend
│   ├── src/app/                  # App Router pages
│   ├── src/components/           # React components
│   ├── src/lib/                  # Utilities, auth
│   └── src/hooks/                # Custom React hooks
├── alembic/                      # DB migrations
│   └── versions/                 # 17 migration files
├── docker-compose.yml            # Local dev compose
├── docker-stack.yml              # Production swarm
├── requirements.txt              # Python dependencies
└── .env.example                  # Environment template
```

---
*Generated: 2026-01-22*
