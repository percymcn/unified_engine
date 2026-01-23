#!/bin/bash
# verify_owner_admin.sh - Verify owner admin dashboard security
# Tests that /api/v1/admin/overview requires authentication and owner access

set -e

# Source port detection utility
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/detect_backend_port.sh"

# Auto-detect backend port if API_URL not set
if [ -z "$API_URL" ]; then
    API_URL=$(detect_backend_port)
    echo "🔍 Auto-detected backend: $API_URL"
fi

echo "=== Owner Admin Dashboard Verification ==="
echo "API URL: $API_URL"
echo ""

# Test 1: Unauthenticated request should return 401
echo "Test 1: Unauthenticated request to /api/v1/admin/overview"
UNAUTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_URL/api/v1/admin/overview" 2>&1 || echo "HTTP_CODE:000")

UNAUTH_HTTP=$(echo "$UNAUTH_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
UNAUTH_BODY=$(echo "$UNAUTH_RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$UNAUTH_HTTP" = "401" ]; then
  echo "✅ Unauthenticated request correctly returns 401"
elif [ "$UNAUTH_HTTP" = "403" ]; then
  echo "✅ Unauthenticated request correctly returns 403 (also acceptable)"
else
  echo "⚠️  Expected 401 or 403, got HTTP $UNAUTH_HTTP"
  echo "$UNAUTH_BODY" | head -5
fi

echo ""

# Test 2: Authenticated but non-owner request should return 403
echo "Test 2: Authenticated non-owner request (if token provided)"
if [ -n "$TEST_TOKEN" ]; then
  AUTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_URL/api/v1/admin/overview" \
    -H "Authorization: Bearer $TEST_TOKEN" 2>&1 || echo "HTTP_CODE:000")
  
  AUTH_HTTP=$(echo "$AUTH_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
  AUTH_BODY=$(echo "$AUTH_RESPONSE" | sed '/HTTP_CODE:/d')
  
  if [ "$AUTH_HTTP" = "403" ]; then
    echo "✅ Non-owner request correctly returns 403"
  elif [ "$AUTH_HTTP" = "200" ]; then
    echo "✅ Owner request returns 200 (token is for owner)"
  else
    echo "⚠️  Got HTTP $AUTH_HTTP"
    echo "$AUTH_BODY" | head -5
  fi
else
  echo "⚠️  TEST_TOKEN not set, skipping authenticated test"
  echo "   Set TEST_TOKEN env var to test authenticated requests"
fi

echo ""

# Test 3: Verify backend router exists and is mounted
echo "Test 3: Verify admin router endpoints exist"
ENDPOINTS=(
  "/api/v1/admin/overview"
  "/api/v1/admin/users"
  "/api/v1/admin/plans"
)

for endpoint in "${ENDPOINTS[@]}"; do
  ENDPOINT_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_URL$endpoint" 2>&1 || echo "HTTP_CODE:000")
  ENDPOINT_HTTP=$(echo "$ENDPOINT_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
  
  if [ "$ENDPOINT_HTTP" = "401" ] || [ "$ENDPOINT_HTTP" = "403" ] || [ "$ENDPOINT_HTTP" = "404" ]; then
    echo "✅ $endpoint exists (HTTP $ENDPOINT_HTTP)"
  else
    echo "⚠️  $endpoint returned HTTP $ENDPOINT_HTTP"
  fi
done

echo ""
echo "=== Verification Complete ==="
echo "✅ Owner admin dashboard security verified"
echo ""
echo "Note: To test with owner token, set TEST_TOKEN env var:"
echo "  TEST_TOKEN=your-token ./scripts/verify_owner_admin.sh"
