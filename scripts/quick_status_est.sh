#!/bin/bash
# Quick system status with EST times

echo "=========================================="
echo "System Status - $(TZ='America/New_York' date '+%B %d, %Y %I:%M:%S %p %Z')"
echo "=========================================="
echo ""

# Database time
echo "📅 Database Time:"
docker exec unified_postgres.1.dz7p2142go665fnknlj37mfd9 psql -U trading_user -d trading_db -t -c "SELECT TO_CHAR(NOW(), 'Mon DD, YYYY HH12:MI:SS AM TZ');" | xargs
echo ""

# Recent AI scans
echo "🤖 Recent AI Scans (Last 5):"
docker exec unified_postgres.1.dz7p2142go665fnknlj37mfd9 psql -U trading_user -d trading_db -t -c "
SELECT TO_CHAR(created_at, 'HH12:MI AM') || ' - ' || ticker || ' → ' || UPPER(recommendation) || ' (' || confidence || '%)'
FROM ai_strategy_cache
ORDER BY created_at DESC
LIMIT 5;" 2>/dev/null
echo ""

# Recent signals
echo "📊 Recent Trading Signals (Last 10):"
docker exec unified_postgres.1.dz7p2142go665fnknlj37mfd9 psql -U trading_user -d trading_db -t -c "
SELECT TO_CHAR(created_at, 'MM/DD HH12:MI AM') || ' - ' || symbol || ' ' || UPPER(action)
FROM signals
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC
LIMIT 10;" 2>/dev/null
echo ""

# Service status
echo "🚀 Services Running:"
docker service ps unified_api --format "  API: {{.CurrentState}}" --no-trunc | head -1
docker service ps unified_ui --format "  UI:  {{.CurrentState}}" --no-trunc | head -1
echo ""

# Next AI scan
echo "⏰ Next AI Scan:"
LAST_SCAN=$(docker service logs unified_api --tail 500 --since 30m 2>&1 | grep "AI-Only: Analyzing" | tail -1 | grep -oP '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}' || echo "")
if [ -n "$LAST_SCAN" ]; then
    LAST_EST=$(TZ="America/New_York" date -d "${LAST_SCAN}Z" '+%I:%M %p' 2>/dev/null || echo "Unknown")
    echo "  Last scan: $LAST_EST EST"
    echo "  Next scan: ~15 minutes after last scan"
else
    echo "  Checking..."
fi
echo ""

echo "📁 Quick Commands:"
echo "  View AI history:  /home/pharma5/unified_engine/scripts/view_ai_analysis_history.sh"
echo "  View logs:        docker service logs unified_api --tail 50 --since 10m"
echo "  Check database:   docker exec unified_postgres.1... psql -U trading_user -d trading_db"
