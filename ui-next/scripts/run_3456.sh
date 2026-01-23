#!/bin/bash
# run_3456.sh - Build and start ui-next on port 3456
# Usage: ./scripts/run_3456.sh
set -e

cd "$(dirname "$0")/.."

echo "=== UI-NEXT BUILD & START ==="
echo "Working directory: $(pwd)"
echo ""

# Step 1: Install dependencies
echo "[1/5] Installing dependencies..."
if [ -f package-lock.json ]; then
    npm ci --silent
else
    npm install --silent
fi

# Step 2: Build
echo "[2/5] Building Next.js app..."
npm run build

# Step 3: Kill existing process on 3456
echo "[3/5] Killing any existing process on port 3456..."
fuser -k 3456/tcp 2>/dev/null || true
sleep 1

# Step 4: Start server
echo "[4/5] Starting server on port 3456..."
PORT=3456 HOSTNAME=0.0.0.0 nohup npm run start > /tmp/ui-next_3456.log 2>&1 &
UI_PID=$!
echo "Started with PID: $UI_PID"

# Step 5: Verify
echo "[5/5] Verifying server is running..."
sleep 5

VERIFY_RESULT=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3456 2>/dev/null || echo "000")
LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ip addr show | grep "inet " | grep -v "127.0.0.1" | head -1 | awk '{print $2}' | cut -d/ -f1 || echo "")

if [ "$VERIFY_RESULT" = "200" ] || [ "$VERIFY_RESULT" = "301" ] || [ "$VERIFY_RESULT" = "302" ]; then
    echo ""
    echo "=== SUCCESS ==="
    echo "UI running on http://localhost:3456"
    if [ -n "$LAN_IP" ]; then
        echo "UI also accessible on http://$LAN_IP:3456"
        LAN_RESULT=$(curl -s -o /dev/null -w "%{http_code}" http://$LAN_IP:3456 2>/dev/null || echo "000")
        if [ "$LAN_RESULT" = "200" ] || [ "$LAN_RESULT" = "301" ] || [ "$LAN_RESULT" = "302" ]; then
            echo "LAN access verified: HTTP $LAN_RESULT"
        else
            echo "⚠️  LAN access check returned: HTTP $LAN_RESULT"
        fi
    fi
    echo "HTTP status: $VERIFY_RESULT"
    echo "Logs: tail -f /tmp/ui-next_3456.log"
    exit 0
else
    echo ""
    echo "=== FAILED ==="
    echo "HTTP status: $VERIFY_RESULT"
    echo "Last 30 lines of log:"
    tail -n 30 /tmp/ui-next_3456.log
    exit 1
fi
