#!/bin/bash
# ui_broker_contract_smoke.sh - Test UI ↔ Backend broker contract alignment
# Tests that UI payload formats match backend expectations

set -e

API_URL="${API_URL:-http://localhost:8765}"
BACKEND_URL="${BACKEND_URL:-$API_URL}"

echo "=== UI Broker Contract Smoke Test ==="
echo "Backend URL: $BACKEND_URL"
echo ""

# Test 1: Test connection with UI payload format (camelCase)
echo "1. Test Connection - UI Payload Format (camelCase)"
echo "POST $BACKEND_URL/api/v1/accounts/test-connection"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BACKEND_URL/api/v1/accounts/test-connection" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "broker": "tradelocker",
    "credentials": {
      "userName": "test@example.com",
      "password": "test123",
      "server": "demo"
    }
  }' 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
echo "HTTP $HTTP_CODE"
echo "$BODY" | head -10
echo ""

# Test 2: Test connection with backend format (snake_case)
echo "2. Test Connection - Backend Payload Format (snake_case)"
echo "POST $BACKEND_URL/api/v1/accounts/test-connection"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BACKEND_URL/api/v1/accounts/test-connection" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "broker": "tradelocker",
    "credentials": {
      "username": "test@example.com",
      "password": "test123",
      "server": "demo"
    }
  }' 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
echo "HTTP $HTTP_CODE"
echo "$BODY" | head -10
echo ""

# Test 3: Test field name variations (api_key vs apiKey)
echo "3. Test Field Name Variations (api_key vs apiKey)"
echo "POST $BACKEND_URL/api/v1/accounts/test-connection"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BACKEND_URL/api/v1/accounts/test-connection" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "broker": "tradelocker",
    "credentials": {
      "apiKey": "test-api-key-123"
    }
  }' 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
echo "HTTP $HTTP_CODE"
echo "$BODY" | head -10
echo ""

# Test 4: Test error response structure
echo "4. Test Error Response Structure (Invalid Broker)"
echo "POST $BACKEND_URL/api/v1/accounts/test-connection"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BACKEND_URL/api/v1/accounts/test-connection" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "broker": "invalid_broker",
    "credentials": {}
  }' 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
echo "HTTP $HTTP_CODE"
if echo "$BODY" | grep -q "detail"; then
    echo "✅ Error response has 'detail' field"
else
    echo "⚠️  Error response missing 'detail' field"
fi
echo "$BODY" | head -10
echo ""

echo "=== Contract Tests Complete ==="
echo ""
echo "Note: These tests verify payload format acceptance."
echo "Actual authentication will fail without valid credentials."
echo "This is expected - we're testing the contract, not auth."
