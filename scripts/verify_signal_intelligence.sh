#!/bin/bash
# Verification script for Signal Intelligence Layer Milestone 1.2
# Run this after deployment to verify all features

set -e

echo "=========================================="
echo "Signal Intelligence Layer Verification"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BACKEND_URL="${BACKEND_URL:-http://localhost:8765}"
TOKEN="${AUTH_TOKEN:-}"

# Check if backend is running
echo "1. Checking backend health..."
if curl -s "$BACKEND_URL/health" > /dev/null; then
    echo -e "${GREEN}✓${NC} Backend is running"
else
    echo -e "${RED}✗${NC} Backend is not running at $BACKEND_URL"
    exit 1
fi

# Check database tables
echo ""
echo "2. Checking database tables..."
# This would require database access - skip for now
echo -e "${YELLOW}⚠${NC}  Database check skipped (requires DB access)"

# Check API endpoints (if token provided)
if [ -n "$TOKEN" ]; then
    echo ""
    echo "3. Testing API endpoints..."
    
    # Test settings endpoint
    if curl -s -H "Authorization: Bearer $TOKEN" "$BACKEND_URL/api/v1/signal-intelligence/settings" > /dev/null; then
        echo -e "${GREEN}✓${NC} Settings endpoint accessible"
    else
        echo -e "${RED}✗${NC} Settings endpoint failed"
    fi
    
    # Test counters endpoint
    if curl -s -H "Authorization: Bearer $TOKEN" "$BACKEND_URL/api/v1/signal-intelligence/counters" > /dev/null; then
        echo -e "${GREEN}✓${NC} Counters endpoint accessible"
    else
        echo -e "${RED}✗${NC} Counters endpoint failed"
    fi
else
    echo ""
    echo "3. Skipping API tests (no AUTH_TOKEN provided)"
    echo "   Set AUTH_TOKEN environment variable to test authenticated endpoints"
fi

# Test webhook endpoints (public)
echo ""
echo "4. Testing webhook endpoints..."

# Test tradingview endpoint (will fail without proper payload, but endpoint should exist)
if curl -s -X POST "$BACKEND_URL/api/v1/webhooks/tradingview" \
    -H "Content-Type: application/json" \
    -d '{"ticker":"EURUSD","action":"buy"}' \
    | grep -q "success\|error\|skipped\|paused"; then
    echo -e "${GREEN}✓${NC} TradingView webhook endpoint responds"
else
    echo -e "${YELLOW}⚠${NC}  TradingView endpoint response unclear"
fi

# Test trailhacker endpoint
if curl -s -X POST "$BACKEND_URL/api/v1/webhooks/trailhacker" \
    -H "Content-Type: application/json" \
    -d '{"symbol":"EURUSD","signal":"buy"}' \
    | grep -q "success\|error\|skipped\|paused"; then
    echo -e "${GREEN}✓${NC} TrailHacker webhook endpoint responds"
else
    echo -e "${YELLOW}⚠${NC}  TrailHacker endpoint response unclear"
fi

# Run tests
echo ""
echo "5. Running unit tests..."
if python3 -m pytest tests/test_signal_intelligence_guard.py -v --tb=short > /tmp/test_output.txt 2>&1; then
    echo -e "${GREEN}✓${NC} All tests passed"
    PASSED=$(grep -c "PASSED" /tmp/test_output.txt || echo "0")
    echo "   $PASSED tests passed"
else
    echo -e "${RED}✗${NC} Some tests failed"
    tail -20 /tmp/test_output.txt
    exit 1
fi

# Check migration
echo ""
echo "6. Checking migration status..."
if [ -f "alembic/versions/018_add_signal_intelligence_tables.py" ]; then
    echo -e "${GREEN}✓${NC} Migration file exists"
else
    echo -e "${RED}✗${NC} Migration file not found"
fi

# Check key files
echo ""
echo "7. Checking key files..."
FILES=(
    "app/services/signal_intelligence_guard.py"
    "app/routers/signal_intelligence.py"
    "app/models/database_models.py"
    "ui-next/src/components/signal-intelligence/momentum-meter.tsx"
    "ui-next/src/components/signal-intelligence/signal-heat-map.tsx"
    "ui-next/src/components/signal-intelligence/guard-modal.tsx"
    "ui-next/src/components/signal-intelligence/flowguard-bot.tsx"
    "docs/INSTALL_AND_API.md"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} $file (missing)"
    fi
done

echo ""
echo "=========================================="
echo -e "${GREEN}Verification Complete${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Run migration: alembic upgrade head"
echo "2. Start backend: uvicorn app.main:app --reload"
echo "3. Start frontend: cd ui-next && npm run dev"
echo "4. Test webhooks with sample signals"
echo "5. Verify UI components in dashboard"
