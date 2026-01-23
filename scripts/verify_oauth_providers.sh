#!/bin/bash
# verify_oauth_providers.sh - Verify OAuth providers endpoint
# Tests backend /api/v1/oauth/providers endpoint without requiring secrets

set -e

# Source port detection utility
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/detect_backend_port.sh"

# Auto-detect backend port if API_URL not set
if [ -z "$API_URL" ]; then
    API_URL=$(detect_backend_port)
    echo "🔍 Auto-detected backend: $API_URL"
fi

echo "=== OAuth Providers Verification ==="
echo "API URL: $API_URL"
echo ""

# Test backend providers endpoint
echo "Test: Backend /api/v1/oauth/providers endpoint"
PROVIDERS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_URL/api/v1/oauth/providers" 2>&1 || echo "HTTP_CODE:000")

HTTP_CODE=$(echo "$PROVIDERS_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$PROVIDERS_RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" != "200" ]; then
  echo "❌ Backend API returned HTTP $HTTP_CODE"
  echo "$BODY" | head -20
  exit 1
fi

echo "✅ Backend API returned HTTP 200"

# Check response structure
if echo "$BODY" | grep -q '"providers"'; then
  echo "✅ Response contains 'providers' field"
  
  # Check if Google provider is listed (if configured)
  if echo "$BODY" | grep -q '"provider":"google"'; then
    echo "✅ Google OAuth provider is configured"
    GOOGLE_AUTH_URL=$(echo "$BODY" | grep -o '"auth_url":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "   Google auth URL: $GOOGLE_AUTH_URL"
  else
    echo "⚠️  Google OAuth provider not configured (GOOGLE_CLIENT_ID not set)"
  fi
  
  # Print full response (pretty-printed if jq available)
  if command -v jq &> /dev/null; then
    echo ""
    echo "Full response:"
    echo "$BODY" | jq .
  else
    echo ""
    echo "Full response:"
    echo "$BODY"
  fi
else
  echo "❌ Response missing 'providers' field"
  echo "$BODY"
  exit 1
fi

echo ""
echo "=== Verification Complete ==="
echo "✅ OAuth providers endpoint is working correctly"
