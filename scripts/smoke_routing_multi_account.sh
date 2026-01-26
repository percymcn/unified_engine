#!/bin/bash
# Smoke test for multi-account routing
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/.gsd/reports/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/smoke_routing_multi_account_${TIMESTAMP}.log"
BACKEND_URL="${BACKEND_URL:-http://localhost:8765}"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

mkdir -p "$LOG_DIR"

log() {
    echo -e "[${BLUE}$1${NC}]" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "[${GREEN}✅ $1${NC}]" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "[${YELLOW}⚠️  $1${NC}]" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "[${RED}❌ $1${NC}]" | tee -a "$LOG_FILE"
}

curl_json() {
    local method=$1
    local endpoint=$2
    local payload=$3
    local token=$4
    local headers=(-H "Content-Type: application/json")

    if [[ -n "${token:-}" ]]; then
        headers+=(-H "Authorization: Bearer $token")
    fi

    if [[ "$method" == "GET" ]]; then
        curl -sS -w "\n%{http_code}" "${headers[@]}" "$BACKEND_URL$endpoint" || true
    else
        curl -sS -w "\n%{http_code}" "${headers[@]}" -X "$method" -d "$payload" "$BACKEND_URL$endpoint" || true
    fi
}
log "=== Multi-Account Routing Smoke Test ===" | tee -a "$LOG_FILE"

TEST_USER="routing_smoke_$(date +%s)"
TEST_EMAIL="${TEST_USER}@smoketest.com"
TEST_PASSWORD="RoutingSmoke123!"

log "1) Registering test user"
signup_payload=$(cat <<EOF
{
  "email": "$TEST_EMAIL",
  "username": "$TEST_USER",
  "password": "$TEST_PASSWORD",
  "full_name": "Routing Smoke"
}
EOF
)
signup_response=$(curl_json "POST" "/api/v1/auth/register" "$signup_payload" "")
signup_body=$(echo "$signup_response" | head -n -1)
signup_code=$(echo "$signup_response" | tail -n 1)

if [[ "$signup_code" =~ ^(200|201)$ ]]; then
    log_success "User registered: $TEST_USER"
else
    log_warning "User signup returned HTTP $signup_code (may already exist)"
fi

log "2) Logging in"
login_response=$(curl_json "POST" "/api/v1/auth/login?username=$TEST_USER&password=$TEST_PASSWORD" "" "")
login_body=$(echo "$login_response" | head -n -1)
login_code=$(echo "$login_response" | tail -n 1)
if [[ "$login_code" == "200" ]]; then
    token=$(python3 - <<PY <<< "$login_body"
import json, sys
data = json.load(sys.stdin)
print(data.get("access_token", ""))
PY
)
    log_success "Login succeeded"
else
    log_error "Login failed with HTTP $login_code"
    exit 1
fi

log "3) Creating two accounts"
create_account() {
    local account_id="$1"
    local payload=$(cat <<EOF
{
  "account_id": "$account_id",
  "broker": "mt4",
  "account_type": "demo",
  "currency": "USD",
  "leverage": 100
}
EOF
)
    local resp=$(curl_json "POST" "/api/v1/accounts/" "$payload" "$token")
    local body=$(echo "$resp" | head -n -1)
    local code=$(echo "$resp" | tail -n 1)
    if [[ "$code" != "200" && "$code" != "201" ]]; then
        log_error "Account $account_id creation failed (HTTP $code)"
        exit 1
    fi
    echo "$body"
}

acct_a=$(create_account "routing-account-a-$TIMESTAMP")
acct_b=$(create_account "routing-account-b-$TIMESTAMP")

parse_account() {
    local field="$1"
    local payload="$2"
    python3 - <<PY <<< "$payload"
import json
data = json.load(sys.stdin)
print(data.get("$field", ""))
PY
}

id_a=$(parse_account id "$acct_a")
key_a=$(parse_account webhook_key "$acct_a")
id_b=$(parse_account id "$acct_b")
key_b=$(parse_account webhook_key "$acct_b")

log "Accounts created: $id_a, $id_b"

log "4) Creating multi-account webhook config"
multi_config_payload=$(cat <<EOF
{
  "name": "multi-account-routing-$TIMESTAMP",
  "source": "tradingview",
  "routing_strategy": "specific_accounts",
  "specific_account_ids": [$id_a, $id_b],
  "is_active": true
}
EOF
)
multi_conf_resp=$(curl_json "POST" "/api/v1/webhook-configs" "$multi_config_payload" "$token")
multi_conf_code=$(echo "$multi_conf_resp" | tail -n 1)
multi_conf_body=$(echo "$multi_conf_resp" | head -n -1)
if [[ "$multi_conf_code" != "201" ]]; then
    log_error "Failed to create multi-account webhook config: HTTP $multi_conf_code"
    exit 1
