#!/bin/bash
# Restart Next.js UI on port 3456

cd "$(dirname "$0")"

# Kill existing process on port 3456
PID=$(ss -ltnp 2>/dev/null | grep :3456 | grep -oP 'pid=\K[0-9]+' | head -1)
if [ ! -z "$PID" ]; then
    echo "Stopping existing Next.js process (PID: $PID)..."
    kill $PID 2>/dev/null
    sleep 2
fi

# Start Next.js on port 3456
echo "Starting Next.js on port 3456..."
HOSTNAME=0.0.0.0 PORT=3456 NODE_ENV=production nohup node_modules/.bin/next start > /tmp/next-ui.log 2>&1 &

sleep 3

# Verify it's running
if ss -ltnp 2>/dev/null | grep -q :3456; then
    echo "✅ Next.js UI started successfully on port 3456"
    echo "Access at: http://$(hostname -I | awk '{print $1}'):3456"
else
    echo "❌ Failed to start Next.js UI"
    echo "Check logs: tail -f /tmp/next-ui.log"
    exit 1
fi
