# Roadmap: Unified Trading Engine

## Overview

Full refactor of the trading signal routing engine from organic growth to clean hexagonal architecture. We start by stabilizing the existing system (critical bug fixes, test infrastructure), then rebuild the backend with proper separation of concerns, build a new Next.js UI, and finish with production deployment configuration. Every phase preserves existing functionality while improving architecture.

## Phases

- [x] **Phase 1: Stability Fixes** - Fix critical crashes blocking development
- [x] **Phase 2: Test Infrastructure** - Get all 101 tests passing as safety net
- [x] **Phase 3: Domain Layer** - Pure business logic with no framework deps
- [x] **Phase 4: Application Layer** - Use cases and service orchestration
- [x] **Phase 5: Infrastructure Adapters** - Broker executors with hexagonal pattern
- [ ] **Phase 6: Security Hardening** - Encryption, credential storage, secrets
- [ ] **Phase 7: UI Foundation** - Next.js 14 setup with auth and layout
- [ ] **Phase 8: UI Dashboard** - Signal status, broker health, trade logs
- [ ] **Phase 9: UI Configuration** - Account management, routing rules, API keys
- [ ] **Phase 10: Deployment** - Docker Swarm with secrets and env configs

## Phase Details

### Phase 1: Stability Fixes
**Goal**: Make the existing system run without crashes
**Depends on**: Nothing (first phase)
**Requirements**: STAB-01, STAB-02, STAB-03, STAB-04
**Success Criteria** (what must be TRUE):
  1. Backend starts without aioredis import errors
  2. Backend starts without broker initialization crashes (even with missing API keys)
  3. NATS connection failure doesn't crash the service
  4. No hardcoded API keys in source code
**Research**: Unlikely (bug fixes with known solutions from CONCERNS.md)
**Plans**: 4 plans (Wave 1: 01, 02, 03 | Wave 2: 04)

### Phase 2: Test Infrastructure
**Goal**: All existing tests pass to provide refactoring safety net
**Depends on**: Phase 1
**Requirements**: TEST-01, TEST-02, TEST-03
**Success Criteria** (what must be TRUE):
  1. pytest runs without fixture errors
  2. All 101 tests pass (or skipped with documented reason)
  3. Broker executor error scenarios have test coverage
**Research**: Unlikely (fixing existing test setup)
**Plans**: 5 plans (Wave 1: 01, 02 | Wave 2: 03, 04 | Wave 3: 05)

### Phase 3: Domain Layer
**Goal**: Pure business logic with no framework dependencies
**Depends on**: Phase 2
**Requirements**: ARCH-01, ARCH-04
**Success Criteria** (what must be TRUE):
  1. Domain models exist in `app/domain/` with no FastAPI/SQLAlchemy imports
  2. Signal, Trade, Account, Position entities defined as pure Python classes
  3. Port interfaces define broker, repository, and event contracts
  4. Domain layer has 100% test coverage with no mocking of external services
**Research**: Likely (hexagonal architecture patterns)
**Research topics**: Python hexagonal architecture examples, ports/adapters in FastAPI, domain modeling patterns
**Plans**: TBD

### Phase 4: Application Layer
**Goal**: Use cases orchestrating domain logic
**Depends on**: Phase 3
**Requirements**: ARCH-02
**Success Criteria** (what must be TRUE):
  1. Use cases exist in `app/application/` calling domain through ports
  2. ProcessSignalUseCase handles the complete signal-to-trade flow
  3. Use cases have no direct infrastructure imports
  4. Application layer tests use mock ports (no real database/brokers)
**Research**: Unlikely (follows from domain layer patterns)
**Plans**: 7 plans (Wave 1: 01, 02 | Wave 2: 03, 04 | Wave 3: 05, 06 | Wave 4: 07)

### Phase 5: Infrastructure Adapters
**Goal**: Concrete implementations of ports for all external services
**Depends on**: Phase 4
**Requirements**: ARCH-03, ARCH-05, BROK-01, BROK-02, BROK-03, BROK-04, BROK-05
**Success Criteria** (what must be TRUE):
  1. All broker executors implement BrokerPort interface
  2. TradeLocker adapter passes existing integration tests
  3. TopStep/ProjectX adapter passes existing integration tests
  4. Tradovate adapter passes existing integration tests
  5. MT4/MT5 adapters pass existing integration tests
  6. SQLAlchemy repository implements RepositoryPort
  7. Dependency injection wires adapters to use cases
