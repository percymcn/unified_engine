# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-22)

**Core value:** Reliable signal-to-trade execution across all configured brokers with zero missed signals.
**Current focus:** v1.2 Full Broker Integration

## Current Position

Phase: 25 — Bug Fix Verification (pending)
Plan: N/A (not yet planned)
Status: v1.2 milestone started, awaiting requirements definition
Last activity: 2026-01-22 — v1.2 milestone initialized

Progress: v1.0 + v1.1 complete (24 phases, 110 plans); v1.2 in progress

## GSD Workflow: Phase 1 Stability Fixes

**Status:** COMPLETE ✅

**Wave 1 Plans:**
- Plan 01: Fix aioredis Deprecated Import — ✅ Done (verified on disk)
- Plan 02: Fix Broker Executor Initialization Crashes — ✅ Done (verified on disk)
- Plan 03: Remove Hardcoded Test API Key — ✅ Done (verified on disk)

**Wave 2 Plans:**
- Plan 04: Verify Phase 1 Stability Fixes — ✅ Done (all verification tests passed)

**Verification Results:**
- ✅ No hardcoded `test-api-key` in source code
- ✅ `funnel_automation.py` uses `redis.asyncio` (no deprecated aioredis)
- ✅ `requirements.txt` has no `aioredis==2.0.1`
- ✅ All broker executors handle missing credentials gracefully (`is_available=False`)
- ✅ All critical imports work without errors
- ✅ NATS graceful fallback verified (already implemented)

**Last verified:** 2026-01-23 (all verification tests passed, ready for handoff)

## Active Milestone: v1.2 Full Broker Integration

**Goal:** Replace placeholder broker adapters with production-ready integrations using official APIs and SDKs.

**Target features:**
- Bug fix verification (auth cookies, risk page, WebSocket)
- ProjectX/TopStep integration via Gateway API (direct HTTP)
- TradeLocker integration via official Python SDK
- Unified account selection UI with Test & Connect flow
- Enhanced symbol/contract mapping for futures

**Planned Phases:**
- Phase 25: Bug Fix Verification
- Phase 26: ProjectX Gateway Integration
- Phase 27: TradeLocker SDK Integration
- Phase 28: Account Selection & Routing
- Phase 29: Symbol Mapping Enhancement

**Constraints:**
- Use ProjectX Gateway API directly (NOT project-x-py pip package)
- Use official tradelocker Python SDK
- All credentials encrypted with Fernet
- Start with Demo environments for testing

## Shipped Milestones

| Milestone | Phases | Plans | Shipped |
|-----------|--------|-------|---------|
| v1.0 Full Refactor | 1-11 | 63 | 2026-01-21 |
| v1.1 Production Ready | 12-24 | 47 | 2026-01-22 |

**Total:** 24 phases, 110 plans, 160 requirements satisfied

## Accumulated Decisions

Key decisions from v1.1 that carry forward:

| Phase | Decision | Rationale |
|-------|----------|-----------|
| 15-01 | Dual-mode TradeLocker (SDK + Brand API) | SDK preferred, API fallback |
| 16-01 | In-memory OAuth state store | Simple for single-instance; needs Redis for HA |
| 20-01 | Preserve symbol numbers in normalization | US30, NAS100 are valid symbols |
| 21-02 | Four routing strategies | all_accounts, specific_accounts, rules_based, default_only |
| 22-01 | Close actions bypass all risk checks | Closing should never be blocked |
| 24-01 | Trial auto-starts on first signal | Zero friction UX |
| 24-02 | 4-tier pricing with broker limits | tier_1=1, tier_2=2, tier_3=3, tier_4=4 |
| 24-03 | Fail open on deduplication errors | Don't block legitimate trades |

## Known Tech Debt

- npm audit: 3 high severity vulnerabilities (dev-only, eslint-related)
- Alembic has multiple heads (001, 002)
- In-memory OAuth state store (needs Redis for multi-instance production)

## Next Steps

1. **Define requirements** via `/gsd:define-requirements`
2. **Create roadmap** via `/gsd:create-roadmap`
3. **Plan phases** via `/gsd:plan-phase 25`
4. **Execute phases** via `/gsd:execute-phase 25`

## 2026-01-27 Multi-account Verification

- Added `tests/domain/test_account_routing_service.py` to cover `specific_accounts`, `rules_based`, and fallback routing strategies.
- `scripts/smoke_routing_multi_account.sh` now writes logs to `.gsd/reports/logs` so verification artifacts are tracked with other reports.
- Targeted pytest run: `python -m pytest tests/domain/test_account_routing_service.py -q` (log at `.gsd/reports/logs/pytest_account_routing.log`).

