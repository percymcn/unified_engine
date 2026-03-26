#!/usr/bin/env python3
"""
Final 2%/2% Pyramid Test - All Tickers
Find the best performers for live trading.
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
    print("FINAL 2%/2% PYRAMID TEST - ALL TICKERS")
    print("=" * 90)

    # All tickers
    all_tickers = ['US30', 'NAS100', 'SPX500', 'MES', 'MNQ', 'MYM']

    # Pyramid configurations to test
    configs = [
        ("Simple 2%/2%", False, False, 2),
        ("Pyramid Longs (2 pos)", True, True, 2),
        ("Pyramid Longs (3 pos)", True, True, 3),
        ("Pyramid Longs (4 pos)", True, True, 4),
        ("Pyramid Both (2 pos)", True, False, 2),
        ("Pyramid Both (3 pos)", True, False, 3),
    ]

    all_results = {}

    for ticker in all_tickers:
        print(f"\n{'='*90}")
        print(f"  {ticker}")
        print(f"{'='*90}")
        print(f"{'Config':<25} {'Trades':>6} {'WR':>7} {'PF':>7} {'Sharpe':>8} {'P&L':>14} {'MaxDD':>8}")
        print("-" * 90)

        all_results[ticker] = {}

        for name, use_pyramid, longs_only, max_pos in configs:
            config = BacktestConfig(
                use_atr_stops=False,
                use_pct_stops=True,
                pct_stop=2.0,
                pct_target=2.0,
                min_ensemble_prob=0.55,
                use_pyramid=use_pyramid,
                pyramid_longs_only=longs_only,
                pyramid_first_rr=1.0,  # 2%/2% = 1:1
                pyramid_addon_rr=1.0,
                pyramid_max_positions=max_pos,
                pyramid_addon_trigger=1.0,  # Add when 1R in profit
                use_runners=False,
            )

            bt = SmartFlowBacktester(config)
            results = await bt.run_backtest(ticker, days=90)

            print(f"{name:<25} {results.total_trades:>6} {results.win_rate:>6.1f}% "
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

    # Rank all ticker/config combinations
    print("\n" + "=" * 90)
    print("RANKING: ALL TICKER/CONFIG COMBINATIONS BY SHARPE")
    print("=" * 90)

    rankings = []
    for ticker, results in all_results.items():
        for config_name, metrics in results.items():
            if metrics['trades'] > 20:  # Minimum trades filter
                rankings.append({
                    'ticker': ticker,
                    'config': config_name,
                    **metrics
                })

    # Sort by Sharpe
    rankings.sort(key=lambda x: x['sharpe'], reverse=True)

    print(f"\n{'Rank':<5} {'Ticker':<10} {'Config':<25} {'Sharpe':>8} {'WR':>7} {'PF':>7} {'P&L':>14}")
    print("-" * 90)

    for i, r in enumerate(rankings[:15], 1):
        print(f"{i:<5} {r['ticker']:<10} {r['config']:<25} {r['sharpe']:>7.2f} "
              f"{r['win_rate']:>6.1f}% {r['pf']:>6.2f} ${r['pnl']:>12,.0f}")

    # Best config per ticker
    print("\n" + "=" * 90)
    print("BEST CONFIG PER TICKER")
    print("=" * 90)

    best_per_ticker = {}
    for ticker in all_tickers:
        best = max(all_results[ticker].items(),
                   key=lambda x: x[1]['sharpe'] if x[1]['trades'] > 20 else -999)
        best_per_ticker[ticker] = (best[0], best[1])
        r = best[1]
        print(f"{ticker:<10} {best[0]:<25} Sharpe={r['sharpe']:.2f}, WR={r['win_rate']:.1f}%, "
              f"PF={r['pf']:.2f}, P&L=${r['pnl']:,.0f}")

    # Summary for forward testing
    print("\n" + "=" * 90)
    print("RECOMMENDED FOR FORWARD TESTING")
    print("=" * 90)

    # Filter: Sharpe > 3.0, WR > 50%, PF > 1.4
    recommended = []
    for r in rankings:
        if r['sharpe'] > 3.0 and r['win_rate'] > 50 and r['pf'] > 1.4:
            recommended.append(r)

    if recommended:
        print("\nTickers meeting criteria (Sharpe>3.0, WR>50%, PF>1.4):\n")
        for r in recommended:
            print(f"  {r['ticker']:<10} {r['config']:<25}")
            print(f"             Sharpe={r['sharpe']:.2f}, WR={r['win_rate']:.1f}%, "
                  f"PF={r['pf']:.2f}, MaxDD={r['max_dd']:.1f}%")
    else:
        print("\nNo configurations met all criteria. Top 3 by Sharpe:")
        for r in rankings[:3]:
            print(f"  {r['ticker']:<10} {r['config']:<25} Sharpe={r['sharpe']:.2f}")

    return best_per_ticker, rankings


if __name__ == "__main__":
    asyncio.run(run_test())
