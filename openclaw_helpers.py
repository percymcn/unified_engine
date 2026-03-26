#!/usr/bin/env python3
"""
OpenClaw Helper Functions
=========================

Quick access scripts for OpenClaw to query SmartFlow data.
"""

import requests
import psycopg2
from datetime import datetime, timedelta
import json


# ============================================================================
# Database Access
# ============================================================================

def get_db_connection():
    """Get PostgreSQL connection"""
    return psycopg2.connect(
        host="localhost",  # or 'postgres' from within docker
        database="trading_db",
        user="trading_user",
        password="your_password_here"  # Update from docker secrets
    )


def query_recent_signals(limit=20):
    """Get recent SmartFlow signals"""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT
            created_at,
            ticker,
            action,
            score,
            confidence_score,
            reasoning,
            was_executed,
            outcome,
            pnl_pct
        FROM smartflow_signal_logs
        ORDER BY created_at DESC
        LIMIT {limit};
    """)

    results = []
    for row in cur.fetchall():
        results.append({
            'time': row[0],
            'symbol': row[1],
            'action': row[2],
            'score': row[3],
            'confidence': row[4],
            'reasoning': row[5],
            'executed': row[6],
            'outcome': row[7],
            'pnl_pct': row[8]
        })

    cur.close()
    conn.close()
    return results


def query_open_positions():
    """Get current open positions"""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            symbol,
            direction,
            entry_price,
            current_price,
            unrealized_pnl_pct,
            entry_time,
            regime
        FROM forward_test_trades
        WHERE status = 'open'
        ORDER BY entry_time DESC;
    """)

    results = []
    for row in cur.fetchall():
        results.append({
            'symbol': row[0],
            'direction': row[1],
            'entry_price': row[2],
            'current_price': row[3],
            'pnl_pct': row[4],
            'entry_time': row[5],
            'regime': row[6]
        })

    cur.close()
    conn.close()
    return results


def query_todays_performance():
    """Get today's trading performance"""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            COUNT(*) as total_trades,
            SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
            ROUND(AVG(pnl_pct), 2) as avg_pnl,
            ROUND(MIN(pnl_pct), 2) as worst_trade,
            ROUND(MAX(pnl_pct), 2) as best_trade
        FROM forward_test_trades
        WHERE DATE(entry_time) = CURRENT_DATE
          AND status = 'closed';
    """)

    row = cur.fetchone()
    result = {
        'total_trades': row[0] or 0,
        'wins': row[1] or 0,
        'avg_pnl': row[2] or 0,
        'worst_trade': row[3] or 0,
        'best_trade': row[4] or 0,
        'win_rate': (row[1] / row[0] * 100) if row[0] else 0
    }

    cur.close()
    conn.close()
    return result


# ============================================================================
# API Access
# ============================================================================

API_BASE = "http://localhost:8765"  # or http://api:8000 from container


def get_smartflow_status():
    """Get current SmartFlow status"""
    response = requests.get(f"{API_BASE}/api/v1/smartflow/status")
    return response.json()


def get_recent_api_signals(limit=20):
    """Get recent signals via API"""
    response = requests.get(f"{API_BASE}/api/v1/smartflow/signals?limit={limit}")
    return response.json()


def get_current_positions():
    """Get current positions via API"""
    response = requests.get(f"{API_BASE}/api/v1/positions")
    return response.json()


def get_recent_trades(limit=20):
    """Get recent trades via API"""
    response = requests.get(f"{API_BASE}/api/v1/trades?limit={limit}")
    return response.json()


# ============================================================================
# Analysis Functions
# ============================================================================

def analyze_signal_quality():
    """Analyze quality of recent signals"""
    signals = query_recent_signals(limit=50)

    total = len(signals)
    executed = sum(1 for s in signals if s['executed'])
    wins = sum(1 for s in signals if s['outcome'] == 'win')
    losses = sum(1 for s in signals if s['outcome'] == 'loss')

    avg_pnl = sum(s['pnl_pct'] or 0 for s in signals) / total if total else 0

    return {
        'total_signals': total,
        'executed': executed,
        'wins': wins,
        'losses': losses,
        'win_rate': (wins / executed * 100) if executed else 0,
        'avg_pnl': round(avg_pnl, 2)
    }


def find_problem_trades():
    """Find trades that lost money and analyze why"""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            ticker,
            action,
            score,
            confidence_score,
            reasoning,
            pnl_pct
        FROM smartflow_signal_logs
        WHERE outcome = 'loss'
          AND created_at > NOW() - INTERVAL '7 days'
        ORDER BY pnl_pct ASC
        LIMIT 10;
    """)

    problems = []
    for row in cur.fetchall():
        problems.append({
            'symbol': row[0],
            'action': row[1],
            'score': row[2],
            'confidence': row[3],
            'reasoning': row[4],
            'loss': row[5]
        })

    cur.close()
    conn.close()
    return problems


