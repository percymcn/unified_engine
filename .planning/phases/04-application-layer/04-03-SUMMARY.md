---
phase: 04-application-layer
plan: 03
subsystem: application
tags: [use-cases, signal-processing, dto-conversion, domain-orchestration]

# Dependency graph
requires:
  - phase: 03-domain-layer
    plan: 06
    provides: SignalService for signal processing orchestration
  - phase: 04-application-layer
    plan: 02
    provides: Signal DTOs (ProcessSignalRequest, ProcessSignalResponse, SignalDTO)
provides:
  - ProcessSignalUseCase - orchestrates signal-to-trade flow
  - GetSignalUseCase - retrieves single signal by ID
  - ListSignalsUseCase - queries signals with filtering
  - DTO-to-entity and entity-to-DTO conversion patterns
affects: [04-05, adapters, api-layer]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Use case pattern: DTO-in, DTO-out with domain service delegation"
    - "Use cases instantiate domain services with injected ports"
    - "Query use cases separate from command use cases"
    - "Error handling converts domain exceptions to DTO responses"

key-files:
  created:
    - app/application/use_cases/process_signal.py
    - app/application/use_cases/get_signals.py
  modified:
    - app/application/use_cases/__init__.py

key-decisions:
  - "Use cases instantiate domain services directly (not injected)"
  - "ProcessSignalUseCase returns error DTOs instead of raising exceptions"
  - "Query use cases (Get/List) separated from command use case (Process)"
  - "Entity-to-DTO conversion duplicated between query use cases (acceptable for now)"

patterns-established:
  - "Use case pattern: Constructor receives ports, instantiates domain service"
  - "Error handling: Try/except wrapping domain calls, return error DTOs"
  - "DTO conversion: Private methods _to_domain_entity and _to_response_dto"
  - "Query pattern: Repository → Entity → DTO transformation"

# Metrics
duration: 5min
completed: 2026-01-20
---

# Phase 4 Plan 3: Signal Use Cases Summary

**Signal processing orchestration with ProcessSignalUseCase, GetSignalUseCase, and ListSignalsUseCase following clean DTO-in/DTO-out pattern**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-20T04:16:02Z
- **Completed:** 2026-01-20T04:21:02Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- ProcessSignalUseCase handles complete signal-to-trade workflow with graceful error handling
- Query use cases (Get/List) provide read-only signal access with DTO conversion
- Use cases follow hexagonal architecture with no infrastructure dependencies
- All use cases accept DTOs, delegate to domain services, and return DTOs

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ProcessSignalUseCase** - `2654bf5` (feat)
2. **Task 2: Create signal query use cases** - `30a3541` (feat)
3. **Task 3: Update use cases package exports** - `7c212f5` (feat)

## Files Created/Modified
- `app/application/use_cases/process_signal.py` - Orchestrates signal processing through SignalService, converts DTOs to/from domain entities
- `app/application/use_cases/get_signals.py` - GetSignalUseCase and ListSignalsUseCase for querying signals
- `app/application/use_cases/__init__.py` - Exports all signal use cases

## Decisions Made

**1. Use cases instantiate domain services directly (not injected)**
- Rationale: Use case IS the composition root for its domain service. Ports are injected, service is composed.
- Pattern: `self._signal_service = SignalService(ports...)`

**2. ProcessSignalUseCase returns error DTOs instead of raising exceptions**
- Rationale: Application layer converts domain exceptions to user-facing responses
- Catches: SignalValidationError, SignalProcessingError, and generic Exception
- Returns: ProcessSignalResponse with error details

**3. Query use cases separated from command use case**
- Rationale: CQRS-lite separation for clarity
- GetSignalUseCase: Single signal by ID
- ListSignalsUseCase: Filtered list with pagination
- ProcessSignalUseCase: Command that mutates state

**4. DTO conversion methods duplicated between query use cases**
- Rationale: Each use case is self-contained. Future extraction to mapper if needed.
- Trade-off: Slight duplication vs keeping use cases independent

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all use cases imported and verified successfully.

## Next Phase Readiness

**Ready for:**
- Plan 04-04: Trade Use Cases (follow same pattern)
- Plan 04-06: Application Services (will compose multiple use cases)
- Adapter layer implementation (use cases ready to be called from FastAPI)

**Patterns established:**
- DTO-in, DTO-out contract
- Domain service delegation through ports
- Error handling at application boundary
- Query/command separation

**No blockers.**

---
*Phase: 04-application-layer*
*Completed: 2026-01-20*
