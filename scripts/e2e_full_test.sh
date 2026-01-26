#!/bin/bash
# E2E Full Test Suite for TradeFlow
# Fixed: ((PASSED++)) -> ((++PASSED)) to avoid exit code 1 when PASSED=0

set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="${LOG_DIR:-/home/pharma5/unified_engine/.gsd/reports/logs}"
LOG_FILE="${LOG_DIR}/e2e_rerun_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"
exec > >(tee "$LOG_FILE") 2>&1

echo "============================================"
echo "TRADEFLOW E2E TEST SUITE"
echo "============================================"
echo "Timestamp: $(date)"
echo "Log file: $LOG_FILE"
echo ""

API_URL="${API_URL:-http://localhost:8000}"
UI_URL="${UI_URL:-http://localhost:3000}"
TEST_USER="e2e_$(date +%s)"
TEST_EMAIL="${TEST_USER}@test.com"
TEST_PASS="TestPass1234"

PASSED=0
FAILED=0

# FIX: Use ((++VAR)) instead of ((VAR++)) to avoid exit code 1 when VAR=0
test_pass() {
    echo "  [PASS] $1"
    ((++PASSED))  # Pre-increment returns the new value (1), not 0
}

test_fail() {
    echo "  [FAIL] $1"
    ((++FAILED))
}

auth() { echo "Authorization: Bearer $token"; }

echo "[1/7] INFRASTRUCTURE HEALTH"
resp=$(curl -s $API_URL/health)
echo "$resp" | grep -q '"status":"healthy"' && test_pass "Backend healthy" || test_fail "Backend healthy"
echo "$resp" | grep -q '"redis":"connected"' && test_pass "Redis connected" || test_fail "Redis connected"
ui_resp=$(curl -s $UI_URL/api/health 2>/dev/null || echo '{}')
echo "$ui_resp" | grep -q '"status":"ok"' && test_pass "UI healthy" || test_fail "UI healthy"

echo ""
echo "[2/7] AUTH FLOW"
echo '{"email": "'$TEST_EMAIL'", "username": "'$TEST_USER'", "password": "'$TEST_PASS'", "full_name": "E2E Test"}' > /tmp/signup.json
echo '{"username": "'$TEST_USER'", "password": "'$TEST_PASS'"}' > /tmp/login.json

code=$(curl -s -w "%{http_code}" -o /tmp/signup_resp.json -X POST $API_URL/api/v1/auth/register -H "Content-Type: application/json" -d @/tmp/signup.json)
[[ "$code" =~ ^(200|201)$ ]] && test_pass "User registration" || test_fail "User registration (HTTP $code)"

resp=$(curl -s $API_URL/api/v1/auth/login -H "Content-Type: application/json" -d @/tmp/login.json)
token=$(echo "$resp" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null || echo "")
[[ -n "$token" ]] && test_pass "User login" || test_fail "User login"

code=$(curl -s -w "%{http_code}" -o /dev/null $API_URL/api/v1/auth/me -H "$(auth)")
[[ "$code" == "200" ]] && test_pass "GET /me" || test_fail "GET /me (HTTP $code)"

echo ""
echo "[3/7] ACCOUNT MANAGEMENT"
resp=$(curl -s -X POST $API_URL/api/v1/accounts/ -H "Content-Type: application/json" -H "$(auth)" \
  -d '{"account_id": "e2e-acct", "broker": "mt4", "account_type": "demo", "currency": "USD", "leverage": 100}')
acct_id=$(echo "$resp" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null || echo "")
[[ -n "$acct_id" ]] && test_pass "Create account (ID: $acct_id)" || test_fail "Create account"

code=$(curl -s -w "%{http_code}" -o /dev/null $API_URL/api/v1/accounts/ -H "$(auth)")
[[ "$code" == "200" ]] && test_pass "List accounts" || test_fail "List accounts (HTTP $code)"

echo ""
echo "[4/7] BROKER CONTRACTS"
resp=$(curl -s $API_URL/api/v1/brokers/contracts)
bc=$(echo "$resp" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
[[ "$bc" -gt 0 ]] && test_pass "GET /brokers/contracts ($bc brokers)" || test_fail "GET /brokers/contracts"

echo ""
echo "[5/7] WEBHOOK CONFIGURATION"
resp=$(curl -s -X POST "$API_URL/api/v1/webhook-configs/" -H "Content-Type: application/json" -H "$(auth)" \
  -d '{"name": "E2E Test Webhook", "source": "tradingview", "routing_strategy": "default_only", "is_active": true}')
wk=$(echo "$resp" | python3 -c "import sys, json; print(json.load(sys.stdin).get('webhook_key', ''))" 2>/dev/null || echo "")
[[ -n "$wk" ]] && test_pass "Create webhook config" || test_fail "Create webhook config"

code=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/api/v1/webhook-configs/" -H "$(auth)")
[[ "$code" == "200" ]] && test_pass "List webhook configs" || test_fail "List webhook configs (HTTP $code)"

echo ""
echo "[6/7] WEBHOOK EXECUTION"
resp=$(curl -s -X POST $API_URL/api/v1/webhooks/tradingview -H "Content-Type: application/json" \
  -d '{"symbol": "EURUSD", "action": "buy", "price": 1.0850, "strategy": "e2e_test", "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}')
echo "$resp" | grep -q '"success":true' && test_pass "TradingView webhook" || test_fail "TradingView webhook"

code=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$API_URL/api/v1/webhooks/incoming?broker=mt4&user=1" \
  -H "Content-Type: application/json" -d '{"symbol": "EURUSD", "action": "buy"}')
[[ "$code" == "403" ]] && test_pass "Security guard (403 on missing key)" || test_fail "Security guard"

echo ""
echo "[7/7] SIGNALS & RISK"
code=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/api/v1/signals/" -H "$(auth)")
[[ "$code" == "200" ]] && test_pass "List signals" || test_fail "List signals (HTTP $code)"

code=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/api/v1/dashboard/executions" -H "$(auth)")
[[ "$code" == "200" ]] && test_pass "Dashboard executions" || test_fail "Dashboard executions (HTTP $code)"

code=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/api/v1/signal-intelligence/settings" -H "$(auth)")
[[ "$code" == "200" ]] && test_pass "Signal Intelligence settings" || test_fail "Signal Intelligence settings (HTTP $code)"

code=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/api/v1/risk/rejected-signals" -H "$(auth)")
[[ "$code" == "200" ]] && test_pass "Rejected signals" || test_fail "Rejected signals (HTTP $code)"

echo ""
echo "============================================"
echo "E2E TEST RESULTS"
echo "============================================"
TOTAL=$((PASSED + FAILED))
echo "PASSED: $PASSED"
echo "FAILED: $FAILED"
echo "TOTAL:  $TOTAL"

if [[ $FAILED -eq 0 ]]; then
    echo ""
    echo "STATUS: ALL TESTS PASSED ($PASSED/$TOTAL)"
    echo "============================================"
    exit 0
else
    echo ""
    echo "STATUS: $FAILED TEST(S) FAILED"
    echo "============================================"
    exit 1
fi
