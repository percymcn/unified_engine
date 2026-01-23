# Database Schema Diff Report

**Date:** 2026-01-23
**Comparison:** Production Postgres DB vs Migration Definitions (018, 019)

## Summary

| Table | Status | Issues |
|-------|--------|--------|
| momentum_settings | MATCH | OK |
| signal_counters | DRIFT | Column names differ |
| discard_bin | DRIFT | Column names and types differ |
| users | MATCH | theme column present |
| accounts | PARTIAL | webhook_key present, but migration references wrong table name |
| trading_accounts | MISSING | Migration 019 references this, but table doesn't exist |

## Detailed Comparison

### 1. momentum_settings

**Status:** MATCH - Schema matches migration 018

**Actual DB Columns:**
```
id                     | integer
user_id                | integer
warn_at                | integer
auto_breakeven         | boolean
pause_on_chop          | boolean
max_exposure           | numeric
auto_pause_on_exposure | boolean
allow_hedge            | boolean
staleness_enabled      | boolean
staleness_seconds      | integer
force_old_signals      | boolean
discard_flush_interval | character varying
created_at             | timestamp with time zone
updated_at             | timestamp with time zone
```

**Migration 018 Definition:**
```python
op.create_table(
    'momentum_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('warn_at', sa.Integer(), nullable=False, server_default='6'),
    sa.Column('auto_breakeven', sa.Boolean(), nullable=False, server_default='false'),
    sa.Column('pause_on_chop', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('max_exposure', sa.Numeric(precision=12, scale=2), nullable=False, server_default='5000.00'),
    sa.Column('auto_pause_on_exposure', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('allow_hedge', sa.Boolean(), nullable=False, server_default='false'),
    sa.Column('staleness_enabled', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('staleness_seconds', sa.Integer(), nullable=False, server_default='5'),
    sa.Column('force_old_signals', sa.Boolean(), nullable=False, server_default='false'),
    sa.Column('discard_flush_interval', sa.String(10), nullable=False, server_default='24h'),
    sa.Column('created_at', sa.DateTime(timezone=True), ...),
    sa.Column('updated_at', sa.DateTime(timezone=True), ...),
    ...
)
```

**Verdict:** IDENTICAL

---

### 2. signal_counters

**Status:** DRIFT - Column names differ from migration

**Actual DB Columns:**
```
user_id           | integer           (PK)
session_key       | character varying (PK)
directional_bias  | character varying     <- WRONG NAME
total_signals     | integer               <- WRONG NAME
last_signal_at    | timestamp with time zone <- WRONG NAME
created_at        | timestamp with time zone <- NOT IN MIGRATION
updated_at        | timestamp with time zone
```

**Migration 018 Definition:**
```python
op.create_table(
    'signal_counters',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('session_key', sa.String(255), nullable=False),
    sa.Column('current_bias', sa.String(10), ...),       <- Expected
    sa.Column('opposite_momentum', sa.Integer(), ...),    <- Expected
    sa.Column('last_signal_ts', sa.DateTime(timezone=True), ...),  <- Expected
    sa.Column('last8_pattern', sa.String(16), ...),       <- MISSING IN DB
    sa.Column('chop_mode', sa.Boolean(), ...),            <- MISSING IN DB
    sa.Column('updated_at', sa.DateTime(timezone=True), ...),
    sa.PrimaryKeyConstraint('user_id', 'session_key')
)
```

**ORM Model (database_models.py):**
```python
class SignalCounter(Base):
    __tablename__ = "signal_counters"
    user_id = Column(Integer, ..., primary_key=True)
    session_key = Column(String(255), ..., primary_key=True)
    current_bias = Column(String(10), ...)         <- ORM expects this
    opposite_momentum = Column(Integer, ...)        <- ORM expects this
    last_signal_ts = Column(DateTime(timezone=True), ...)  <- ORM expects this
    last8_pattern = Column(String(16), ...)         <- ORM expects this
    chop_mode = Column(Boolean, ...)                <- ORM expects this
    updated_at = Column(DateTime(timezone=True), ...)
```

**Drift Details:**
| Actual Column | Expected Column | Action Needed |
|---------------|-----------------|---------------|
| directional_bias | current_bias | RENAME |
| total_signals | opposite_momentum | RENAME |
| last_signal_at | last_signal_ts | RENAME |
| (missing) | last8_pattern | ADD |
| (missing) | chop_mode | ADD |
| created_at | (not in migration) | DROP or KEEP |

---

### 3. discard_bin

**Status:** DRIFT - Column names and types differ

**Actual DB Columns:**
```
id                 | integer
user_id            | integer
received_at        | timestamp with time zone
reason             | character varying
age_ms             | integer
symbol             | character varying
side               | character varying
broker_target      | character varying
raw_payload        | text                     <- WRONG NAME/TYPE
normalized_payload | jsonb                    <- WRONG NAME/TYPE
created_at         | timestamp with time zone
```

