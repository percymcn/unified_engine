# CHANGESET INDEX - January 2026

**Generated:** 2026-01-23
**Last Updated:** 2026-01-23 19:15 UTC
**Branch:** `wire-brokers-tradelocker-projectx-20260122`
**Status:** Continuation session complete

## Overview

This document indexes all changes made during:
1. **Milestone 1.2** - Signal Intelligence Layer "Self-Healing Execution"
2. **Patch 1.2.1** - Secure Per-Broker Webhooks + Theme Isolation
3. **DB Reconciliation** - Alembic migrations-first convergence

---

## Feature Area: Signal Intelligence Guard Layer (Milestone 1.2)

### Commits
- `4acc73e` feat: Complete Signal Intelligence Layer v1.2 - Self-Healing Execution
- `7f54e54` docs: Add final verification summary and update status reports

### Files Changed

**Backend:**
| File | Type | Description |
|------|------|-------------|
| `app/services/signal_intelligence_guard.py` | NEW | Core guard logic (sg-001 to sg-007) |
| `app/routers/signal_intelligence.py` | NEW | API endpoints for settings/counters/discard-bin |
| `app/routers/webhooks.py` | MOD | Guard layer integration at all 3 endpoints |
| `app/models/database_models.py` | MOD | Added MomentumSettings, SignalCounter, DiscardBin |
| `app/main.py` | MOD | Registered signal_intelligence router |
| `alembic/versions/018_add_signal_intelligence_tables.py` | NEW | Migration for guard tables |

**Frontend:**
| File | Type | Description |
|------|------|-------------|
| `ui-next/src/components/signal-intelligence/momentum-meter.tsx` | NEW | Visual momentum progress bar |
| `ui-next/src/components/signal-intelligence/signal-heat-map.tsx` | NEW | 24h buy/sell heat map |
| `ui-next/src/components/signal-intelligence/guard-modal.tsx` | NEW | Breakeven/Close/Ignore/Hedge actions |
| `ui-next/src/components/signal-intelligence/flowguard-bot.tsx` | NEW | Alert JSON generator (sg-008) |
| `ui-next/src/app/api/signal-intelligence/*/route.ts` | NEW | BFF proxy routes |
| `ui-next/src/app/dashboard/settings/risk/page.tsx` | MOD | Momentum settings UI |
| `ui-next/src/app/dashboard/page.tsx` | MOD | Heat map + FlowGuard bot integration |

**Tests:**
| File | Type | Description |
|------|------|-------------|
| `tests/test_signal_intelligence_guard.py` | NEW | 13 unit tests for guard layer |

**Docs:**
| File | Type | Description |
|------|------|-------------|
| `docs/INSTALL_AND_API.md` | NEW | API documentation (sg-009) |
| `STATUS_REPORT_1_2.md` | NEW | Full milestone status report |
| `.planning/PHASE_0_MAP.md` | NEW | Architecture injection points map |
| `.planning/IMPLEMENTATION_VERIFICATION.md` | NEW | Blueprint compliance verification |

### Migration
- **018**: `alembic/versions/018_add_signal_intelligence_tables.py`
  - Creates: `momentum_settings`, `signal_counters`, `discard_bin`

---

## Feature Area: Secure Per-Broker Webhooks + Theme (Patch 1.2.1)

### Commits
- `5d10064` feat: Patch 1.2.1 secure per-broker webhooks + theme isolation

### Files Changed

**Backend:**
| File | Type | Description |
|------|------|-------------|
| `app/routers/webhooks_secure.py` | NEW | `/webhooks/incoming` secure endpoint |
| `app/routers/accounts.py` | MOD | Webhook key generation helper |
| `app/routers/users.py` | MOD | Theme handling in preferences |
| `app/models/models.py` | MOD | Added `theme` to User model |
| `app/models/database_models.py` | MOD | Added `webhook_key` to TradingAccount |
| `app/models/schemas.py` | MOD | Theme in PreferencesResponse/Update |
| `app/application/use_cases/manage_accounts.py` | MOD | Auto-generate webhook key |
| `app/main.py` | MOD | Registered webhooks_secure_router |
| `alembic/versions/019_add_per_broker_webhooks_and_theme.py` | NEW | Migration for theme + webhook_key |

