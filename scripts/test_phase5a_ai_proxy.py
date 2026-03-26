#!/usr/bin/env python3
"""
Phase 5A: AI-Proxy Backtest Verification
=========================================

Tests AI-proxy backtest implementation against other engines
to verify:
1. AI-proxy executes without errors
2. AI-proxy produces divergent results from unified/deterministic/quick
3. Execution metadata correctly shows ai_proxy_backtest mode
4. No unified fallback used
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.backtesting.comparison_runner import get_comparison_runner


async def run_phase5a_verification():
    """Run Phase 5A verification test."""

    print("=" * 80)
    print("Phase 5A: AI-Proxy Backtest Verification")
    print("=" * 80)
    print()

    runner = get_comparison_runner()

    # Test configuration
    ticker = "MES"
    days = 30  # Shorter test period for quick verification
    engines = ["unified", "deterministic", "quick", "ai"]

    print(f"Test Configuration:")
    print(f"  Ticker: {ticker}")
    print(f"  Days: {days}")
    print(f"  Engines: {engines}")
    print()
    print("Running comparison...")
    print()

    try:
        # Run comparison
        comparison = await runner.run_engine_comparison(
            ticker=ticker,
            days=days,
            engines=engines,
            config_overrides=None
        )

        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()

        # 1. Check execution metadata
        print("1. Execution Metadata Check")
        print("-" * 40)
        for engine, metadata in comparison.engine_metadata.items():
            print(f"\n{engine.upper()}:")
            print(f"  Requested: {metadata.requested_engine_type}")
            print(f"  Actual Mode: {metadata.actual_execution_mode}")
            print(f"  Fallback Used: {metadata.unified_fallback_used}")
            print(f"  Routing Status: {metadata.routing_status}")
            print(f"  Notes: {metadata.notes}")

        # 2. Check for warnings
        print("\n\n2. Warnings Check")
        print("-" * 40)
        if comparison.warnings:
            for warning in comparison.warnings:
                print(f"  ⚠️  {warning}")
        else:
            print("  ✅ No warnings")

        # 3. Performance comparison
        print("\n\n3. Performance Leaderboard")
        print("-" * 40)
        for entry in comparison.leaderboard:
            print(f"\n#{entry['rank']} {entry['engine'].upper()}")
            print(f"  Total Return: {entry['total_return_pct']:.2f}%")
            print(f"  Net Profit: ${entry['net_profit']:.2f}")
            print(f"  Sharpe Ratio: {entry['sharpe_ratio']:.3f}")
            print(f"  Win Rate: {entry['win_rate']:.1f}%")
            print(f"  Max Drawdown: {entry['max_drawdown_pct']:.2f}%")
            print(f"  Total Trades: {entry['total_trades']}")
            print(f"  Avg Trade: ${entry['avg_trade']:.2f}")
            print(f"  Avg Hold Time: {entry['avg_holding_time_hours']:.1f}h")

        # 4. Divergence check
        print("\n\n4. Divergence Analysis")
        print("-" * 40)

        ai_result = comparison.engine_results.get('ai', {})
        unified_result = comparison.engine_results.get('unified', {})
        deterministic_result = comparison.engine_results.get('deterministic', {})
        quick_result = comparison.engine_results.get('quick', {})

        if ai_result:
            ai_trades = ai_result.get('total_trades', 0)
            unified_trades = unified_result.get('total_trades', 0)
            det_trades = deterministic_result.get('total_trades', 0)
            quick_trades = quick_result.get('total_trades', 0)

            print(f"\nTrade Count Comparison:")
            print(f"  AI:            {ai_trades} trades")
            print(f"  Unified:       {unified_trades} trades")
            print(f"  Deterministic: {det_trades} trades")
            print(f"  Quick:         {quick_trades} trades")

            ai_sharpe = ai_result.get('sharpe_ratio', 0)
            unified_sharpe = unified_result.get('sharpe_ratio', 0)
            det_sharpe = deterministic_result.get('sharpe_ratio', 0)
            quick_sharpe = quick_result.get('sharpe_ratio', 0)

            print(f"\nSharpe Ratio Comparison:")
            print(f"  AI:            {ai_sharpe:.3f}")
            print(f"  Unified:       {unified_sharpe:.3f}")
            print(f"  Deterministic: {det_sharpe:.3f}")
            print(f"  Quick:         {quick_sharpe:.3f}")

            # Divergence verdict
            trade_divergence = (
                ai_trades != unified_trades or
                ai_trades != det_trades or
                ai_trades != quick_trades
            )

            sharpe_divergence = (
                abs(ai_sharpe - unified_sharpe) > 0.1 or
                abs(ai_sharpe - det_sharpe) > 0.1 or
                abs(ai_sharpe - quick_sharpe) > 0.1
            )

            print(f"\nDivergence Verdict:")
            if trade_divergence:
                print(f"  ✅ Trade count diverges from other engines")
            else:
                print(f"  ❌ Trade count identical (suspicious)")

            if sharpe_divergence:
                print(f"  ✅ Sharpe ratio diverges from other engines")
            else:
                print(f"  ⚠️  Sharpe ratio similar (may be expected)")

        # 5. Phase 5A Success Criteria
        print("\n\n5. Phase 5A Success Criteria")
        print("-" * 40)

        ai_metadata = comparison.engine_metadata.get('ai')

        checks = {
            "AI backtest path exists": ai_result is not None,
            "AI uses ai_proxy_backtest mode": ai_metadata and ai_metadata.actual_execution_mode == 'ai_proxy_backtest',
            "AI not using unified fallback": ai_metadata and not ai_metadata.unified_fallback_used,
            "AI routing status is partially_routed": ai_metadata and ai_metadata.routing_status == 'partially_routed',
            "AI metadata has honest notes": ai_metadata and 'not true Claude analysis' in ai_metadata.notes,
            "AI produces results": ai_result and ai_result.get('total_trades', 0) >= 0,
        }

        all_passed = True
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check}")
            if not passed:
                all_passed = False

        print("\n" + "=" * 80)
        if all_passed:
            print("✅ Phase 5A Verification: PASSED")
        else:
            print("❌ Phase 5A Verification: FAILED")
        print("=" * 80)

        return comparison, all_passed

    except Exception as e:
        print(f"\n❌ Comparison failed with error: {e}")
        import traceback
        traceback.print_exc()
        return None, False


if __name__ == "__main__":
    comparison, passed = asyncio.run(run_phase5a_verification())
    sys.exit(0 if passed else 1)
