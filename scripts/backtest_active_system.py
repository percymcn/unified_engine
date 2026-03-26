#!/usr/bin/env python3
"""
Backtest Active System Configuration
=====================================
Tests the currently deployed SmartFlow configuration:
- Ensemble gate: 62%
- Flow confirmation: MEDIUM+ conviction
- Deterministic + Quick modes
- Instruments: MES, MNQ, NQ, US30, USDJPY, BTCUSD
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('ActiveBacktest')

from app.services.smartflow_backtest import SmartFlowBacktester, BacktestConfig
from datetime import datetime
import json


async def run_active_backtest():
    """Run backtest with active system configuration."""
    
    # Active system configuration
    config = BacktestConfig(
        # Capital
        initial_capital=25000.0,
        position_size_pct=2.0,
        
        # Costs (realistic)
        commission_per_trade=2.50,
        base_slippage_ticks=2.0,
        
        # Risk (active settings)
        max_positions=3,
        max_daily_loss_pct=3.0,
        use_atr_stops=True,
        atr_stop_mult=1.5,
        atr_target_mult=3.0,
        
        # ACTIVE: 62% ensemble gate
        min_ensemble_prob=0.62,
        min_signal_strength=50.0,
        
        # ACTIVE: Flow confirmation enabled
        use_flow_filter=True,
        require_flow_confirmation=True,  # Require MEDIUM+ flow
        flow_prob_boost=True,
        
        # Walk-forward settings
        wf_train_days=60,
        wf_test_days=20,
        wf_folds=3,
        
        # Monte Carlo
        mc_simulations=500,
    )
    
    # Active instruments from smartflow_service.py
    instruments = ['MES', 'MNQ', 'NQ']  # Start with futures that have good data
    
    print("=" * 60)
    print("  SMARTFLOW ACTIVE SYSTEM BACKTEST")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  - Ensemble Gate: {config.min_ensemble_prob * 100:.0f}%")
    print(f"  - Flow Confirmation: {config.require_flow_confirmation}")
    print(f"  - Initial Capital: ${config.initial_capital:,.0f}")
    print(f"  - Position Size: {config.position_size_pct}%")
    print(f"  - ATR Stop: {config.atr_stop_mult}x, Target: {config.atr_target_mult}x")
    print(f"\nInstruments: {', '.join(instruments)}")
    print("=" * 60)
    
    all_results = {}
    combined_trades = []
    combined_pnl = 0.0
    
    for ticker in instruments:
        print(f"\n{'='*40}")
        print(f"  BACKTESTING: {ticker}")
        print(f"{'='*40}")
        
        bt = SmartFlowBacktester(config)
        
        try:
            # Run 90-day backtest
            metrics = await bt.run_backtest(ticker, days=90)
            
            if metrics:
                all_results[ticker] = {
                    'total_trades': metrics.total_trades,
                    'win_rate': metrics.win_rate,
                    'net_profit': metrics.net_profit,
                    'sharpe': metrics.sharpe_ratio,
                    'max_dd': metrics.max_drawdown_pct,
                    'profit_factor': metrics.profit_factor,
                    'flow_confirmed_wr': metrics.flow_confirmed_win_rate,
                    'flow_unconfirmed_wr': metrics.flow_unconfirmed_win_rate,
                }
                combined_pnl += metrics.net_profit
                combined_trades.extend(bt.trades)
                
                print(f"\n{ticker} Results:")
                print(f"  Trades: {metrics.total_trades}")
                print(f"  Win Rate: {metrics.win_rate:.1f}%")
                print(f"  Net P&L: ${metrics.net_profit:.2f}")
                print(f"  Sharpe: {metrics.sharpe_ratio:.2f}")
                print(f"  Max DD: {metrics.max_drawdown_pct:.2f}%")
                print(f"  Profit Factor: {metrics.profit_factor:.2f}")
                print(f"  Flow Confirmed WR: {metrics.flow_confirmed_win_rate:.1f}%")
            else:
                print(f"  No metrics returned for {ticker}")
                
        except Exception as e:
            print(f"  Error backtesting {ticker}: {e}")
            logger.exception(f"Backtest error for {ticker}")
    
    # Summary
    print("\n" + "=" * 60)
    print("  COMBINED RESULTS")
    print("=" * 60)
    
    total_trades = sum(r.get('total_trades', 0) for r in all_results.values())
    avg_win_rate = sum(r.get('win_rate', 0) for r in all_results.values()) / len(all_results) if all_results else 0
    avg_sharpe = sum(r.get('sharpe', 0) for r in all_results.values()) / len(all_results) if all_results else 0
    
    print(f"\nTotal Trades: {total_trades}")
    print(f"Average Win Rate: {avg_win_rate:.1f}%")
    print(f"Combined Net P&L: ${combined_pnl:.2f}")
    print(f"Average Sharpe: {avg_sharpe:.2f}")
    
    # Per-instrument breakdown
    print(f"\nPer Instrument:")
    for ticker, r in all_results.items():
        print(f"  {ticker}: {r['total_trades']} trades, {r['win_rate']:.1f}% WR, ${r['net_profit']:.2f} P&L")
    
    # Export results
    output = {
        'timestamp': datetime.now().isoformat(),
        'config': {
            'ensemble_gate': config.min_ensemble_prob,
            'flow_confirmation': config.require_flow_confirmation,
            'initial_capital': config.initial_capital,
            'position_size_pct': config.position_size_pct,
        },
        'instruments': instruments,
        'results': all_results,
        'combined': {
            'total_trades': total_trades,
            'avg_win_rate': avg_win_rate,
            'combined_pnl': combined_pnl,
            'avg_sharpe': avg_sharpe,
        }
    }
    
    with open('backtest_active_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nResults exported to backtest_active_results.json")
    
    return output


if __name__ == "__main__":
    result = asyncio.run(run_active_backtest())
