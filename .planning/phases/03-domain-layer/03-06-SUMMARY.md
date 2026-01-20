---
phase: 03-domain-layer
plan: 06
subsystem: domain
tags: [domain-services, hexagonal-architecture, dependency-injection, business-logic, ports-and-adapters]

# Dependency graph
requires:
  - phase: 03-01
    provides: Domain package structure and exception hierarchy
  - phase: 03-02
    provides: Domain enums and value objects (SignalId, Symbol, Volume, Price, Money)
  - phase: 03-03
    provides: Signal, Trade, Order entities with business logic
  - phase: 03-04
    provides: Account and Position entities with margin/P&L logic
  - phase: 03-05
    provides: Repository and Broker port interfaces

provides:
  - SignalService for signal processing orchestration
  - TradeService for trade execution orchestration
  - Constructor injection pattern for ports (hexagonal architecture)
  - Event publishing for domain operations
  - Business logic layer isolated from infrastructure

affects: [03-07, 04-application, 05-adapters, signal-processing, trade-execution]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Domain services depend only on port interfaces, never concrete implementations"
    - "Constructor injection for all dependencies (repositories, brokers, event ports)"
    - "Domain services orchestrate business logic across entities and ports"
    - "Event publishing for all significant domain operations"

key-files:
  created:
    - app/domain/services/signal_service.py
    - app/domain/services/trade_service.py
  modified: []

key-decisions:
  - "SignalService routes signals to connected accounts through BrokerPort interface"
  - "TradeService performs margin checks before placing orders through broker"
  - "Services publish domain events through EventPort for observability"
  - "All dependencies injected through constructor (no global state)"
  - "Services contain business logic, entities contain invariants"

patterns-established:
  - "Service pattern: Orchestrate operations across multiple entities and ports"
  - "Event-driven pattern: Publish events for signal lifecycle, order placement, trade closure"
  - "Hexagonal architecture: Services depend on abstractions (ports), not implementations"
  - "Simplified margin calculation: Real implementation would need symbol specifications"

# Metrics
duration: 4min
completed: 2026-01-20
---

# Phase 3 Plan 6: Domain Services Summary

**SignalService and TradeService orchestrate business logic through port interfaces with no infrastructure dependencies**

## Performance

- **Duration:** 4 minutes
- **Started:** 2026-01-20T03:31:58Z
- **Completed:** 2026-01-20T03:35:41Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- SignalService processes signals: validates, routes to accounts, executes actions, publishes events
- TradeService manages trades: places orders with margin checks, closes positions with P&L application, modifies positions
- Both services use constructor injection for all dependencies (repositories, brokers, event port)
- Pure business logic with zero infrastructure imports (no FastAPI, SQLAlchemy, or broker SDKs)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create SignalService** - `5d8c532` (feat)
2. **Task 2: Create TradeService** - `27b94af` (feat)

## Files Created/Modified
- `app/domain/services/signal_service.py` - Signal processing orchestration through port interfaces
- `app/domain/services/trade_service.py` - Trade execution orchestration through port interfaces

## Decisions Made

1. **SignalService action routing**: Implemented routing logic for BUY/SELL (place order), CLOSE (close positions), MODIFY (update SL/TP) signal actions
2. **Margin validation**: TradeService performs upfront margin checks before placing orders, raises InsufficientBalanceError if insufficient
3. **P&L application**: TradeService applies realized P&L to account balance and releases margin when closing positions
4. **Event publishing**: Both services publish domain events at key lifecycle points (signal received/processed/failed, order placed/cancelled, position closed/modified)
5. **Simplified margin estimation**: Margin calculation uses simplified formula (volume * price * lot_size / leverage) - real implementation would need symbol specifications from broker
6. **Error handling**: Signal execution continues across accounts even if one fails, aggregates results to determine final signal status

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation proceeded smoothly with all domain entities and port interfaces available from prior plans.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Domain layer services complete - ready for application layer and adapters.**

What's ready:
- SignalService ready to be wired into webhook endpoints
- TradeService ready to be wired into trade API endpoints
- Both services ready for adapter implementations (SQLAlchemy repositories, broker adapters)
- Event publishing ready for NATS/Redis/WebSocket adapter implementations

Next steps:
- Phase 4: Application layer (use cases, DTOs, API layer) will depend on these services
- Phase 5: Adapters layer will implement port interfaces (SQLAlchemy repositories, MT4/MT5/TradeLocker adapters)

No blockers or concerns.

---
*Phase: 03-domain-layer*
*Completed: 2026-01-20*
