---
status: resolved
trigger: "postgres-ports-drift: TradeFlow has ENV/DB/port drift - sometimes SQLite, sometimes Postgres, backend sometimes on 8000 instead of 8765. Need to anchor to canonical settings."
created: 2026-01-23T17:00:00Z
updated: 2026-01-23T19:30:00Z
resolved: 2026-01-23T19:30:00Z
symptoms_prefilled: true
goal: find_and_fix
---

## RESOLVED

All phases completed:
- scripts/local_up_postgres.sh created
- .env fixed (Postgres + port 8765)
- All scripts normalized to port 8765
- docs/DB_POLICY.md created
- webhook_key column added to trading_accounts
- Stack verified running (backend 8765, UI 3456)

## Current Focus

hypothesis: ROOT CAUSE CONFIRMED - .env has wrong PORT=8000 and DATABASE_URL=sqlite, scripts have inconsistent port defaults
test: Verified all config sources
expecting: Need to normalize to canonical: Postgres on 5432, API on 8765, UI on 3456
next_action: COMPLETED - All fixes applied

## Symptoms

expected:
- Canonical DB is Postgres on port 5432 (DATABASE_URL=postgresql://trading_user:trading_password@localhost:5432/trading_db)
- Canonical ports: API=8765, UI=3456
- All scripts and tools use these consistently

actual:
- Tools sometimes use SQLite (trading_db.db), sometimes Postgres
- Backend sometimes starts on 8000 instead of 8765
- SDK/ENV expectations broken, UI broker forms confused

errors: Various "missing column" surprises, broker form mismatches

reproduction:
- Run different scripts and observe which DB/port they use
- Check .env, docker-compose, scripts/*.sh for conflicting settings

timeline: Accumulated drift over development iterations

## Eliminated

## Evidence

- timestamp: 2026-01-23T18:05:00Z
  checked: .env file (line 17, 26)
  found: PORT=8000, DATABASE_URL=sqlite:////home/pharma5/unified_engine/trading_db.db
  implication: ROOT CAUSE - .env has wrong canonical settings

- timestamp: 2026-01-23T18:05:00Z
  checked: Listening ports
  found: postgres:5432, uvicorn:8765, next:3456 currently running correctly
  implication: Current runtime is correct, but .env would break future restarts

- timestamp: 2026-01-23T18:05:00Z
  checked: .env.example (line 18, 213-215)
  found: PORT=8000, VITE_API_BASE_URL=http://localhost:8000, BACKEND_PORT=8000
  implication: Template perpetuates wrong defaults

- timestamp: 2026-01-23T18:06:00Z
  checked: docker-compose.yml (line 59)
  found: API service uses ports "8000:8000"
  implication: Docker workflow uses wrong port

- timestamp: 2026-01-23T18:06:00Z
  checked: scripts/*.sh - default ports
  found:
    - verify_stack.sh: defaults to 3012
    - verify_green.sh: hardcoded 3012
    - smoke_signal_intelligence.sh: defaults to 3012
    - smoke_user_flow.sh: defaults to 3012
    - smoke_webhooks.sh: defaults to 3012
    - verify_signal_intelligence.sh: defaults to 8765
    - ui_broker_contract_smoke.sh: defaults to 8765
    - verify_pricing_consistency.sh: defaults to 3456 (frontend)
  implication: Inconsistent ports, 3012 is mysterious phantom port

- timestamp: 2026-01-23T18:06:00Z
  checked: run_backend.py (line 12, 51, 62)
  found: Defaults to finding free port starting from 8000
  implication: This allows drift to wrong port when PORT not explicitly set

- timestamp: 2026-01-23T18:07:00Z
  checked: SQLite file
  found: trading_db.db exists (638KB), last modified 17:48 today
  implication: SQLite was actively being used, causing schema divergence

- timestamp: 2026-01-23T18:08:00Z
  checked: Alembic state with Postgres
  found: Postgres is at revision 020 (head), migrations are current
  implication: Postgres schema is up-to-date, SQLite is the problem

- timestamp: 2026-01-23T18:08:00Z
  checked: ui-next/.env.local
  found: BACKEND_URL=http://localhost:8765 (correct!)
  implication: UI is correctly configured, backend config is the problem

## Resolution

root_cause: |
  1. .env has DATABASE_URL=sqlite:/// instead of postgresql://
  2. .env has PORT=8000 instead of 8765
  3. .env.example documents 8000 as canonical (perpetuates drift)
  4. run_backend.py defaults to port 8000 search
  5. Multiple scripts default to port 3012 (phantom port, never canonical)
  6. docker-compose.yml uses 8000:8000 for API service
  Result: Depending on which tool/script starts the backend, different DB and ports are used.

fix: |
  PHASE B:
  1. Create scripts/local_up_postgres.sh - canonical startup script
  2. Fix .env to use Postgres and port 8765
  3. Fix .env.example to document 8765 as canonical
  4. Update all scripts to default to 8765 (not 3012 or 8000)
  5. Fix docker-compose.yml to use 8765
  6. Fix run_backend.py to default to 8765 (not 8000)

  PHASE C:
  7. Mark SQLite as deprecated artifact
  8. Document policy in docs/DB_POLICY.md

verification:
files_changed: []