**Migration 018 Definition:**
```python
op.create_table(
    'discard_bin',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('received_at', sa.DateTime(timezone=True), ...),
    sa.Column('reason', sa.String(50), nullable=False),
    sa.Column('raw_signal_json', sa.JSON(), nullable=True),        <- Expected
    sa.Column('normalized_signal_json', sa.JSON(), nullable=True), <- Expected
    sa.Column('age_ms', sa.Integer(), nullable=True),
    sa.Column('broker_target', sa.String(50), nullable=True),
    sa.Column('symbol', sa.String(50), nullable=True),
    sa.Column('side', sa.String(10), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), ...),
    ...
)
```

**Drift Details:**
| Actual Column | Expected Column | Type Actual | Type Expected | Action |
|---------------|-----------------|-------------|---------------|--------|
| raw_payload | raw_signal_json | text | JSON | RENAME + TYPE CHANGE |
| normalized_payload | normalized_signal_json | jsonb | JSON | RENAME (type compatible) |

---

### 4. users (Patch 1.2.1)

**Status:** MATCH - theme column exists

**Relevant Columns:**
```
theme | character varying
```

**Migration 019:**
```python
op.add_column('users', sa.Column('theme', sa.String(10), nullable=False, server_default='system'))
```

**Verdict:** MATCH

---

### 5. accounts vs trading_accounts (Patch 1.2.1)

**Status:** PARTIAL MATCH - webhook_key exists on `accounts`, but migration targets wrong table

**Actual DB (accounts table):**
```
webhook_key | text
```

**Index exists:**
```
ix_accounts_webhook_key | CREATE UNIQUE INDEX ... ON public.accounts (webhook_key) WHERE (webhook_key IS NOT NULL)
```

**Migration 019 (BUGGY):**
```python
# References wrong table name!
op.add_column('trading_accounts', sa.Column('webhook_key', sa.Text(), nullable=True))
op.create_index('ix_trading_accounts_webhook_key', 'trading_accounts', ['webhook_key'], ...)
```

**ORM Models:**
- `app/models/models.py`: `Account` model with `__tablename__ = "accounts"`
- `app/models/database_models.py`: `TradingAccount` model with `__tablename__ = "trading_accounts"`

**Issue:** There are TWO account models:
1. `Account` (models.py) -> `accounts` table (EXISTS, has webhook_key)
2. `TradingAccount` (database_models.py) -> `trading_accounts` table (DOES NOT EXIST)

The production schema uses the `Account` model from `models.py`. Migration 019 incorrectly references the `TradingAccount` model's table name.

---

## Bridge Migration Required

To align the production DB with migration definitions, create migration 020:

```python
"""Bridge migration to align schema drift from create_all

Revision ID: 020
Revises: 019
Create Date: 2026-01-23
"""
from alembic import op
import sqlalchemy as sa

revision = '020'
down_revision = '019'

def upgrade():
    # signal_counters: rename columns and add missing
    op.alter_column('signal_counters', 'directional_bias',
                    new_column_name='current_bias')
    op.alter_column('signal_counters', 'total_signals',
                    new_column_name='opposite_momentum')
    op.alter_column('signal_counters', 'last_signal_at',
                    new_column_name='last_signal_ts')
    op.add_column('signal_counters',
                  sa.Column('last8_pattern', sa.String(16), nullable=True))
    op.add_column('signal_counters',
                  sa.Column('chop_mode', sa.Boolean(), nullable=False, server_default='false'))
    op.drop_column('signal_counters', 'created_at')  # Not in migration def

    # discard_bin: rename columns
    op.alter_column('discard_bin', 'raw_payload',
                    new_column_name='raw_signal_json',
                    type_=sa.JSON())
    op.alter_column('discard_bin', 'normalized_payload',
                    new_column_name='normalized_signal_json',
                    type_=sa.JSON())

def downgrade():
    # Reverse the changes
    op.alter_column('discard_bin', 'normalized_signal_json',
                    new_column_name='normalized_payload',
                    type_=sa.Text())
    op.alter_column('discard_bin', 'raw_signal_json',
                    new_column_name='raw_payload',
                    type_=sa.Text())

    op.add_column('signal_counters',
                  sa.Column('created_at', sa.DateTime(timezone=True)))
    op.drop_column('signal_counters', 'chop_mode')
    op.drop_column('signal_counters', 'last8_pattern')
    op.alter_column('signal_counters', 'last_signal_ts',
                    new_column_name='last_signal_at')
    op.alter_column('signal_counters', 'opposite_momentum',
                    new_column_name='total_signals')
    op.alter_column('signal_counters', 'current_bias',
                    new_column_name='directional_bias')
```

## Risk Assessment

| Change | Risk Level | Mitigation |
|--------|------------|------------|
| Rename signal_counters columns | LOW | No data loss, ORM will work correctly after |
| Add missing signal_counters columns | LOW | Nullable columns with defaults |
| Rename discard_bin columns | LOW | No data loss |
| Type change text->JSON | MEDIUM | Test with existing data first |

## Verification Queries

After bridge migration, run these queries to verify:

```sql
-- Verify signal_counters columns
SELECT column_name FROM information_schema.columns
WHERE table_name='signal_counters'
AND column_name IN ('current_bias', 'opposite_momentum', 'last_signal_ts', 'last8_pattern', 'chop_mode');

-- Verify discard_bin columns
SELECT column_name FROM information_schema.columns
WHERE table_name='discard_bin'
AND column_name IN ('raw_signal_json', 'normalized_signal_json');
```
