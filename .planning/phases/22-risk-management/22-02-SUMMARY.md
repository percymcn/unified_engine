---
phase: 22-risk-management
plan: 02
subsystem: risk-management
tags: [position-sizing, risk-management, futures, forex, domain-services]

# Dependency graph
requires:
  - phase: 22-01
    provides: Risk enforcement infrastructure and account risk settings
provides:
  - Dynamic position sizing with four modes (fixed, percent_balance, percent_equity, risk_based)
  - Symbol specifications service with defaults for 30+ instruments
  - Automatic position size calculation integrated into signal processing
  - API endpoint for position size preview calculations
affects: [22-03, 22-04, signal-processing, account-management]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Domain service for position sizing calculations
    - Symbol specifications with broker API fallback
    - Balance refresh after trade execution

key-files:
  created:
    - app/domain/services/position_sizing_service.py
    - app/domain/services/symbol_specs_service.py
  modified:
    - app/services/signal_processor.py
    - app/routers/risk.py
    - app/domain/services/__init__.py

key-decisions:
  - "Use four position sizing modes: fixed, percent_balance, percent_equity, risk_based"
  - "Default symbol specs for common instruments (forex, indices, futures)"
  - "Auto-refresh account balance after successful trades for accurate sizing"
  - "Graceful fallback to signal quantity if position sizing calculation fails"

patterns-established:
  - "SymbolSpecs dataclass with min/max/step/contract_size/pip_value/digits"
  - "PositionSizingConfig built from TradingAccount database fields"
  - "Risk-based sizing uses stop loss distance in pips"

# Metrics
duration: 6min
completed: 2026-01-22
---

# Phase 22 Plan 02: Position Sizing Engine Summary

**Dynamic position sizing with four calculation modes (fixed, % balance, % equity, risk-based), symbol specifications for 30+ instruments, and automatic integration into signal execution**

## Performance

- **Duration:** 6 minutes
- **Started:** 2026-01-22T02:10:04Z
- **Completed:** 2026-01-22T02:15:40Z
- **Tasks:** 5 (including Task 5 which was pre-completed in Task 3)
- **Files modified:** 5

## Accomplishments

- Position sizing service with four modes supporting all trading styles
- Symbol specifications service with comprehensive defaults and broker API integration
- Automatic position size calculation in signal processing pipeline
- Account balance auto-refresh after trades for accurate subsequent calculations
- API endpoint for position size preview and "what if" scenarios

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Position Sizing Service** - `3a7e172` (feat)
2. **Task 2: Create Symbol Specs Service** - `0ea33fb` (feat)
3. **Task 3: Integrate Position Sizing with Signal Processing** - `e0bae46` (feat)
4. **Task 4: Add Position Sizing API Endpoints** - `2ea0da0` (feat)
5. **Task 5: Update Account Balance on Trade Execution** - Completed in Task 3

## Files Created/Modified

### Created
- `app/domain/services/position_sizing_service.py` - Four sizing modes with broker spec adjustments
- `app/domain/services/symbol_specs_service.py` - Symbol specifications with 30+ instrument defaults

### Modified
- `app/services/signal_processor.py` - Added position sizing calculation and balance refresh
- `app/routers/risk.py` - Added POST /api/v1/risk/calculate-position-size endpoint
- `app/domain/services/__init__.py` - Exported new position sizing services

## Decisions Made

1. **Four position sizing modes** - Covers all trading styles:
   - Fixed: Simple lot size
   - Percent balance: Risk % of balance (e.g., 1% = $100 of $10k)
   - Percent equity: Risk % of equity (accounts for floating P&L)
   - Risk-based: Risk % with stop loss distance in pips

2. **Comprehensive symbol defaults** - Pre-configured specs for:
   - Forex majors (EURUSD, GBPUSD, USDJPY, etc.)
   - US indices (US30, NAS100, SPX500)
   - Futures (ES, NQ, MES, MNQ, YM, RTY, etc.)
   - Commodities (XAUUSD, USOIL, CL)

3. **Graceful fallback strategy**:
   - Try broker API for specs → Defaults → Pattern inference
   - Position sizing error → Use signal quantity
   - Balance unavailable → Default to $10,000

4. **Auto-refresh balance** - After successful trades, refresh account balance/equity for accurate next calculation

5. **Position size only for non-fixed modes** - Fixed mode uses signal quantity, other modes calculate dynamically

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed without issues.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for 22-03 (Drawdown & Loss Tracking):**
- Position sizing engine complete and integrated
- Account balance tracking in place
- API endpoint available for UI integration
- Symbol specifications support all major instruments

**Ready for 22-04 (Risk Management UI):**
- API endpoint `/api/v1/risk/calculate-position-size` ready for UI preview
- All position sizing fields already in TradingAccount model
- Position sizing modes clearly defined

**Integration notes:**
- Signal processor now calculates position sizes automatically
- Balance refreshes after each trade for accurate dynamic sizing
- Risk enforcement service (22-01) and position sizing (22-02) work together seamlessly

---
*Phase: 22-risk-management*
*Completed: 2026-01-22*
