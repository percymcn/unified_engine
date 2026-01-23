#!/bin/bash
# Run migrations from within Docker container or with correct DATABASE_URL

set -e

# Check if running in Docker
if [ -f /.dockerenv ] || [ -n "$DOCKER_CONTAINER" ]; then
    echo "Running inside Docker container"
    export DATABASE_URL="${DATABASE_URL:-postgresql://trading_user@postgres:5432/trading_db}"
else
    echo "Running on host - need DATABASE_URL"
    if [ -z "$DATABASE_URL" ]; then
        echo "ERROR: DATABASE_URL not set"
        echo "Set it to: postgresql://trading_user:PASSWORD@postgres:5432/trading_db"
        echo "Or run from within Docker container"
        exit 1
    fi
fi

echo "Using DATABASE_URL: ${DATABASE_URL:0:50}..."
echo ""

echo "1. Check Alembic heads"
alembic heads
echo ""

echo "2. Check current migration"
CURRENT=$(alembic current 2>&1 || echo "empty")
echo "$CURRENT"
echo ""

echo "3. Check if schema exists"
python3 << EOF
from sqlalchemy import create_engine, inspect, text
import os
engine = create_engine(os.getenv('DATABASE_URL'))
conn = engine.connect()
try:
    result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"))
    table_count = result.scalar()
    print(f"Tables in DB: {table_count}")
    if table_count > 0:
        result2 = conn.execute(text("SELECT version_num FROM alembic_version"))
        version = result2.scalar()
        print(f"Alembic version: {version}")
    else:
        print("Database is empty - will run migrations")
finally:
    conn.close()
EOF
echo ""

echo "4. Run migrations"
alembic upgrade head
echo ""

echo "5. Verify Patch 1.2.1 columns"
python3 << EOF
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.getenv('DATABASE_URL'))
conn = engine.connect()
try:
    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='theme'"))
    print(f"users.theme exists: {result.rowcount > 0}")
    result2 = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='trading_accounts' AND column_name='webhook_key'"))
    print(f"trading_accounts.webhook_key exists: {result2.rowcount > 0}")
finally:
    conn.close()
EOF
echo ""

echo "✅ Migrations complete"
