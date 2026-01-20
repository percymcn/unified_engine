# Requirements

## Overview

Requirements for Unified Trading Engine full refactor with hexagonal architecture, new Next.js UI, and comprehensive backend fixes.

**Scope:** v1.0 Refactor Milestone
**Total v1 Requirements:** 30

## Categories

### STAB: Stability Fixes (4 requirements)

Critical fixes to make the existing system run without crashes.

- **STAB-01**: Fix aioredis deprecated import — migrate to redis.asyncio
- **STAB-02**: Fix broker executor initialization crashes — handle missing API keys gracefully
- **STAB-03**: Fix NATS connection timeout issues — proper error handling and fallback
- **STAB-04**: Remove hardcoded API keys from source code — use environment variables

### TEST: Testing Infrastructure (3 requirements)

Get tests passing to have a safety net for refactoring.

- **TEST-01**: Fix test fixtures and setup — 101 tests should run
- **TEST-02**: All 101 existing tests passing
- **TEST-03**: Add test coverage for broker executor error handling

### ARCH: Architecture Refactor (5 requirements)

Hexagonal architecture with clean separation of concerns.

- **ARCH-01**: Domain layer — pure business logic with no framework dependencies
- **ARCH-02**: Application layer — use cases and service orchestration
- **ARCH-03**: Infrastructure layer — concrete implementations (adapters)
- **ARCH-04**: Ports — interfaces defining domain boundaries
- **ARCH-05**: Dependency inversion — domain never imports infrastructure

### BROK: Broker Integration (5 requirements)

All broker executors working with new architecture.

- **BROK-01**: TradeLocker executor — migrated to hexagonal adapter pattern
- **BROK-02**: TopStep/ProjectX executor — migrated to hexagonal adapter pattern
- **BROK-03**: Tradovate executor — migrated to hexagonal adapter pattern
- **BROK-04**: MT4 executor — migrated to hexagonal adapter pattern
- **BROK-05**: MT5 executor — migrated to hexagonal adapter pattern

### SEC: Security Fixes (4 requirements)

Fix security vulnerabilities identified in codebase audit.

- **SEC-01**: Persist encryption key in environment — not generated at runtime
- **SEC-02**: Move credential storage from in-memory to database with encryption
- **SEC-03**: Encrypt OAuth tokens in database
- **SEC-04**: Implement proper API key hashing with salt

### UI: User Interface (9 requirements)

New Next.js 14 dashboard with shadcn/ui.

- **UI-01**: Next.js 14 project setup with shadcn/ui and dark theme
- **UI-02**: Self-hosted JWT authentication flow (login, logout, session)
- **UI-03**: Dashboard layout with navigation
- **UI-04**: Real-time signal status display with WebSocket
- **UI-05**: Broker connection health monitoring
- **UI-06**: Trade execution logs with filtering
- **UI-07**: Account management (CRUD, balances per broker)
- **UI-08**: Signal routing rules configuration
- **UI-09**: API key and webhook endpoint management

### DEPLOY: Deployment (3 requirements)

Production-ready Docker Swarm deployment.

- **DEPLOY-01**: Docker Swarm stack configuration (docker-stack.yml)
- **DEPLOY-02**: Environment-based configuration (dev/staging/prod)
- **DEPLOY-03**: Secret management via Docker secrets

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| STAB-01 | Phase 1 | Complete |
| STAB-02 | Phase 1 | Complete |
| STAB-03 | Phase 1 | Complete |
| STAB-04 | Phase 1 | Complete |
| TEST-01 | Phase 2 | Complete |
| TEST-02 | Phase 2 | Complete |
| TEST-03 | Phase 2 | Complete |
| ARCH-01 | Phase 3 | Complete |
| ARCH-02 | Phase 4 | Complete |
| ARCH-03 | Phase 5 | Complete |
| ARCH-04 | Phase 3 | Complete |
| ARCH-05 | Phase 5 | Complete |
| BROK-01 | Phase 5 | Complete |
| BROK-02 | Phase 5 | Complete |
| BROK-03 | Phase 5 | Complete |
| BROK-04 | Phase 5 | Complete |
| BROK-05 | Phase 5 | Complete |
| SEC-01 | Phase 6 | Complete |
| SEC-02 | Phase 6 | Complete |
| SEC-03 | Phase 6 | Complete |
| SEC-04 | Phase 6 | Complete |
| UI-01 | Phase 7 | Complete |
| UI-02 | Phase 7 | Complete |
| UI-03 | Phase 7 | Complete |
| UI-04 | Phase 8 | Complete |
| UI-05 | Phase 8 | Complete |
| UI-06 | Phase 8 | Complete |
| UI-07 | Phase 9 | Pending |
| UI-08 | Phase 9 | Pending |
| UI-09 | Phase 9 | Pending |
| DEPLOY-01 | Phase 10 | Pending |
| DEPLOY-02 | Phase 10 | Pending |
| DEPLOY-03 | Phase 10 | Pending |

**Coverage:**
- v1 requirements: 33 total
- Mapped to phases: 33
- Unmapped: 0 ✓

---
*Last updated: 2026-01-20 after Phase 8 completion*
