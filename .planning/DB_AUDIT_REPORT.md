# Database Audit Report

**Date:** 2026-01-23
**Author:** GSD Debug Agent
**Status:** AUDIT COMPLETE - ISSUES FOUND

## Executive Summary

The TradeFlow Unified Engine has **THREE DATABASE_URL targets** that operate independently:
1. Local .env file (SQLite)
2. Docker Swarm stack (Postgres)
3. Alembic defaults (localhost Postgres)

Additionally, **SCHEMA DRIFT** exists between the production Postgres DB and migration definitions due to prior use of `Base.metadata.create_all()` + manual SQL + `alembic stamp head`.

## A. Runtime DB Targets

### 1. Local Development (.env file)
```
File: /home/pharma5/unified_engine/.env
Value: DATABASE_URL=sqlite:////home/pharma5/unified_engine/trading_db.db
Status: POINTS TO SQLITE (local file)
```

### 2. Docker Swarm Stack (docker-stack.yml)
```yaml
# api, celery-worker, celery-beat, flower, funnel-automation services:
environment:
  - DATABASE_URL=postgresql://trading_user@postgres:5432/trading_db

# postgres service:
environment:
  POSTGRES_DB: trading_db
  POSTGRES_USER: trading_user
  POSTGRES_PASSWORD_FILE: /run/secrets/db_password

# Network: unified-network (overlay)
# Port: 5432 exposed via `ports: - "5432:5432"` (confirmed running)
```
**Status:** CORRECTLY CONFIGURED FOR POSTGRES (Docker secret for password)

### 3. Alembic env.py Defaults
```python
# File: alembic/env.py line 31-32
def get_url():
    return os.getenv("DATABASE_URL", "postgresql://trading_user:trading_password@localhost:5432/trading_db")
```
**Status:** DEFAULTS TO LOCALHOST POSTGRES (not Docker service)

## B. Configuration Matrix

| Component | DATABASE_URL Source | Default Target | Current Status |
|-----------|---------------------|----------------|----------------|
| FastAPI App (local) | .env file | SQLite | MISMATCH |
| FastAPI App (Docker) | Env var in stack | Postgres (docker) | OK |
| Alembic (local) | Env var or default | localhost Postgres | MISMATCH |
| Alembic (Docker) | Env var | Postgres (docker) | OK |
| Celery Worker | Env var in stack | Postgres (docker) | OK |
| Celery Beat | Env var in stack | Postgres (docker) | OK |

## C. Docker Services Status

```
ID             NAME          MODE         REPLICAS   IMAGE                           PORTS
2lpz6x9lqki0   postgres      replicated   1/1        postgres:15                     *:5432->5432/tcp
27asdmdph3qm   redis         replicated   1/1        redis:7-alpine
tyh9zwmzygka   nats          replicated   1/1        nats:2.10-alpine
tw56e3orb564   cloudflared   replicated   1/1        cloudflare/cloudflared:latest
```

**Postgres Container:** 330ce5e4921e (Up 16+ minutes at audit time)

## D. Production Database State

### Database Connection Details
```
Host: postgres (Docker service name) or localhost:5432 (exposed)
Database: trading_db
User: trading_user
Password: [from Docker secret db_password]
```

### Alembic Version
```sql
SELECT version_num FROM alembic_version;
-- Result: 019
```

### Tables in Public Schema (22 total)
```
account_strategies    futures_contracts      signals
accounts              momentum_settings      strategies
alembic_version       orders                 symbol_aliases
alerts                positions              system_config
api_keys              signal_counters        trades
broker_symbol_formats discard_bin            user_contract_positions
execution_logs                               user_sessions
                                             users
                                             webhook_logs
```

## E. Issues Identified

### Issue 1: DATABASE_URL Inconsistency
**Severity:** MEDIUM
**Impact:** Local development/testing may use wrong database

The `.env` file points to SQLite while the production stack uses Postgres. Running Alembic commands locally without setting DATABASE_URL will target the wrong database.

### Issue 2: Migration 019 Table Name Bug
**Severity:** HIGH
**Impact:** Migration references non-existent table

```python
# Migration 019 references:
op.add_column('trading_accounts', ...)

# But actual table is:
__tablename__ = "accounts"  # from app/models/models.py
```

The migration will fail if run against a fresh database.

### Issue 3: Schema Drift in Signal Intelligence Tables
**Severity:** CRITICAL
**Impact:** ORM models expect different column names than actual DB has

**signal_counters table:**
| Actual DB Column | ORM/Migration Expects | Match? |
|------------------|----------------------|--------|
| directional_bias | current_bias | NO |
| total_signals | opposite_momentum | NO |
| last_signal_at | last_signal_ts | NO |
| (missing) | last8_pattern | NO |
| (missing) | chop_mode | NO |

**discard_bin table:**
| Actual DB Column | ORM/Migration Expects | Match? |
|------------------|----------------------|--------|
| raw_payload (text) | raw_signal_json (JSON) | NO |
| normalized_payload (jsonb) | normalized_signal_json (JSON) | NO |

### Issue 4: Prior Stamp Without Migration
**Severity:** HIGH
**Impact:** Alembic history does not reflect actual schema

The DB was stamped to 019 via `alembic stamp head` after manual schema creation with `Base.metadata.create_all()`. This means:
- Alembic thinks migrations 001-019 were applied
- In reality, the schema was created from ORM models (possibly older versions)
- Running `alembic upgrade head` on a fresh DB will fail at tables that already exist

## F. Recommendations

### Immediate (Zero Risk)
1. Update `.env` to use Postgres for local development (or remove DATABASE_URL to use default)
2. Create audit scripts to verify schema state

### Short-term (Low Risk)
1. Create bridge migration (020) to rename columns and add missing columns
2. Fix migration 019 to reference `accounts` instead of `trading_accounts`

### Long-term (Requires Planning)
1. Create parallel clean database to test full migration chain
2. Compare schemas and create reconciliation migration
3. Consider schema versioning/checksum validation

## G. Files Examined

- `/home/pharma5/unified_engine/.env`
- `/home/pharma5/unified_engine/docker-stack.yml`
- `/home/pharma5/unified_engine/alembic.ini`
- `/home/pharma5/unified_engine/alembic/env.py`
- `/home/pharma5/unified_engine/alembic/versions/018_add_signal_intelligence_tables.py`
- `/home/pharma5/unified_engine/alembic/versions/019_add_per_broker_webhooks_and_theme.py`
- `/home/pharma5/unified_engine/app/core/config.py`
- `/home/pharma5/unified_engine/app/db/database.py`
- `/home/pharma5/unified_engine/app/models/models.py`
- `/home/pharma5/unified_engine/app/models/database_models.py`
