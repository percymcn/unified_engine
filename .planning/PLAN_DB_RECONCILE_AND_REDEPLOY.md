# DB Reconciliation and Redeployment Plan

**Date:** January 22, 2026  
**Goal:** Align DB configuration (Alembic + app runtime) to Postgres, rebuild/redeploy, verify Milestone 1.2 + Patch 1.2.1

## Plan Overview

### Checkpoints

1. ✅ **Repo Safety Snapshot** - Capture current state
2. ⏳ **Discover Postgres Credentials** - Extract from Docker Swarm service
3. ⏳ **Align App Config** - Ensure DATABASE_URL points to Postgres
4. ⏳ **Align Alembic Config** - Same DATABASE_URL source
5. ⏳ **Migration State Fix** - Stamp/upgrade safely
6. ⏳ **Verify Schema** - Confirm Patch 1.2.1 columns exist
7. ⏳ **Rebuild/Redeploy** - Existing containers only
8. ⏳ **Smoke Tests** - End-to-end verification
9. ⏳ **Versioning** - Lightweight release notes
10. ⏳ **Lockdown** - Commit and document

## Current State

- Alembic: Uses Postgres via `alembic/env.py` (reads DATABASE_URL)
- App Runtime: Defaults to SQLite when DATABASE_URL unset
- Docker Swarm: `unified_trading_db` service (postgres:15) on port 5432
- Migrations: Up to head 019 (Patch 1.2.1)

## Risks & Mitigations

- **Risk:** Alembic/app pointing to different DBs
  - **Mitigation:** Use same DATABASE_URL env var for both
- **Risk:** Migration state out of sync
  - **Mitigation:** Use `alembic stamp head` if schema exists, then verify
- **Risk:** Breaking existing deployments
  - **Mitigation:** Backward compatible changes only, no schema deletions

## Execution Log

### Step 0: Repo Safety Snapshot
- [x] git status captured
- [x] git log captured

### Step 1: Discover Postgres Creds
- [ ] Inspect Docker Swarm service
- [ ] Extract DB name, user, password
- [ ] Construct DATABASE_URL (redacted in docs)

### Step 2: Align App Config
- [ ] Check app/core/config.py for DATABASE_URL handling
- [ ] Ensure .env or service env file sets DATABASE_URL
- [ ] Verify app reads Postgres URL

### Step 3: Align Alembic
- [ ] Verify alembic/env.py reads DATABASE_URL
- [ ] Export DATABASE_URL for migration commands

### Step 4: Migration State Fix
- [ ] Check alembic heads/current
- [ ] Stamp if needed
- [ ] Upgrade to head

### Step 5: Verify Schema
- [ ] Check users.theme exists
- [ ] Check trading_accounts.webhook_key exists

### Step 6: Rebuild/Redeploy
- [ ] Detect deployment method
- [ ] Rebuild/restart services
- [ ] Verify services UP

### Step 7: Smoke Tests
- [ ] Create verify_stack.sh
- [ ] Create smoke_webhooks.sh
- [ ] Run and capture outputs

### Step 8: Versioning
- [ ] Create docs/RELEASE_NOTES.md
- [ ] Update app/main.py logging (non-breaking)

### Step 9: Lockdown
- [ ] Update STATUS_REPORT_1_2.md
- [ ] Update FINAL_VERIFICATION_SUMMARY.md
- [ ] Commit changes
