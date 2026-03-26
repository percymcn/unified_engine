#!/bin/bash
#
# Daily Health Check for Forward Tests
# =====================================
#
# Run this daily to monitor forward test progress for trend and liquidity_reversal engines.
#
# Usage: bash scripts/check_forward_test_health.sh
#

CONTAINER_ID=$(docker ps | grep unified_api | awk '{print $1}')

if [ -z "$CONTAINER_ID" ]; then
    echo "❌ Container not found"
    exit 1
fi

echo "================================================================================"
echo "  FORWARD TEST HEALTH CHECK"
echo "================================================================================"
echo "Date: $(date)"
echo ""

# Check engine health scores
echo "📊 Engine Health Scores:"
echo "--------------------------------------------------------------------------------"

docker exec $CONTAINER_ID python3 -c "
from app.db.database import SessionLocal
from app.services.strategy_registry import get_health_monitor

db = SessionLocal()
health_monitor = get_health_monitor()

engines = ['trend_v1', 'liquidity_reversal_v1']

print(f'{'Engine':<25} {'Health Score':<15} {'Status':<15}')
print('-' * 60)

for engine_id in engines:
    try:
        score = health_monitor.evaluate_strategy_health(db, engine_id)
        print(f'{engine_id:<25} {score.score:>5.1f}/100      {score.status.value:<15}')
    except Exception as e:
        print(f'{engine_id:<25} ERROR: {str(e)}')

db.close()
"

echo ""
echo "--------------------------------------------------------------------------------"
echo ""

# Check forward test sessions
echo "📈 Forward Test Sessions:"
echo "--------------------------------------------------------------------------------"

docker exec $CONTAINER_ID ls -lh /tmp/forward_test/ 2>/dev/null | grep -E "(ft_trend|ft_liquidity)" || echo "No sessions found yet"

echo ""
echo "================================================================================"
echo ""
echo "💡 Tips:"
echo "  - Health > 50 = Good"
echo "  - Health 40-50 = Monitor closely"
echo "  - Health < 40 = Auto-paused (needs investigation)"
echo ""
echo "  View detailed results: docker exec $CONTAINER_ID cat /tmp/forward_test/ft_*_results.json"
echo ""
echo "================================================================================"