def generate_daily_report():
    """Generate comprehensive daily report"""
    perf = query_todays_performance()
    positions = query_open_positions()
    signals = analyze_signal_quality()

    report = f"""
🤖 OPENCLAW DAILY REPORT - {datetime.now().strftime('%Y-%m-%d')}
{'═' * 60}

📊 TODAY'S PERFORMANCE:
  Total Trades: {perf['total_trades']}
  Wins: {perf['wins']} ({perf['win_rate']:.1f}%)
  Avg P&L: {perf['avg_pnl']:.2f}%
  Best Trade: {perf['best_trade']:.2f}%
  Worst Trade: {perf['worst_trade']:.2f}%

📈 SIGNAL QUALITY (Last 50):
  Total Analyzed: {signals['total_signals']}
  Executed: {signals['executed']}
  Win Rate: {signals['win_rate']:.1f}%
  Avg P&L: {signals['avg_pnl']:.2f}%

💼 OPEN POSITIONS: {len(positions)}
"""

    for pos in positions:
        report += f"\n  • {pos['symbol']} {pos['direction'].upper()}: "
        report += f"{pos['pnl_pct']:+.2f}% (Entry: {pos['entry_time'].strftime('%H:%M')})"

    return report


# ============================================================================
# Command-Line Interface
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python openclaw_helpers.py [command]")
        print("\nCommands:")
        print("  status      - SmartFlow status")
        print("  signals     - Recent signals")
        print("  positions   - Open positions")
        print("  trades      - Recent trades")
        print("  performance - Today's performance")
        print("  problems    - Find problem trades")
        print("  report      - Generate daily report")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "status":
        print(json.dumps(get_smartflow_status(), indent=2))

    elif command == "signals":
        signals = get_recent_api_signals()
        for s in signals[:10]:
            print(f"{s.get('created_at')} | {s.get('ticker')} {s.get('action').upper()} | "
                  f"Score: {s.get('score'):.1f} | Conf: {s.get('confidence_score'):.0f}%")

    elif command == "positions":
        positions = query_open_positions()
        for p in positions:
            print(f"{p['symbol']} {p['direction'].upper()}: {p['pnl_pct']:+.2f}% "
                  f"(Entry: ${p['entry_price']:.2f})")

    elif command == "trades":
        trades = get_recent_trades()
        for t in trades[:10]:
            print(f"{t.get('symbol')} {t.get('action').upper()}: {t.get('pnl_pct', 0):+.2f}%")

    elif command == "performance":
        perf = query_todays_performance()
        print(json.dumps(perf, indent=2))

    elif command == "problems":
        problems = find_problem_trades()
        for p in problems:
            print(f"\n{p['symbol']} {p['action'].upper()} → {p['loss']:.2f}% loss")
            print(f"  Score: {p['score']:.1f} | Conf: {p['confidence']:.0f}%")
            print(f"  Reason: {p['reasoning']}")

    elif command == "report":
        print(generate_daily_report())

    else:
        print(f"Unknown command: {command}")
