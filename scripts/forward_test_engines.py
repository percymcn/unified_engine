#!/usr/bin/env python3
"""
Controlled Forward-Testing for Strategy Engines
================================================

Runs strategy engines in paper/forward-test mode with:
- Health system active (Phase 10)
- Allocator metadata visible (Phase 9)
- Router decisions logged (Phase 3)
- Execution quality tracking (Phase 12)
- Portfolio risk monitoring (Phase 11)

Usage:
    # Test single engine
    python scripts/forward_test_engines.py --engine breakout --days 30

    # Test multiple engines
    python scripts/forward_test_engines.py --engine breakout,trend --days 30

    # Test all validated engines
    python scripts/forward_test_engines.py --engine validated --days 30
"""

import sys
import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.strategy_engines import get_engine
from app.services.strategy_registry import (
    get_health_monitor,
    get_execution_tracker,
    get_portfolio_risk_engine
)
from app.services.smartflow_engine_router import get_router, RoutingMode


class ForwardTestManager:
    """
    Manages controlled forward-testing of strategy engines.

    Features:
    - Paper trading mode (no real money)
    - Health monitoring active
    - Portfolio risk constraints
    - Execution quality tracking
    - Detailed logging
    """

    def __init__(self, db: Session, output_dir: str = "/tmp/forward_test"):
        self.db = db
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Services
        self.health_monitor = get_health_monitor()
        self.exec_tracker = get_execution_tracker()
        self.risk_engine = get_portfolio_risk_engine()
        self.router = get_router(db)

        # Test state
        self.active_tests = {}
        self.test_results = {}

        print(f"✅ ForwardTestManager initialized")
        print(f"   Output: {self.output_dir}")

    def start_forward_test(
        self,
        engine_name: str,
        duration_days: int = 30,
        max_position_size: float = 1.0,
        max_daily_loss: float = 500.0
    ) -> str:
        """
        Start forward test for an engine.

        Args:
            engine_name: Engine to test
            duration_days: How long to run test
            max_position_size: Max position size multiplier
            max_daily_loss: Max daily loss before auto-pause

        Returns:
            Test session ID
        """
        session_id = f"ft_{engine_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        test_config = {
            'session_id': session_id,
            'engine_name': engine_name,
            'strategy_id': f"{engine_name}_v1",
            'start_time': datetime.now().isoformat(),
            'end_time': (datetime.now() + timedelta(days=duration_days)).isoformat(),
            'duration_days': duration_days,
            'mode': 'paper',
            'max_position_size': max_position_size,
            'max_daily_loss': max_daily_loss,
            'status': 'active',

            # Risk controls
            'health_monitoring': True,
            'portfolio_risk_checks': True,
            'execution_tracking': True,
            'router_logging': True,

            # Thresholds
            'min_health_score': 40,  # Auto-pause if health < 40
            'max_portfolio_risk': 15,  # Max portfolio risk %

            # Results
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'current_drawdown': 0.0,
            'max_drawdown': 0.0,

            # Logs
            'trades': [],
            'health_checks': [],
            'risk_checks': [],
            'router_decisions': []
        }

        self.active_tests[session_id] = test_config

        # Save config
        config_file = self.output_dir / f"{session_id}_config.json"
        with open(config_file, 'w') as f:
            json.dump(test_config, f, indent=2)

        print(f"\n✅ Forward test started: {session_id}")
        print(f"   Engine: {engine_name}")
        print(f"   Duration: {duration_days} days")
        print(f"   Mode: paper")
        print(f"   Config: {config_file}")

        return session_id

    def check_health(self, session_id: str) -> Dict[str, Any]:
        """
        Run health check for forward test session.

        Uses Phase 10 health monitoring.
        """
        if session_id not in self.active_tests:
            raise ValueError(f"Session not found: {session_id}")

        test = self.active_tests[session_id]
        strategy_id = test['strategy_id']

        # Run health evaluation
        health_score = self.health_monitor.evaluate_strategy_health(
            self.db,
            strategy_id,
            auto_pause_on_critical=True
        )

        health_check = {
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'strategy_id': strategy_id,
            'health_score': health_score.score,
            'status': health_score.status.value,
            'drift_metrics': {
                'sharpe_drift_pct': health_score.drift_metrics.sharpe_drift_pct if health_score.drift_metrics else None,
                'win_rate_drift_pct': health_score.drift_metrics.win_rate_drift_pct if health_score.drift_metrics else None,
                'drawdown_drift_pct': health_score.drift_metrics.drawdown_drift_pct if health_score.drift_metrics else None
            },
            'recommendation': 'continue' if health_score.score >= test['min_health_score'] else 'pause'
        }

        test['health_checks'].append(health_check)

        # Auto-pause if health too low
        if health_score.score < test['min_health_score']:
            test['status'] = 'paused'
            test['pause_reason'] = f"Health score too low: {health_score.score:.1f}"
            print(f"⚠️  Forward test paused: {test['pause_reason']}")

        return health_check

    def check_portfolio_risk(self, session_id: str) -> Dict[str, Any]:
        """
        Check portfolio risk for forward test.

        Uses Phase 11 portfolio risk engine.
        """
        if session_id not in self.active_tests:
            raise ValueError(f"Session not found: {session_id}")

        test = self.active_tests[session_id]

        # Calculate current portfolio risk
        # Note: This would use actual position data
        allocations = [{
            'strategy_id': test['strategy_id'],
            'weight': test['max_position_size']
        }]

        risk_snapshot = self.risk_engine.calculate_portfolio_risk(
            self.db,
            allocations
        )

        risk_check = {
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'portfolio_var': risk_snapshot.portfolio_var,
            'portfolio_cvar': risk_snapshot.portfolio_cvar,
            'risk_budget_used': risk_snapshot.risk_budget_used,
            'is_halted': risk_snapshot.is_halted,
            'recommendation': 'continue' if not risk_snapshot.is_halted else 'halt'
        }

        test['risk_checks'].append(risk_check)

        # Auto-halt if risk too high
        if risk_snapshot.is_halted:
            test['status'] = 'halted'
            test['halt_reason'] = risk_snapshot.halt_reason
            print(f"🛑 Forward test halted: {test['halt_reason']}")

        return risk_check

    def log_router_decision(
        self,
        session_id: str,
        regime: str,
        selected_engine: str
    ):
        """Log router decision for this session."""
        if session_id not in self.active_tests:
            return

        test = self.active_tests[session_id]

        decision = {
            'timestamp': datetime.now().isoformat(),
            'regime': regime,
            'selected_engine': selected_engine,
            'expected_engine': test['engine_name'],
            'match': selected_engine == test['engine_name']
        }

        test['router_decisions'].append(decision)

    def record_trade(
        self,
        session_id: str,
        trade: Dict[str, Any]
    ):
        """Record a trade for this forward test session."""
        if session_id not in self.active_tests:
            return

        test = self.active_tests[session_id]

        trade['session_id'] = session_id
        trade['timestamp'] = datetime.now().isoformat()

        test['trades'].append(trade)
        test['total_trades'] += 1

        if trade.get('pnl', 0) > 0:
            test['winning_trades'] += 1
        else:
            test['losing_trades'] += 1

        test['total_pnl'] += trade.get('pnl', 0)

        # Update drawdown
        if test['total_pnl'] < test['current_drawdown']:
            test['current_drawdown'] = test['total_pnl']
            test['max_drawdown'] = min(test['max_drawdown'], test['current_drawdown'])

        # Check daily loss limit
        if abs(test['current_drawdown']) > test['max_daily_loss']:
            test['status'] = 'paused'
            test['pause_reason'] = f"Daily loss limit exceeded: {test['current_drawdown']:.2f}"
            print(f"⚠️  Forward test paused: {test['pause_reason']}")

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current status of forward test session."""
        if session_id not in self.active_tests:
            raise ValueError(f"Session not found: {session_id}")

        test = self.active_tests[session_id]

        return {
            'session_id': session_id,
            'engine_name': test['engine_name'],
            'status': test['status'],
            'total_trades': test['total_trades'],
            'win_rate': test['winning_trades'] / test['total_trades'] if test['total_trades'] > 0 else 0,
            'total_pnl': test['total_pnl'],
            'max_drawdown': test['max_drawdown'],
            'health_checks': len(test['health_checks']),
            'risk_checks': len(test['risk_checks']),
            'router_match_rate': sum(1 for d in test['router_decisions'] if d['match']) / len(test['router_decisions']) if test['router_decisions'] else 0
        }

    def stop_forward_test(self, session_id: str) -> Dict[str, Any]:
        """Stop forward test and generate final report."""
        if session_id not in self.active_tests:
            raise ValueError(f"Session not found: {session_id}")

        test = self.active_tests[session_id]
        test['status'] = 'completed'
        test['end_time_actual'] = datetime.now().isoformat()

        # Save final results
        results_file = self.output_dir / f"{session_id}_results.json"
        with open(results_file, 'w') as f:
            json.dump(test, f, indent=2)

        # Generate summary
        summary = self.get_session_status(session_id)

        print(f"\n✅ Forward test completed: {session_id}")
        print(f"   Total trades: {summary['total_trades']}")
        print(f"   Win rate: {summary['win_rate']:.1%}")
        print(f"   Total P&L: ${summary['total_pnl']:.2f}")
        print(f"   Max drawdown: ${summary['max_drawdown']:.2f}")
        print(f"   Results: {results_file}")

        # Move to completed
        self.test_results[session_id] = test
        del self.active_tests[session_id]

        return summary

    def generate_comparison_report(self) -> str:
        """Generate comparison report across all forward tests."""
        print("\n📊 Generating Forward Test Comparison Report")

        report = []
        report.append("=" * 80)
        report.append("FORWARD TEST COMPARISON REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append(f"Active tests: {len(self.active_tests)}")
        report.append(f"Completed tests: {len(self.test_results)}")
        report.append("")

        for session_id, test in self.test_results.items():
            report.append("=" * 80)
            report.append(f"Session: {session_id}")
            report.append("=" * 80)
            report.append(f"Engine: {test['engine_name']}")
            report.append(f"Status: {test['status']}")
            report.append(f"Total Trades: {test['total_trades']}")

            if test['total_trades'] > 0:
                win_rate = test['winning_trades'] / test['total_trades']
                report.append(f"Win Rate: {win_rate:.1%}")

            report.append(f"Total P&L: ${test['total_pnl']:.2f}")
            report.append(f"Max Drawdown: ${test['max_drawdown']:.2f}")
            report.append("")

        report_text = "\n".join(report)

        # Save report
        output_file = self.output_dir / "comparison_report.txt"
        with open(output_file, 'w') as f:
            f.write(report_text)

        print(f"✅ Comparison report saved: {output_file}")
        print(f"\n{report_text}")

        return report_text


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Forward test strategy engines")
    parser.add_argument('--engine', required=True, help='Engine name or "validated"')
    parser.add_argument('--days', type=int, default=30, help='Test duration in days')
    parser.add_argument('--output', default='/tmp/forward_test', help='Output directory')

    args = parser.parse_args()

    db = SessionLocal()

    try:
        manager = ForwardTestManager(db, output_dir=args.output)

        # Determine which engines to test
        if args.engine == 'validated':
            # Load validation results to find validated engines
            validation_dir = Path('/tmp/engine_validation')
            if not validation_dir.exists():
                print("❌ No validation results found. Run validate_strategy_engines.py first.")
                return

            engines_to_test = []  # Would load from validation results
            print("⚠️  'validated' mode requires validation results")
            print("   Run: python scripts/validate_strategy_engines.py first")
            return
        else:
            engines_to_test = args.engine.split(',')

        # Start forward tests
        sessions = []
        for engine in engines_to_test:
            session_id = manager.start_forward_test(
                engine_name=engine,
                duration_days=args.days
            )
            sessions.append(session_id)

        print(f"\n✅ {len(sessions)} forward test(s) started")
        print(f"📊 Monitor progress in: {args.output}")
        print(f"\nTo stop tests and generate report:")
        print(f"  python scripts/forward_test_engines.py --stop {','.join(sessions)}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
