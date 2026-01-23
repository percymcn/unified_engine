#!/bin/bash
# =============================================================================
# Parallel DB Migration Validation Script
# =============================================================================
# Usage: ./scripts/db_parallel_migrate_validate.sh
#
# This script:
# 1. Creates a CLEAN parallel database (trading_db_clean)
# 2. Runs full alembic migration chain against it
# 3. Compares schema with production database
# 4. Reports differences
# 5. Cleans up (drops the test database)
#
# NON-DESTRUCTIVE to production database
# =============================================================================

set -e

CLEAN_DB="trading_db_clean"
PROD_DB="trading_db"
DB_USER="trading_user"

echo "=============================================="
echo "Parallel DB Migration Validation"
echo "Date: $(date -Iseconds)"
echo "=============================================="
echo ""

# Detect Postgres container
POSTGRES_CONTAINER=$(docker ps -q -f "name=postgres" 2>/dev/null | head -1)

if [ -z "$POSTGRES_CONTAINER" ]; then
    echo "ERROR: No Postgres container found"
    exit 1
fi

echo "Postgres Container: $POSTGRES_CONTAINER"
echo ""

# Function to run psql command
run_psql() {
    docker exec "$POSTGRES_CONTAINER" psql -U "$DB_USER" -d postgres -c "$1" 2>&1
}

run_psql_db() {
    local db=$1
    local cmd=$2
    docker exec "$POSTGRES_CONTAINER" psql -U "$DB_USER" -d "$db" -c "$cmd" 2>&1
}

# Step 1: Create clean database
echo "Step 1: Creating clean database '$CLEAN_DB'"
echo "-------------------------------------------"

# Check if clean DB already exists
DB_EXISTS=$(run_psql "SELECT 1 FROM pg_database WHERE datname='$CLEAN_DB';" | grep -c "1 row" || echo "0")

if [ "$DB_EXISTS" -gt 0 ]; then
    echo "Clean database already exists, dropping it first..."
    run_psql "DROP DATABASE $CLEAN_DB;"
fi

run_psql "CREATE DATABASE $CLEAN_DB;"
echo "Created database: $CLEAN_DB"
echo ""

# Step 2: Run migrations against clean DB
echo "Step 2: Running Alembic migrations on clean DB"
echo "-----------------------------------------------"

# Get the password from Docker secret (or use default)
# We'll run alembic from inside the container to use the correct DATABASE_URL
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Export DATABASE_URL for clean DB (using localhost since port is exposed)
export DATABASE_URL="postgresql://${DB_USER}@localhost:5432/${CLEAN_DB}"

echo "DATABASE_URL for clean DB: $DATABASE_URL"
echo ""

cd "$PROJECT_DIR"

echo "Running: alembic upgrade head"
alembic upgrade head 2>&1 || {
    MIGRATION_EXIT=$?
    echo ""
    echo "!!! MIGRATION FAILED !!!"
    echo "Exit code: $MIGRATION_EXIT"
    echo ""
    echo "This indicates a bug in the migration chain."
    echo "Common issues:"
    echo "  - Migration 019 references 'trading_accounts' but table is 'accounts'"
    echo "  - Tables created by create_all() causing DuplicateTable errors"
    echo ""
    echo "Cleaning up..."
    run_psql "DROP DATABASE IF EXISTS $CLEAN_DB;"
    exit 1
}

echo ""
echo "Migrations completed successfully!"
echo ""

# Step 3: Compare schemas
echo "Step 3: Comparing schemas"
echo "-------------------------"
echo ""

# Get table lists
PROD_TABLES=$(run_psql_db "$PROD_DB" "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;" | grep -v "tablename\|---\|rows)" | tr -d ' ')
CLEAN_TABLES=$(run_psql_db "$CLEAN_DB" "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;" | grep -v "tablename\|---\|rows)" | tr -d ' ')

echo "Tables in production:"
echo "$PROD_TABLES" | head -30
echo ""

