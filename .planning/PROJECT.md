# Tradeflow (formerly Unified Trading Engine)

## What This Is

A production-ready SaaS signal routing engine that receives TradingView webhook alerts and executes trades across multiple brokers (TradeLocker, TopStep/ProjectX, Tradovate, MT4, MT5). Users configure accounts, set routing rules, select which accounts receive signals, and monitor executions in real-time via a modern Next.js dashboard. Includes 4-tier Stripe subscription billing, free trial system, comprehensive risk management, and enterprise-grade landing page.

## Core Value

**Reliable signal-to-trade execution across all configured brokers with zero missed signals.**

If everything else fails, signals must reach brokers and trades must execute. The UI can be down, metrics can fail, but the signal pipeline cannot.

## Current State

**v1.1 Production Ready with Monetization** — Shipped 2026-01-22

Tradeflow is now a complete SaaS platform with:
- 4-tier pricing ($19.99-$129.99/month) with Stripe billing
- Free trial: 100 trades OR 3 days
- Official broker SDKs: TradeLocker, ProjectX, Tradovate OAuth, MetaAPI
- Multi-account signal routing with account selection UI
- Comprehensive risk management and position sizing
- Enterprise landing page with testimonials and animated charts

**Stats:**
- 60,648 lines of code (Python + TypeScript)
- 24 phases, 110 plans executed across v1.0 and v1.1
- 160 requirements satisfied

## Next Milestone Goals

*To be defined via `/gsd:discuss-milestone` and `/gsd:new-milestone`*

Potential directions:
- Production hardening and monitoring
- Mobile optimization / PWA enhancements
- Additional broker integrations
- Advanced analytics and reporting
- Performance optimization

---

## v1.1 Shipped

**Shipped:** 2026-01-22

Complete SaaS transformation:

- **Billing:** 4-tier Stripe pricing ($19.99, $39.99, $69.99, $129.99)
- **Trial:** 100 trades OR 3 days free trial with upgrade prompts
- **Broker SDKs:** All 4 brokers using official packages
- **Risk Management:** Position sizing, daily loss limits, drawdown protection
- **Signal Protection:** Deduplication, cooldown, rejected signal logging
- **Multi-Account:** Account selection per broker, routing to multiple accounts
- **Symbol Mapping:** Auto-detection, aliases, futures rollover
- **Landing Page:** Enterprise design with testimonials, animated charts
- **Dashboard:** Equity chart, positions, executions, risk meters, trial status

**Stats:**
- 13 phases (12-24), 47 plans executed
- 127 requirements satisfied
- 288 commits, 475 files changed

## v1.0 Shipped

**Shipped:** 2026-01-21

Complete hexagonal architecture refactor:

- **Backend:** FastAPI 0.104.1 with domain/application/infrastructure layers
- **Frontend:** Next.js 14 with shadcn/ui dark theme dashboard
- **Database:** PostgreSQL 15 with encrypted credential storage (Fernet)
- **Brokers:** 5 adapters implementing BrokerPort
- **Security:** bcrypt API keys, encrypted OAuth tokens, Docker secrets
- **Deployment:** Docker Swarm with health checks and persistent volumes

**Stats:**
- 11 phases (1-11), 63 plans executed
- 33 requirements satisfied
- ~500 minutes total execution

## Requirements

### Validated

