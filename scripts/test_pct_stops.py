#!/usr/bin/env python3
"""
Test percentage-based stops vs ATR-based stops.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app.services.smartflow_backtest import SmartFlowBacktester, BacktestConfig


async def run_test():
    print("\n" + "=" * 70)
    print("PERCENTAGE-BASED STOPS - FINDING OPTIMAL LEVELS")
    print("=" * 70)

    # Test different percentage levels for MES
    print("\n--- MES: Testing Different Percentage Levels ---")
    print("Price ~$5000, so:")
    print("  0.5% = $25 stop, 1% = $50, 1.5% = $75, 2% = $100, 2.5% = $125")

    pct_levels = [
        (0.5, 0.5),   # 1:1 tight
        (0.5, 1.0),   # 1:2 very tight
        (1.0, 1.0),   # 1:1
        (1.0, 2.0),   # 1:2
        (1.5, 1.5),   # 1:1
        (1.5, 3.0),   # 1:2
        (2.0, 2.0),   # 1:1
        (2.5, 2.5),   # 1:1 (requested)
    ]

    print(f"\n{'Config':<20} {'Trades':>6} {'WR':>8} {'PF':>8} {'Sharpe':>8} {'P&L':>12}")
    print("-" * 70)

    best_sharpe = -999
    best_config = None

    for pct_sl, pct_tp in pct_levels:
        config = BacktestConfig(
            use_atr_stops=False,
            use_pct_stops=True,
            pct_stop=pct_sl,
            pct_target=pct_tp,
            min_ensemble_prob=0.55,
            use_pyramid=False,
            use_runners=False,
        )

        bt = SmartFlowBacktester(config)
        results = await bt.run_backtest('MES', days=90)

        rr = pct_tp / pct_sl
        config_name = f"{pct_sl}%/{pct_tp}% ({rr:.1f}:1)"
        print(f"{config_name:<20} {results.total_trades:>6} {results.win_rate:>7.1f}% "
              f"{results.profit_factor:>7.2f} {results.sharpe_ratio:>7.2f} ${results.net_profit:>10,.2f}")

        if results.sharpe_ratio > best_sharpe and results.total_trades > 20:
            best_sharpe = results.sharpe_ratio
            best_config = (pct_sl, pct_tp)

    # Also test ATR baseline
    print("\n--- ATR Baseline for Comparison ---")
    config_atr = BacktestConfig(
        use_atr_stops=True,
        use_pct_stops=False,
        atr_stop_mult=1.5,
        atr_target_mult=3.0,
        min_ensemble_prob=0.55,
        use_pyramid=False,
        use_runners=False,
    )
    bt_atr = SmartFlowBacktester(config_atr)
    results_atr = await bt_atr.run_backtest('MES', days=90)
    print(f"ATR 1.5x/3.0x         {results_atr.total_trades:>6} {results_atr.win_rate:>7.1f}% "
          f"{results_atr.profit_factor:>7.2f} {results_atr.sharpe_ratio:>7.2f} ${results_atr.net_profit:>10,.2f}")

    # Test best config on MNQ which showed promise
    print("\n--- MNQ: Testing Best Percentage Levels ---")
    for pct_sl, pct_tp in [(2.5, 2.5), (2.0, 2.0), (1.5, 1.5), (2.0, 4.0)]:
        config = BacktestConfig(
            use_atr_stops=False,
            use_pct_stops=True,
            pct_stop=pct_sl,
            pct_target=pct_tp,
            min_ensemble_prob=0.55,
            use_pyramid=False,
            use_runners=False,
        )

        bt = SmartFlowBacktester(config)
        results = await bt.run_backtest('MNQ', days=90)

        rr = pct_tp / pct_sl
        config_name = f"{pct_sl}%/{pct_tp}% ({rr:.1f}:1)"
        print(f"{config_name:<20} {results.total_trades:>6} {results.win_rate:>7.1f}% "
              f"{results.profit_factor:>7.2f} {results.sharpe_ratio:>7.2f} ${results.net_profit:>10,.2f}")

    # Summary
    print("\n" + "=" * 70)
    print("FINDINGS:")
    print("=" * 70)
    if best_config:
        print(f"\nBest MES config: {best_config[0]}% SL / {best_config[1]}% TP (Sharpe: {best_sharpe:.2f})")
    print("\nNote: MNQ with 2.5%/2.5% showed strong performance (Sharpe=2.11)")


if __name__ == "__main__":
    asyncio.run(run_test())
