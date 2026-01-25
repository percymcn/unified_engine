# Post-GREEN Hardening Report

**Date:** 2026-01-24
**Branch:** `fix/post-green-3fixes-20260124`
**Tag (pre-fix):** `post-green-fixes-pre-20260124`
**Commit:** 59ea94d

---

## WHAT CHANGED

### Fix 1: Google OAuth Cookie Name Mismatch (CRITICAL)
- **File:** `ui-next/src/app/api/auth/google/callback/route.ts`
- **Change:** Replaced hardcoded `'token'` with `AUTH_COOKIE_NAME` constant (`'auth-token'`)
- **Import added:** `import { AUTH_COOKIE_NAME } from '@/lib/auth';`

### Fix 2: Add Unique Index for webhook_key (MEDIUM)
- **File:** `alembic/versions/024_add_unique_index_trading_accounts_webhook_key.py`
- **New migration:** Creates partial unique index on `trading_accounts.webhook_key`
- **SQL:** `CREATE UNIQUE INDEX IF NOT EXISTS ix_trading_accounts_webhook_key ON trading_accounts(webhook_key) WHERE webhook_key IS NOT NULL;`

### Fix 3: Redis Tradovate OAuth State (PRODUCTION)
- **File:** `app/routers/tradovate_oauth.py`
- **Change:** Replaced in-memory `_oauth_states: dict[str, dict] = {}` with Redis storage
- **Key pattern:** `tradovate:oauth_state:{state}`
- **TTL:** 600 seconds (10 minutes)
- **Behavior:** One-time use (key deleted after retrieval)

---

## WHY

| Issue | Impact | Risk Without Fix |
|-------|--------|------------------|
| Cookie name mismatch | Google OAuth login completely broken | Users cannot log in via Google |
| Missing unique index | Potential duplicate webhook keys | Data integrity issues, routing conflicts |
| In-memory OAuth state | State lost across process restarts/workers | Multi-process deployments fail CSRF validation |

---

## HOW VERIFIED

### A) Database Index
```bash
$ psql -c "SELECT indexname, indexdef FROM pg_indexes WHERE tablename='trading_accounts' AND indexname='ix_trading_accounts_webhook_key';"

             indexname            |                                                                 indexdef
---------------------------------+------------------------------------------------------------------------------------------------------------------------------------------
 ix_trading_accounts_webhook_key | CREATE UNIQUE INDEX ix_trading_accounts_webhook_key ON public.trading_accounts USING btree (webhook_key) WHERE (webhook_key IS NOT NULL)
(1 row)
```

### B) Alembic Migration
```bash
$ python3 -m alembic current
024_webhook_key_unique_index (head)
```

### C) Redis OAuth State Test
```
1. Store state: OK
2. Key exists: OK
3. Retrieve data: OK - {'user_id': 999, 'environment': 'demo'}
4. TTL is set: OK (TTL=600s)
5. Delete on consume: OK
6. Key deleted: OK

Redis OAuth state test: ALL PASSED
```

### D) Backend Health
```bash
$ curl http://127.0.0.1:8765/health
{"status":"healthy","redis":"connected","brokers":{"mt4":true,"mt5":true,"tradelocker":false,"tradovate":false,"projectx":false},"timestamp":39060.906838741}
```

### E) No In-Memory Dict
```bash
$ grep "_oauth_states" app/routers/tradovate_oauth.py
No in-memory dict found - GOOD
```

---

## ROLLBACK INSTRUCTIONS

### Option 1: Git Revert (Recommended)
```bash
# Revert to previous state
git checkout fix/missing-greenlet-startup

# Or reset to pre-fix tag
git checkout post-green-fixes-pre-20260124
```

### Option 2: Downgrade Database Migration
```bash
# Only if migration 024 was applied
export DATABASE_URL="postgresql://trading_user:trading_password@localhost:5432/trading_db"
python3 -m alembic downgrade 023_fix_fk_to_trading_accounts
```

### Option 3: Full Recovery Snapshot
```bash
# Return to GREEN recovery point
git checkout recovery/claude-green-20260124

# Or tag
git checkout pre_claude_green_20260124
```

---

## FILES MODIFIED

| File | Lines Changed | Type |
|------|---------------|------|
| `ui-next/src/app/api/auth/google/callback/route.ts` | +2, -1 | Bug fix |
| `alembic/versions/024_add_unique_index_trading_accounts_webhook_key.py` | +42 | New file |
| `app/routers/tradovate_oauth.py` | +41, -6 | Refactor |

**Total:** 3 files, +85 insertions, -7 deletions

---

## STATUS: COMPLETE

All verification checks passed. System is operational.
