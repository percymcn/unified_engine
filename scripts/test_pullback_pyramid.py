#!/usr/bin/env python3
"""
Test Pullback-Based Pyramid Strategy
=====================================

Compares:
- Original: Add at 1R profit
- Pullback: Wait for pullback + trend continuation before adding

Tests both longs and shorts with 3-4 max positions.
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
    print("\n" + "=" * 90)
    print("PULLBACK PYRAMID TEST - 2%/2% STOPS")
    print("=" * 90)
    print("\nPullback Strategy:")
    print("  - Wait for price to pull back 50% of the move")
    print("  - Then wait for 2 bars of trend continuation")
    print("  - Add position on continuation (better entry price)")
    print("  - Works for both LONGS and SHORTS")

    all_tickers = ['US30', 'NAS100', 'SPX500', 'MES', 'MNQ', 'MYM']

    # Test configurations
    configs = [
        # (name, use_pullback, longs_only, max_pos, pullback_pct, continuation_bars)
        ("Original 1R (2pos)", False, True, 2, 0, 0),
        ("Original 1R (3pos)", False, True, 3, 0, 0),
        ("Original 1R Both (3pos)", False, False, 3, 0, 0),
        ("Pullback 50% (3pos Longs)", True, True, 3, 0.5, 2),
        ("Pullback 50% (4pos Longs)", True, True, 4, 0.5, 2),
        ("Pullback 50% (3pos Both)", True, False, 3, 0.5, 2),
        ("Pullback 50% (4pos Both)", True, False, 4, 0.5, 2),
        ("Pullback 38% (3pos Both)", True, False, 3, 0.38, 2),
        ("Pullback 62% (3pos Both)", True, False, 3, 0.62, 2),
    ]

    all_results = {}

    for ticker in all_tickers:
        print(f"\n{'='*90}")
        print(f"  {ticker}")
        print(f"{'='*90}")
        print(f"{'Config':<28} {'Trades':>6} {'WR':>7} {'PF':>7} {'Sharpe':>8} {'P&L':>14} {'MaxDD':>8}")
        print("-" * 90)

        all_results[ticker] = {}

        for name, use_pullback, longs_only, max_pos, pb_pct, cont_bars in configs:
            config = BacktestConfig(
                use_atr_stops=False,
                use_pct_stops=True,
                pct_stop=2.0,
                pct_target=2.0,
                min_ensemble_prob=0.55,
                use_pyramid=True,
                pyramid_longs_only=longs_only,
                pyramid_max_positions=max_pos,
                pyramid_first_rr=1.0,
                pyramid_addon_rr=1.0,
                pyramid_addon_trigger=1.0,
                pyramid_use_pullback=use_pullback,
                pyramid_pullback_pct=pb_pct,
                pyramid_continuation_bars=cont_bars,
                use_runners=False,
            )

            bt = SmartFlowBacktester(config)
            results = await bt.run_backtest(ticker, days=90)

            print(f"{name:<28} {results.total_trades:>6} {results.win_rate:>6.1f}% "
                  f"{results.profit_factor:>6.2f} {results.sharpe_ratio:>7.2f} "
                  f"${results.net_profit:>12,.0f} {results.max_drawdown_pct:>7.1f}%")

            all_results[ticker][name] = {
                'trades': results.total_trades,
                'win_rate': results.win_rate,
                'pf': results.profit_factor,
                'sharpe': results.sharpe_ratio,
                'pnl': results.net_profit,
                'max_dd': results.max_drawdown_pct
            }

    # Rankings
    print("\n" + "=" * 90)
    print("TOP 15 CONFIGURATIONS BY SHARPE")
    print("=" * 90)

    rankings = []
    for ticker, results in all_results.items():
        for config_name, metrics in results.items():
            if metrics['trades'] > 20:
                rankings.append({
                    'ticker': ticker,
                    'config': config_name,
                    **metrics
                })

    rankings.sort(key=lambda x: x['sharpe'], reverse=True)

    print(f"\n{'Rank':<5} {'Ticker':<10} {'Config':<28} {'Sharpe':>8} {'WR':>7} {'PF':>7} {'P&L':>12}")
    print("-" * 90)

    for i, r in enumerate(rankings[:15], 1):
        print(f"{i:<5} {r['ticker']:<10} {r['config']:<28} {r['sharpe']:>7.2f} "
              f"{r['win_rate']:>6.1f}% {r['pf']:>6.2f} ${r['pnl']:>10,.0f}")

    # Compare original vs pullback
    print("\n" + "=" * 90)
    print("ORIGINAL vs PULLBACK COMPARISON (3 positions)")
    print("=" * 90)

    for ticker in all_tickers:
        orig = all_results[ticker].get("Original 1R Both (3pos)", {})
        pull = all_results[ticker].get("Pullback 50% (3pos Both)", {})

        if orig and pull:
            orig_sharpe = orig.get('sharpe', 0)
            pull_sharpe = pull.get('sharpe', 0)
            winner = "PULLBACK" if pull_sharpe > orig_sharpe else "ORIGINAL"
            diff = pull_sharpe - orig_sharpe

            print(f"{ticker:<10} Original={orig_sharpe:>6.2f}  Pullback={pull_sharpe:>6.2f}  "
                  f"Diff={diff:>+6.2f}  Winner={winner}")

    # Best per ticker
    print("\n" + "=" * 90)
    print("BEST CONFIG PER TICKER")
    print("=" * 90)

    for ticker in all_tickers:
        best = max(all_results[ticker].items(),
                   key=lambda x: x[1]['sharpe'] if x[1]['trades'] > 20 else -999)
        r = best[1]
        print(f"{ticker:<10} {best[0]:<28} Sharpe={r['sharpe']:.2f}, WR={r['win_rate']:.1f}%, P&L=${r['pnl']:,.0f}")


if __name__ == "__main__":
    asyncio.run(run_test())
