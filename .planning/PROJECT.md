# Unified Trading Engine

## What This Is

A signal routing engine that receives TradingView webhook alerts and executes trades across multiple brokers (TradeLocker, TopStep/ProjectX, Tradovate, MT4, MT5). Users configure accounts, set routing rules, and monitor executions in real-time. This refactor rebuilds the system with clean hexagonal architecture while preserving all existing functionality.

## Core Value

**Reliable signal-to-trade execution across all configured brokers with zero missed signals.**

If everything else fails, signals must reach brokers and trades must execute. The UI can be down, metrics can fail, but the signal pipeline cannot.

## Requirements

### Validated

<!-- Shipped and confirmed valuable — inferred from existing codebase -->

- ✓ TradingView webhook signal ingestion (`/api/v1/webhooks/tradingview`) — existing
- ✓ TrailHacker webhook signal ingestion (`/api/v1/webhooks/trailhacker`) — existing
- ✓ Multi-broker trade execution via unified abstraction layer — existing
- ✓ TradeLocker broker integration with REST + WebSocket — existing
- ✓ TopStep/ProjectX broker integration — existing
- ✓ Tradovate futures broker integration — existing
- ✓ MT4/MT5 MetaTrader broker integration — existing
- ✓ PostgreSQL database with SQLAlchemy ORM — existing
- ✓ Redis caching and session storage — existing
- ✓ WebSocket real-time updates to connected clients — existing
- ✓ JWT authentication for API endpoints — existing
- ✓ API key authentication for webhooks — existing
- ✓ Docker containerization with compose files — existing
- ✓ Alembic database migrations — existing
- ✓ Health check endpoints (`/healthz`, `/status`) — existing
- ✓ Prometheus metrics endpoint (`/metrics`) — existing
- ✓ Structured JSON logging — existing

### Active

<!-- Current scope. Building toward these. -->

**Architecture Refactor:**
- [ ] Hexagonal architecture with ports and adapters pattern
- [ ] Domain layer with pure business logic (no framework deps)
- [ ] Application layer with use cases and orchestration
- [ ] Infrastructure layer with concrete implementations
- [ ] Clear dependency inversion (domain doesn't import infrastructure)

**New UI (Next.js 14):**
- [ ] Modern dashboard with dark theme (shadcn/ui)
- [ ] Real-time signal status display
- [ ] Broker connection health monitoring
- [ ] Trade execution logs with filtering
- [ ] Account balances per broker
- [ ] Signal routing rules configuration
- [ ] API key management interface
- [ ] Webhook endpoint management
- [ ] Account CRUD operations

**Backend Fixes:**
- [ ] Fix aioredis deprecated import (migrate to redis.asyncio)
- [ ] Persist encryption key in environment (not generated at runtime)
- [ ] Move credential storage from in-memory to database
- [ ] Implement actual Celery task logic (not placeholders)
- [ ] Remove hardcoded API keys from source code
- [ ] Encrypt OAuth tokens in database
- [ ] Fix NATS connection issues with proper error handling

**Testing:**
- [ ] All 101 tests passing
- [ ] Test coverage for broker executor error handling
- [ ] Test coverage for signal processing rollback

**Deployment:**
- [ ] Docker Swarm deployment ready (docker-stack.yml)
- [ ] Environment-based configuration (dev/staging/prod)
- [ ] Secret management via Docker secrets

### Out of Scope

- Mobile app — web-first approach, mobile later
- Additional broker integrations beyond existing 5 — stabilize current first
- Multi-tenancy — single-user/single-org for v1
- Billing/payments — not a SaaS product yet
- CI/CD pipeline setup — deployment scripts exist, manual for now
- High availability (HA) database — single PostgreSQL instance sufficient

## Context

**Existing Codebase State:**
- Backend: FastAPI 0.104.1 with Python 3.13.7
- Frontend: React 18 with Vite (being replaced)
- Database: PostgreSQL 15 with SQLAlchemy 2.0.23
- 90/101 tests currently failing (fixture/setup issues)
- Several services crash on startup (aioredis import, missing API keys)
- Celery tasks are placeholder implementations
- Credential storage is in-memory (lost on restart)

**Codebase Mapping Available:**
- `.planning/codebase/ARCHITECTURE.md` — current layered architecture
- `.planning/codebase/STACK.md` — technology stack details
- `.planning/codebase/CONCERNS.md` — tech debt and known issues
- `.planning/codebase/INTEGRATIONS.md` — external service integrations
- `.planning/codebase/STRUCTURE.md` — directory layout
- `.planning/codebase/CONVENTIONS.md` — code style patterns
- `.planning/codebase/TESTING.md` — test structure

**Reference UIs:**
- `ui/` — current React/Vite UI (TypeScript)
- `ui.old.backup/` — older React UI (JSX)
- Both contain feature references for what UI needs to support

## Constraints

- **Tech Stack**: FastAPI backend (keep), Next.js 14 frontend (new), PostgreSQL, Redis, Docker Swarm
- **Auth**: Self-hosted JWT only (no Supabase dependency)
- **UI Framework**: shadcn/ui with dark theme, Tailwind CSS
- **Broker SDKs**: Use existing SDKs in `broker_sdks/` directory
- **Deployment**: Must work with Docker Swarm orchestration
- **Backwards Compatible**: All existing API endpoints must continue working

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Full hexagonal architecture | Clean separation enables testing and future broker additions | — Pending |
| Self-hosted JWT auth | Removes Supabase dependency, simpler deployment | — Pending |
| Next.js 14 over React/Vite | Better SSR, built-in API routes for BFF pattern, shadcn native | — Pending |
| Keep all 5 broker integrations | User needs all of them working | — Pending |
| Fix tests before refactor | Ensures we don't break existing functionality | — Pending |

---
*Last updated: 2026-01-19 after initialization*
