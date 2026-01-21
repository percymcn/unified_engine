---
phase: 11-integration-wiring
plan: 02
subsystem: integration
tags: [hexagonal-architecture, dependency-injection, webhooks, signal-processing, domain-driven-design]

# Dependency graph
requires:
  - phase: 11-01
    provides: DI Container initialized in main.py lifespan
  - phase: 04-application-layer
    provides: ProcessSignalUseCase with domain orchestration
  - phase: 03-domain-layer
    provides: Signal entity, SignalService, domain events
provides:
  - Webhook endpoints use hexagonal architecture
  - Signal processing flows through domain layer
  - Broker adapters from container execute trades
  - Domain events published for WebSocket updates
affects: [11-03-accounts-wiring, future-webhook-additions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Webhook payload mapping to domain DTOs"
    - "Container dependency injection in route handlers"
    - "Domain result to API response mapping"

key-files:
  created: []
  modified:
    - app/routers/webhooks.py

key-decisions:
  - "Webhook routing handled by domain SignalService, not router"
  - "Empty target_account_ids in request - routing delegated to domain layer"
  - "Maintained backward-compatible API response schema"
  - "Removed old SignalProcessor import - full migration to hexagonal architecture"

patterns-established:
  - "get_container(request) pattern for DI in route handlers"
  - "ProcessSignalRequest DTO construction from webhook payloads"
  - "TradingView uses ticker/action/quantity field names"
  - "TrailHacker uses symbol/signal/size/entry/stop/target field names"
  - "Domain status enum to API response mapping"

# Metrics
duration: 4min
completed: 2026-01-21
---

# Phase 11 Plan 02: Wire Webhook Router to Hexagonal Architecture Summary

**Webhook endpoints migrated from old SignalProcessor to ProcessSignalUseCase, enabling signal-to-trade flow through hexagonal architecture with domain validation and event publishing**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-21T00:19:29Z
- **Completed:** 2026-01-21T00:23:50Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- POST /api/v1/webhooks/tradingview uses ProcessSignalUseCase from container
- POST /api/v1/webhooks/trailhacker uses ProcessSignalUseCase from container
- Signal processing flows: Webhook → Use Case → Domain Service → Broker Adapter → Events
- Backward-compatible API responses maintained for existing integrations

## Task Commits

Each task was committed atomically:

1. **Task 1: Update imports** - `61f40fe` (refactor)
2. **Task 2: Migrate /tradingview endpoint** - `1b5c926` (feat)
3. **Task 3: Migrate /trailhacker endpoint** - `4a23cbf` (feat)

## Files Created/Modified

- `app/routers/webhooks.py` - Migrated from SignalProcessor to ProcessSignalUseCase with container DI

## Decisions Made

**1. Routing delegation to domain layer**
- Webhook payloads pass empty `target_account_ids` array
- SignalService in domain layer handles account routing logic
- Keeps routing rules in domain, not presentation layer

**2. Payload field mapping**
- TradingView: ticker → symbol, quantity → volume, action → action
- TrailHacker: signal → action, size → volume, entry → price, stop → stop_loss, target → take_profit
- Normalized to ProcessSignalRequest DTO for consistent domain input

**3. Response schema compatibility**
- Domain status enum mapped to API response strings
- Success determined by status not being "failed" or "rejected"
- Processing time calculated in router, not use case
- Maintained exact response shape for TradingView/TrailHacker compatibility

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Plan Artifact] No /custom endpoint found**
- **Found during:** Task review after migrating /tradingview and /trailhacker
- **Issue:** Plan mentioned Task 4 to migrate /custom endpoint, but no such endpoint exists in codebase
- **Fix:** Skipped non-existent task - plan was written from documentation, actual implementation only has 2 webhook endpoints
- **Files modified:** None
- **Verification:** Confirmed only /tradingview and /trailhacker signal processing endpoints exist
- **Committed in:** N/A (no code change needed)

---

**Total deviations:** 1 (plan artifact - task not applicable)
**Impact on plan:** No impact - completed all applicable webhook migrations. Plan documented hypothetical endpoint.

## Issues Encountered

None - migration was straightforward with clear separation between presentation and domain layers.

## User Setup Required

None - no external service configuration required. Webhook URLs remain unchanged.

## Next Phase Readiness

**Ready for 11-03 (Wire Accounts Router):**
- Container DI pattern established and working
- Use case integration pattern proven with webhooks
- Account use cases in container ready to be wired to /api/v1/accounts routes

**Verification completed:**
- ✓ POST /api/v1/webhooks/tradingview calls ProcessSignalUseCase
- ✓ POST /api/v1/webhooks/trailhacker calls ProcessSignalUseCase
- ✓ Signal events published via EventPort (configured in container)
- ✓ Broker adapters from container used for execution
- ✓ WebSocket updates triggered via domain events (infrastructure layer subscribers)
- ✓ Python syntax valid

**No blockers.** Phase 11 Wave 2 ready to complete in parallel (11-03 independent).

---
*Phase: 11-integration-wiring*
*Completed: 2026-01-21*