echo "Tables in clean DB:"
echo "$CLEAN_TABLES" | head -30
echo ""

# Compare
echo "Table comparison:"
echo ""
echo "ONLY in production:"
comm -23 <(echo "$PROD_TABLES" | sort) <(echo "$CLEAN_TABLES" | sort) | while read table; do
    [ -n "$table" ] && echo "  + $table"
done

echo ""
echo "ONLY in clean DB:"
comm -13 <(echo "$PROD_TABLES" | sort) <(echo "$CLEAN_TABLES" | sort) | while read table; do
    [ -n "$table" ] && echo "  + $table"
done

echo ""
echo "Common tables with column differences:"
echo ""

# Compare columns for key tables
COMPARE_TABLES=("signal_counters" "discard_bin" "momentum_settings" "accounts" "users")

for table in "${COMPARE_TABLES[@]}"; do
    PROD_COLS=$(run_psql_db "$PROD_DB" "SELECT column_name FROM information_schema.columns WHERE table_name='$table' ORDER BY column_name;" | grep -v "column_name\|---\|rows)" | tr -d ' ')
    CLEAN_COLS=$(run_psql_db "$CLEAN_DB" "SELECT column_name FROM information_schema.columns WHERE table_name='$table' ORDER BY column_name;" | grep -v "column_name\|---\|rows)" | tr -d ' ')

    echo "[$table]"

    ONLY_PROD=$(comm -23 <(echo "$PROD_COLS" | sort) <(echo "$CLEAN_COLS" | sort))
    ONLY_CLEAN=$(comm -13 <(echo "$PROD_COLS" | sort) <(echo "$CLEAN_COLS" | sort))

    if [ -n "$ONLY_PROD" ]; then
        echo "  Only in PRODUCTION:"
        echo "$ONLY_PROD" | while read col; do
            [ -n "$col" ] && echo "    - $col"
        done
    fi

    if [ -n "$ONLY_CLEAN" ]; then
        echo "  Only in CLEAN (expected by migrations):"
        echo "$ONLY_CLEAN" | while read col; do
            [ -n "$col" ] && echo "    + $col"
        done
    fi

    if [ -z "$ONLY_PROD" ] && [ -z "$ONLY_CLEAN" ]; then
        echo "  MATCH - columns identical"
    fi
    echo ""
done

# Step 4: Generate diff file
echo "Step 4: Generating schema diff files"
echo "-------------------------------------"

DIFF_DIR="$PROJECT_DIR/.planning"
mkdir -p "$DIFF_DIR"

# Dump schemas
docker exec "$POSTGRES_CONTAINER" pg_dump -U "$DB_USER" -s "$PROD_DB" > "$DIFF_DIR/prod_schema_dump.sql" 2>/dev/null || echo "Could not dump prod schema"
docker exec "$POSTGRES_CONTAINER" pg_dump -U "$DB_USER" -s "$CLEAN_DB" > "$DIFF_DIR/clean_schema_dump.sql" 2>/dev/null || echo "Could not dump clean schema"

echo "Schema dumps saved to:"
echo "  - $DIFF_DIR/prod_schema_dump.sql"
echo "  - $DIFF_DIR/clean_schema_dump.sql"
echo ""

# Step 5: Cleanup
echo "Step 5: Cleaning up"
echo "-------------------"

read -p "Drop clean database '$CLEAN_DB'? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    run_psql "DROP DATABASE $CLEAN_DB;"
    echo "Dropped $CLEAN_DB"
else
    echo "Keeping $CLEAN_DB for further inspection"
    echo "To drop manually: docker exec $POSTGRES_CONTAINER psql -U $DB_USER -d postgres -c 'DROP DATABASE $CLEAN_DB;'"
fi

echo ""
echo "=============================================="
echo "Validation Complete"
echo "=============================================="
echo ""
echo "Summary:"
echo "  - Clean DB migration: SUCCESS"
echo "  - Schema differences: See above"
echo "  - Next steps: Review .planning/ALEMBIC_RECONCILIATION_PLAN.md"
