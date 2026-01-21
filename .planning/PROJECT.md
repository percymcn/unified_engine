# Unified Trading Engine

## What This Is

A signal routing engine that receives TradingView webhook alerts and executes trades across multiple brokers (TradeLocker, TopStep/ProjectX, Tradovate, MT4, MT5). Users configure accounts, set routing rules, and monitor executions in real-time via a modern Next.js dashboard with clean hexagonal architecture.

## Core Value

**Reliable signal-to-trade execution across all configured brokers with zero missed signals.**

If everything else fails, signals must reach brokers and trades must execute. The UI can be down, metrics can fail, but the signal pipeline cannot.

## Current State (v1.0 Shipped)

**Shipped:** 2026-01-21

The v1.0 milestone delivered a complete refactor of the trading engine:

- **Backend:** FastAPI 0.104.1 with hexagonal architecture (domain/application/infrastructure layers)
- **Frontend:** Next.js 14 with shadcn/ui dark theme dashboard
- **Database:** PostgreSQL 15 with encrypted credential storage (Fernet)
- **Brokers:** 5 adapters implementing BrokerPort (TradeLocker, TopStep, Tradovate, MT4, MT5)
- **Security:** bcrypt API keys, encrypted OAuth tokens, Docker secrets
- **Deployment:** Docker Swarm with health checks and persistent volumes

**Stats:**
- 11 phases, 63 plans executed
- 33 requirements satisfied
- ~500 minutes total execution

## Requirements

### Validated

<!-- Shipped and confirmed valuable -->

**v1.0 (2026-01-21):**
- ✓ Hexagonal architecture with ports/adapters pattern — v1.0
- ✓ Domain layer with pure business logic — v1.0
- ✓ Application layer with use cases — v1.0
- ✓ Infrastructure layer with adapters — v1.0
- ✓ Dependency inversion (domain isolated) — v1.0
- ✓ Next.js 14 dashboard with dark theme — v1.0
- ✓ Real-time signal status with WebSocket — v1.0
- ✓ Broker health monitoring — v1.0
- ✓ Trade logs with filtering — v1.0
- ✓ Account management with balances — v1.0
- ✓ Signal routing configuration — v1.0
- ✓ API key management — v1.0
- ✓ Webhook endpoint management — v1.0
- ✓ Encrypted credential storage (Fernet) — v1.0
- ✓ bcrypt API key hashing — v1.0
- ✓ OAuth token encryption — v1.0
- ✓ Docker Swarm deployment — v1.0
- ✓ Environment configs (dev/staging/prod) — v1.0
- ✓ Docker secrets integration — v1.0
- ✓ All 5 broker adapters working — v1.0

**Existing (pre-v1.0):**
- ✓ TradingView webhook ingestion — existing
- ✓ TrailHacker webhook ingestion — existing
- ✓ Multi-broker trade execution — existing
- ✓ PostgreSQL with SQLAlchemy — existing
- ✓ Redis caching — existing
- ✓ JWT authentication — existing
- ✓ Health check endpoints — existing

### Active

<!-- Building toward these -->

(None — define requirements for next milestone with `/gsd:define-requirements`)

### Out of Scope

- Mobile app — web-first approach, PWA works
- Additional broker integrations — stabilize current 5 first
- Multi-tenancy — single-user/single-org for v1
- Billing/payments — not a SaaS product yet
- CI/CD pipeline — deployment scripts exist, manual for now
- HA database — single PostgreSQL instance sufficient

## Context

**Current Codebase:**
- Backend: FastAPI 0.104.1, Python 3.13.7, hexagonal architecture
- Frontend: Next.js 14.2.35, React 18, shadcn/ui, TypeScript
- Database: PostgreSQL 15, SQLAlchemy 2.0.23, Alembic migrations
- Tests: 173 tests collected (some skipped due to missing socketio)
- Deployment: Docker Swarm ready with health checks

**Codebase Mapping:**
- `.planning/codebase/` — architecture, stack, concerns, integrations

**Archives:**
- `.planning/milestones/v1.0-ROADMAP.md` — full v1.0 roadmap
- `.planning/milestones/v1.0-REQUIREMENTS.md` — v1.0 requirements
- `.planning/milestones/v1.0-MILESTONE-AUDIT.md` — audit report

## Constraints

- **Tech Stack**: FastAPI backend, Next.js 14 frontend, PostgreSQL, Redis, Docker Swarm
- **Auth**: Self-hosted JWT only (no external auth providers)
- **UI Framework**: shadcn/ui with dark theme, Tailwind CSS
- **Broker SDKs**: Use existing SDKs in `broker_sdks/`
- **Deployment**: Docker Swarm orchestration
- **Backwards Compatible**: API endpoints preserved

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Full hexagonal architecture | Clean separation enables testing and future broker additions | ✓ Good |
| Self-hosted JWT auth | Removes Supabase dependency, simpler deployment | ✓ Good |
| Next.js 14 over React/Vite | Better SSR, built-in API routes for BFF pattern | ✓ Good |
| Keep all 5 broker integrations | User needs all of them working | ✓ Good |
| Fix tests before refactor | Ensures we don't break existing functionality | ✓ Good |
| Fernet symmetric encryption | Standard for credential storage, key from environment | ✓ Good |
| bcrypt for API keys | Rainbow table protection vs SHA256 | ✓ Good |
| httpOnly cookies for JWT | XSS protection, BFF pattern | ✓ Good |
| Domain layer strictly isolated | No FastAPI/SQLAlchemy imports in domain | ✓ Good |
| DI container in FastAPI lifespan | Clean initialization and shutdown | ✓ Good |

---
*Last updated: 2026-01-21 after v1.0 milestone*
