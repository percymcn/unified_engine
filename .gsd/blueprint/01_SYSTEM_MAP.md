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
1. Alembic migrations (production) or `create_all()` (dev fallback)
2. `redis_client._connect()` - Redis
3. `Container.initialize()` - DI container
4. `event_emitter.initialize()` - NATS (optional)
5. `signal_processor.initialize()` - Broker connections

**Important:** Production uses migrations-first (`alembic upgrade head`). Never use `create_all()` to fix schema.

---

## Signal Intelligence Guard Layer (Milestone 1.2)

### Guard Injection Points

```
Webhook Endpoint             Guard Layer                    Execution
─────────────────────────────────────────────────────────────────────
/webhooks/tradingview ──────► evaluate_guard_layer() ──────► process_signal_use_case
/webhooks/trailhacker ──────► evaluate_guard_layer() ──────► process_signal_use_case
/webhooks/signal/{key} ─────► evaluate_guard_layer() ──────► process_signal_use_case
/webhooks/incoming ─────────► webhook_key validation ──────► evaluate_guard_layer() ──► process_signal_use_case
```

### Guard Checks (sg-001 to sg-007)

| ID | Guard | Decision |
|----|-------|----------|
| sg-002 | Staleness | SKIP if signal too old |
| sg-001 | Momentum | WARN_MODAL_REQUIRED if opposite threshold hit |
| sg-001 | Chop Detection | PAUSE_NEW_ENTRIES if alternating pattern |
| sg-004 | Max Exposure | PAUSE_NEW_ENTRIES if limit exceeded |
| sg-005 | Discard Bin | Log all skipped signals with audit trail |

### Fail-Open Design

Guard layer errors **never block execution**. If guard service throws:
- Log error
- Continue with `CONTINUE` decision
- Execution proceeds normally

---

## Secure Per-Broker Webhooks (Patch 1.2.1)

### Endpoint

```
POST /api/v1/webhooks/incoming?broker={broker}&user={userId}&key={webhook_key}
```

### Validation Flow

```
Incoming Request
      │
      ▼
Validate: broker + user + key match TradingAccount
      │
      ├── Match found → Route to that account ONLY
      │
      └── Mismatch → 403 Forbidden + log to discard_bin (reason: broker_mismatch)
```

### Webhook Key Format

```
webhook_{broker}_user{userId}_{random6}
Example: webhook_tradelocker_user1234_a8f3c1
```

---

## Theme Isolation (Patch 1.2.1)

### Route-Based Theme

| Route Pattern | Theme Behavior |
|---------------|----------------|
| `/dashboard/*`, `/app/*` | Uses user's `theme` preference (system/dark/light) |
| `/`, `/login`, `/register` | **Always dark** (landing page) |

### Theme Provider Logic

```typescript
// ui-next/src/providers/theme-provider.tsx
if (pathname.startsWith('/dashboard') || pathname.startsWith('/app')) {
  // Use theme from cookie/database
} else {
  // Force dark theme, ignore cookie
}
```

---

## Database Migrations Pipeline

### Current State

| Version | Purpose | Status |
|---------|---------|--------|
| 018 | Signal Intelligence tables | Applied |
| 019 | Per-broker webhooks + theme | Applied (fixed) |
| 020 | Bridge migration (schema drift) | Applied |

**Alembic Head:** 020

### Migration Rules

1. **Migrations-first**: Always use `alembic upgrade head`
2. **Never use `create_all()`** to fix schema in production
3. **Bridge migrations** for drift reconciliation (no drops)
4. **Test on clean DB** before production

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
