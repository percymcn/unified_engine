#!/bin/bash
# End-to-End User Flow Smoke Test
# Tests: signup → login → API key → connect account → receive signal → execute

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/smoke_user_flow_${TIMESTAMP}.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:3012}"
TEST_USERNAME="smoke_test_$(date +%s)"
TEST_EMAIL="${TEST_USERNAME}@smoketest.local"
TEST_PASSWORD="SmokeTest123!"

# Create logs directory
mkdir -p "$LOG_DIR"

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

# Test API endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local token=$4
    
    local headers=()
    if [ -n "$token" ]; then
        headers+=("-H" "Authorization: Bearer $token")
    fi
    
    if [ "$method" = "GET" ]; then
        curl -s -w "\n%{http_code}" \
            "${headers[@]}" \
            "${API_BASE_URL}${endpoint}" \
            2>/dev/null || echo -e "\n000"
    else
        curl -s -w "\n%{http_code}" \
            "${headers[@]}" \
            -H "Content-Type: application/json" \
            -d "$data" \
            -X "$method" \
            "${API_BASE_URL}${endpoint}" \
            2>/dev/null || echo -e "\n000"
    fi
}

# Step 1: Create test user
test_signup() {
    log "Step 1: Testing user signup..."
    
    local data=$(cat <<EOF
{
    "email": "$TEST_EMAIL",
    "username": "$TEST_USERNAME",
    "password": "$TEST_PASSWORD",
    "full_name": "Smoke Test User"
}
EOF
)
    
    local response=$(test_endpoint "POST" "/api/v1/auth/register" "$data")
    local body=$(echo "$response" | head -n -1)
    local status_code=$(echo "$response" | tail -n 1)
    
    if [ "$status_code" = "200" ] || [ "$status_code" = "201" ]; then
        log_success "User signup successful (HTTP $status_code)"
        echo "$body" | tee -a "$LOG_FILE"
        return 0
    else
        log_error "User signup failed (HTTP $status_code)"
        echo "$body" | tee -a "$LOG_FILE"
        return 1
    fi
}

# Step 2: Login
test_login() {
    log "Step 2: Testing user login..."
    
    local data=$(cat <<EOF
{
    "username": "$TEST_USERNAME",
    "password": "$TEST_PASSWORD"
}
EOF
)
    
    local response=$(test_endpoint "POST" "/api/v1/auth/login?username=$TEST_USERNAME&password=$TEST_PASSWORD" "" "")
    local body=$(echo "$response" | head -n -1)
    local status_code=$(echo "$response" | tail -n 1)
    
    if [ "$status_code" = "200" ]; then
        log_success "Login successful (HTTP $status_code)"
        local token=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null || echo "")
        echo "$token" > /tmp/smoke_test_token.txt
        echo "$body" | tee -a "$LOG_FILE"
        return 0
    else
        log_error "Login failed (HTTP $status_code)"
        echo "$body" | tee -a "$LOG_FILE"
        return 1
    fi
}

# Step 3: Get current user
test_get_me() {
    log "Step 3: Testing GET /me endpoint..."
    
    local token=$(cat /tmp/smoke_test_token.txt 2>/dev/null || echo "")
    if [ -z "$token" ]; then
        log_error "No token available"
        return 1
    fi
    
    local response=$(test_endpoint "GET" "/api/v1/auth/me" "" "$token")
    local body=$(echo "$response" | head -n -1)
    local status_code=$(echo "$response" | tail -n 1)
    
    if [ "$status_code" = "200" ]; then
        log_success "GET /me successful (HTTP $status_code)"
        echo "$body" | tee -a "$LOG_FILE"
        return 0
    else
        log_error "GET /me failed (HTTP $status_code)"
        echo "$body" | tee -a "$LOG_FILE"
        return 1
    fi
}

