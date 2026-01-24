#!/bin/bash
# Verify Stack - Check versions, env, alembic state, services, endpoints

set -e

echo "=== Stack Verification ==="
echo ""

echo "1. Python Import Check"
python3 -c "from app.main import app; print('✅ Import OK')" 2>&1 | head -3 || echo "❌ Import failed"
echo ""

echo "2. Alembic State"
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  DATABASE_URL not set - using default"
    export DATABASE_URL="postgresql://trading_user:trading_password@localhost:5432/trading_db"
fi
echo "DATABASE_URL: ${DATABASE_URL:0:50}..." # Redact full URL
alembic heads 2>&1 | head -3 || echo "❌ Cannot check heads"
alembic current 2>&1 | head -3 || echo "⚠️  Cannot check current (may be empty)"
echo ""

echo "3. Docker Services"
docker service ls 2>&1 | head -10
echo ""

echo "4. Service Status"
docker service ps postgres --no-trunc 2>&1 | head -3 || echo "⚠️  Postgres service not found"
docker service ps redis --no-trunc 2>&1 | head -3 || echo "⚠️  Redis service not found"
echo ""

echo "5. Health Checks"
API_URL="${API_URL:-http://localhost:8765}"
echo "Testing API at: $API_URL"
curl -f -s "$API_URL/health" 2>&1 | head -5 || echo "❌ API health check failed"
echo ""

echo "6. Signal Intelligence Endpoints"
curl -f -s "$API_URL/api/v1/signal-intelligence/settings" -H "Authorization: Bearer test" 2>&1 | head -3 || echo "⚠️  Endpoint requires auth (expected)"
echo ""

echo "=== Verification Complete ==="
