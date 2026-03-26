#!/usr/bin/env python3
"""
Configuration Comparison Backtest
==================================
Tests multiple configurations to find optimal settings:
1. Current: 62% gate, MEDIUM+ flow, 1.5x/3x ATR
2. Stricter: 65% gate, HIGH+ flow only
3. User's actual: 1:3 R:R (risk 1 to make 3)
4. Uptrend fix: Higher target in trending_up
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('ConfigComparison')

from app.services.smartflow_backtest import SmartFlowBacktester, BacktestConfig
from datetime import datetime
import json

# Suppress verbose logs
logging.getLogger('app.services.smartflow_backtest').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)


async def run_single_backtest(name: str, config: BacktestConfig, ticker: str = 'MES', days: int = 90):
    """Run a single backtest and return metrics."""
    bt = SmartFlowBacktester(config)
    metrics = await bt.run_backtest(ticker, days=days)
    
    if not metrics:
        return None
    
    # Run Monte Carlo
    bt.run_monte_carlo()
    
    return {
        'name': name,
        'trades': metrics.total_trades,
        'win_rate': metrics.win_rate,
        'net_pnl': metrics.net_profit,
        'return_pct': metrics.total_return_pct,
        'sharpe': metrics.sharpe_ratio,
        'sortino': metrics.sortino_ratio,
        'max_dd': metrics.max_drawdown_pct,
        'profit_factor': metrics.profit_factor,
        'expectancy': metrics.expectancy,
        'avg_win': metrics.avg_win,
        'avg_loss': metrics.avg_loss,
        'regime_wr': metrics.regime_win_rates,
        'regime_pnl': metrics.regime_pnl,
        'mc_worst_dd': metrics.mc_worst_case_dd,
        'flow_confirmed_wr': metrics.flow_confirmed_win_rate,
        'trades_obj': bt.trades,
    }


async def run_comparison():
    """Run all configuration comparisons."""
    
    print("=" * 70)
    print("  SMARTFLOW CONFIGURATION COMPARISON BACKTEST")
    print("  Testing: 62% vs 65% gate, MEDIUM vs HIGH flow, R:R variants")
    print("=" * 70)
    
    # Define configurations
    configs = {
        # Current deployed config
        'A_CURRENT': BacktestConfig(
            initial_capital=25000.0,
            position_size_pct=2.0,
            commission_per_trade=2.50,
            base_slippage_ticks=2.0,
            min_ensemble_prob=0.62,  # Current: 62%
            min_signal_strength=50.0,
            use_flow_filter=True,
            require_flow_confirmation=True,  # MEDIUM+ flow
            flow_prob_boost=True,
            use_atr_stops=True,
            atr_stop_mult=1.5,
            atr_target_mult=3.0,  # 1:2 R:R
            mc_simulations=300,
        ),
        
        # Stricter: 65% gate, HIGH+ flow only
        'B_STRICT_65': BacktestConfig(
            initial_capital=25000.0,
            position_size_pct=2.0,
            commission_per_trade=2.50,
            base_slippage_ticks=2.0,
            min_ensemble_prob=0.65,  # RAISED to 65%
            min_signal_strength=55.0,  # Also raise signal strength
            use_flow_filter=True,
            require_flow_confirmation=True,
            flow_prob_boost=True,
            use_atr_stops=True,
            atr_stop_mult=1.5,
            atr_target_mult=3.0,
            mc_simulations=300,
        ),
        
        # User's actual R:R: 1:3 (risk 1 to make 3)
        'C_1TO3_RR': BacktestConfig(
            initial_capital=25000.0,
            position_size_pct=2.0,
            commission_per_trade=2.50,
            base_slippage_ticks=2.0,
            min_ensemble_prob=0.62,
            min_signal_strength=50.0,
            use_flow_filter=True,
            require_flow_confirmation=True,
            flow_prob_boost=True,
            use_atr_stops=True,
            atr_stop_mult=1.0,  # Tighter stop (1x ATR)
            atr_target_mult=3.0,  # 1:3 R:R
            mc_simulations=300,
        ),
        
        # Strict + 1:3 R:R combo
        'D_STRICT_1TO3': BacktestConfig(
            initial_capital=25000.0,
            position_size_pct=2.0,
            commission_per_trade=2.50,
            base_slippage_ticks=2.0,
            min_ensemble_prob=0.65,  # 65% gate
            min_signal_strength=55.0,
            use_flow_filter=True,
            require_flow_confirmation=True,
            flow_prob_boost=True,
            use_atr_stops=True,
            atr_stop_mult=1.0,  # Tighter stop
            atr_target_mult=3.0,  # 1:3 R:R
            mc_simulations=300,
        ),
        
        # Uptrend fix: Higher target in uptrends (4.5x)
        'E_UPTREND_FIX': BacktestConfig(
            initial_capital=25000.0,
            position_size_pct=2.0,
            commission_per_trade=2.50,
            base_slippage_ticks=2.0,
            min_ensemble_prob=0.65,
            min_signal_strength=55.0,
            use_flow_filter=True,
            require_flow_confirmation=True,
            flow_prob_boost=True,
            use_atr_stops=True,
            atr_stop_mult=1.0,
            atr_target_mult=4.5,  # HIGHER target for uptrend capture
            mc_simulations=300,
        ),
        
        # Aggressive: 64% gate, HIGH flow, 1:3 R:R
        'F_OPTIMAL': BacktestConfig(
            initial_capital=25000.0,
            position_size_pct=2.0,
            commission_per_trade=2.50,
            base_slippage_ticks=2.0,
            min_ensemble_prob=0.64,  # Sweet spot 64%
            min_signal_strength=52.0,
            use_flow_filter=True,
            require_flow_confirmation=True,
            flow_prob_boost=True,
            use_atr_stops=True,
            atr_stop_mult=1.0,
            atr_target_mult=3.0,  # 1:3 R:R
            mc_simulations=300,
        ),
    }
    
    results = {}
    
    for name, config in configs.items():
        print(f"\n{'='*50}")
        print(f"  Testing: {name}")
        print(f"  Gate: {config.min_ensemble_prob*100:.0f}%, Stop: {config.atr_stop_mult}x, Target: {config.atr_target_mult}x")
        print(f"{'='*50}")
        
        result = await run_single_backtest(name, config, 'MES', 90)
        
        if result:
            results[name] = result
            print(f"  Trades: {result['trades']}, WR: {result['win_rate']:.1f}%, PF: {result['profit_factor']:.2f}")
            print(f"  P&L: ${result['net_pnl']:.2f}, Sharpe: {result['sharpe']:.2f}, MaxDD: {result['max_dd']:.2f}%")
        else:
            print(f"  FAILED - No data")
    
    # Comparison table
    print("\n" + "=" * 90)
    print("  COMPARISON RESULTS")
    print("=" * 90)
    print(f"{'Config':<16} {'Trades':>7} {'WR%':>6} {'PF':>6} {'Sharpe':>7} {'MaxDD%':>7} {'P&L':>10} {'Expect':>8}")
    print("-" * 90)
    
    sorted_results = sorted(results.items(), key=lambda x: x[1]['profit_factor'], reverse=True)
    
    for name, r in sorted_results:
        print(f"{name:<16} {r['trades']:>7} {r['win_rate']:>5.1f}% {r['profit_factor']:>6.2f} {r['sharpe']:>7.2f} {r['max_dd']:>6.2f}% ${r['net_pnl']:>9.2f} ${r['expectancy']:>7.2f}")
    
    # Regime breakdown
    print("\n" + "=" * 90)
    print("  REGIME PERFORMANCE (Trending Up vs Down)")
    print("=" * 90)
    print(f"{'Config':<16} {'Up WR%':>8} {'Up P&L':>12} {'Down WR%':>8} {'Down P&L':>12}")
    print("-" * 90)
    
    for name, r in sorted_results:
        up_wr = r['regime_wr'].get('trending_up', 0)
        down_wr = r['regime_wr'].get('trending_down', 0)
        up_pnl = r['regime_pnl'].get('trending_up', 0)
        down_pnl = r['regime_pnl'].get('trending_down', 0)
        print(f"{name:<16} {up_wr:>7.1f}% ${up_pnl:>11.2f} {down_wr:>7.1f}% ${down_pnl:>11.2f}")
    
    # Best config recommendation
    print("\n" + "=" * 90)
    print("  RECOMMENDATION")
    print("=" * 90)
    
    best = sorted_results[0]
    print(f"\nBest Profit Factor: {best[0]}")
    print(f"  - PF: {best[1]['profit_factor']:.2f}")
    print(f"  - Win Rate: {best[1]['win_rate']:.1f}%")
    print(f"  - Sharpe: {best[1]['sharpe']:.2f}")
    print(f"  - Max DD: {best[1]['max_dd']:.2f}%")
    
    # Criteria check
    print("\n  Paper Trading Criteria Check:")
    for name, r in sorted_results[:3]:
        wr_pass = "✓" if r['win_rate'] >= 48 else "✗"
        pf_pass = "✓" if r['profit_factor'] >= 1.35 else "✗"
        sh_pass = "✓" if r['sharpe'] >= 1.2 else "✗"
        dd_pass = "✓" if r['max_dd'] <= 10 else "✗"
        print(f"  {name}: WR≥48%{wr_pass} PF≥1.35{pf_pass} Sharpe≥1.2{sh_pass} DD≤10%{dd_pass}")
    
    # Export
    output = {
        'timestamp': datetime.now().isoformat(),
        'results': {k: {kk: vv for kk, vv in v.items() if kk != 'trades_obj'} for k, v in results.items()},
        'best_config': best[0],
    }
    
    with open('config_comparison_results.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\nResults exported to config_comparison_results.json")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_comparison())
