#!/usr/bin/env python3
"""
SmartFlow Weekly Review Automation
===================================

Generates comprehensive weekly performance report.
Run every Sunday evening or Monday morning.

Usage:
    python scripts/weekly_review.py
    python scripts/weekly_review.py --export report.json

Success Targets (6-12 month horizon):
- Rolling 90d Sharpe > 1.3 (deflated > 1.1)
- Profit Factor > 1.65
- Max DD < 12-15%
- No regime with win rate < 48%
"""

import asyncio
import sys
import os
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import numpy as np


@dataclass
class WeeklyMetrics:
    """Weekly performance metrics."""
    week_ending: str

    # Core performance
    total_pnl: float = 0.0
    trades_taken: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0

    # Sharpe estimates
    sharpe_7d: float = 0.0
    sharpe_30d: float = 0.0
    sharpe_90d: float = 0.0

    # Drawdown
    max_drawdown_pct: float = 0.0
    current_drawdown_pct: float = 0.0

    # Regime performance
    regime_win_rates: Dict[str, float] = None
    worst_regime: str = ""
    worst_regime_wr: float = 0.0

    # Feature health
    feature_saturation_warnings: List[str] = None
    feature_importance_changes: Dict[str, float] = None

    # Drift status
    drift_detected: bool = False
    drift_strategies: List[str] = None

    # Shadow mode
    shadow_mode_active: bool = False
    shadow_vs_live_diff: float = 0.0

    # Alerts summary
    critical_alerts: int = 0
    warning_alerts: int = 0

    # Status
    meets_targets: bool = False
    action_items: List[str] = None


