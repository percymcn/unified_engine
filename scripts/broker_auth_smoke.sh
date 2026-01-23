#!/bin/bash
# broker_auth_smoke.sh - Test broker authentication without placing trades
# Usage: ./scripts/broker_auth_smoke.sh [broker]
# Brokers: mt4, mt5, tradelocker, tradovate, projectx

set -e

BROKER="${1:-all}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="${PYTHON:-python3}"

cd "$PROJECT_ROOT"

echo "=== Broker Auth Smoke Test ==="
echo "Broker: $BROKER"
echo "Working directory: $PROJECT_ROOT"
echo ""

# Check if Python script exists
if [ ! -f "$SCRIPT_DIR/broker_auth_smoke.py" ]; then
    echo "❌ ERROR: broker_auth_smoke.py not found"
    echo "   Expected: $SCRIPT_DIR/broker_auth_smoke.py"
    exit 1
fi

# Run Python script
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
$PYTHON "$SCRIPT_DIR/broker_auth_smoke.py" "$BROKER"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "=== Smoke Test Complete ==="
    exit 0
else
    echo ""
    echo "=== Smoke Test Failed ==="
    exit $exit_code
fi