## 2026-01-27 DB Availability Recheck

- Re-ran `alembic current` with `DATABASE_URL=postgresql://trading_user:trading_password@localhost:5432/trading_db`; still fails with `psycopg2.OperationalError` while opening a TCP connection (log at `.gsd/reports/logs/alembic_current.log`).
- Tried the smoke scripts (`scripts/smoke_backend.sh`, `scripts/smoke_webhooks.sh`, `scripts/smoke_user_flow.sh`, `scripts/smoke_signal_intelligence.sh`, `scripts/smoke_routing_multi_account.sh`); each fails because the backend never starts (`scripts/smoke_backend.sh` ends with “Database connection timed out”) or because the frontend requests return HTTP 000 when the service is unreachable (logs under `.gsd/reports/logs/`).
- `python -m pytest` was re-run (log at `.gsd/reports/logs/pytest.log`) but the command timed out at 600 s while dozens of tests failed immediately; the suite cannot make progress until the database connection is healthy.

## 2026-01-27 Verification Retry (third attempt)

- `alembic current` rerun (log: `.gsd/reports/logs/alembic_current_retry.log`) still fails with `psycopg2.OperationalError` on the DB connection handshake.
- Smoke scripts rerun with recorded logs (`.gsd/reports/logs/smoke_backend_retry.log`, `.gsd/reports/logs/smoke_webhooks_retry.log`, `.gsd/reports/logs/smoke_user_flow_retry.log`, `.gsd/reports/logs/smoke_signal_intelligence_retry.log`, `.gsd/reports/logs/smoke_routing_multi_account_retry.log`) and continue to trip over backend startup failure and HTTP 000 responses because `_verify_database_connection()` cannot reach Postgres.
- `python -m pytest` rerun (log: `.gsd/reports/logs/pytest_retry.log`) again timed out at 600 s while numerous signal/service/adapter tests failed immediately; the DB must be reachable before rerunning the suite could succeed.

## 2026-01-27 Final Verification Attempt

- `test_pg_connection.py` (log: `.gsd/reports/logs/postgres_final_test.log`) reports PostgreSQL is responsive on `127.0.0.1:5432`, but the rest of the stack still cannot establish a connection.
- `psql` against `127.0.0.1:5432` (log: `.gsd/reports/logs/psql_final.log`) still fails with `psql: error:` (no additional text), reinforcing that the CLI and SQLAlchemy clients cannot reach the socket.
- `alembic current` (log: `.gsd/reports/logs/alembic_current_final.log`) still raises `psycopg2.OperationalError` while attempting to connect.
- Smoke scripts rerun and log to `.gsd/reports/logs/smoke_*_final.log`; each script terminates because the backend cannot start (`RuntimeError("Database connection timed out")`) and HTTP requests receive code `000`.
- `python -m pytest` + `python -m pytest -x -v` (logs: `.gsd/reports/logs/pytest_final.log`, `.gsd/reports/logs/pytest_final_rerun.log`) both fail; rerun stops at `tests/application/test_signal_use_cases.py::TestProcessSignalUseCase::test_process_buy_signal_success` with an `invalid literal for int()` error, proving the signal processing pipeline still breaks when accounts are labeled with strings.

## 2026-01-26 Production Hardening Assessment

**Backend Status:** HEALTHY
- Health endpoint: `{"status":"healthy","redis":"connected"}`
- Brokers: MT4=true, MT5=true, TradeLocker=false (no creds), Tradovate=false, ProjectX=false
- Database: 40 tables, Alembic at revision 024 (single head)
- All smoke tests passing

**Fixes Applied:**
1. TradeLocker: Updated `environment` → `sdk_environment` with full URLs in contracts JSON
2. Tradovate: Added `app_version` field to contracts JSON
3. Backend routers updated to accept both old and new field names for backwards compatibility

**Verified Working:**
- ✅ Webhook ingestion pipeline (`POST /api/v1/webhook/execute`)
- ✅ Signal Intelligence Guard (staleness, momentum, pause)
- ✅ Risk Management (limits, rejections logged)
- ✅ Credential encryption (Fernet)
- ✅ Broker contracts API (`GET /api/v1/brokers/contracts`)
- ✅ All smoke tests pass

**Gaps Identified:**
- Multi-account simultaneous routing not implemented (routes to ONE account only)
- Symbol-based routing rules not implemented
- Strategy-based routing rules not implemented
- Account discovery needs real-credential testing
- Execution trace UI view missing

**Report:** `.gsd/reports/TRADEFLOW_PROD_HARDENING_20260126.md`

---
*Last updated: 2026-01-26 after production hardening Phase 0*
