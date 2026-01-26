#!/bin/bash
# Smoke Test Webhooks - Test webhook endpoints with sample payloads

set -e

API_URL="${API_URL:-${BACKEND_URL:-http://localhost:8765}}"
BASE_URL="${BASE_URL:-$API_URL}"

echo "=== Webhook Smoke Tests ==="
echo ""

echo "1. Test TradingView Webhook (should process or guard)"
echo "POST $BASE_URL/api/v1/webhooks/tradingview"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/api/v1/webhooks/tradingview" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "EURUSD",
    "action": "buy",
    "quantity": 0.01,
    "price": 1.1000,
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
  }' 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
echo "HTTP $HTTP_CODE"
echo "$BODY" | head -10
echo ""

echo "2. Test Stale Signal (should skip)"
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

echo "3. Test Secure Webhook Endpoint - Valid (Patch 1.2.1)"
echo "POST $BASE_URL/api/v1/webhooks/incoming?broker=tradelocker&user=1&key=test_key"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/api/v1/webhooks/incoming?broker=tradelocker&user=1&key=test_key" \
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
    echo "⚠️  Unexpected response"
fi
echo "$BODY" | head -10
echo ""

echo "4. Test Secure Webhook - Missing Key (should return 403)"
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
    echo "⚠️  Unexpected response"
fi
echo "$BODY" | head -10
echo ""

echo "=== Smoke Tests Complete ==="
