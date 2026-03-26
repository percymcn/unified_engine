#!/usr/bin/env python3
"""
Test 1% SL / 2% TP across all tickers - CFDs and Futures.
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
    print("\n" + "=" * 85)
    print("1% SL / 2% TP TEST - ALL TICKERS (CFDs + Futures)")
    print("=" * 85)

    # All tickers to test
    tickers = {
        'CFDs': ['US30', 'NAS100', 'SPX500'],
        'Futures': ['MES', 'MNQ', 'MYM']
    }

    # Test configurations
    configs = [
        # (name, pct_stop, pct_target, use_pyramid, pyramid_longs_only)
        ("Simple 1%/2%", 1.0, 2.0, False, False),
        ("Simple 2%/2%", 2.0, 2.0, False, False),
        ("Pyramid 1%/2% (Longs)", 1.0, 2.0, True, True),
        ("Pyramid 2%/2% (Longs)", 2.0, 2.0, True, True),
        ("Pyramid 1%/2% (Both)", 1.0, 2.0, True, False),
    ]

    all_results = {}

    for category, ticker_list in tickers.items():
        print(f"\n{'='*85}")
        print(f"  {category.upper()}")
        print(f"{'='*85}")

        for ticker in ticker_list:
            print(f"\n--- {ticker} ---")
            print(f"{'Config':<25} {'Trades':>6} {'WR':>7} {'PF':>7} {'Sharpe':>7} {'P&L':>12} {'MaxDD':>7}")
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
                    pyramid_first_rr=pct_tp/pct_sl,
                    pyramid_addon_rr=1.0,
                    pyramid_max_positions=3,
                    use_runners=False,
                )

                bt = SmartFlowBacktester(config)
                results = await bt.run_backtest(ticker, days=90)

                print(f"{name:<25} {results.total_trades:>6} {results.win_rate:>6.1f}% "
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

    # Summary - best config per ticker
    print("\n" + "=" * 85)
    print("BEST CONFIGURATION BY TICKER")
    print("=" * 85)

    for ticker, results in all_results.items():
        best = max(results.items(), key=lambda x: x[1]['sharpe'] if x[1]['trades'] > 20 else -999)
        r = best[1]
        print(f"{ticker:<10} {best[0]:<25} Sharpe={r['sharpe']:.2f}, WR={r['win_rate']:.1f}%, P&L=${r['pnl']:,.0f}")

    # 1%/2% vs 2%/2% comparison
    print("\n" + "=" * 85)
    print("1%/2% vs 2%/2% COMPARISON (Simple)")
    print("=" * 85)
    print(f"{'Ticker':<10} {'1%/2% Sharpe':>12} {'1%/2% P&L':>12} {'2%/2% Sharpe':>12} {'2%/2% P&L':>12} {'Winner':>10}")
    print("-" * 70)

    for ticker, results in all_results.items():
        r1 = results.get("Simple 1%/2%", {})
        r2 = results.get("Simple 2%/2%", {})

        if r1 and r2:
            winner = "1%/2%" if r1.get('sharpe', 0) > r2.get('sharpe', 0) else "2%/2%"
            print(f"{ticker:<10} {r1.get('sharpe', 0):>11.2f} ${r1.get('pnl', 0):>10,.0f} "
                  f"{r2.get('sharpe', 0):>11.2f} ${r2.get('pnl', 0):>10,.0f} {winner:>10}")

    # Pyramid comparison
    print("\n" + "=" * 85)
    print("PYRAMID 1%/2% vs 2%/2% COMPARISON (Longs Only)")
    print("=" * 85)
    print(f"{'Ticker':<10} {'1%/2% Sharpe':>12} {'1%/2% P&L':>12} {'2%/2% Sharpe':>12} {'2%/2% P&L':>12} {'Winner':>10}")
    print("-" * 70)

    for ticker, results in all_results.items():
        r1 = results.get("Pyramid 1%/2% (Longs)", {})
        r2 = results.get("Pyramid 2%/2% (Longs)", {})

        if r1 and r2:
            winner = "1%/2%" if r1.get('sharpe', 0) > r2.get('sharpe', 0) else "2%/2%"
            print(f"{ticker:<10} {r1.get('sharpe', 0):>11.2f} ${r1.get('pnl', 0):>10,.0f} "
                  f"{r2.get('sharpe', 0):>11.2f} ${r2.get('pnl', 0):>10,.0f} {winner:>10}")


if __name__ == "__main__":
    asyncio.run(run_test())
