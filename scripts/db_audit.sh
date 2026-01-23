#!/bin/bash
# =============================================================================
# DB Audit Script - Read-Only Database State Check
# =============================================================================
# Usage: ./scripts/db_audit.sh
#
# This script performs READ-ONLY checks on the database:
# 1. DATABASE_URL detection (where is the DB?)
# 2. Alembic version check (what migrations are applied?)
# 3. Table existence checks (are expected tables present?)
# 4. Column checks for Signal Intelligence tables (schema drift detection)
#
# NO DESTRUCTIVE OPERATIONS - Safe to run at any time
# =============================================================================

set -e

echo "=============================================="
echo "TradeFlow Unified Engine - DB Audit"
echo "Date: $(date -Iseconds)"
echo "=============================================="
echo ""

# Detect Postgres container
POSTGRES_CONTAINER=$(docker ps -q -f "name=postgres" 2>/dev/null | head -1)

if [ -z "$POSTGRES_CONTAINER" ]; then
    echo "ERROR: No Postgres container found"
    echo "Looking for container with name containing 'postgres'"
    docker ps --format "table {{.Names}}\t{{.Status}}" | grep -i postgres || echo "No postgres containers running"
    exit 1
fi

echo "1. DATABASE_URL Configuration"
echo "------------------------------"
echo ""
echo "A) Local .env file:"
if [ -f ".env" ]; then
    grep "DATABASE_URL" .env 2>/dev/null || echo "   DATABASE_URL not set in .env"
else
    echo "   .env file not found"
fi
echo ""

echo "B) Docker stack (docker-stack.yml):"
if [ -f "docker-stack.yml" ]; then
    grep "DATABASE_URL" docker-stack.yml | head -3 || echo "   DATABASE_URL not in docker-stack.yml"
fi
echo ""

echo "C) Alembic default (alembic/env.py):"
grep -A1 "def get_url" alembic/env.py 2>/dev/null | tail -1 || echo "   Could not read alembic/env.py"
echo ""

echo "D) Current shell:"
echo "   DATABASE_URL=${DATABASE_URL:-<not set>}"
echo ""

echo "2. Postgres Container Status"
echo "-----------------------------"
echo "Container ID: $POSTGRES_CONTAINER"
docker inspect "$POSTGRES_CONTAINER" --format '{{.State.Status}}' 2>/dev/null || echo "Could not get status"
echo ""

echo "3. Alembic Migration State"
echo "--------------------------"
echo ""
echo "A) Alembic heads (available migrations):"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"
alembic heads 2>/dev/null || echo "   Could not run alembic heads (check DATABASE_URL)"
echo ""

echo "B) Current DB version:"
docker exec "$POSTGRES_CONTAINER" psql -U trading_user -d trading_db -t -c "SELECT version_num FROM alembic_version;" 2>/dev/null || echo "   Could not query alembic_version"
echo ""

echo "4. Table Existence Check"
echo "------------------------"
echo ""
echo "Expected tables and their status:"

EXPECTED_TABLES=(
    "users"
    "accounts"
    "signals"
    "trades"
    "positions"
    "orders"
    "api_keys"
    "strategies"
    "momentum_settings"
    "signal_counters"
    "discard_bin"
    "alembic_version"
)

for table in "${EXPECTED_TABLES[@]}"; do
    EXISTS=$(docker exec "$POSTGRES_CONTAINER" psql -U trading_user -d trading_db -t -c "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='$table');" 2>/dev/null | tr -d ' ')
    if [ "$EXISTS" = "t" ]; then
        echo "   [OK] $table"
    else
        echo "   [MISSING] $table"
    fi
done
echo ""

echo "5. Signal Intelligence Schema Check"
echo "------------------------------------"
echo ""

echo "A) signal_counters columns:"
docker exec "$POSTGRES_CONTAINER" psql -U trading_user -d trading_db -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='signal_counters' ORDER BY ordinal_position;" 2>/dev/null
echo ""

echo "   Expected columns: user_id, session_key, current_bias, opposite_momentum, last_signal_ts, last8_pattern, chop_mode, updated_at"
echo "   Known drift: directional_bias (should be current_bias), total_signals (should be opposite_momentum), last_signal_at (should be last_signal_ts)"
echo ""

echo "B) discard_bin columns:"
docker exec "$POSTGRES_CONTAINER" psql -U trading_user -d trading_db -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='discard_bin' ORDER BY ordinal_position;" 2>/dev/null
echo ""

echo "   Expected columns: id, user_id, received_at, reason, raw_signal_json (JSON), normalized_signal_json (JSON), age_ms, broker_target, symbol, side, created_at"
echo "   Known drift: raw_payload (should be raw_signal_json), normalized_payload (should be normalized_signal_json)"
echo ""

echo "C) Patch 1.2.1 columns:"
THEME_EXISTS=$(docker exec "$POSTGRES_CONTAINER" psql -U trading_user -d trading_db -t -c "SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='theme');" 2>/dev/null | tr -d ' ')
WEBHOOK_EXISTS=$(docker exec "$POSTGRES_CONTAINER" psql -U trading_user -d trading_db -t -c "SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='accounts' AND column_name='webhook_key');" 2>/dev/null | tr -d ' ')

if [ "$THEME_EXISTS" = "t" ]; then
    echo "   [OK] users.theme exists"
else
    echo "   [MISSING] users.theme"
fi

if [ "$WEBHOOK_EXISTS" = "t" ]; then
    echo "   [OK] accounts.webhook_key exists"
else
    echo "   [MISSING] accounts.webhook_key"
fi
echo ""

echo "6. Index Check"
echo "--------------"
echo ""
echo "Signal Intelligence indexes:"
docker exec "$POSTGRES_CONTAINER" psql -U trading_user -d trading_db -c "SELECT indexname FROM pg_indexes WHERE tablename IN ('momentum_settings', 'signal_counters', 'discard_bin');" 2>/dev/null
echo ""

echo "=============================================="
echo "Audit Complete"
echo "=============================================="
echo ""
echo "Next steps:"
echo "  - If schema drift detected: Review .planning/ALEMBIC_RECONCILIATION_PLAN.md"
echo "  - If tables missing: Run alembic upgrade head"
echo "  - If DATABASE_URL mismatch: Update .env or set environment variable"
