#!/bin/bash
# View AI Analysis History
# Shows full AI analysis logs with recommendations and summaries

CONTAINER=$(docker ps --filter "name=unified_postgres" --format "{{.Names}}" | head -1)

if [ -z "$CONTAINER" ]; then
    echo "ERROR: Could not find unified_postgres container"
    exit 1
fi

# Default: last 24 hours, or custom hours via argument
HOURS=${1:-24}

echo "==================================="
echo "AI Analysis History (Last ${HOURS}h)"
echo "==================================="
echo ""

docker exec $CONTAINER psql -U trading_user -d trading_db << EOF
-- Full AI analysis history with formatted output (EST times)
SELECT
    TO_CHAR(created_at, 'MM-DD HH12:MI AM') as time_est,
    ticker,
    UPPER(recommendation) as rec,
    LPAD(confidence::text, 3) || '%' as conf,
    LEFT(summary, 120) as analysis_summary
FROM ai_strategy_cache
WHERE created_at > NOW() - INTERVAL '${HOURS} hours'
ORDER BY created_at DESC;

-- Summary stats
SELECT
    '---' as "──────────",
    'SUMMARY' as "Statistics"
UNION ALL
SELECT
    ticker,
    COUNT(*)::text || ' analyses, ' ||
    ROUND(AVG(confidence))::text || '% avg conf'
FROM ai_strategy_cache
WHERE created_at > NOW() - INTERVAL '${HOURS} hours'
GROUP BY ticker
ORDER BY COUNT(*) DESC;
EOF

echo ""
echo "==================================="
echo "Recent Recommendations by Ticker"
echo "==================================="
echo ""

docker exec $CONTAINER psql -U trading_user -d trading_db << EOF
-- Latest recommendation per ticker
WITH latest AS (
    SELECT DISTINCT ON (ticker)
        ticker,
        recommendation,
        confidence,
        summary,
        created_at
    FROM ai_strategy_cache
    WHERE created_at > NOW() - INTERVAL '${HOURS} hours'
    ORDER BY ticker, created_at DESC
)
SELECT
    ticker,
    UPPER(recommendation) as latest_rec,
    confidence::text || '%' as conf,
    TO_CHAR(created_at, 'MM-DD HH12:MI AM') as last_analysis_est,
    LEFT(summary, 100) as reasoning
FROM latest
ORDER BY created_at DESC;
EOF

echo ""
echo "Usage: $0 [hours]  (default: 24 hours)"
echo "Example: $0 48     (show last 48 hours)"