**Frontend:**
| File | Type | Description |
|------|------|-------------|
| `ui-next/src/providers/theme-provider.tsx` | MOD | Route-based theme isolation |
| `ui-next/src/app/dashboard/settings/preferences/page.tsx` | MOD | Appearance section |
| `ui-next/src/components/accounts/account-card.tsx` | MOD | Copy Webhook button |
| `ui-next/src/types/account.ts` | MOD | Added webhook_key, user_id fields |

**Docs:**
| File | Type | Description |
|------|------|-------------|
| `.planning/PATCH_1_2_1_STATUS.md` | NEW | Patch status report |

### Migration
- **019**: `alembic/versions/019_add_per_broker_webhooks_and_theme.py`
  - Adds: `users.theme`, `accounts.webhook_key`
  - **Note:** Fixed 2026-01-23 to use `accounts` table (not `trading_accounts`)

---

## Feature Area: DB + Alembic Reconciliation

### Commits
- `af1d12c` chore: reconcile DB + alembic to 020 and verify deploy (safe, non-destructive)
- `2d264e8` chore: DB alignment + redeploy verification for milestones 1.2 and patch 1.2.1

### Files Changed

**Migrations:**
| File | Type | Description |
|------|------|-------------|
| `alembic/versions/019_add_per_broker_webhooks_and_theme.py` | FIX | Changed `trading_accounts` → `accounts` |
| `alembic/versions/020_bridge_schema_drift_reconciliation.py` | NEW | Bridge migration for schema drift |

**Scripts:**
| File | Type | Description |
|------|------|-------------|
| `scripts/db_audit.sh` | NEW | Read-only DB state verification |
| `scripts/db_parallel_migrate_validate.sh` | NEW | Non-destructive clean DB validation |
| `scripts/redeploy_unified_engine.sh` | NEW | Safe redeploy script |
| `scripts/run_migrations.sh` | NEW | Migration runner |
| `scripts/smoke_signal_intelligence.sh` | NEW | Signal intelligence smoke tests |

**Docs:**
| File | Type | Description |
|------|------|-------------|
| `.planning/DB_AUDIT_REPORT.md` | NEW | Runtime DB targets documentation |
| `.planning/DB_SCHEMA_DIFF.md` | NEW | Column-by-column comparison |
| `.planning/ALEMBIC_RECONCILIATION_PLAN.md` | NEW | Step-by-step reconciliation options |
| `.planning/DEPLOY_VERIFY_PLAN.md` | NEW | Safe rebuild/redeploy commands |
| `.planning/debug/db-alembic-reconciliation.md` | NEW | Debug session log |

### Migration
- **020**: `alembic/versions/020_bridge_schema_drift_reconciliation.py`
  - Reconciles schema drift from prior `create_all` runs
  - Fixes column naming mismatches

---

## Feature Area: Broker Wiring (TradeLocker + ProjectX)

### Commits
- `0eaa187` docs: add live wiring status document
- `bfeece0` docs: complete wiring report with final summary and guardrails
- `b8da4d9` test: add smoke tests documentation and fix ProjectX SDK test
- `d149a33` feat(ui): add Brand API requirement detection and dynamic form fields
- `ce728fe` feat(projectx): improve test connection and discovery error handling
- `137ef02` feat(tradelocker): add Brand API requirement detection and improved auth logic
- `3f53277` fix(backend): convert broker risk units to absolute prices at execution time
- `cf6eb79` fix(ui): convert broker risk units to absolute prices before execution

### Files Changed

**Backend:**
| File | Type | Description |
|------|------|-------------|
| `app/application/use_cases/test_connection.py` | MOD | Brand API detection, ProjectX fixes |
| `app/routers/accounts.py` | MOD | Discovery improvements |
| `app/domain/services/risk_unit_converter.py` | NEW | Risk unit conversion service |
| `app/services/signal_processor.py` | MOD | Execution-time risk conversion |
| `tests/test_connection_test.py` | NEW | 25+ connection tests |
| `tests/test_risk_unit_converter.py` | NEW | 14 risk converter tests |

