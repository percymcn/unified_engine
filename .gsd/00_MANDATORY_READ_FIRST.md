# MANDATORY READ FIRST — TradeFlow Unified Engine (Jan 2026)

You MUST read these files BEFORE any edits:
1) .planning/STATE.md
2) .planning/ROADMAP.md
3) .planning/PROJECT.md
4) .planning/DB_POLICY.md (if missing, use docs/DB_POLICY.md)
5) .planning/DB_ALIGNMENT_REPORT.md
6) .planning/REHYDRATION_REPORT.md
7) .planning/codebase/ARCHITECTURE.md
8) .planning/codebase/CONVENTIONS.md
9) .planning/CHANGESET_INDEX.md
10) .planning/DEPLOY_VERIFY_PLAN.md

HARD GUARDRAILS (NON-NEGOTIABLE)
- Canonical ports: API=8765, UI=3456, Postgres=5432
- Postgres is canonical DB. SQLite is NOT allowed for this stack.
- DO NOT use alembic --autogenerate unless explicitly told (drift risk).
- Never commit .env or secrets. .env must stay gitignored.
- Any change requires:
  (1) preflight verification
  (2) smallest logical commit(s)
  (3) .gsd report with Commands Run + Results
  (4) postflight verification

PRE/POST COMMANDS (must run)
- ./scripts/verify_stack.sh
- ./scripts/verify_green.sh
- ./scripts/doctor_env.sh
- curl http://localhost:8765/health
- curl http://localhost:8765/api/billing/plans
- curl http://localhost:8765/api/v1/brokers/contracts

WHAT “DONE” MEANS
- Git status clean
- Ports stable
- Postgres in use
- UI+API reachable on LAN
- Reports written under .gsd/reports/
