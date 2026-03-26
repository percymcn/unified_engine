#!/usr/bin/env python3
"""
Test pyramid strategy with percentage-based stops on CFD tickers.
US30 (~40000), NAS100 (~18000), SPX500 (~5000)
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
    print("\n" + "=" * 80)
    print("PYRAMID STRATEGY TEST - PERCENTAGE-BASED STOPS")
    print("=" * 80)

    tickers = ['US30', 'NAS100', 'SPX500']
    print("\nTickers: US30 (~$40000), NAS100 (~$18000), SPX500 (~$5000)")

    # Test configurations
    configs = [
        # (name, pct_stop, pct_target, use_pyramid, pyramid_longs_only)
        ("Simple 2.0%/2.0%", 2.0, 2.0, False, False),
        ("Simple 2.0%/3.0%", 2.0, 3.0, False, False),
        ("Pyramid 2.0%/2.0% (Longs)", 2.0, 2.0, True, True),
        ("Pyramid 2.0%/3.0% (Longs)", 2.0, 3.0, True, True),
        ("Pyramid 2.0%/2.0% (Both)", 2.0, 2.0, True, False),
        ("Pyramid 2.0%/3.0% (Both)", 2.0, 3.0, True, False),
    ]

    # Store results for summary
    all_results = {}

    for ticker in tickers:
        print(f"\n{'='*80}")
        print(f"TICKER: {ticker}")
        print(f"{'='*80}")
        print(f"\n{'Config':<28} {'Trades':>6} {'WR':>7} {'PF':>7} {'Sharpe':>7} {'P&L':>12} {'MaxDD':>7}")
        print("-" * 80)

        all_results[ticker] = {}

        for name, pct_sl, pct_tp, use_pyramid, longs_only in configs:
            config = BacktestConfig(
                use_atr_stops=False,
                use_pct_stops=True,
                pct_stop=pct_sl,
                pct_target=pct_tp,
                min_ensemble_prob=0.55,
                use_pyramid=use_pyramid,
                pyramid_longs_only=longs_only,
                pyramid_first_rr=pct_tp/pct_sl,  # Match the R:R
                pyramid_addon_rr=1.0,  # Add-ons at 1:1
                pyramid_max_positions=3,
                use_runners=False,
            )

            bt = SmartFlowBacktester(config)
            results = await bt.run_backtest(ticker, days=90)

            print(f"{name:<28} {results.total_trades:>6} {results.win_rate:>6.1f}% "
                  f"{results.profit_factor:>6.2f} {results.sharpe_ratio:>6.2f} "
                  f"${results.net_profit:>10,.0f} {results.max_drawdown_pct:>6.1f}%")

            all_results[ticker][name] = {
                'trades': results.total_trades,
                'win_rate': results.win_rate,
                'pf': results.profit_factor,
                'sharpe': results.sharpe_ratio,
                'pnl': results.net_profit,
                'max_dd': results.max_drawdown_pct
            }

    # Summary - best configs
    print("\n" + "=" * 80)
    print("BEST CONFIGURATIONS BY TICKER")
    print("=" * 80)

    for ticker in tickers:
        best_name = max(all_results[ticker].items(),
                       key=lambda x: x[1]['sharpe'] if x[1]['trades'] > 20 else -999)
        r = best_name[1]
        print(f"\n{ticker}: {best_name[0]}")
        print(f"  Trades={r['trades']}, WR={r['win_rate']:.1f}%, PF={r['pf']:.2f}, "
              f"Sharpe={r['sharpe']:.2f}, P&L=${r['pnl']:,.0f}")

    # Overall comparison
    print("\n" + "=" * 80)
    print("PYRAMID vs SIMPLE COMPARISON")
    print("=" * 80)

    for ticker in tickers:
        simple = all_results[ticker].get("Simple 2.0%/2.0%", {})
        pyramid = all_results[ticker].get("Pyramid 2.0%/2.0% (Longs)", {})

        if simple and pyramid:
            print(f"\n{ticker}:")
            print(f"  Simple:  Sharpe={simple.get('sharpe', 0):.2f}, P&L=${simple.get('pnl', 0):,.0f}")
            print(f"  Pyramid: Sharpe={pyramid.get('sharpe', 0):.2f}, P&L=${pyramid.get('pnl', 0):,.0f}")
            diff = pyramid.get('pnl', 0) - simple.get('pnl', 0)
            print(f"  Pyramid advantage: ${diff:,.0f}")


if __name__ == "__main__":
    asyncio.run(run_test())