**Frontend:**
| File | Type | Description |
|------|------|-------------|
| `ui-next/src/components/accounts/account-form.tsx` | MOD | Dynamic Brand API fields |
| `ui-next/src/lib/brokers/credentialSchemas.ts` | NEW | Broker credential field schemas |
| `ui-next/src/lib/brokers/riskUnitConverter.ts` | NEW | UI risk converter |

**Docs:**
| File | Type | Description |
|------|------|-------------|
| `docs/WIRING_REPORT.md` | NEW | Complete wiring details |
| `docs/SMOKE_TESTS.md` | NEW | Test commands |
| `docs/LIVE_WIRING_STATUS.md` | NEW | Live testing status |

---

## Migration Summary

| Version | File | Purpose | Tables/Columns |
|---------|------|---------|----------------|
| 018 | `018_add_signal_intelligence_tables.py` | Signal Intelligence | momentum_settings, signal_counters, discard_bin |
| 019 | `019_add_per_broker_webhooks_and_theme.py` | Secure Webhooks + Theme | users.theme, accounts.webhook_key |
| 020 | `020_bridge_schema_drift_reconciliation.py` | Schema Drift Fix | Column renames/reconciliation |

**Current Alembic Head:** 020

---

## Scripts Summary

| Script | Purpose |
|--------|---------|
| `scripts/db_audit.sh` | Read-only DB state verification |
| `scripts/db_parallel_migrate_validate.sh` | Non-destructive clean DB test |
| `scripts/redeploy_unified_engine.sh` | Safe stack redeploy |
| `scripts/run_migrations.sh` | Run Alembic migrations |
| `scripts/smoke_signal_intelligence.sh` | Signal Intelligence tests |

---

## UI Components Summary

| Component | Path | Feature |
|-----------|------|---------|
| MomentumMeter | `ui-next/src/components/signal-intelligence/momentum-meter.tsx` | sg-003 |
| SignalHeatMap | `ui-next/src/components/signal-intelligence/signal-heat-map.tsx` | sg-006 |
| GuardModal | `ui-next/src/components/signal-intelligence/guard-modal.tsx` | sg-001/004 |
| FlowGuardBot | `ui-next/src/components/signal-intelligence/flowguard-bot.tsx` | sg-008 |
| AccountForm | `ui-next/src/components/accounts/account-form.tsx` | Brand API detection |
| AccountCard | `ui-next/src/components/accounts/account-card.tsx` | Webhook copy |

---

## Current Session (2026-01-23 18:30 UTC)

### Phase 0: Baseline Snapshot
- `aa17b39` phase0: baseline snapshot + session log

### Phase 1: Frontend Build Verification
**Status:** ✅ COMPLETE
- Frontend builds successfully
- Runs on port 3456 (verified)
- Script: `ui-next/scripts/run_3456.sh` exists

**Files:**
- `.planning/PROD_BUILD_REPORT.md` - Updated with verification

### Phase 2: GSD Documentation Rehydration
**Status:** 🔄 IN PROGRESS
- `.planning/GSD_HANDOFF_BUNDLE.md` - Created
- `.planning/CHANGESET_INDEX.md` - Updated
- `.gsd/STATE_CAPSULE_2026-01.md` - To be updated

### Phase 3: SSO UI Cleanup
**Status:** ⏳ PENDING
- Remove/disable broken SSO buttons (GitHub/Google)
- Create `.planning/AUTH_UI_SSO_AUDIT.md`

### Phase 4: Broker Auth Smoke Test
**Status:** ⏳ PENDING
- Create `scripts/broker_auth_smoke.sh`
- Create `.planning/BROKER_AUTH_REPORT.md`

---

*Generated: 2026-01-23*
*Last Updated: 2026-01-23 18:40 UTC*
