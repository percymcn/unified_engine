#!/bin/bash
#
# local_up_postgres.sh - Canonical local development startup
#
# CANONICAL SETTINGS (DO NOT CHANGE):
#   API:      0.0.0.0:8765
#   UI:       0.0.0.0:3456
#   Postgres: localhost:5432
#   Database: trading_db
#
# Usage: ./scripts/local_up_postgres.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Canonical settings
export DATABASE_URL="postgresql://trading_user:trading_password@127.0.0.1:5432/trading_db"
export BACKEND_URL="http://127.0.0.1:8765"
export API_PORT=8765
export UI_PORT=3456

# Log files
API_LOG="/tmp/tradeflow_api.log"
UI_LOG="/tmp/tradeflow_ui.log"

echo "=========================================="
echo "TradeFlow Local Development Stack"
echo "=========================================="
echo ""
echo "Canonical Ports:"
echo "  API:      0.0.0.0:$API_PORT"
echo "  UI:       0.0.0.0:$UI_PORT"
echo "  Postgres: localhost:5432"
echo ""

# Check Postgres
echo "[1/5] Checking Postgres..."
if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo "  ✓ Postgres is ready on port 5432"
else
    echo "  ✗ Postgres is not running!"
    echo "    Start with: sudo systemctl start postgresql"
    exit 1
fi

# Kill stale processes on our ports
echo "[2/5] Killing stale processes on ports 8765, 3456, 8000, 3000..."
for port in 8765 3456 8000 3000; do
    pids=$(lsof -t -i:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "  Killing processes on port $port: $pids"
        kill -9 $pids 2>/dev/null || true
    fi
done
sleep 1

# Start backend
echo "[3/5] Starting backend on 0.0.0.0:$API_PORT..."
echo "  Log: $API_LOG"
DATABASE_URL="$DATABASE_URL" uvicorn app.main:app \
    --host 0.0.0.0 \
    --port $API_PORT \
    --reload \
    > "$API_LOG" 2>&1 &
API_PID=$!
echo "  PID: $API_PID"

# Wait for backend
echo "  Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s "http://localhost:$API_PORT/health" >/dev/null 2>&1; then
        echo "  ✓ Backend ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "  ✗ Backend failed to start. Check $API_LOG"
        exit 1
    fi
    sleep 1
done

# Start UI
echo "[4/5] Starting UI on 0.0.0.0:$UI_PORT..."
echo "  Log: $UI_LOG"
cd ui-next
NEXT_PUBLIC_API_URL="http://127.0.0.1:$API_PORT" \
BACKEND_URL="http://127.0.0.1:$API_PORT" \
npm run dev -- -H 0.0.0.0 -p $UI_PORT \
    > "$UI_LOG" 2>&1 &
UI_PID=$!
cd "$PROJECT_DIR"
echo "  PID: $UI_PID"

# Wait for UI
echo "  Waiting for UI to be ready..."
for i in {1..60}; do
    if curl -s "http://localhost:$UI_PORT" >/dev/null 2>&1; then
        echo "  ✓ UI ready"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "  ⚠ UI may still be compiling. Check $UI_LOG"
    fi
    sleep 1
done

# Get LAN IP for iPhone testing
echo "[5/5] Getting network URLs..."
LAN_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "=========================================="
echo "Stack is running!"
echo "=========================================="
echo ""
echo "Local URLs:"
echo "  API:   http://localhost:$API_PORT"
echo "  UI:    http://localhost:$UI_PORT"
echo ""
echo "LAN URLs (for iPhone):"
echo "  API:   http://$LAN_IP:$API_PORT"
echo "  UI:    http://$LAN_IP:$UI_PORT"
echo ""
echo "Logs:"
echo "  API:   tail -f $API_LOG"
echo "  UI:    tail -f $UI_LOG"
echo ""
echo "Stop with: pkill -f 'uvicorn app.main' && pkill -f 'next-server'"
echo ""

# Keep script running to show logs
echo "Press Ctrl+C to stop..."
trap "echo 'Stopping...'; kill $API_PID $UI_PID 2>/dev/null; exit 0" INT TERM
wait
