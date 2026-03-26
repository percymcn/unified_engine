#!/usr/bin/env python3
"""
Strategy Switcher
==================

Switch between saved SmartFlow strategies:
- quick_primary: Uses quick engine for all regimes (validated, Sharpe 7.30)
- regime_adaptive_v1: Routes to specialized engines based on regime

Usage:
    python scripts/switch_strategy.py quick_primary
    python scripts/switch_strategy.py regime_adaptive_v1
    python scripts/switch_strategy.py --list
    python scripts/switch_strategy.py --backtest regime_adaptive_v1
"""

import argparse
import json
import shutil
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


STRATEGIES_DIR = '.smartflow_data/strategies'
RANKINGS_FILE = '.smartflow_data/comparisons/regime_rankings.json'


def list_strategies():
    """List available strategies."""
    print("\n=== Available Strategies ===\n")

    strategies = {
        'quick_primary': {
            'name': 'Quick Primary Strategy',
            'description': 'Uses quick engine for ALL regimes. Best performer with Sharpe 7.30, 73.5% win rate.',
            'slim_map': True,
            'engines': ['quick', 'unified']
        },
        'regime_adaptive_v1': {
            'name': 'Regime-Adaptive Multi-Engine',
            'description': 'Routes to specialized engines based on detected market regime.',
            'slim_map': False,
            'engines': ['breakout', 'trend', 'mean_reversion', 'liquidity_reversal', 'unified']
        }
    }

    for strategy_id, info in strategies.items():
        print(f"  {strategy_id}")
        print(f"    Name: {info['name']}")
        print(f"    {info['description']}")
        print(f"    Slim Map: {info['slim_map']}")
        print(f"    Engines: {', '.join(info['engines'])}")
        print()


def switch_to_quick_primary():
    """Switch to quick primary strategy."""
    print("\nSwitching to QUICK PRIMARY strategy...")

    # Create quick primary rankings
    rankings = {}
    all_regimes = [
        'trending_up', 'trending_down', 'ranging', 'mean_reverting',
        'vol_expansion', 'vol_contraction', 'chaotic', 'neutral',
        'volatile', 'breakout', 'default', ''
    ]

    for regime in all_regimes:
        rankings[regime] = {
            'ranked_engines': ['quick', 'unified'],
            'engine_stats': {},
            'sample_count': 1,
            'last_updated': '2026-03-16T20:00:00.000000',
            'comparison_ids': ['quick_primary'],
            'notes': 'QUICK PRIMARY: Sharpe 7.30, 73.5% win rate'
        }

    # Save rankings
    with open(RANKINGS_FILE, 'w') as f:
        json.dump(rankings, f, indent=2)

    print("  Rankings updated to quick/unified for all regimes")
    print("  Set SMARTFLOW_SLIM_MAP=true for slim map mode")
    print("\n  To apply: Restart forward test or refresh router")
    print("  Done!")


def switch_to_regime_adaptive():
    """Switch to regime-adaptive strategy."""
    print("\nSwitching to REGIME-ADAPTIVE strategy...")

    rankings_path = f'{STRATEGIES_DIR}/regime_adaptive_v1_rankings.json'

    if not os.path.exists(rankings_path):
        print(f"  ERROR: Rankings file not found: {rankings_path}")
        return False

    # Copy rankings file
    shutil.copy(rankings_path, RANKINGS_FILE)

    print("  Rankings updated to regime-adaptive mapping")
    print("  Set SMARTFLOW_SLIM_MAP=false to use all engines")
    print("\n  To apply: Restart forward test or refresh router")
    print("  Done!")
    return True


async def backtest_strategy(strategy_id: str):
    """Run backtest on a strategy."""
    print(f"\n=== Backtesting {strategy_id} ===\n")

    from app.services.backtesting.comparison_runner import get_comparison_runner

    runner = get_comparison_runner()

    if strategy_id == 'quick_primary':
        engines = ['quick', 'unified']
    elif strategy_id == 'regime_adaptive_v1':
        engines = ['breakout', 'trend', 'mean_reversion', 'liquidity_reversal', 'unified']
    else:
        print(f"Unknown strategy: {strategy_id}")
        return

    print(f"Running comparison on engines: {engines}")
    print("Ticker: MES, Days: 30\n")

    comparison = await runner.run_engine_comparison(
        ticker='MES',
        days=30,
        engines=engines
    )

    print("\nLEADERBOARD:")
    print("-" * 70)
    print(f"{'Rank':<5} {'Engine':<22} {'Return':>10} {'Sharpe':>10} {'Win Rate':>10}")
    print("-" * 70)

    for entry in comparison.leaderboard:
        print(f"#{entry['rank']:<4} {entry['engine']:<22} {entry['total_return_pct']:>+9.1f}% {entry['sharpe_ratio']:>9.2f} {entry['win_rate']:>9.1f}%")

    print()
    print("EXECUTION STATUS:")
    for engine, meta in comparison.engine_metadata.items():
        status = 'TRUE' if not meta.unified_fallback_used else 'FALLBACK'
        print(f"  {engine}: {meta.actual_execution_mode} [{status}]")


def main():
    parser = argparse.ArgumentParser(description='Switch SmartFlow strategies')
    parser.add_argument('strategy', nargs='?', help='Strategy to switch to')
    parser.add_argument('--list', action='store_true', help='List available strategies')
    parser.add_argument('--backtest', type=str, help='Run backtest on strategy')

    args = parser.parse_args()

    if args.list:
        list_strategies()
        return

    if args.backtest:
        asyncio.run(backtest_strategy(args.backtest))
        return

    if not args.strategy:
        print("Usage: python scripts/switch_strategy.py <strategy>")
        print("       python scripts/switch_strategy.py --list")
        print("       python scripts/switch_strategy.py --backtest <strategy>")
        return

    if args.strategy == 'quick_primary':
        switch_to_quick_primary()
    elif args.strategy == 'regime_adaptive_v1':
        switch_to_regime_adaptive()
    else:
        print(f"Unknown strategy: {args.strategy}")
        print("Use --list to see available strategies")


if __name__ == '__main__':
    main()