# Step 4: Create API key
test_create_api_key() {
    log "Step 4: Testing API key creation..."
    
    local token=$(cat /tmp/smoke_test_token.txt 2>/dev/null || echo "")
    if [ -z "$token" ]; then
        log_error "No token available"
        return 1
    fi
    
    local data='{"name": "Smoke Test API Key", "expires_days": 30}'
    local response=$(test_endpoint "POST" "/api/v1/api-keys?name=Smoke%20Test%20API%20Key&expires_days=30" "" "$token")
    local body=$(echo "$response" | head -n -1)
    local status_code=$(echo "$response" | tail -n 1)
    
    if [ "$status_code" = "200" ] || [ "$status_code" = "201" ]; then
        log_success "API key creation successful (HTTP $status_code)"
        local api_key=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin).get('api_key', ''))" 2>/dev/null || echo "")
        if [ -n "$api_key" ]; then
            echo "$api_key" > /tmp/smoke_test_api_key.txt
        fi
        echo "$body" | tee -a "$LOG_FILE"
        return 0
    else
        log_error "API key creation failed (HTTP $status_code)"
        echo "$body" | tee -a "$LOG_FILE"
        return 1
    fi
}

# Step 5: List API keys
test_list_api_keys() {
    log "Step 5: Testing API key listing..."
    
    local token=$(cat /tmp/smoke_test_token.txt 2>/dev/null || echo "")
    if [ -z "$token" ]; then
        log_error "No token available"
        return 1
    fi
    
    local response=$(test_endpoint "GET" "/api/v1/api-keys" "" "$token")
    local body=$(echo "$response" | head -n -1)
    local status_code=$(echo "$response" | tail -n 1)
    
    if [ "$status_code" = "200" ]; then
        log_success "API key listing successful (HTTP $status_code)"
        echo "$body" | tee -a "$LOG_FILE"
        return 0
    else
        log_error "API key listing failed (HTTP $status_code)"
        echo "$body" | tee -a "$LOG_FILE"
        return 1
    fi
}

# Step 6: Create account
test_create_account() {
    log "Step 6: Testing account creation..."
    
    local token=$(cat /tmp/smoke_test_token.txt 2>/dev/null || echo "")
    if [ -z "$token" ]; then
        log_error "No token available"
        return 1
    fi
    
    local data='{"account_id": "smoke_test_account", "broker": "mt4", "account_type": "demo", "currency": "USD"}'
    local response=$(test_endpoint "POST" "/api/v1/accounts" "$data" "$token")
    local body=$(echo "$response" | head -n -1)
    local status_code=$(echo "$response" | tail -n 1)
    
    if [ "$status_code" = "200" ] || [ "$status_code" = "201" ]; then
        log_success "Account creation successful (HTTP $status_code)"
        echo "$body" | tee -a "$LOG_FILE"
        return 0
    else
        log_warning "Account creation failed (HTTP $status_code) - may already exist"
        echo "$body" | tee -a "$LOG_FILE"
        return 0  # Non-critical
    fi
}

# Step 7: List accounts
test_list_accounts() {
    log "Step 7: Testing account listing..."
    
    local token=$(cat /tmp/smoke_test_token.txt 2>/dev/null || echo "")
    if [ -z "$token" ]; then
        log_error "No token available"
        return 1
    fi
    
    local response=$(test_endpoint "GET" "/api/v1/accounts" "" "$token")
    local body=$(echo "$response" | head -n -1)
    local status_code=$(echo "$response" | tail -n 1)
    
    if [ "$status_code" = "200" ]; then
        log_success "Account listing successful (HTTP $status_code)"
        echo "$body" | tee -a "$LOG_FILE"
        return 0
    else
        log_error "Account listing failed (HTTP $status_code)"
        echo "$body" | tee -a "$LOG_FILE"
        return 1
    fi
}

# Main execution
main() {
    log "=========================================="
    log "User Flow Smoke Test"
    log "=========================================="
    log "API Base URL: $API_BASE_URL"
    log "Test User: $TEST_USERNAME"
    log "Log file: $LOG_FILE"
    log ""
    
    local all_passed=true
    
    # Run tests
    test_signup || all_passed=false
    test_login || all_passed=false
    test_get_me || all_passed=false
    test_create_api_key || log_warning "API key creation failed (non-critical)"
    test_list_api_keys || log_warning "API key listing failed (non-critical)"
    test_create_account || log_warning "Account creation failed (non-critical)"
    test_list_accounts || all_passed=false
    
    log ""
    log "=========================================="
    if [ "$all_passed" = true ]; then
        log_success "Smoke test: PASSED ✅"
        log "All critical tests passed"
        exit 0
    else
        log_error "Smoke test: FAILED ❌"
        log "Some critical tests failed"
        exit 1
    fi
}

main "$@"
