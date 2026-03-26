#!/usr/bin/env python3
"""
Backtest Variant Comparison - 2026 Enhancements
=================================================
Compares 3 variants over 90 days:
1. Current (VWAP but no uptrend fix/trailing/sentiment)
2. Full new stack (all enhancements)
3. Strict uptrend only (HIGH flow + imbalance >0.45)

Expected outcomes:
- Uptrend P&L flips positive
- PF moves toward 1.55-1.75
- Sharpe stays >2.0 or improves
- DD remains <6%
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('VariantComparison')

from app.services.smartflow_backtest import SmartFlowBacktester, BacktestConfig
from datetime import datetime
import json


async def run_variant_backtest(name: str, config: BacktestConfig, instruments: list, data_cache: dict = None) -> dict:
    """Run backtest for a single variant."""
    print(f"\n{'='*60}")
    print(f"  VARIANT: {name}")
    print(f"{'='*60}")

    all_results = {}
    combined_pnl = 0.0
    regime_pnl_combined = {}

    for ticker in instruments:
        print(f"\n  Testing {ticker}...")
        bt = SmartFlowBacktester(config)

        try:
            # Pass cached data to run_backtest
            cached = data_cache.get(ticker) if data_cache else None
            metrics = await bt.run_backtest(ticker, days=90, cached_data=cached)

            if metrics:
                all_results[ticker] = {
                    'total_trades': metrics.total_trades,
                    'win_rate': metrics.win_rate,
                    'net_profit': metrics.net_profit,
                    'sharpe': metrics.sharpe_ratio,
                    'max_dd': metrics.max_drawdown_pct,
                    'profit_factor': metrics.profit_factor,
                    'regime_pnl': metrics.regime_pnl,
                    'regime_win_rates': metrics.regime_win_rates,
                }
                combined_pnl += metrics.net_profit

                # Aggregate regime P&L
                for regime, pnl in metrics.regime_pnl.items():
                    regime_pnl_combined[regime] = regime_pnl_combined.get(regime, 0) + pnl

                print(f"    {ticker}: {metrics.total_trades} trades, "
                      f"{metrics.win_rate:.1f}% WR, ${metrics.net_profit:.2f}, "
                      f"PF={metrics.profit_factor:.2f}, Sharpe={metrics.sharpe_ratio:.2f}")
        except Exception as e:
            logger.error(f"Error testing {ticker}: {e}")

    # Calculate combined metrics
    total_trades = sum(r.get('total_trades', 0) for r in all_results.values())
    avg_win_rate = sum(r.get('win_rate', 0) for r in all_results.values()) / len(all_results) if all_results else 0
    avg_sharpe = sum(r.get('sharpe', 0) for r in all_results.values()) / len(all_results) if all_results else 0
    avg_pf = sum(r.get('profit_factor', 0) for r in all_results.values()) / len(all_results) if all_results else 0
    max_dd = max(r.get('max_dd', 0) for r in all_results.values()) if all_results else 0

    return {
        'name': name,
        'total_trades': total_trades,
        'avg_win_rate': avg_win_rate,
        'combined_pnl': combined_pnl,
        'avg_sharpe': avg_sharpe,
        'avg_profit_factor': avg_pf,
        'max_drawdown': max_dd,
        'regime_pnl': regime_pnl_combined,
        'uptrend_pnl': regime_pnl_combined.get('trending_up', 0),
        'per_instrument': all_results,
    }


async def prefetch_data(instruments: list) -> dict:
    """Pre-fetch data for all instruments with delays to avoid rate limiting."""
    import time
    from datetime import timedelta

    data_cache = {}
    base_config = BacktestConfig(initial_capital=25000.0)

    print("=" * 70)
    print("  PRE-FETCHING DATA (with delays to avoid rate limiting)")
    print("=" * 70)

    for ticker in instruments:
        print(f"\n  Fetching {ticker}...")
        bt = SmartFlowBacktester(base_config)

        # Fetch data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        try:
            df = await bt.fetch_data(ticker, start_date, end_date, "1h")
            if df is not None and len(df) > 100:
                data_cache[ticker] = df
                print(f"    Cached {len(df)} bars for {ticker}")
            else:
                print(f"    No data for {ticker}, will use synthetic")
        except Exception as e:
            print(f"    Error fetching {ticker}: {e}")

        # Delay to avoid rate limiting
        time.sleep(2)

    return data_cache


async def run_comparison():
    """Run all 3 variant backtests and compare."""
    instruments = ['MES', 'MNQ', 'NQ']

    print("=" * 70)
    print("  SMARTFLOW 2026 - VARIANT COMPARISON BACKTEST")
    print("  90-Day Period | MES, MNQ, NQ")
    print("=" * 70)

    # Pre-fetch data with delays
    data_cache = await prefetch_data(instruments)

    results = []

    # ========================================
    # VARIANT 1: Current (VWAP, no new features)
    # ========================================
    config_current = BacktestConfig(
        initial_capital=25000.0,
        position_size_pct=2.0,
        commission_per_trade=2.50,
        base_slippage_ticks=2.0,
        max_positions=3,
        max_daily_loss_pct=3.0,
        use_atr_stops=True,
        atr_stop_mult=1.5,
        atr_target_mult=3.0,
        min_ensemble_prob=0.62,
        min_signal_strength=50.0,
        use_flow_filter=True,
        require_flow_confirmation=True,
        flow_prob_boost=True,
        # NEW FEATURES DISABLED
        uptrend_tightening=False,
        trailing_vwap_ema=False,
        news_sentiment_enabled=False,
        wf_train_days=60,
        wf_test_days=20,
        wf_folds=3,
        mc_simulations=500,
    )

    result_current = await run_variant_backtest("Current (VWAP only)", config_current, instruments, data_cache)
    results.append(result_current)

    # ========================================
    # VARIANT 2: Full New Stack (all enhancements)
    # ========================================
    config_full = BacktestConfig(
        initial_capital=25000.0,
        position_size_pct=2.0,
        commission_per_trade=2.50,
        base_slippage_ticks=2.0,
        max_positions=3,
        max_daily_loss_pct=3.0,
        use_atr_stops=True,
        atr_stop_mult=1.5,
        atr_target_mult=3.0,
        min_ensemble_prob=0.62,
        min_signal_strength=50.0,
        use_flow_filter=True,
        require_flow_confirmation=True,
        flow_prob_boost=True,
        # NEW FEATURES ENABLED
        uptrend_tightening=True,
        uptrend_min_prob=0.66,
        uptrend_flow_require='HIGH',
        uptrend_imbalance_min=0.45,
        trailing_vwap_ema=True,
        trailing_to_vwap=True,
        trailing_to_ema21=True,
        trailing_vwap_buffer_pct=0.1,
        trailing_partial_at_3x=True,
        trailing_partial_pct=50.0,
        news_sentiment_enabled=True,
        news_boost_min=0.08,
        news_boost_max=0.12,
        news_sentiment_threshold=0.5,
        news_flow_require='MEDIUM',
        wf_train_days=60,
        wf_test_days=20,
        wf_folds=3,
        mc_simulations=500,
    )

    result_full = await run_variant_backtest("Full New Stack", config_full, instruments, data_cache)
    results.append(result_full)

    # ========================================
    # VARIANT 3: Strict Uptrend Only
    # ========================================
    config_uptrend = BacktestConfig(
        initial_capital=25000.0,
        position_size_pct=2.0,
        commission_per_trade=2.50,
        base_slippage_ticks=2.0,
        max_positions=3,
        max_daily_loss_pct=3.0,
        use_atr_stops=True,
        atr_stop_mult=1.5,
        atr_target_mult=3.0,
        min_ensemble_prob=0.62,
        min_signal_strength=50.0,
        use_flow_filter=True,
        require_flow_confirmation=True,
        flow_prob_boost=True,
        # ONLY UPTREND TIGHTENING ENABLED
        uptrend_tightening=True,
        uptrend_min_prob=0.66,
        uptrend_flow_require='HIGH',
        uptrend_imbalance_min=0.45,
        trailing_vwap_ema=False,
        news_sentiment_enabled=False,
        wf_train_days=60,
        wf_test_days=20,
        wf_folds=3,
        mc_simulations=500,
    )

    result_uptrend = await run_variant_backtest("Strict Uptrend Only", config_uptrend, instruments, data_cache)
    results.append(result_uptrend)

    # ========================================
    # COMPARISON SUMMARY
    # ========================================
    print("\n" + "=" * 70)
    print("  COMPARISON RESULTS")
    print("=" * 70)

    print(f"\n{'Variant':<25} {'Trades':>8} {'WR%':>8} {'P&L':>12} {'PF':>8} {'Sharpe':>8} {'DD%':>8} {'Uptrend$':>12}")
    print("-" * 100)

    for r in results:
        print(f"{r['name']:<25} {r['total_trades']:>8} {r['avg_win_rate']:>7.1f}% "
              f"${r['combined_pnl']:>10.2f} {r['avg_profit_factor']:>7.2f} "
              f"{r['avg_sharpe']:>7.2f} {r['max_drawdown']:>7.2f}% "
              f"${r['uptrend_pnl']:>10.2f}")

    # Calculate improvements
    print("\n" + "-" * 70)
    print("  IMPROVEMENTS vs CURRENT")
    print("-" * 70)

    baseline = results[0]
    for r in results[1:]:
        wr_delta = r['avg_win_rate'] - baseline['avg_win_rate']
        pf_delta = r['avg_profit_factor'] - baseline['avg_profit_factor']
        sharpe_delta = r['avg_sharpe'] - baseline['avg_sharpe']
        uptrend_delta = r['uptrend_pnl'] - baseline['uptrend_pnl']

        print(f"\n{r['name']}:")
        print(f"  Win Rate:     {'+' if wr_delta >= 0 else ''}{wr_delta:.1f}%")
        print(f"  Profit Factor: {'+' if pf_delta >= 0 else ''}{pf_delta:.2f}")
        print(f"  Sharpe:       {'+' if sharpe_delta >= 0 else ''}{sharpe_delta:.2f}")
        print(f"  Uptrend P&L:  {'+' if uptrend_delta >= 0 else ''}${uptrend_delta:.2f}")

    # Target validation
    print("\n" + "=" * 70)
    print("  TARGET VALIDATION")
    print("=" * 70)

    full_stack = results[1]
    targets = {
        'Uptrend P&L Positive': full_stack['uptrend_pnl'] > 0,
        'PF >= 1.55': full_stack['avg_profit_factor'] >= 1.55,
        'Sharpe >= 2.0': full_stack['avg_sharpe'] >= 2.0,
        'DD < 6%': full_stack['max_drawdown'] < 6.0,
    }

    for target, passed in targets.items():
        status = "PASS" if passed else "MISS"
        print(f"  [{status}] {target}")

    all_passed = all(targets.values())
    print(f"\n  Overall: {'ALL TARGETS MET' if all_passed else 'SOME TARGETS MISSED'}")

    # Export results
    output = {
        'timestamp': datetime.now().isoformat(),
        'instruments': instruments,
        'period_days': 90,
        'results': results,
        'targets_met': targets,
        'all_passed': all_passed,
    }

    with open('backtest_variant_comparison.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n  Results exported to backtest_variant_comparison.json")

    return output


if __name__ == "__main__":
    result = asyncio.run(run_comparison())
