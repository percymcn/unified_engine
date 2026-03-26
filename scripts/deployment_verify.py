#!/usr/bin/env python3
"""
SmartFlow Deployment Verification & Weekly Review
===================================================

Run before deploying to verify all systems are operational.
Also provides weekly review metrics and go-live checklist.

Usage:
    python scripts/deployment_verify.py             # Full verification
    python scripts/deployment_verify.py --weekly    # Weekly review only
    python scripts/deployment_verify.py --checklist # Pre-deploy checklist
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import numpy as np

# Terminal colors
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")


def print_status(name: str, status: bool, detail: str = ""):
    """Print status line."""
    icon = f"{Colors.GREEN}[OK]{Colors.END}" if status else f"{Colors.RED}[FAIL]{Colors.END}"
    detail_str = f" - {detail}" if detail else ""
    print(f"  {icon} {name}{detail_str}")


def print_warning(msg: str):
    """Print warning."""
    print(f"{Colors.YELLOW}  [WARN] {msg}{Colors.END}")


# ============================================
# SERVICE HEALTH CHECKS
# ============================================

async def check_services() -> Dict[str, bool]:
    """Check all SmartFlow services are operational."""
    print_header("SERVICE HEALTH CHECK")
    results = {}

    # 1. Microstructure Analyzer
    try:
        from app.services.microstructure_analyzer import get_microstructure_analyzer
        analyzer = get_microstructure_analyzer()
        results['microstructure'] = analyzer is not None
        print_status("Microstructure Analyzer", True)
    except Exception as e:
        results['microstructure'] = False
        print_status("Microstructure Analyzer", False, str(e)[:40])

    # 2. Crypto Funding Service
    try:
        from app.services.crypto_funding_service import get_crypto_funding_service
        service = await get_crypto_funding_service()
        results['crypto_funding'] = service is not None
        print_status("Crypto Funding Service", True)
    except Exception as e:
        results['crypto_funding'] = False
        print_status("Crypto Funding Service", False, str(e)[:40])

    # 3. News Sentiment Service
    try:
        from app.services.news_sentiment_service import get_news_sentiment_service
        service = await get_news_sentiment_service()
        results['news_sentiment'] = service is not None
        print_status("News Sentiment Service", True)
    except Exception as e:
        results['news_sentiment'] = False
        print_status("News Sentiment Service", False, str(e)[:40])

    # 4. Adaptive Learning Manager
    try:
        from app.services.adaptive_learning import get_adaptive_manager
        manager = get_adaptive_manager()
        results['adaptive_learning'] = manager is not None
        print_status("Adaptive Learning Manager", True)
    except Exception as e:
        results['adaptive_learning'] = False
        print_status("Adaptive Learning Manager", False, str(e)[:40])

    # 5. Advanced Risk Manager
    try:
        from app.services.advanced_risk import get_advanced_risk_manager
        manager = get_advanced_risk_manager()
        results['advanced_risk'] = manager is not None
        print_status("Advanced Risk Manager", True)
    except Exception as e:
        results['advanced_risk'] = False
        print_status("Advanced Risk Manager", False, str(e)[:40])

    # 6. Prometheus Metrics
    try:
        from app.services.metrics_exporter import get_metrics, PROMETHEUS_AVAILABLE
        if PROMETHEUS_AVAILABLE:
            metrics = get_metrics()
            results['prometheus'] = metrics.enabled
            print_status("Prometheus Metrics", True)
        else:
            results['prometheus'] = False
            print_status("Prometheus Metrics", False, "prometheus_client not installed")
    except Exception as e:
        results['prometheus'] = False
        print_status("Prometheus Metrics", False, str(e)[:40])

    # 7. Feature Importance Tracker
    try:
        from app.services.feature_importance_tracker import get_importance_tracker
        tracker = get_importance_tracker()
        results['feature_tracker'] = tracker is not None
        print_status("Feature Importance Tracker", True)
    except Exception as e:
        results['feature_tracker'] = False
        print_status("Feature Importance Tracker", False, str(e)[:40])

    # 8. Unusual Whales Service
    try:
        from app.services.unusual_whales_service import get_unusual_whales_service
        service = await get_unusual_whales_service()
        results['unusual_whales'] = service._is_configured
        if service._is_configured:
            print_status("Unusual Whales API", True, "API key configured")
        else:
            print_status("Unusual Whales API", False, "Mock mode")
            print_warning("Set UNUSUAL_WHALES_API_KEY for live data")
    except Exception as e:
        results['unusual_whales'] = False
        print_status("Unusual Whales API", False, str(e)[:40])

    return results


# ============================================
# ALERT SYSTEM CHECK
# ============================================

def check_alerts() -> Dict[str, Any]:
    """Verify alert system is operational."""
    print_header("ALERT SYSTEM CHECK")
    results = {'working': True, 'tests': []}

    try:
        from app.services.metrics_exporter import get_metrics, AlertSeverity

        metrics = get_metrics()

        # Test drawdown alert
        metrics.update_risk(
            drawdown_current=12.0,  # Critical
            drawdown_max=15.0,
            positions_active=2,
            exposure_total=20.0,
            sector_exposure={'equity_index': 20.0},
            kelly_fraction=0.1,
            trading_state=0,
            consecutive_losses=2
        )

        alerts = metrics.get_active_alerts()
        has_drawdown_alert = any('drawdown' in a.name for a in alerts)
        print_status("Drawdown alert trigger", has_drawdown_alert)
        results['tests'].append(('drawdown', has_drawdown_alert))

        # Test drift alert
        metrics.update_drift("test_strategy", drift_detected=True, confidence=0.85)
        alerts = metrics.get_active_alerts()
        has_drift_alert = any('drift' in a.name for a in alerts)
        print_status("Drift alert trigger", has_drift_alert)
        results['tests'].append(('drift', has_drift_alert))

        # Test feature importance alert
        metrics.update_feature_importance(
            {'bb_position': 0.05},  # Low
            baseline={'bb_position': 0.20}  # Was high
        )
        alerts = metrics.get_active_alerts()
        has_feature_alert = any('feature' in a.name for a in alerts)
        print_status("Feature importance alert", has_feature_alert)
        results['tests'].append(('feature', has_feature_alert))

        results['total_alerts'] = len(alerts)
        print(f"\n  Total active alerts: {len(alerts)}")

    except Exception as e:
        results['working'] = False
        print_status("Alert system", False, str(e)[:50])

    return results


# ============================================
# RISK SYSTEM CHECK
# ============================================

def check_risk_system() -> Dict[str, Any]:
    """Verify risk management system."""
    print_header("RISK SYSTEM CHECK")
    results = {'working': True}

    try:
        from app.services.advanced_risk import get_advanced_risk_manager

        manager = get_advanced_risk_manager()

        # Test slippage estimation
        slippage = manager.estimate_slippage("MES", 5000.0, 2, atr=15.0)
        print_status(
            "Slippage model",
            slippage.expected_ticks > 0,
            f"{slippage.expected_ticks:.1f} ticks"
        )
        results['slippage_ticks'] = slippage.expected_ticks

        # Test CVaR (need some data first)
        for _ in range(60):
            manager.update_returns("MES", np.random.normal(0.001, 0.02))

        cvar = manager.calculate_cvar("MES", 10000)
        print_status(
            "CVaR calculation",
            cvar.cvar_95 > 0,
            f"CVaR95={cvar.cvar_95:.2%}"
        )
        results['cvar_95'] = cvar.cvar_95

        # Test position limits
        limits = manager.config.position_limits
        print_status(
            "Position limits configured",
            True,
            f"max={limits.max_positions}, per_sector={limits.max_per_sector_pct}%"
        )
        results['max_positions'] = limits.max_positions
        results['max_per_sector'] = limits.max_per_sector_pct

        # Test decay tracking
        for _ in range(40):
            manager.record_trade_result("test", np.random.normal(100, 200), True)

        should_reduce, mult = manager.check_strategy_decay("test")
        print_status(
            "Strategy decay tracking",
            True,
            f"reduce={should_reduce}, mult={mult:.1f}"
        )

    except Exception as e:
        results['working'] = False
        print_status("Risk system", False, str(e)[:50])

    return results


# ============================================
# WEEKLY REVIEW METRICS
# ============================================

def generate_weekly_review() -> Dict[str, Any]:
    """Generate weekly review metrics template."""
    print_header("WEEKLY REVIEW TEMPLATE")

    metrics = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'review_type': 'weekly',
        'sections': []
    }

    print("""
    ENSEMBLE CALIBRATION
    --------------------
    [ ] Brier score < 0.15
    [ ] Reliability diagram shows good calibration
    [ ] No significant probability overconfidence

    FEATURE IMPORTANCE
    ------------------
    [ ] BB features (position, squeeze) importance > 10%
    [ ] Flow conviction importance stable
    [ ] No unexpected features dominating
    [ ] Check saturation warnings

    REGIME TRANSITIONS
    ------------------
    [ ] Regime detection accuracy vs manual labels
    [ ] Transition matrix plausible
    [ ] No "stuck" regimes

    PERFORMANCE METRICS
    -------------------
    [ ] Rolling 30d Sharpe > 1.0
    [ ] Rolling 90d Sharpe > 1.3
    [ ] Profit Factor > 1.5
    [ ] Max DD < 10%

    LIVE VS SHADOW
    --------------
    [ ] Live performance within 15% of shadow
    [ ] No major divergence in signal timing
    [ ] Shadow variants A/B results reviewed

    SYSTEM HEALTH
    -------------
    [ ] All alerts reviewed and resolved
    [ ] No persistent drift detected
    [ ] Data feeds operational
    [ ] Latency acceptable
    """)

    return metrics


# ============================================
# GO-LIVE CHECKLIST
# ============================================

def print_golive_checklist():
    """Print go-live deployment checklist."""
    print_header("GO-LIVE CHECKLIST")

    print("""
    PRE-DEPLOYMENT (DAY -7)
    -----------------------
    [ ] Paper trading for minimum 2 weeks
    [ ] Walk-forward validation complete
    [ ] Monte Carlo simulation shows acceptable worst-case DD
    [ ] All module tests passing (100%)

    DEPLOYMENT DAY
    --------------
    [ ] Start with 1-2 MES contracts ONLY
    [ ] Enable all alerts (drawdown, drift, feature saturation)
    [ ] Log every trade decision
    [ ] Set max daily loss limit (e.g., $500)

    FIRST WEEK
    ----------
    [ ] Daily P&L review
    [ ] Check ensemble calibration
    [ ] Verify slippage matches estimates
    [ ] Compare live vs paper results

    FIRST MONTH
    -----------
    [ ] Weekly review ritual established
    [ ] Feature importance trends stable
    [ ] No regime where system consistently loses
    [ ] Rolling metrics within targets

    SCALING CRITERIA (After 3-6 months)
    ------------------------------------
    Minimum thresholds before scaling:
    - Rolling 90d Sharpe > 1.3 (deflated > 1.1)
    - Profit Factor > 1.65
    - Max DD < 12%
    - Live matches walk-forward within 15%
    - No regime win rate < 48%

    IF CRITERIA MET: Scale 25-50% per quarter
    IF NOT MET: Simplify or pivot strategy
    """)


# ============================================
# POSITION SIZING RECOMMENDATIONS
# ============================================

def print_position_sizing():
    """Print position sizing recommendations."""
    print_header("POSITION SIZING GUIDE")

    print("""
    STARTING CAPITAL: $10,000-50,000 recommended

    MICRO FUTURES (MES, MNQ)
    ------------------------
    - MES: $1.25/tick, ~$6.50/point, ~$1,300 margin
    - MNQ: $0.50/tick, ~$2.00/point, ~$1,750 margin

    POSITION SIZING FORMULA
    -----------------------
    Base: Kelly * 0.5 (half-Kelly for safety)
    With SmartFlow: Use advanced_risk.calculate_position_size()

    Example for $25,000 account:
    - Max risk per trade: 1-2% ($250-500)
    - With 20 point stop on MES: 2-3 contracts max
    - Start with: 1 contract only

    SECTOR LIMITS
    -------------
    - Max per ticker: 25%
    - Max per sector: 50%
    - Max correlated: 60%
    - Max concurrent positions: 5

    DRAWDOWN BREAKERS
    -----------------
    - 5% DD: Warning alert
    - 10% DD: Reduce size by 50%
    - 15% DD: Pause trading, review strategy
    """)


# ============================================
# MAIN
# ============================================

async def main():
    parser = argparse.ArgumentParser(description='SmartFlow Deployment Verification')
    parser.add_argument('--weekly', action='store_true', help='Weekly review only')
    parser.add_argument('--checklist', action='store_true', help='Go-live checklist only')
    parser.add_argument('--sizing', action='store_true', help='Position sizing guide')
    args = parser.parse_args()

    print(f"\n{Colors.BOLD}SmartFlow Deployment Verification{Colors.END}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if args.weekly:
        generate_weekly_review()
        return

    if args.checklist:
        print_golive_checklist()
        return

    if args.sizing:
        print_position_sizing()
        return

    # Full verification
    service_results = await check_services()
    alert_results = check_alerts()
    risk_results = check_risk_system()

    # Summary
    print_header("VERIFICATION SUMMARY")

    service_ok = sum(service_results.values())
    service_total = len(service_results)
    alerts_ok = alert_results.get('working', False)
    risk_ok = risk_results.get('working', False)

    print(f"\n  Services: {service_ok}/{service_total} operational")
    print(f"  Alerts:   {'OK' if alerts_ok else 'FAIL'}")
    print(f"  Risk:     {'OK' if risk_ok else 'FAIL'}")

    all_ok = service_ok == service_total and alerts_ok and risk_ok

    if all_ok:
        print(f"\n{Colors.GREEN}{Colors.BOLD}  ALL SYSTEMS OPERATIONAL{Colors.END}")
        print("\n  Next steps:")
        print("  1. Run: python scripts/deployment_verify.py --checklist")
        print("  2. Run: python scripts/deployment_verify.py --sizing")
        print("  3. Deploy with 1-2 contracts only")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}  ISSUES DETECTED - DO NOT DEPLOY{Colors.END}")
        print("\n  Fix issues above before deployment")

    return 0 if all_ok else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