fi
multi_webhook_key=$(parse_account webhook_key "$multi_conf_body")

log "5) Creating single-account webhook config"
single_config_payload=$(cat <<EOF
{
  "name": "single-account-routing-$TIMESTAMP",
  "source": "tradingview",
  "routing_strategy": "specific_accounts",
  "specific_account_ids": [$id_a],
  "is_active": true
}
EOF
)
single_conf_resp=$(curl_json "POST" "/api/v1/webhook-configs" "$single_config_payload" "$token")
single_conf_code=$(echo "$single_conf_resp" | tail -n 1)
single_conf_body=$(echo "$single_conf_resp" | head -n -1)
if [[ "$single_conf_code" != "201" ]]; then
    log_error "Failed to create single-account webhook config: HTTP $single_conf_code"
    exit 1
fi
single_webhook_key=$(parse_account webhook_key "$single_conf_body")

log "6) Creating rules-based config that should reject"
rules_config_payload=$(cat <<EOF
{
  "name": "rules-block-$TIMESTAMP",
  "source": "tradingview",
  "routing_strategy": "rules_based",
  "routing_rules": [
    {
      "condition": {
        "field": "symbol",
        "operator": "eq",
        "value": "NOMATCH"
      },
      "target_account_id": $id_a,
      "priority": 5
    }
  ],
  "is_active": true
}
EOF
)
rules_conf_resp=$(curl_json "POST" "/api/v1/webhook-configs" "$rules_config_payload" "$token")
rules_conf_code=$(echo "$rules_conf_resp" | tail -n 1)
rules_conf_body=$(echo "$rules_conf_resp" | head -n -1)
if [[ "$rules_conf_code" != "201" ]]; then
    log_error "Failed to create rules-based webhook config: HTTP $rules_conf_code"
    exit 1
fi
rules_webhook_key=$(parse_account webhook_key "$rules_conf_body")

trigger_signal() {
    local key="$1"
    local payload=$(cat <<EOF
{
  "ticker": "EURUSD",
  "action": "buy",
  "quantity": 0.01,
  "price": 1.1,
  "stop_loss": 1.08,
  "take_profit": 1.2,
  "strategy_id": "routing-smoke",
  "strategy_name": "Routing Smoke"
}
EOF
)
    response=$(curl_json "POST" "/api/v1/webhooks/signal/$key" "$payload" "")
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    echo "$http_code:$body"
}

log "7) Triggering multi-account signal"
multi_result=$(trigger_signal "$multi_webhook_key")
multi_code=${multi_result%%:*}
multi_body=${multi_result#*:}
multi_targets=$(python3 - <<PY <<< "$multi_body"
import json
data = json.load(sys.stdin)
print(len(data.get("target_account_ids", [])))
PY
)
if [[ "$multi_code" == "200" ]]; then
    log_success "Multi-account signal succeeded; targets: $multi_targets"
else
    log_error "Multi-account signal failed (HTTP $multi_code)"
    echo "$multi_body" | tee -a "$LOG_FILE"
fi

log "8) Triggering single-account signal"
single_result=$(trigger_signal "$single_webhook_key")
single_code=${single_result%%:*}
single_body=${single_result#*:}
single_targets=$(python3 - <<PY <<< "$single_body"
import json
data = json.load(sys.stdin)
print(data.get("target_account_ids", []))
PY
)
if [[ "$single_code" == "200" ]]; then
    log_success "Single-account signal succeeded; target list: $single_targets"
else
    log_error "Single-account signal failed (HTTP $single_code)"
    echo "$single_body" | tee -a "$LOG_FILE"
fi

log "9) Triggering ambiguous routing (should reject)"
rules_result=$(trigger_signal "$rules_webhook_key")
rules_code=${rules_result%%:*}
rules_body=${rules_result#*:}
if [[ "$rules_code" == "200" ]]; then
    routing_state=$(python3 - <<PY <<< "$rules_body"
import json
body = json.load(sys.stdin)
if not body.get("success") and "No accounts matched" in body.get("error", ""):
    print("BLOCKED")
else:
    print("PASSED")
PY
    )
    routing_error=$(python3 - <<PY <<< "$rules_body"
import json
body = json.load(sys.stdin)
print(body.get("error", ""))
PY
    )
    if [[ "$routing_state" == "BLOCKED" ]]; then
        log_success "Ambiguous routing blocked as expected - reason: $routing_error"
    else
        log_warning "Ambiguous routing produced unexpected response: $rules_body"
    fi
else
    log_success "Routing rejection triggered (HTTP $rules_code)"
fi

log_success "Smoke routing test complete"