**Research**: Likely (broker API changes, SDK updates)
**Research topics**: Current TradeLocker API docs, TopStep/ProjectX gateway API, Tradovate WebSocket patterns
**Plans**: 14 plans (Wave 1: 01, 02 | Wave 2: 03, 04, 05 | Wave 3: 06, 07, 08, 09, 10 | Wave 4: 11, 12 | Wave 5: 13, 14 gap closure)

### Phase 6: Security Hardening
**Goal**: Fix all security vulnerabilities from codebase audit
**Depends on**: Phase 5
**Requirements**: SEC-01, SEC-02, SEC-03, SEC-04
**Success Criteria** (what must be TRUE):
  1. CREDENTIAL_ENCRYPTION_KEY read from environment, fails fast if missing
  2. Credentials stored encrypted in database, not in-memory dicts
  3. OAuth tokens encrypted before database storage
  4. API keys use bcrypt with salt (not plain SHA256)
  5. Encrypted credentials survive service restarts
**Research**: Unlikely (standard security patterns)
**Plans**: TBD

### Phase 7: UI Foundation
**Goal**: Next.js 14 project with auth and layout ready
**Depends on**: Phase 6
**Requirements**: UI-01, UI-02, UI-03
**Success Criteria** (what must be TRUE):
  1. Next.js 14 app runs with shadcn/ui components
  2. Dark theme applied globally
  3. User can log in with JWT from backend
  4. User session persists across page refresh
  5. Protected routes redirect to login
  6. Dashboard layout with sidebar navigation renders
**Research**: Likely (Next.js 14 app router, shadcn/ui setup)
**Research topics**: Next.js 14 app router patterns, shadcn/ui theming, JWT auth in Next.js
**Plans**: TBD

### Phase 8: UI Dashboard
**Goal**: Real-time monitoring dashboard
**Depends on**: Phase 7
**Requirements**: UI-04, UI-05, UI-06
**Success Criteria** (what must be TRUE):
  1. Signal status table shows live signals with WebSocket updates
  2. Broker connection health cards show connected/disconnected state
  3. Trade execution logs display with date/broker/status filtering
  4. Dashboard updates in real-time without page refresh
**Research**: Unlikely (WebSocket patterns established in backend)
**Plans**: TBD

### Phase 9: UI Configuration
**Goal**: Complete account and configuration management
**Depends on**: Phase 8
**Requirements**: UI-07, UI-08, UI-09
**Success Criteria** (what must be TRUE):
  1. User can create, edit, delete broker accounts
  2. Account balances display per broker (fetched from broker APIs)
  3. Signal routing rules can be configured (which signals go to which accounts)
  4. API keys can be created, viewed (masked), and revoked
  5. Webhook endpoints displayed with copy-to-clipboard URLs
**Research**: Unlikely (CRUD patterns)
**Plans**: TBD

### Phase 10: Deployment
**Goal**: Production-ready Docker Swarm deployment
**Depends on**: Phase 9
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03
**Success Criteria** (what must be TRUE):
  1. docker-stack.yml deploys full stack to Swarm
  2. Environment configs work for dev/staging/prod
  3. Secrets (DB password, encryption key, JWT secret) use Docker secrets
  4. Health checks pass for all services in stack
  5. Stack survives node restart with persistent data
**Research**: Unlikely (existing docker-stack.yml as base)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Stability Fixes | 4/4 | Complete | 2026-01-19 |
| 2. Test Infrastructure | 5/5 | Complete | 2026-01-19 |
| 3. Domain Layer | 7/7 | Complete | 2026-01-20 |
| 4. Application Layer | 7/7 | Complete | 2026-01-20 |
| 5. Infrastructure Adapters | 14/14 | Complete | 2026-01-20 |
| 6. Security Hardening | 0/TBD | Not started | - |
| 7. UI Foundation | 0/TBD | Not started | - |
| 8. UI Dashboard | 0/TBD | Not started | - |
| 9. UI Configuration | 0/TBD | Not started | - |
| 10. Deployment | 0/TBD | Not started | - |

---
*Last updated: 2026-01-20 after Phase 5 completion*
