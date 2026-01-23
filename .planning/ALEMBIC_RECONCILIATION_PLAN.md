# Alembic Reconciliation Plan

**Date:** 2026-01-23
**Status:** PLAN READY - Awaiting Approval

## Problem Statement

The production database schema has drifted from Alembic migration definitions:
1. `signal_counters` table has wrong column names and missing columns
2. `discard_bin` table has wrong column names and types
3. Migration 019 references `trading_accounts` but actual table is `accounts`
4. Alembic shows version 019 (head) via stamp, but schema doesn't match

## Option A: Bridge Migration (RECOMMENDED)

**Approach:** Create migration 020 to rename/add columns to align DB with ORM expectations.

### Pros
- Non-destructive (no data loss)
- Quick to implement (~30 minutes)
- Production DB stays online
- Alembic history becomes accurate going forward

### Cons
- Does not fix migration 019's table name bug
- Future fresh installs will still fail at 019

### Steps

1. **Create bridge migration 020:**
```bash
# From container or with correct DATABASE_URL
alembic revision -m "bridge_schema_drift_reconciliation"
```

2. **Edit the migration file** (see DB_SCHEMA_DIFF.md for SQL):
```python
def upgrade():
    # signal_counters fixes
    op.alter_column('signal_counters', 'directional_bias', new_column_name='current_bias')
    op.alter_column('signal_counters', 'total_signals', new_column_name='opposite_momentum')
    op.alter_column('signal_counters', 'last_signal_at', new_column_name='last_signal_ts')
    op.add_column('signal_counters', sa.Column('last8_pattern', sa.String(16), nullable=True))
    op.add_column('signal_counters', sa.Column('chop_mode', sa.Boolean(), nullable=False, server_default='false'))

    # discard_bin fixes
    op.alter_column('discard_bin', 'raw_payload', new_column_name='raw_signal_json', type_=sa.JSON())
    op.alter_column('discard_bin', 'normalized_payload', new_column_name='normalized_signal_json', type_=sa.JSON())
```

3. **Run the migration:**
```bash
docker exec <api_container_id> alembic upgrade head
```

4. **Verify:**
```bash
docker exec <postgres_container> psql -U trading_user -d trading_db -c "\\d signal_counters"
docker exec <postgres_container> psql -U trading_user -d trading_db -c "\\d discard_bin"
```

### Timeline
- Development: 30 minutes
- Testing on clean DB: 30 minutes
- Production deployment: 5 minutes
- **Total: ~1 hour**

---

## Option B: Parallel Clean Database Validation

**Approach:** Create a new database, run full migration chain, compare schemas.

### Pros
- Validates entire migration chain works
- Identifies all discrepancies
- Non-destructive to production

### Cons
- More time-consuming
- May reveal issues requiring significant refactoring
- Doesn't directly fix production

### Steps

1. **Create clean test database:**
```bash
docker exec <postgres_container> psql -U trading_user -d postgres -c "CREATE DATABASE trading_db_clean;"
```

2. **Run migrations against clean DB:**
```bash
export DATABASE_URL="postgresql://trading_user:PASSWORD@localhost:5432/trading_db_clean"
alembic upgrade head
```

3. **Compare schemas:**
```bash
# Dump both schemas
docker exec <postgres_container> pg_dump -U trading_user -s trading_db > prod_schema.sql
docker exec <postgres_container> pg_dump -U trading_user -s trading_db_clean > clean_schema.sql

# Diff
diff prod_schema.sql clean_schema.sql
```

4. **Analyze differences and create reconciliation plan**

5. **Clean up:**
```bash
docker exec <postgres_container> psql -U trading_user -d postgres -c "DROP DATABASE trading_db_clean;"
```

### Expected Failures in Clean DB

Migration 019 will fail because:
```python
op.add_column('trading_accounts', ...)  # Table doesn't exist
```

**To fix:** Modify migration 019 to use `accounts` instead of `trading_accounts`.

### Timeline
- Setup: 15 minutes
- Run migrations: 5 minutes (will fail at 019)
- Fix migration 019: 15 minutes
- Rerun: 5 minutes
- Schema comparison: 30 minutes
- **Total: ~1.5 hours**

---

## Option C: Hybrid Approach (SAFEST)

**Approach:** Do both - parallel validation first, then bridge migration.

### Steps

1. Run Option B to understand full scope of drift
2. Fix migration 019 in source (change `trading_accounts` to `accounts`)
3. Create bridge migration 020 for production
4. Test full chain on clean DB
5. Deploy bridge migration to production

### Timeline
- Option B: 1.5 hours
- Option A: 1 hour
- **Total: ~2.5 hours**

---

## Recommendation

**Implement Option A (Bridge Migration)** first for immediate production alignment, then **follow up with Option B** to ensure fresh installs work.

### Immediate Actions (Today)
1. Create and run bridge migration 020
2. Verify ORM operations work correctly

### Follow-up Actions (This Week)
1. Fix migration 019 table name bug
2. Test full migration chain on clean DB
3. Document migration best practices

---

## Migration 019 Fix (Required for Fresh Installs)

**Current (buggy):**
```python
def upgrade():
    op.add_column('users', sa.Column('theme', ...))
    op.add_column('trading_accounts', sa.Column('webhook_key', ...))  # WRONG
    op.create_index('ix_trading_accounts_webhook_key', 'trading_accounts', ...)  # WRONG
```

**Fixed:**
```python
def upgrade():
    op.add_column('users', sa.Column('theme', ...))
    op.add_column('accounts', sa.Column('webhook_key', ...))  # FIXED
    op.create_index('ix_accounts_webhook_key', 'accounts', ...)  # FIXED
```

**Note:** This change is safe because:
- Production already has the column on `accounts` table
- The migration is already stamped as applied (019)
- Only affects fresh database installs

---

## Rollback Plan

If bridge migration fails:

1. **Immediate rollback:**
```bash
alembic downgrade -1
```

2. **If downgrade fails:**
```bash
# Manual column renames (reverse of upgrade)
ALTER TABLE signal_counters RENAME COLUMN current_bias TO directional_bias;
ALTER TABLE signal_counters RENAME COLUMN opposite_momentum TO total_signals;
ALTER TABLE signal_counters RENAME COLUMN last_signal_ts TO last_signal_at;
ALTER TABLE signal_counters DROP COLUMN IF EXISTS last8_pattern;
ALTER TABLE signal_counters DROP COLUMN IF EXISTS chop_mode;

ALTER TABLE discard_bin RENAME COLUMN raw_signal_json TO raw_payload;
ALTER TABLE discard_bin RENAME COLUMN normalized_signal_json TO normalized_payload;

# Re-stamp to 019
DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num) VALUES ('019');
```

3. **Verify app still works with old schema**

---

## Verification Checklist

After reconciliation:

- [ ] `alembic current` shows head (020)
- [ ] `signal_counters` has columns: current_bias, opposite_momentum, last_signal_ts, last8_pattern, chop_mode
- [ ] `discard_bin` has columns: raw_signal_json, normalized_signal_json
- [ ] Signal Intelligence endpoints work: GET /api/v1/signal-intelligence/settings
- [ ] Creating discarded signal works (writes to discard_bin)
- [ ] Momentum tracking works (writes to signal_counters)
- [ ] App starts without ORM errors
