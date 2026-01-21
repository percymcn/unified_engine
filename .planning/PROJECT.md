# Unified Trading Engine

## What This Is

A signal routing engine that receives TradingView webhook alerts and executes trades across multiple brokers (TradeLocker, TopStep/ProjectX, Tradovate, MT4, MT5). Users configure accounts, set routing rules, and monitor executions in real-time via a modern Next.js dashboard with clean hexagonal architecture.

## Core Value

**Reliable signal-to-trade execution across all configured brokers with zero missed signals.**

If everything else fails, signals must reach brokers and trades must execute. The UI can be down, metrics can fail, but the signal pipeline cannot.

## Current Milestone: v1.1 Production Ready with Monetization

**Goal:** Rebrand to Tradeflow, fix critical bugs, integrate official broker SDKs, polish UI/UX, add marketing landing page with Stripe subscription billing.

**Target features:**

**Branding:**
- Rename "Unified Engine" to "Tradeflow" everywhere

**Infrastructure:**
- Frontend: https://tradeflow.fluxeo.net (port 3456)
- Backend: https://api.tradeflow.fluxeo.net (port 8765)
- Backend bound to LAN IP for Caddy routing

**Critical Fixes:**
- Fix "Failed to fetch webhook configs" API error
- Replace hardcoded localhost with NEXT_PUBLIC_API_URL env var
- Fix 5-10 second UI lag with loading skeletons
- Fix desktop sidebar not clickable (works mobile, broken laptop)
- Fix WebSocket "Disconnected" status
- Fix webhook URLs showing localhost (should show public domain)
- Fix dashboard showing "-" (fetch real data)

**Broker SDK Integrations:**
- TradeLocker — `pip install tradelocker` (official SDK, JWT auth)
- Tradovate — OAuth 2.0 redirect flow (redirect to login, capture token callback)
- TopStep/ProjectX — `pip install project-x-py`
- MT4/MT5 — `pip install metaapi-cloud-sdk`

**UI Enhancements:**
- User Profile page (edit name/email/avatar, change password, notification prefs)
- Settings page (position sizing defaults, risk rules, timezone)
- Fix sidebar navigation (back button, active states, mobile menu)
- Dashboard improvements (real-time updates, loading skeletons, quick actions)

**Landing Page + Stripe:**
- Marketing landing page at "/" (hero, features, pricing, testimonials)
- Pricing plans: Free (1 broker), Pro ($29/mo all brokers)
- Stripe integration (checkout, customer portal, webhooks)
- Auth flow: Landing → Signup → Payment/Trial → Dashboard

**OAuth Callback Pages:**
- /auth/tradovate/callback — handle Tradovate OAuth redirect
- /auth/callback — generic OAuth handler

---

## v1.0 Shipped

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

<!-- Building toward these — v1.1 -->

**Branding:**
- [ ] Rename "Unified Engine" to "Tradeflow" everywhere (code, UI, docs)

**Infrastructure:**
- [ ] Frontend URL: https://tradeflow.fluxeo.net (port 3456)
- [ ] Backend URL: https://api.tradeflow.fluxeo.net (port 8765)
- [ ] Backend bound to LAN IP for Caddy routing

**Critical Fixes:**
- [ ] Fix webhook configs API error
- [ ] Use NEXT_PUBLIC_API_URL env var (no hardcoded localhost)
- [ ] Fix UI lag with loading skeletons
- [ ] Fix desktop sidebar not clickable (works on mobile, broken on laptop)
- [ ] Fix WebSocket "Disconnected" status
- [ ] Fix webhook URLs showing localhost (should show public domain)
- [ ] Fix dashboard showing "-" (fetch real data from backend)

**Broker SDKs:**
- [ ] TradeLocker — official SDK with JWT auth
- [ ] Tradovate — OAuth 2.0 redirect flow
- [ ] TopStep/ProjectX — project-x-py SDK
- [ ] MT4/MT5 — metaapi-cloud-sdk

**UI/UX:**
- [ ] User Profile page
- [ ] Settings page (position sizing, risk rules, timezone)
- [ ] Sidebar navigation fixes (back button, active states, mobile)
- [ ] Dashboard real-time updates and loading states

**Monetization:**
- [ ] Marketing landing page at "/"
- [ ] Stripe checkout integration
- [ ] Stripe customer portal
- [ ] Stripe webhooks for subscription management
- [ ] Pricing tiers: Free (1 broker), Pro ($29/mo)

**OAuth:**
- [ ] /auth/tradovate/callback page
- [ ] /auth/callback generic handler

### Out of Scope

- Mobile app — web-first approach, PWA works
- Additional broker integrations — stabilize current 5 first
- Multi-tenancy — single-user/single-org for v1
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
| Fix tests before refactor | Ensures we don't break existing functionality | ✓ Good |
| Fernet symmetric encryption | Standard for credential storage, key from environment | ✓ Good |
| bcrypt for API keys | Rainbow table protection vs SHA256 | ✓ Good |
| httpOnly cookies for JWT | XSS protection, BFF pattern | ✓ Good |
| Domain layer strictly isolated | No FastAPI/SQLAlchemy imports in domain | ✓ Good |
| DI container in FastAPI lifespan | Clean initialization and shutdown | ✓ Good |

---
*Last updated: 2026-01-21 after starting v1.1 milestone*
