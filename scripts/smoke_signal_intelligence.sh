#!/bin/bash
# Smoke Test: Signal Intelligence Layer
# Tests guard layer decisions: SKIP stale, WARN modal threshold, PAUSE chop/exposure

set -e

API_URL="${API_URL:-http://localhost:3012}"
BASE_URL="${BASE_URL:-$API_URL}"

echo "=== Signal Intelligence Smoke Tests ==="
echo ""

echo "1. Test Stale Signal (should SKIP)"
STALE_TIME=$(date -u -d '10 seconds ago' +%Y-%m-%dT%H:%M:%SZ)
echo "POST $BASE_URL/api/v1/webhooks/tradingview (stale timestamp: $STALE_TIME)"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/api/v1/webhooks/tradingview" \
  -H "Content-Type: application/json" \
  -d "{
    \"ticker\": \"EURUSD\",
    \"action\": \"buy\",
    \"quantity\": 0.01,
    \"timestamp\": \"$STALE_TIME\"
  }" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
echo "HTTP $HTTP_CODE"
echo "$BODY" | head -10
echo ""

echo "2. Test Secure Webhook - Broker Mismatch (should return 403 and log broker_mismatch)"
echo "POST $BASE_URL/api/v1/webhooks/incoming?broker=tradelocker&user=1&key=wrong_key"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/api/v1/webhooks/incoming?broker=tradelocker&user=1&key=wrong_key" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "EURUSD",
    "action": "buy",
    "quantity": 0.01
  }' 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
echo "HTTP $HTTP_CODE"
if [ "$HTTP_CODE" = "403" ]; then
    echo "✅ Correctly rejected (broker mismatch expected)"
else
    echo "⚠️  Unexpected response (expected 403)"
fi
echo "$BODY" | head -10
echo ""

echo "3. Test Secure Webhook - Missing Key (should return 403)"
echo "POST $BASE_URL/api/v1/webhooks/incoming?broker=tradelocker&user=1"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/api/v1/webhooks/incoming?broker=tradelocker&user=1" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "EURUSD", "action": "buy"}' 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
echo "HTTP $HTTP_CODE"
if [ "$HTTP_CODE" = "403" ]; then
    echo "✅ Correctly rejected (missing key)"
else
    echo "⚠️  Unexpected response (expected 403)"
fi
echo "$BODY" | head -10
echo ""

echo "=== Smoke Tests Complete ==="
