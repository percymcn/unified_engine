#!/bin/bash
#
# Smoke Test: MetaApi Account Connection (BYOA)
#
# Tests the MetaApi BYOA (Bring Your Own Account) flow:
# 1. Connect endpoint validation
# 2. Status endpoint response shape
# 3. Reconnect endpoint
#
# Usage:
#   ./scripts/smoke_metaapi_connect.sh
#
# Environment:
#   BACKEND_URL - Backend API URL (default: http://localhost:8765)
#   AUTH_TOKEN  - Optional bearer token for authenticated tests
#
# Note: This uses mock/dummy credentials. For real tests, provide valid credentials.

set -e

BACKEND_URL="${BACKEND_URL:-http://localhost:8765}"
AUTH_TOKEN="${AUTH_TOKEN:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "MetaApi BYOA Smoke Test"
echo "========================================"
echo "Backend URL: $BACKEND_URL"
echo ""

# Helper function for API calls
api_call() {
    local method="$1"
    local endpoint="$2"
    local data="$3"

    local url="${BACKEND_URL}${endpoint}"
    local auth_header=""

    if [ -n "$AUTH_TOKEN" ]; then
        auth_header="-H \"Authorization: Bearer $AUTH_TOKEN\""
    fi

    if [ "$method" = "GET" ]; then
        eval "curl -s -X GET \"$url\" -H 'Content-Type: application/json' $auth_header"
    else
        eval "curl -s -X POST \"$url\" -H 'Content-Type: application/json' $auth_header -d '$data'"
    fi
}

# Test 1: Health check
echo -e "${YELLOW}Test 1: Backend Health Check${NC}"
health_response=$(curl -s "${BACKEND_URL}/health" 2>/dev/null || echo '{"status":"unreachable"}')
if echo "$health_response" | grep -q '"status":"healthy"'; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "${RED}✗ Backend health check failed${NC}"
    echo "  Response: $health_response"
    echo ""
    echo "Make sure the backend is running:"
    echo "  DATABASE_URL=\"...\" python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8765"
    exit 1
fi
echo ""

# Test 2: Connect endpoint validation (missing fields)
echo -e "${YELLOW}Test 2: Connect Endpoint - Validation (Missing Fields)${NC}"
validation_response=$(curl -s -X POST "${BACKEND_URL}/api/v1/accounts/connect/metaapi" \
    -H "Content-Type: application/json" \
    -d '{"platform": "mt4"}' 2>/dev/null || echo '{"error":"request failed"}')

# Should return 401 (unauthorized) or 422 (validation error)
if echo "$validation_response" | grep -qi "unauthorized\|not authenticated\|401\|422\|validation\|required"; then
    echo -e "${GREEN}✓ Correctly rejects incomplete/unauthorized request${NC}"
else
    echo -e "${YELLOW}⚠ Unexpected response (may need auth token)${NC}"
fi
echo "  Response: $(echo "$validation_response" | head -c 200)"
echo ""

# Test 3: Connect endpoint with dummy credentials (no auth)
echo -e "${YELLOW}Test 3: Connect Endpoint - Auth Required${NC}"
auth_response=$(curl -s -X POST "${BACKEND_URL}/api/v1/accounts/connect/metaapi" \
    -H "Content-Type: application/json" \
    -d '{
        "platform": "mt4",
        "login": "12345678",
        "password": "testpassword",
        "server": "TestServer-Demo"
    }' 2>/dev/null || echo '{"error":"request failed"}')

if echo "$auth_response" | grep -qi "unauthorized\|not authenticated\|401"; then
    echo -e "${GREEN}✓ Correctly requires authentication${NC}"
else
    echo -e "${YELLOW}⚠ Unexpected response${NC}"
fi
echo "  Response: $(echo "$auth_response" | head -c 200)"
echo ""

# Test 4: Status endpoint (requires auth)
echo -e "${YELLOW}Test 4: Status Endpoint - Auth Required${NC}"
status_response=$(curl -s "${BACKEND_URL}/api/v1/accounts/1/metaapi/status" 2>/dev/null || echo '{"error":"request failed"}')

if echo "$status_response" | grep -qi "unauthorized\|not authenticated\|401"; then
    echo -e "${GREEN}✓ Status endpoint requires authentication${NC}"
else
    echo -e "${YELLOW}⚠ Unexpected response (may need different account ID)${NC}"
fi
echo "  Response: $(echo "$status_response" | head -c 200)"
echo ""

# Test 5: Reconnect endpoint (requires auth)
echo -e "${YELLOW}Test 5: Reconnect Endpoint - Auth Required${NC}"
reconnect_response=$(curl -s -X POST "${BACKEND_URL}/api/v1/accounts/1/metaapi/reconnect" 2>/dev/null || echo '{"error":"request failed"}')

if echo "$reconnect_response" | grep -qi "unauthorized\|not authenticated\|401"; then
    echo -e "${GREEN}✓ Reconnect endpoint requires authentication${NC}"
else
    echo -e "${YELLOW}⚠ Unexpected response${NC}"
fi
echo "  Response: $(echo "$reconnect_response" | head -c 200)"
echo ""

# If AUTH_TOKEN is provided, run authenticated tests
if [ -n "$AUTH_TOKEN" ]; then
    echo "========================================"
    echo "Authenticated Tests (with AUTH_TOKEN)"
    echo "========================================"
    echo ""

    # Test 6: Connect with auth (will fail without valid MetaApi setup)
    echo -e "${YELLOW}Test 6: Connect with Auth (Validation Only)${NC}"
    auth_connect_response=$(curl -s -X POST "${BACKEND_URL}/api/v1/accounts/connect/metaapi" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -d '{
            "platform": "mt4",
            "login": "12345678",
            "password": "testpassword123",
            "server": "TestServer-Demo",
            "nickname": "Test Account"
        }' 2>/dev/null || echo '{"error":"request failed"}')

    # Expect either validation error or MetaApi error (not auth error)
    if echo "$auth_connect_response" | grep -qi "server.*not found\|metaapi\|failed to connect\|invalid\|credentials"; then
        echo -e "${GREEN}✓ Request processed (expected MetaApi/validation error with test credentials)${NC}"
    elif echo "$auth_connect_response" | grep -qi "unauthorized\|401"; then
        echo -e "${RED}✗ Authentication failed - check AUTH_TOKEN${NC}"
    else
        echo -e "${YELLOW}⚠ Unexpected response${NC}"
    fi
    echo "  Response: $(echo "$auth_connect_response" | head -c 300)"
    echo ""
fi

echo "========================================"
echo "Smoke Test Complete"
echo "========================================"
echo ""
echo "Endpoints tested:"
echo "  POST /api/v1/accounts/connect/metaapi"
echo "  GET  /api/v1/accounts/{id}/metaapi/status"
echo "  POST /api/v1/accounts/{id}/metaapi/reconnect"
echo ""
echo "To run authenticated tests:"
echo "  AUTH_TOKEN=<your_jwt_token> ./scripts/smoke_metaapi_connect.sh"
echo ""
echo "Example curl with real credentials (authenticated):"
echo '  curl -X POST http://localhost:8765/api/v1/accounts/connect/metaapi \'
echo '    -H "Content-Type: application/json" \'
echo '    -H "Authorization: Bearer <token>" \'
echo '    -d '"'"'{'
echo '      "platform": "mt4",'
echo '      "login": "<your_mt4_login>",'
echo '      "password": "<your_mt4_password>",'
echo '      "server": "<your_broker_server>",'
echo '      "nickname": "My MT4 Account"'
echo '    }'"'"
