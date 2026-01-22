#!/bin/bash
# SMOKE_TESTS.sh - Tradeflow API smoke tests
# Generated: 2026-01-22
#
# Usage:
#   ./SMOKE_TESTS.sh                    # Run all tests
#   ./SMOKE_TESTS.sh health             # Run only health checks
#   ./SMOKE_TESTS.sh auth               # Run only auth tests
#   ./SMOKE_TESTS.sh tradelocker        # Run TradeLocker connection test
#
# Prerequisites:
#   - Backend running on port 8765
#   - jq installed (apt install jq)
#   - Fill in placeholders below

set -e

# ============================================
# CONFIGURATION - FILL IN YOUR VALUES
# ============================================
BASE_URL="${BASE_URL:-http://localhost:8765}"

# Tradeflow app credentials
APP_EMAIL="${APP_EMAIL:-PLACEHOLDER_EMAIL}"
APP_PASSWORD="${APP_PASSWORD:-PLACEHOLDER_PASSWORD}"

# TradeLocker credentials (SDK mode)
TL_USERNAME="${TL_USERNAME:-PLACEHOLDER_TL_EMAIL}"
TL_PASSWORD="${TL_PASSWORD:-PLACEHOLDER_TL_PASSWORD}"
TL_SERVER="${TL_SERVER:-Demo Server}"
TL_ENVIRONMENT="${TL_ENVIRONMENT:-https://demo.tradelocker.com}"

# ProjectX/TopStep credentials
PX_USERNAME="${PX_USERNAME:-PLACEHOLDER_PX_USERNAME}"
PX_API_KEY="${PX_API_KEY:-PLACEHOLDER_PX_API_KEY}"

# ============================================
# HELPER FUNCTIONS
# ============================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
  echo ""
  echo "============================================"
  echo "$1"
  echo "============================================"
}

print_pass() {
  echo -e "${GREEN}[PASS]${NC} $1"
}

print_fail() {
  echo -e "${RED}[FAIL]${NC} $1"
}

print_skip() {
  echo -e "${YELLOW}[SKIP]${NC} $1"
}

check_placeholder() {
  if [[ "$1" == PLACEHOLDER_* ]]; then
    return 0  # is placeholder
  fi
  return 1  # not placeholder
}

# ============================================
# TEST: Health Checks
# ============================================
test_health() {
  print_header "Health Checks"

  # Backend health
  echo -n "Backend health... "
  RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/health" 2>/dev/null || echo -e "\n000")
  HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
  BODY=$(echo "$RESPONSE" | sed '$d')

  if [ "$HTTP_CODE" == "200" ]; then
    STATUS=$(echo "$BODY" | jq -r '.status' 2>/dev/null || echo "unknown")
    if [ "$STATUS" == "healthy" ]; then
      print_pass "Status: healthy"
    else
      print_fail "Status: $STATUS"
    fi
  else
    print_fail "HTTP $HTTP_CODE"
  fi
}

# ============================================
# TEST: Authentication
# ============================================
test_auth() {
  print_header "Authentication"

  if check_placeholder "$APP_EMAIL"; then
    print_skip "APP_EMAIL is placeholder - set env var to test"
    return
  fi

  # Login
  echo -n "Login... "
  RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$APP_EMAIL\",\"password\":\"$APP_PASSWORD\"}" 2>/dev/null)

  TOKEN=$(echo "$RESPONSE" | jq -r '.access_token' 2>/dev/null)

  if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
    print_pass "Got access_token"
    export AUTH_TOKEN="$TOKEN"

    # Get current user
    echo -n "Get /auth/me... "
    ME_RESPONSE=$(curl -s "$BASE_URL/api/v1/auth/me" \
      -H "Authorization: Bearer $TOKEN" 2>/dev/null)

    ME_EMAIL=$(echo "$ME_RESPONSE" | jq -r '.email' 2>/dev/null)
    if [ "$ME_EMAIL" == "$APP_EMAIL" ]; then
      print_pass "Email matches"
    else
      print_fail "Email mismatch: $ME_EMAIL"
    fi
  else
    print_fail "No token: $(echo $RESPONSE | jq -r '.detail' 2>/dev/null || echo $RESPONSE)"
  fi
}

