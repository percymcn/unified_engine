#!/bin/bash
#
# Smoke test script for backend health
# Starts backend, tests /health and /openapi.json endpoints
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8765}"
API_PORT="${API_PORT:-8765}"
API_LOG="/tmp/smoke_backend_$$.log"
API_PID=""

# Cleanup function
cleanup() {
    if [ -n "$API_PID" ]; then
        echo "Stopping backend (PID: $API_PID)..."
        kill $API_PID 2>/dev/null || true
        wait $API_PID 2>/dev/null || true
    fi
    rm -f "$API_LOG"
}
trap cleanup EXIT INT TERM

# Check if backend is already running
if curl -s -m 2 "$BACKEND_URL/health" >/dev/null 2>&1; then
    echo "✓ Backend is already running on $BACKEND_URL"
    USE_EXISTING=true
else
    USE_EXISTING=false
    echo "Starting backend on port $API_PORT..."
    
    # Kill any existing backend on this port
    pids=$(lsof -t -i:$API_PORT 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "Killing existing processes on port $API_PORT: $pids"
        kill -9 $pids 2>/dev/null || true
        sleep 1
    fi
    
    # Start backend without reload for stability
    export DATABASE_URL="${DATABASE_URL:-postgresql://trading_user:trading_password@localhost:5432/trading_db}"
    export RELOAD=false
    
    python3 -m uvicorn app.main:app \
        --host 0.0.0.0 \
        --port $API_PORT \
        > "$API_LOG" 2>&1 &
    API_PID=$!
    
    echo "Backend PID: $API_PID"
    echo "Log file: $API_LOG"
    
    # Wait for backend to start (max 30 seconds)
    echo "Waiting for backend to be ready..."
    for i in {1..30}; do
        if curl -s -m 2 "$BACKEND_URL/health" >/dev/null 2>&1; then
            echo "✓ Backend is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "✗ Backend failed to start within 30 seconds"
            echo "Last 20 lines of log:"
            tail -20 "$API_LOG"
            exit 1
        fi
        sleep 1
    done
fi

# Test /health endpoint
echo ""
echo "Testing /health endpoint..."
HEALTH_RESPONSE=$(curl -s -m 5 "$BACKEND_URL/health" || echo "FAILED")
if [ "$HEALTH_RESPONSE" = "FAILED" ]; then
    echo "✗ /health endpoint failed (timeout or error)"
    if [ "$USE_EXISTING" = "false" ]; then
        echo "Backend log:"
        tail -30 "$API_LOG"
    fi
    exit 1
fi

# Check if response is valid JSON or contains expected content
if echo "$HEALTH_RESPONSE" | grep -q "status\|healthy\|ok" || echo "$HEALTH_RESPONSE" | python3 -m json.tool >/dev/null 2>&1; then
    echo "✓ /health endpoint responded:"
    echo "$HEALTH_RESPONSE" | head -5
else
    echo "⚠ /health endpoint returned unexpected response:"
    echo "$HEALTH_RESPONSE" | head -5
fi

# Test /openapi.json endpoint
echo ""
echo "Testing /openapi.json endpoint..."
OPENAPI_RESPONSE=$(curl -s -m 10 "$BACKEND_URL/openapi.json" || echo "FAILED")
if [ "$OPENAPI_RESPONSE" = "FAILED" ]; then
    echo "✗ /openapi.json endpoint failed (timeout or error)"
    if [ "$USE_EXISTING" = "false" ]; then
        echo "Backend log:"
        tail -30 "$API_LOG"
    fi
    exit 1
fi

# Validate JSON
if echo "$OPENAPI_RESPONSE" | python3 -m json.tool >/dev/null 2>&1; then
    OPENAPI_SIZE=$(echo "$OPENAPI_RESPONSE" | wc -c)
    if [ "$OPENAPI_SIZE" -lt 100 ]; then
        echo "✗ /openapi.json is too small ($OPENAPI_SIZE bytes) - likely empty or incomplete"
        echo "Response:"
        echo "$OPENAPI_RESPONSE"
        exit 1
    fi
    
    # Check for required OpenAPI fields
    if echo "$OPENAPI_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); assert 'openapi' in d or 'swagger' in d, 'Missing openapi/swagger field'" 2>/dev/null; then
        echo "✓ /openapi.json is valid JSON with OpenAPI structure ($OPENAPI_SIZE bytes)"
    else
        echo "⚠ /openapi.json is valid JSON but may be missing OpenAPI structure"
        echo "First 200 chars:"
        echo "$OPENAPI_RESPONSE" | head -c 200
    fi
else
    echo "✗ /openapi.json is not valid JSON"
    echo "Response:"
    echo "$OPENAPI_RESPONSE" | head -20
    exit 1
fi

echo ""
echo "============================================================"
echo "✓ All smoke tests passed!"
echo "============================================================"
echo ""
echo "Backend URL: $BACKEND_URL"
echo "API Docs: $BACKEND_URL/docs"
if [ "$USE_EXISTING" = "false" ]; then
    echo "Log file: $API_LOG"
    echo ""
    echo "Backend will continue running. Press Ctrl+C to stop."
    wait $API_PID
fi
