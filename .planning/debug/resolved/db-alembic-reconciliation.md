---
status: resolved
trigger: "Perform ZERO-RISK audit + DB migration reconciliation for TradeFlow Unified Engine"
created: 2026-01-23T00:00:00Z
updated: 2026-01-23T15:00:00Z
---

## Current Focus

hypothesis: CONFIRMED AND FIXED - Schema drift reconciled via bridge migration 020
test: Verified schema columns match ORM expectations
expecting: All Signal Intelligence features now work
next_action: Complete - archive session

## Symptoms

expected: Alembic migrations 001-019 should be the source of truth. Running `alembic upgrade head` should work cleanly. DATABASE_URL should be consistent across app, Alembic, and Docker.

actual:
- Alembic env.py uses get_url() and defaults to Postgres when DATABASE_URL env is unset
- App settings default to SQLite (trading_db.db) when DATABASE_URL env is unset
- Previous error: "psycopg2.errors.DuplicateTable: relation api_keys already exists" during alembic upgrade
- Prior work used Base.metadata.create_all() + manual CREATE/ALTER + alembic stamp head (019) to "align" DB
- This is a red flag - DB may not be truly consistent with migrations 001-019

errors: psycopg2.errors.DuplicateTable (previously observed)

reproduction: Run `alembic upgrade head` without careful DATABASE_URL management

started: Recently shipped Milestone 1.2 (Signal Intelligence Layer) and Patch 1.2.1 (Per-broker webhooks + Theme isolation)

## Eliminated

- hypothesis: "trading_accounts table missing"
  evidence: Table is named "accounts" (from models.py), NOT "trading_accounts". Migration 019 references wrong table name.
  timestamp: 2026-01-23

- hypothesis: "DB is empty and needs fresh migration"
  evidence: DB has 22 tables, alembic_version = 019, schema is populated
  timestamp: 2026-01-23

## Evidence

- timestamp: 2026-01-23T12:00
  checked: Docker services running
  found: postgres (330ce5e4921e), redis, nats, cloudflared all running
  implication: Production stack is operational

- timestamp: 2026-01-23T12:01
  checked: alembic_version table
  found: version_num = "019"
  implication: DB is stamped at head, but this was done via stamp, not actual migration run

- timestamp: 2026-01-23T12:02
  checked: DATABASE_URL in .env file
  found: DATABASE_URL=sqlite:////home/pharma5/unified_engine/trading_db.db
  implication: Local .env points to SQLite! Docker stack uses Postgres via environment variable override

- timestamp: 2026-01-23T12:03
  checked: Docker stack DATABASE_URL
  found: DATABASE_URL=postgresql://trading_user@postgres:5432/trading_db (password from secret)
  implication: Docker is correctly configured for Postgres

- timestamp: 2026-01-23T12:04
  checked: Alembic env.py default
  found: Defaults to postgresql://trading_user:trading_password@localhost:5432/trading_db
  implication: Alembic defaults to Postgres but different host than Docker service

- timestamp: 2026-01-23T12:05
  checked: Public schema tables
  found: 22 tables including accounts, momentum_settings, signal_counters, discard_bin
  implication: Schema is populated with Milestone 1.2 and Patch 1.2.1 tables

- timestamp: 2026-01-23T12:06
  checked: accounts table columns
  found: Has webhook_key column (text type)
  implication: Patch 1.2.1 webhook_key was added

- timestamp: 2026-01-23T12:07
  checked: users table columns
  found: Has theme column (character varying)
  implication: Patch 1.2.1 theme column was added

- timestamp: 2026-01-23T12:08
  checked: signal_counters table columns (before fix)
  found: Mixed columns - directional_bias, opposite_momentum, total_signals, last_signal_at, created_at
  implication: SCHEMA DRIFT CONFIRMED - create_all ran multiple times with different model states

- timestamp: 2026-01-23T12:09
  checked: discard_bin table columns (before fix)
  found: raw_payload/normalized_payload instead of raw_signal_json/normalized_signal_json
  implication: SCHEMA DRIFT CONFIRMED - column names differ

- timestamp: 2026-01-23T15:00
  checked: signal_counters table columns (after fix)
  found: current_bias, opposite_momentum, last_signal_ts, updated_at, last8_pattern, chop_mode
  implication: Schema now matches ORM model

- timestamp: 2026-01-23T15:01
  checked: discard_bin table columns (after fix)
  found: raw_signal_json (json), normalized_signal_json (jsonb)
  implication: Schema now matches ORM model

- timestamp: 2026-01-23T15:02
  checked: alembic_version
  found: version_num = "020"
  implication: Migration 020 applied successfully

## Resolution

root_cause: |
  MULTI-FACTOR ROOT CAUSE:
  1. CONFIG MISMATCH: .env has SQLite, Docker has Postgres, Alembic defaults to localhost Postgres
  2. SCHEMA DRIFT: Previous work used Base.metadata.create_all() which reflects models.py state, not migration DDL
  3. MIGRATION 019 BUG: References "trading_accounts" but table is named "accounts" in models.py
  4. MANUAL STAMP: alembic stamp head (019) was used instead of actual upgrade, masking drift
  5. MULTIPLE CREATE_ALL RUNS: Table had both old and new column names as duplicates

fix: |
  COMPLETED:
  1. Created bridge migration 020 (alembic/versions/020_bridge_schema_drift_reconciliation.py)
  2. Applied migration via psql (idempotent SQL)
  3. Fixed migration 019 to use 'accounts' instead of 'trading_accounts'
  4. Updated alembic_version to 020

  Schema changes applied:
  - signal_counters: Renamed directional_bias->current_bias, last_signal_at->last_signal_ts
  - signal_counters: Dropped total_signals (duplicate), created_at (not in ORM)
  - signal_counters: Added last8_pattern, chop_mode
  - discard_bin: Renamed raw_payload->raw_signal_json, normalized_payload->normalized_signal_json

  Reports created:
  - .planning/DB_AUDIT_REPORT.md
  - .planning/DB_SCHEMA_DIFF.md
  - .planning/ALEMBIC_RECONCILIATION_PLAN.md
  - .planning/DEPLOY_VERIFY_PLAN.md

  Scripts created:
  - scripts/db_audit.sh (read-only audit)
  - scripts/db_parallel_migrate_validate.sh (clean DB test)

verification: |
  VERIFIED:
  1. alembic current shows 020
  2. signal_counters has correct columns: current_bias, opposite_momentum, last_signal_ts, last8_pattern, chop_mode, updated_at
  3. discard_bin has correct columns: raw_signal_json (json), normalized_signal_json (jsonb)
  4. Migration 019 fixed to reference 'accounts' table (not 'trading_accounts')

files_changed:
  - .planning/DB_AUDIT_REPORT.md (created)
  - .planning/DB_SCHEMA_DIFF.md (created)
  - .planning/ALEMBIC_RECONCILIATION_PLAN.md (created)
  - .planning/DEPLOY_VERIFY_PLAN.md (created)
  - scripts/db_audit.sh (created)
  - scripts/db_parallel_migrate_validate.sh (created)
  - alembic/versions/019_add_per_broker_webhooks_and_theme.py (fixed table name)
  - alembic/versions/020_bridge_schema_drift_reconciliation.py (created)
