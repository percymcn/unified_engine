---
phase: 05-infrastructure-adapters
plan: 11
subsystem: infra
tags: [dependency-injection, container, hexagonal-architecture, sqlalchemy, fastapi]

# Dependency graph
requires:
  - phase: 03-domain-layer
    provides: Port interfaces (BrokerPort, EventPort, Repository interfaces)
  - phase: 04-application-layer
    provides: Use cases requiring dependency injection
  - phase: 05-03
    provides: SQLAlchemy repository implementations
  - phase: 05-04
    provides: Unit of Work and session management
  - phase: 05-05
    provides: Event publisher implementations
  - phase: 05-06
    provides: TradeLockerAdapter
  - phase: 05-07
    provides: TopstepAdapter
  - phase: 05-08
    provides: TradovateAdapter
  - phase: 05-09
    provides: MT4Adapter
  - phase: 05-10
    provides: MT5Adapter
provides:
  - Dependency injection container wiring all infrastructure to application layer
  - Container factory methods for all 12 use cases with injected dependencies
  - Global container instance with FastAPI lifecycle integration (initialize/shutdown)
  - Infrastructure layer single entry point for dependency access
affects: [06-api-layer, fastapi-integration, testing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "DI container provides factory methods for use cases with injected ports"
    - "Global singleton container with async initialize/shutdown lifecycle"
    - "Container creates new session per request via SessionFactory"
    - "Use cases depend on ports, container provides concrete adapters"
    - "Broker adapters lazy-connect (connected when account uses them)"

key-files:
  created:
    - app/infrastructure/container.py
  modified:
    - app/infrastructure/__init__.py

key-decisions:
  - "Container provides repositories directly to use cases (not via UnitOfWork pattern in constructors)"
  - "New session created per request in factory methods (not singleton)"
  - "Event publisher is CompositeEventPublisher with NATS primary, Redis fallback"
  - "All 5 broker adapters registered in container by BrokerType enum"
  - "Global container instance accessed via get_container() function"
  - "Container lifecycle integrated with FastAPI startup/shutdown events"

patterns-established:
  - "Container pattern: Single responsibility wiring layer between infrastructure and application"
  - "Factory methods: One method per use case returning configured instance"
  - "Lifecycle management: Async initialize() connects event publishers, shutdown() cleans up"
  - "Direct dependency injection: Use cases receive port instances via constructor"

# Metrics
duration: 5min
completed: 2026-01-20
---

# Phase 5 Plan 11: DI Container Summary

**Centralized dependency injection container wiring 12 use cases with repositories, brokers, and event publishers via factory methods**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-20T07:18:05Z
- **Completed:** 2026-01-20T07:23:18Z
- **Tasks:** 3 (Task 2 merged with Task 1)
- **Files modified:** 2

## Accomplishments

- Created Container class with factory methods for all 12 application use cases
- Wired 5 broker adapters (TradeLocker, Topstep, Tradovate, MT4, MT5) indexed by BrokerType
- Integrated composite event publisher (NATS + Redis fallback) with connection lifecycle
- Exported container and lifecycle functions from infrastructure package for FastAPI integration

## Task Commits

Each task was committed atomically:

1. **Task 1: Create DI container** - `49614e0` (feat)
2. **Task 2: Create global container instance** - (merged with Task 1)
3. **Task 3: Update infrastructure __init__ exports** - `a7ff638` (feat)

## Files Created/Modified

- `app/infrastructure/container.py` - DI container with factory methods for all use cases
- `app/infrastructure/__init__.py` - Export container and lifecycle functions

## Decisions Made

**1. Use direct repository injection instead of UnitOfWork in use case constructors**
- **Rationale:** Current use cases receive individual repositories directly, not a UnitOfWork factory. Container follows existing use case signatures.
- **Impact:** UnitOfWork is available via `container.uow_factory` for explicit transaction scenarios, but use cases don't require it in constructors.

**2. Create new session per request via `_get_repositories()` helper**
- **Rationale:** Each use case invocation should have its own database session for transaction isolation.
- **Impact:** Container factory methods call `_get_repositories()` which creates fresh session and repositories per request.

**3. Use CompositeEventPublisher with NATS primary, Redis fallback**
- **Rationale:** Provides resilience if NATS is unavailable while maintaining preferred event infrastructure.
- **Impact:** Events published to both NATS and Redis, automatic fallback on failure.

**4. Register all 5 broker adapters by BrokerType enum in dict**
- **Rationale:** Enables dynamic broker selection based on account.broker property.
- **Impact:** Use cases access correct broker adapter via `brokers[account.broker]` lookup.

**5. Provide global singleton container via `get_container()` function**
- **Rationale:** FastAPI dependency injection works best with global accessor functions.
- **Impact:** API routes call `get_container()` to access use cases; single container instance per application lifecycle.

**6. Merge Task 2 into Task 1 implementation**
- **Rationale:** Global instance functions (`get_container`, `initialize_container`, `shutdown_container`) are small and logically part of container module.
- **Impact:** Single cohesive commit instead of artificial split.

## Deviations from Plan

**1. [Rule 1 - Bug] Merged Task 2 into Task 1 commit**
- **Found during:** Task 1 implementation
- **Issue:** Plan split global instance functions into separate task, but they're 15 lines in same file
- **Fix:** Implemented both Container class and global instance functions in single container.py file
- **Files modified:** app/infrastructure/container.py
- **Verification:** All global functions present in Task 1 commit
- **Committed in:** 49614e0 (Task 1 commit)

**2. [Rule 1 - Bug] Adapted container to use direct repository injection**
- **Found during:** Task 1 implementation - reviewing use case constructors
- **Issue:** Plan template assumed use cases use `uow_factory`, but actual implementation uses direct repository injection
- **Fix:** Container factory methods call `_get_repositories()` helper to create repositories, then pass them individually to use case constructors
- **Files modified:** app/infrastructure/container.py
- **Verification:** Constructor signatures match actual use cases in app/application/use_cases/
- **Committed in:** 49614e0 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both auto-fixes align implementation with existing codebase architecture. No scope creep.

## Issues Encountered

**1. Missing broker executor dependencies**
- **Issue:** Broker adapters import executors which import `socketio` (not installed)
- **Resolution:** Import error expected in development environment. Container structure verified via code review and partial import tests. Full verification requires `pip install -r requirements.txt`.
- **Impact:** Verification limited to structure checks; runtime tests deferred to integration testing in Plan 05-12.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 6 (API Layer):**
- Container provides all use cases with dependencies injected
- FastAPI can call `initialize_container()` on startup, `shutdown_container()` on shutdown
- API routes access use cases via `container = get_container(); container.process_signal_use_case()`

**Ready for Plan 05-12 (Infrastructure Tests):**
- Container integration tests can verify:
  - All use cases instantiate correctly
  - Broker adapters accessible by type
  - Event publisher connects/disconnects
  - Session factory creates sessions

**Blockers:**
- None

**Concerns:**
- Broker executor dependencies (socketio, websockets) must be installed before runtime testing
- requirements.txt should include all broker dependencies for complete environment setup

---
*Phase: 05-infrastructure-adapters*
*Completed: 2026-01-20*