# ============================================
# TEST: TradeLocker Connection
# ============================================
test_tradelocker() {
  print_header "TradeLocker Connection Test"

  if [ -z "$AUTH_TOKEN" ]; then
    echo "No auth token - running auth test first..."
    test_auth
  fi

  if [ -z "$AUTH_TOKEN" ]; then
    print_skip "Cannot test TradeLocker without auth token"
    return
  fi

  if check_placeholder "$TL_USERNAME"; then
    print_skip "TL_USERNAME is placeholder - set env var to test"
    return
  fi

  echo -n "Test connection... "
  RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/accounts/test-connection" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"broker\": \"tradelocker\",
      \"credentials\": {
        \"username\": \"$TL_USERNAME\",
        \"password\": \"$TL_PASSWORD\",
        \"server\": \"$TL_SERVER\",
        \"environment\": \"$TL_ENVIRONMENT\"
      }
    }" 2>/dev/null)

  SUCCESS=$(echo "$RESPONSE" | jq -r '.success' 2>/dev/null)
  MESSAGE=$(echo "$RESPONSE" | jq -r '.message' 2>/dev/null)

  if [ "$SUCCESS" == "true" ]; then
    print_pass "$MESSAGE"

    # Show detected symbols
    SYMBOLS=$(echo "$RESPONSE" | jq -r '.sample_symbols[:5] | join(", ")' 2>/dev/null)
    if [ -n "$SYMBOLS" ] && [ "$SYMBOLS" != "null" ]; then
      echo "  Sample symbols: $SYMBOLS"
    fi
  else
    print_fail "$MESSAGE"
    DETAILS=$(echo "$RESPONSE" | jq -c '.details' 2>/dev/null)
    if [ -n "$DETAILS" ] && [ "$DETAILS" != "null" ]; then
      echo "  Details: $DETAILS"
    fi
  fi
}

# ============================================
# TEST: ProjectX Connection
# ============================================
test_projectx() {
  print_header "ProjectX/TopStep Connection Test"

  if [ -z "$AUTH_TOKEN" ]; then
    echo "No auth token - running auth test first..."
    test_auth
  fi

  if [ -z "$AUTH_TOKEN" ]; then
    print_skip "Cannot test ProjectX without auth token"
    return
  fi

  if check_placeholder "$PX_USERNAME"; then
    print_skip "PX_USERNAME is placeholder - set env var to test"
    return
  fi

  echo -n "Test connection... "
  RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/accounts/test-connection" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"broker\": \"projectx\",
      \"credentials\": {
        \"username\": \"$PX_USERNAME\",
        \"api_key\": \"$PX_API_KEY\"
      }
    }" 2>/dev/null)

  SUCCESS=$(echo "$RESPONSE" | jq -r '.success' 2>/dev/null)
  MESSAGE=$(echo "$RESPONSE" | jq -r '.message' 2>/dev/null)

  if [ "$SUCCESS" == "true" ]; then
    print_pass "$MESSAGE"
  else
    print_fail "$MESSAGE"
  fi
}

# ============================================
# TEST: Accounts CRUD
# ============================================
test_accounts() {
  print_header "Accounts API"

  if [ -z "$AUTH_TOKEN" ]; then
    echo "No auth token - running auth test first..."
    test_auth
  fi

  if [ -z "$AUTH_TOKEN" ]; then
    print_skip "Cannot test accounts without auth token"
    return
  fi

  # List accounts
  echo -n "List accounts... "
  RESPONSE=$(curl -s "$BASE_URL/api/v1/accounts/" \
    -H "Authorization: Bearer $AUTH_TOKEN" 2>/dev/null)

  if echo "$RESPONSE" | jq -e 'type == "array"' > /dev/null 2>&1; then
    COUNT=$(echo "$RESPONSE" | jq 'length')
    print_pass "Found $COUNT accounts"
  else
    print_fail "Invalid response: $RESPONSE"
  fi
}

# ============================================
# TEST: System Status
# ============================================
test_unified_status() {
  print_header "Unified API Status"

  if [ -z "$AUTH_TOKEN" ]; then
    echo "No auth token - running auth test first..."
    test_auth
  fi

  if [ -z "$AUTH_TOKEN" ]; then
    print_skip "Cannot test unified status without auth token"
    return
  fi

  echo -n "System status... "
  RESPONSE=$(curl -s "$BASE_URL/api/v1/unified/status" \
    -H "Authorization: Bearer $AUTH_TOKEN" 2>/dev/null)

  STATUS=$(echo "$RESPONSE" | jq -r '.status' 2>/dev/null)

  if [ "$STATUS" == "operational" ]; then
    print_pass "Status: operational"

    # Show broker statuses
    BROKERS=$(echo "$RESPONSE" | jq -r '.brokers | to_entries[] | "\(.key): \(.value)"' 2>/dev/null)
    if [ -n "$BROKERS" ]; then
      echo "  Broker statuses:"
      echo "$BROKERS" | while read line; do echo "    $line"; done
    fi
  else
    print_fail "Status: $STATUS"
  fi
}

# ============================================
# MAIN
# ============================================
main() {
  echo "Tradeflow Smoke Tests"
  echo "Base URL: $BASE_URL"
  echo "Date: $(date)"

  case "${1:-all}" in
    health)
      test_health
      ;;
    auth)
      test_auth
      ;;
    tradelocker)
      test_tradelocker
      ;;
    projectx)
      test_projectx
      ;;
    accounts)
      test_accounts
      ;;
    status)
      test_unified_status
      ;;
    all)
      test_health
      test_auth
      test_accounts
      test_unified_status
      test_tradelocker
      test_projectx
      ;;
    *)
      echo "Usage: $0 [health|auth|tradelocker|projectx|accounts|status|all]"
      exit 1
      ;;
  esac

  echo ""
  echo "============================================"
  echo "Done"
  echo "============================================"
}

main "$@"
