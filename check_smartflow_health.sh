#!/bin/bash
# Check SmartFlow health and restart if needed

echo "=== SmartFlow Health Check ==="
echo "Time: $(date)"
echo ""

# Check FlowAlgo Proxy
echo "1. FlowAlgo Proxy:"
if curl -s http://localhost:9001/health > /dev/null 2>&1; then
    HEALTH=$(curl -s http://localhost:9001/health)
    FLOWS=$(echo $HEALTH | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_entries',0))" 2>/dev/null)
    LOGGED_IN=$(echo $HEALTH | python3 -c "import sys,json; print(json.load(sys.stdin).get('logged_in','unknown'))" 2>/dev/null)
    echo "   Status: RUNNING"
    echo "   Logged in: $LOGGED_IN"
    echo "   Flow entries: $FLOWS"
else
    echo "   Status: DOWN - restarting..."
    sudo systemctl restart flow_confluence_proxy 2>/dev/null || \
        (cd /home/pharma5/unified_engine && source flow_venv/bin/activate && python3 flow_confluence_proxy.py &)
fi

# Check API
echo ""
echo "2. Trading API:"
if curl -s http://localhost:8765/health > /dev/null 2>&1; then
    echo "   Status: RUNNING"
else
    echo "   Status: DOWN"
    echo "   Attempting restart..."
    docker service update unified_api --force
fi

# Check SmartFlow in API logs
echo ""
echo "3. SmartFlow Background Task:"
SMARTFLOW_LOG=$(docker ps -q -f name=unified_api | xargs -I{} docker logs --since 2m {} 2>&1 | grep -c "SmartFlow cycle" 2>/dev/null)
if [ "$SMARTFLOW_LOG" -gt 0 ]; then
    echo "   Status: RUNNING ($SMARTFLOW_LOG cycles in last 2 min)"
else
    echo "   Status: NO RECENT CYCLES"
fi

# Summary
echo ""
echo "=== Summary ==="
docker service ls | grep unified
