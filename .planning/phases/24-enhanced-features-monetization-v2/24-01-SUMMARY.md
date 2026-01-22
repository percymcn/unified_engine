---
phase: 24
plan: 01
subsystem: trial-system
tags: [trial, monetization, user-limits, free-tier]
requires: [13]
provides: [trial-tracking, trial-enforcement, trial-api]
affects: [24-04]
tech-stack:
  added: []
  patterns: [service-pattern, enum-status-tracking]
key-files:
  created:
    - app/services/trial_service.py
    - app/routers/trial.py
    - alembic/versions/016_add_trial_fields.py
  modified:
    - app/models/models.py
    - app/models/database_models.py
    - app/services/signal_processor.py
    - app/main.py
decisions:
  - Trial auto-starts on first signal execution (no manual start required)
  - Trial expired status stored permanently, not re-evaluated dynamically
  - Paid users bypass trial checks entirely (subscription_tier != 'free')
  - Trial rejections logged to RejectedSignal table for analytics
metrics:
  duration: 11m
  completed: 2026-01-22
---

# Phase 24 Plan 01: Trial System Backend Summary

**One-liner:** Free trial system with 100-trade/3-day dual limits, auto-start on first signal, and enforcement in signal processor.

## Completed Tasks

| Task | Description | Commit | Key Files |
|------|-------------|--------|-----------|
| 1 | Add trial fields to User model | aade39a (prior) | models.py, 016_add_trial_fields.py |
| 2 | Create trial service and API | 2134e85 | trial_service.py, trial.py, main.py |
| 3 | Integrate trial into signal processor | 07e5d59 | signal_processor.py, database_models.py |

## Implementation Details

### Trial Database Schema
Added to User model:
- `trial_trade_count` (Integer, default 0): Tracks trades used during trial
- `trial_started_at` (DateTime): When trial began (set on first signal)
- `trial_ended_at` (DateTime): When trial expired
- `trial_status` (String): pending, active, expired, completed

Migration 016 handles existing users:
- Free tier users: trial_status = "pending"
- Pro users: trial_status = "completed"

### Trial Service (244 lines)
Core methods:
- `start_trial(user)`: Begin trial, set trial_started_at and status=active
- `increment_trade_count(user)`: Add 1 to trade count after successful execution
- `check_trial_status(user)`: Return NOT_STARTED/ACTIVE/EXPIRED/NOT_APPLICABLE
- `get_trial_info(user)`: Detailed trial info with remaining trades/days
- `expire_trial(user)`: Mark trial as expired

TrialStatus enum:
- NOT_STARTED: Trial pending, hasn't executed first signal
- ACTIVE: Trial in progress, limits not exceeded
- EXPIRED: Trial ended (100 trades or 3 days exceeded)
- NOT_APPLICABLE: User on paid tier

### Trial API Endpoints
- `GET /api/trial/status`: Full trial info for current user
- `POST /api/trial/start`: Manually start trial (normally auto-started)
- `GET /api/trial/check`: Quick can_trade check for UI

### Signal Processor Integration
Trial check happens in `_execute_on_account()` before deduplication:
1. Check trial status for user
2. If NOT_STARTED: Auto-start trial
3. If EXPIRED: Block with trial_expired reason
4. After successful execution: Increment trade count
5. If trade count >= 100: Auto-expire trial

Added TRIAL_EXPIRED to RejectedSignalReason enum for rejection logging.

## Verification Results

| Check | Status |
|-------|--------|
| Migration 016 valid Python | PASS |
| Trial service >= 80 lines | PASS (244 lines) |
| TrialStatus enum has 4 values | PASS |
| User model has trial fields | PASS |
| Trial check before signal execution | PASS |
| Trade count increments on success | PASS |
| RejectedSignalReason.TRIAL_EXPIRED | PASS |

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **Trial auto-starts on first signal**: Rather than requiring explicit trial start, the trial begins automatically when a free user sends their first signal. This provides better UX with zero friction.

2. **Trial status stored in database**: The trial_status field stores the current state. Once expired, it stays expired (except admin reset). This allows efficient queries without re-calculating dates every time.

3. **Fail-open on errors**: If trial check errors, execution is allowed. This prevents system issues from blocking legitimate trades.

4. **Trial rejections in RejectedSignal table**: Using existing rejection logging infrastructure provides analytics on trial expiration patterns.

## Files Created/Modified

### Created
- `app/services/trial_service.py` (244 lines): TrialService class, TrialStatus enum, MAX_TRIAL_TRADES/MAX_TRIAL_DAYS constants
- `app/routers/trial.py` (148 lines): Trial API endpoints
- `alembic/versions/016_add_trial_fields.py` (44 lines): Database migration

### Modified
- `app/models/models.py`: Added trial_trade_count, trial_started_at, trial_ended_at, trial_status to User
- `app/models/database_models.py`: Added TRIAL_EXPIRED to RejectedSignalReason
- `app/services/signal_processor.py`: Added trial check before execution, increment after success
- `app/main.py`: Registered trial_router at /api/trial

## Next Phase Readiness

Plan 24-04 (Trial UI & Upgrade Prompts) can now:
- Call `GET /api/trial/status` for trial widget data
- Check `can_trade` from `/api/trial/check`
- Show remaining trades/days
- Display upgrade prompts when trial expired

## Testing Notes

Database not available locally - migration syntax validated via Python import.
Signal processor integration verified via import check.
Manual testing required in staging environment:
1. Create new free user
2. Send first signal - verify trial starts
3. Verify trade count increments
4. Test GET /api/trial/status endpoint
