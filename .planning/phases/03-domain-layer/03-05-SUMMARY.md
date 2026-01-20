---
phase: 03-domain-layer
plan: 05
subsystem: domain
tags: [hexagonal-architecture, ports, abstract-interfaces, dependency-inversion]

# Dependency graph
requires:
  - phase: 03-03
    provides: Domain entities (Signal, Trade, Order, Position)
  - phase: 03-04
    provides: Account entity
  - phase: 03-02
    provides: Domain value objects and enums
provides:
  - BrokerPort interface defining all broker operations
  - Repository port interfaces for all domain entities
  - EventPort interface for domain event publishing
  - Abstract base classes enforcing hexagonal architecture
affects: [03-06, 05-adapters, domain-services]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hexagonal architecture with ports defining contracts"
    - "ABC-based abstract interfaces with no implementation"
    - "Repository pattern with generic base and specific interfaces"
    - "Domain events with EventType enum and DomainEvent dataclass"
    - "Dependency inversion: domain defines needs, infrastructure adapts"

key-files:
  created:
    - app/domain/ports/broker_port.py
    - app/domain/ports/repository_port.py
    - app/domain/ports/event_port.py
  modified:
    - app/domain/ports/__init__.py

key-decisions:
  - "BrokerPort mirrors BaseExecutor methods but uses domain types (Symbol, Volume, Price, OrderId)"
  - "Repository interfaces use domain entities as return types (Signal, Trade, Order, etc.)"
  - "Generic Repository[T] base with save/delete, specific repos add query methods"
  - "EventPort publishes DomainEvent with EventType enum for all domain events"
  - "All ports strictly abstract (no implementation code) for true hexagonal architecture"

patterns-established:
  - "Port interfaces inherit from ABC with all methods @abstractmethod"
  - "Ports return domain entities, never dicts or primitives"
  - "No framework imports (FastAPI, SQLAlchemy, NATS) in domain layer"
  - "Repository queries named by intent (get_pending, get_active, get_connected)"

# Metrics
duration: 5min
completed: 2026-01-20
---

# Phase 3 Plan 5: Repository Ports Summary

**Hexagonal architecture port interfaces: BrokerPort for trading operations, repository ports for all entities, and EventPort for domain events**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-20T03:23:35Z
- **Completed:** 2026-01-20T03:28:46Z
- **Tasks:** 3 completed + 1 metadata update
- **Files modified:** 4

## Accomplishments

- Created abstract BrokerPort interface mirroring BaseExecutor but using domain types
- Created repository port interfaces for all 5 domain entities (Signal, Trade, Order, Account, Position)
- Created EventPort interface with DomainEvent dataclass and EventType enum
- Established complete hexagonal architecture port layer with zero framework dependencies

## Task Commits

Each task was committed atomically:

1. **Task 1: Create BrokerPort interface** - `4a39ed8` (feat)
2. **Task 2: Create RepositoryPort interfaces** - `6c8017b` (feat)
3. **Task 3: Create EventPort interface** - `26ce90b` (feat)
4. **Update ports __init__.py** - `25a6a65` (feat)

## Files Created/Modified

- `app/domain/ports/broker_port.py` - Abstract broker interface with 14 methods (connect, authenticate, place_order, get_positions, etc.)
- `app/domain/ports/repository_port.py` - Repository interfaces for all entities with generic base Repository[T]
- `app/domain/ports/event_port.py` - Event publishing interface with DomainEvent and EventType enum
- `app/domain/ports/__init__.py` - Exports all port interfaces for clean public API

## Decisions Made

1. **BrokerPort method signatures use domain value objects**
   - Rationale: Pure domain interface - takes Symbol/Volume/Price, returns Order/Position/Trade entities

2. **Repository pattern with generic base**
   - Rationale: Repository[T] provides common CRUD (save, delete), specific repos add entity-specific queries

3. **EventPort uses DomainEvent dataclass with EventType enum**
   - Rationale: Type-safe event publishing with factory method for timestamp injection

4. **All repository methods return domain entities or None**
   - Rationale: No database concerns leak into domain - adapters handle ORM mapping

5. **No async in ABC properties, only in methods**
   - Rationale: Python ABC doesn't support async properties, only async methods

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all port interfaces created successfully, imports verified, ABC inheritance confirmed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 3 Plan 6 (Broker Ports) and Plan 7 (Domain Services):**
- All port interfaces defined as contracts
- Domain layer complete dependency inversion (domain defines interfaces, infrastructure implements)
- Next: Domain services using these ports, then Phase 5 adapters implementing them

**Infrastructure adapters (Phase 5) can now implement:**
- BrokerPort → MT4Adapter, MT5Adapter, TradeLockerAdapter, etc.
- Repository ports → SQLAlchemySignalRepository, SQLAlchemyAccountRepository, etc.
- EventPort → NATSEventPublisher, RedisEventPublisher, WebSocketEventPublisher

**No blockers or concerns.**

---
*Phase: 03-domain-layer*
*Completed: 2026-01-20*