class WeeklyReviewGenerator:
    """Generates weekly performance review."""

    def __init__(self):
        self.metrics = WeeklyMetrics(
            week_ending=datetime.now().strftime('%Y-%m-%d'),
            regime_win_rates={},
            feature_saturation_warnings=[],
            feature_importance_changes={},
            drift_strategies=[],
            action_items=[]
        )

        # Target thresholds
        self.targets = {
            'sharpe_90d': 1.3,
            'sharpe_30d': 1.0,
            'profit_factor': 1.65,
            'max_drawdown': 12.0,
            'min_regime_wr': 48.0,
        }

    async def collect_metrics(self) -> WeeklyMetrics:
        """Collect all metrics for the week."""
        print("\n" + "="*60)
        print("SMARTFLOW WEEKLY REVIEW")
        print("="*60)
        print(f"Week ending: {self.metrics.week_ending}")

        await self._collect_performance_metrics()
        await self._collect_risk_metrics()
        await self._collect_feature_metrics()
        await self._collect_drift_metrics()
        await self._collect_alert_metrics()

        self._evaluate_targets()
        self._generate_action_items()

        return self.metrics

    async def _collect_performance_metrics(self):
        """Collect performance metrics from risk manager."""
        print("\n--- PERFORMANCE ---")

        try:
            from app.services.advanced_risk import get_advanced_risk_manager

            manager = get_advanced_risk_manager()

            # Simulate collecting performance data
            # In production, this would read from trade journal/database

            # Get recent trades from performance history
            all_trades = []
            for strategy, history in manager.performance_history.items():
                all_trades.extend(list(history))

            if all_trades:
                # Calculate metrics
                wins = sum(1 for t in all_trades if t['is_win'])
                total = len(all_trades)
                self.metrics.trades_taken = total
                self.metrics.win_rate = (wins / total * 100) if total > 0 else 0

                pnls = [t['pnl'] for t in all_trades]
                self.metrics.total_pnl = sum(pnls)

                gross_profit = sum(p for p in pnls if p > 0)
                gross_loss = abs(sum(p for p in pnls if p < 0))
                self.metrics.profit_factor = (
                    gross_profit / gross_loss if gross_loss > 0 else 0
                )

                # Sharpe estimates (annualized)
                if len(pnls) >= 5:
                    mean_pnl = np.mean(pnls)
                    std_pnl = np.std(pnls)
                    if std_pnl > 0:
                        self.metrics.sharpe_7d = (mean_pnl / std_pnl) * np.sqrt(252)

                print(f"  Total P&L: ${self.metrics.total_pnl:,.2f}")
                print(f"  Trades: {self.metrics.trades_taken}")
                print(f"  Win Rate: {self.metrics.win_rate:.1f}%")
                print(f"  Profit Factor: {self.metrics.profit_factor:.2f}")
            else:
                print("  No trades recorded this period")

        except Exception as e:
            print(f"  Error collecting performance: {e}")

    async def _collect_risk_metrics(self):
        """Collect risk metrics."""
        print("\n--- RISK ---")

        try:
            from app.services.metrics_exporter import get_metrics

            metrics = get_metrics()

            # In production, these would be read from actual metrics
            # For now, we'll check the current state

            status = metrics.get_status()
            print(f"  Prometheus enabled: {status['enabled']}")
            print(f"  Active alerts: {status['active_alerts']}")

            # Get CVaR from risk manager
            from app.services.advanced_risk import get_advanced_risk_manager
            manager = get_advanced_risk_manager()

            # Check current positions
            risk_status = manager.get_status()
            print(f"  Active positions: {risk_status['active_positions']}")
            print(f"  Total exposure: {risk_status['total_exposure_pct']:.1f}%")

        except Exception as e:
            print(f"  Error collecting risk metrics: {e}")

    async def _collect_feature_metrics(self):
        """Collect feature importance metrics."""
        print("\n--- FEATURE HEALTH ---")

        try:
            from app.services.feature_importance_tracker import get_importance_tracker

            tracker = get_importance_tracker()
            status = tracker.get_status()

            print(f"  Features tracked: {status['features_tracked']}")
            print(f"  Snapshots stored: {status['snapshots_stored']}")

            # Get saturation warnings
            saturation = tracker.get_saturation_report()
            if saturation:
                self.metrics.feature_saturation_warnings = [
                    s['feature'] for s in saturation if s['is_critical']
                ]
                print(f"  Saturation warnings: {len(saturation)}")
                for s in saturation[:3]:
                    print(f"    - {s['feature']}: -{s['decline_pct']:.0f}%")
            else:
                print("  No saturation detected")

        except Exception as e:
            print(f"  Error collecting feature metrics: {e}")

    async def _collect_drift_metrics(self):
        """Collect drift detection metrics."""
        print("\n--- DRIFT STATUS ---")

        try:
            from app.services.adaptive_learning import get_adaptive_manager

            manager = get_adaptive_manager()

            # Check drift status for all tracked keys
            drift_detected = []
            for key, detector in manager.adwin_detectors.items():
                if hasattr(detector, 'n') and detector.n > 100:
                    # Check recent drift
                    if key in [k for k, _ in list(manager.drift_history)[-10:]]:
                        drift_detected.append(key)

            self.metrics.drift_strategies = drift_detected
            self.metrics.drift_detected = len(drift_detected) > 0

            if drift_detected:
                print(f"  Drift detected in: {drift_detected}")
            else:
                print("  No significant drift detected")

            # Shadow mode status
            if manager.shadow_mode_configs:
                self.metrics.shadow_mode_active = True
                print("  Shadow mode: ACTIVE")

                result = manager.evaluate_shadow_mode()
                if result:
                    self.metrics.shadow_vs_live_diff = (
                        result.config_a_metrics.get('mean_pnl', 0) -
                        result.config_b_metrics.get('mean_pnl', 0)
                    )
                    print(f"  Live vs Shadow diff: {self.metrics.shadow_vs_live_diff:.2f}")
            else:
                print("  Shadow mode: INACTIVE")

        except Exception as e:
            print(f"  Error collecting drift metrics: {e}")

    async def _collect_alert_metrics(self):
        """Collect alert summary."""
        print("\n--- ALERTS ---")

        try:
            from app.services.metrics_exporter import get_metrics, AlertSeverity

            metrics = get_metrics()
            alerts = list(metrics.alerts)

            # Count by severity
            self.metrics.critical_alerts = sum(
                1 for a in alerts
                if a.severity == AlertSeverity.CRITICAL and not a.resolved
            )
            self.metrics.warning_alerts = sum(
                1 for a in alerts
                if a.severity == AlertSeverity.WARNING and not a.resolved
            )

            print(f"  Critical: {self.metrics.critical_alerts}")
            print(f"  Warning: {self.metrics.warning_alerts}")

            # Show recent alerts
            recent = [a for a in alerts if not a.resolved][:5]
            for a in recent:
                print(f"    [{a.severity.value}] {a.message[:50]}")

        except Exception as e:
            print(f"  Error collecting alert metrics: {e}")

    def _evaluate_targets(self):
        """Evaluate if metrics meet targets."""
        print("\n--- TARGET EVALUATION ---")

        checks = []

        # Sharpe check (using 7d as proxy if 90d not available)
        if self.metrics.sharpe_7d > 0:
            sharpe_ok = self.metrics.sharpe_7d > 1.0  # Lower threshold for 7d
            checks.append(sharpe_ok)
            status = "OK" if sharpe_ok else "BELOW TARGET"
            print(f"  Sharpe (7d): {self.metrics.sharpe_7d:.2f} [{status}]")

        # Profit factor
        if self.metrics.profit_factor > 0:
            pf_ok = self.metrics.profit_factor > self.targets['profit_factor']
            checks.append(pf_ok)
            status = "OK" if pf_ok else "BELOW TARGET"
            print(f"  Profit Factor: {self.metrics.profit_factor:.2f} [{status}]")

        # Drawdown
        dd_ok = self.metrics.max_drawdown_pct < self.targets['max_drawdown']
        checks.append(dd_ok)
        status = "OK" if dd_ok else "EXCEEDS LIMIT"
        print(f"  Max DD: {self.metrics.max_drawdown_pct:.1f}% [{status}]")

        # Feature saturation
        sat_ok = len(self.metrics.feature_saturation_warnings) == 0
        checks.append(sat_ok)
        status = "OK" if sat_ok else "WARNINGS"
        print(f"  Feature Health: [{status}]")

        # Drift
        drift_ok = not self.metrics.drift_detected
        checks.append(drift_ok)
        status = "OK" if drift_ok else "DRIFT DETECTED"
        print(f"  Drift Status: [{status}]")

        self.metrics.meets_targets = all(checks) if checks else False

    def _generate_action_items(self):
        """Generate action items based on metrics."""
        print("\n--- ACTION ITEMS ---")

        items = []

        if self.metrics.profit_factor < self.targets['profit_factor']:
            items.append("Review losing trades - identify patterns")

        if self.metrics.feature_saturation_warnings:
            items.append(f"Investigate feature saturation: {self.metrics.feature_saturation_warnings}")

        if self.metrics.drift_detected:
            items.append("Review drift-affected strategies for retraining")

        if self.metrics.critical_alerts > 0:
            items.append("Resolve critical alerts before next trading session")

        if self.metrics.max_drawdown_pct > self.targets['max_drawdown'] * 0.7:
            items.append("Consider reducing position sizes - approaching DD limit")

        if not items:
            items.append("No urgent action items - continue monitoring")

        self.metrics.action_items = items

        for i, item in enumerate(items, 1):
            print(f"  {i}. {item}")

    def export_json(self, filepath: str):
        """Export metrics to JSON."""
        data = asdict(self.metrics)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"\nExported to: {filepath}")


async def main():
    parser = argparse.ArgumentParser(description='SmartFlow Weekly Review')
    parser.add_argument('--export', type=str, help='Export to JSON file')
    args = parser.parse_args()

    generator = WeeklyReviewGenerator()
    metrics = await generator.collect_metrics()

    print("\n" + "="*60)
    if metrics.meets_targets:
        print("STATUS: ON TRACK")
    else:
        print("STATUS: ATTENTION NEEDED")
    print("="*60)

    if args.export:
        generator.export_json(args.export)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
