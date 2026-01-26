#!/bin/bash
# TradeFlow Release Gate Runner
# Executes comprehensive test suite and smoke tests

set -e

TIMESTAMP=${1:-$(date +%s)}
LOG_FILE=".gsd/reports/logs/release_gate_${TIMESTAMP}.log"

echo "=== TradeFlow Release Gate Runner ===" | tee "$LOG_FILE"
echo "Timestamp: $TIMESTAMP" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Function to run command and log result
run_command() {
    local cmd="$1"
    local description="$2"
    
    echo "Running: $description" | tee -a "$LOG_FILE"
    echo "Command: $cmd" | tee -a "$LOG_FILE"
    
    if eval "$cmd" >> "$LOG_FILE" 2>&1; then
        echo "✅ PASS: $description" | tee -a "$LOG_FILE"
        return 0
    else
        echo "❌ FAIL: $description" | tee -a "$LOG_FILE"
        echo "Check log for details: $LOG_FILE" | tee -a "$LOG_FILE"
        return 1
    fi
}

# Function to run with verbose output when debugging
run_verbose() {
    local cmd="$1"
    local description="$2"
    
    echo "Running VERBOSE: $description" | tee -a "$LOG_FILE"
    echo "Command: $cmd" | tee -a "$LOG_FILE"
    
    if eval "$cmd" >> "$LOG_FILE" 2>&1; then
        echo "✅ PASS: $description" | tee -a "$LOG_FILE"
        return 0
    else
        echo "❌ FAIL: $description" | tee -a "$LOG_FILE"
        echo "Check log for details: $LOG_FILE" | tee -a "$LOG_FILE"
        return 1
    fi
}

# Ensure we're in the right directory
cd /home/pharma5/unified_engine

# Set environment
export DATABASE_URL="postgresql://trading_user:trading_password@localhost:5432/trading_db"

echo "Environment Setup" | tee -a "$LOG_FILE"
echo "DATABASE_URL: $DATABASE_URL" | tee -a "$LOG_FILE"
echo "Working directory: $(pwd)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

FAILED_TESTS=0

echo "=== STEP 1: Pytest Release Suite ===" | tee -a "$LOG_FILE"

# Run pytest tests
if ! run_command "source venv/bin/activate && pytest tests/infrastructure -v" "Pytest infrastructure tests"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

if ! run_command "source venv/bin/activate && pytest tests/routers/test_webhook_execute.py -v" "Pytest webhook execute tests"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

if ! run_command "source venv/bin/activate && pytest tests/routers/test_webhooks_guard.py -v" "Pytest webhooks guard tests"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

if ! run_command "source venv/bin/activate && pytest tests/routers/test_accounts_auto_connect.py -v" "Pytest accounts auto connect tests"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

if ! run_command "source venv/bin/activate && pytest tests/test_broker_errors.py -v" "Pytest broker errors tests"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

if ! run_command "source venv/bin/activate && pytest tests/test_projectx_sdk.py -v" "Pytest ProjectX SDK tests"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

if ! run_command "source venv/bin/activate && pytest tests/test_tradelocker_sdk.py -v" "Pytest TradeLocker SDK tests"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

if ! run_command "source venv/bin/activate && pytest tests/test_ui_integration.py -v" "Pytest UI integration tests"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo "=== STEP 2: Smoke Tests ===" | tee -a "$LOG_FILE"

# Run smoke tests
if ! run_command "bash scripts/smoke_backend.sh" "Smoke backend tests"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

if ! run_command "bash scripts/smoke_webhooks.sh" "Smoke webhooks tests"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

if ! run_command "bash scripts/smoke_user_flow.sh" "Smoke user flow tests"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

if ! run_command "bash scripts/smoke_signal_intelligence.sh" "Smoke signal intelligence tests"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

if ! run_command "bash scripts/smoke_routing_multi_account.sh" "Smoke routing multi-account tests"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo "=== RELEASE GATE SUMMARY ===" | tee -a "$LOG_FILE"
echo "Failed test buckets: $FAILED_TESTS" | tee -a "$LOG_FILE"

if [ $FAILED_TESTS -eq 0 ]; then
    echo "🎉 RELEASE GATE: PASS" | tee -a "$LOG_FILE"
    echo "All tests passed successfully!" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "Production readiness: VERIFIED" | tee -a "$LOG_FILE"
    exit 0
else
    echo "❌ RELEASE GATE: FAIL" | tee -a "$LOG_FILE"
    echo "Some tests failed. Review logs and fix issues." | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "Production readiness: NOT VERIFIED" | tee -a "$LOG_FILE"
    exit 1
fi