**v1.1 (2026-01-22):**
- ✓ Tradeflow branding complete — v1.1
- ✓ Production URLs configured (tradeflow.fluxeo.net) — v1.1
- ✓ All critical UI bugs fixed — v1.1
- ✓ 4-tier Stripe billing ($19.99-$129.99) — v1.1
- ✓ Free trial (100 trades OR 3 days) — v1.1
- ✓ TradeLocker official SDK — v1.1
- ✓ Tradovate OAuth 2.0 — v1.1
- ✓ ProjectX official SDK — v1.1
- ✓ MetaAPI SDK for MT4/MT5 — v1.1
- ✓ Symbol mapping with auto-detection — v1.1
- ✓ Futures rollover support — v1.1
- ✓ Multi-account per broker — v1.1
- ✓ Account selection UI with checkboxes — v1.1
- ✓ Signal routing to multiple accounts — v1.1
- ✓ Position sizing (fixed, %, risk-based) — v1.1
- ✓ Risk management (daily loss, drawdown limits) — v1.1
- ✓ Signal deduplication — v1.1
- ✓ Enterprise landing page — v1.1
- ✓ Testimonials and animated charts — v1.1
- ✓ User profile and preferences — v1.1
- ✓ Dark/light theme toggle — v1.1
- ✓ Dashboard widgets (equity, positions, executions) — v1.1

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

*No active requirements — next milestone not yet defined*

Run `/gsd:define-requirements` after `/gsd:new-milestone` to scope v1.2 or v2.0.

### Out of Scope

- Mobile app — web-first approach, PWA works
- Additional broker integrations — stabilize current 5 first
- Multi-tenancy — single-user/single-org for v1
- CI/CD pipeline — deployment scripts exist, manual for now
- HA database — single PostgreSQL instance sufficient
- Credit-based pricing — confusing, use simple tier gating
- Per-trade fees — creates anxiety, discourages usage

## Context

**Current Codebase:**
- Backend: FastAPI 0.104.1, Python 3.13.7, hexagonal architecture
- Frontend: Next.js 14.2.35, React 18, shadcn/ui, TypeScript
- Database: PostgreSQL 15, SQLAlchemy 2.0.23, Alembic migrations
- Total: 60,648 lines of code

**Codebase Mapping:**
- `.planning/codebase/` — architecture, stack, concerns, integrations

**Archives:**
- `.planning/milestones/v1.1-ROADMAP.md` — full v1.1 roadmap
- `.planning/milestones/v1.1-REQUIREMENTS.md` — v1.1 requirements
- `.planning/milestones/v1.0-ROADMAP.md` — full v1.0 roadmap
- `.planning/milestones/v1.0-REQUIREMENTS.md` — v1.0 requirements
- `.planning/milestones/v1.0-MILESTONE-AUDIT.md` — v1.0 audit report

## Constraints

- **Tech Stack**: FastAPI backend, Next.js 14 frontend, PostgreSQL, Redis, Docker Swarm
- **Auth**: Self-hosted JWT only (no external auth providers for user auth)
- **UI Framework**: shadcn/ui with dark theme, Tailwind CSS
- **Broker SDKs**: Official SDKs — tradelocker, project-x-py, metaapi-cloud-sdk
- **Payments**: Stripe for subscriptions (checkout, portal, webhooks)
- **Deployment**: Docker Swarm orchestration
- **Backwards Compatible**: API endpoints preserved

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Full hexagonal architecture | Clean separation enables testing and future broker additions | ✓ Good |
| Self-hosted JWT auth | Removes Supabase dependency, simpler deployment | ✓ Good |
| Next.js 14 over React/Vite | Better SSR, built-in API routes for BFF pattern | ✓ Good |
| Keep all 5 broker integrations | User needs all of them working | ✓ Good |
| Fernet symmetric encryption | Standard for credential storage, key from environment | ✓ Good |
| bcrypt for API keys | Rainbow table protection vs SHA256 | ✓ Good |
| httpOnly cookies for JWT | XSS protection, BFF pattern | ✓ Good |
| 4-tier pricing model | Clear value ladder, each tier unlocks +1 broker | ✓ Good |
| Trial auto-starts on first signal | Zero friction UX, no manual start required | ✓ Good |
| Fail-open on risk/trial errors | System issues don't block legitimate trades | ✓ Good |
| In-memory OAuth state store | Simple for single-instance; needs Redis for multi-instance | ⚠️ Revisit |

---
*Last updated: 2026-01-22 after v1.1 milestone completion*
