#!/usr/bin/env python3
"""
Auto-cleanup script for AI analysis logs
Runs daily to clean up old AI analysis cache entries
"""

import os
import sys
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

# US Eastern timezone
EST = ZoneInfo("America/New_York")

def now_est():
    """Get current time in EST"""
    return datetime.now(EST)

def format_est(msg):
    """Format with EST timestamp"""
    return f"[{now_est().strftime('%Y-%m-%d %I:%M:%S %p %Z')}] {msg}"

# Use Docker exec instead of direct connection
def run_sql(query):
    """Run SQL query via Docker exec"""
    cmd = [
        'docker', 'exec',
        subprocess.check_output(['docker', 'ps', '--filter', 'name=unified_postgres', '--format', '{{.Names}}']).decode().strip().split('\n')[0],
        'psql', '-U', 'trading_user', '-d', 'trading_db', '-t', '-c', query
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()

def cleanup_ai_logs():
    """Delete AI analysis cache entries older than 24 hours"""

    # Delete old cache entries
    deleted = run_sql("DELETE FROM ai_strategy_cache WHERE created_at < NOW() - INTERVAL '24 hours'; SELECT ROW_COUNT();")
    print(format_est("Cleaned up AI analysis cache entries older than 24 hours"))

    # Also clean up expired entries
    expired = run_sql("DELETE FROM ai_strategy_cache WHERE expires_at < NOW(); SELECT ROW_COUNT();")
    print(format_est("Cleaned up expired AI cache entries"))

    # Show current cache stats
    stats = run_sql("SELECT COUNT(*) as total, COUNT(DISTINCT ticker) as tickers FROM ai_strategy_cache;")
    print(format_est(f"Current cache: {stats}"))

    # Show date range (in EST)
    dates = run_sql("SELECT TO_CHAR(MIN(created_at), 'MM/DD HH12:MI AM'), TO_CHAR(MAX(created_at), 'MM/DD HH12:MI AM') FROM ai_strategy_cache;")
    print(format_est(f"Date range (EST): {dates}"))

if __name__ == "__main__":
    try:
        cleanup_ai_logs()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
