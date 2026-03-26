#!/usr/bin/env python3
"""
Forward Test Runner for SmartFlow 2%/2% Pyramid Strategy
=========================================================

Run this script to start paper trading the optimized strategy.

Usage:
    python scripts/run_forward_test.py                    # Start with default tickers
    python scripts/run_forward_test.py --tickers MNQ MES  # Specific tickers
    python scripts/run_forward_test.py --status           # Check current status
    python scripts/run_forward_test.py --simulate         # Run simulation test
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app.services.forward_test import ForwardTester, ForwardTestConfig


def print_banner():
    print("\n" + "=" * 70)
    print("  SMARTFLOW FORWARD TEST - 2%/2% PULLBACK PYRAMID")
    print("=" * 70)
    print("\nOptimized Configuration:")
    print("  - Stop Loss: 2% of entry price")
    print("  - Take Profit: 2% of entry price")
    print("  - Pyramid: BOTH directions, max 3 positions")
    print("  - Add-on: Pullback 50% + 2 bars continuation")
    print("\nBacktest Results (Pullback vs Original):")
    print("  MNQ:    Sharpe=4.72 (+1.39), WR=56.6%, PF=2.03, P&L=$90K")
    print("  US30:   Sharpe=4.70 (+1.39), WR=56.6%, PF=2.03, P&L=$100K")
    print("  MES:    Sharpe=4.53 (+1.28), WR=56.6%, PF=1.98, P&L=$61K")
    print("  MYM:    Sharpe=4.54 (+1.32), WR=56.6%, PF=2.02, P&L=$51K")
    print("  NAS100: Sharpe=4.38 (+1.19), WR=56.6%, PF=2.01, P&L=$47K")
    print("=" * 70)


async def simulate_forward_test(tickers: list, num_signals: int = 20):
    """Run a simulation of the forward test using synthetic signals."""
    import random
    import numpy as np

    print("\n--- SIMULATION MODE (Pullback Pyramid) ---")
    print(f"Simulating {num_signals} trading signals across {tickers}...")
    print("Config: 2%/2%, Pullback 50%, 2 bars continuation, 3 max positions\n")

    tester = ForwardTester(ForwardTestConfig())
    session = tester.start_session(tickers)

    # Base prices
    base_prices = {
        'MNQ': 18000, 'MES': 5000, 'MYM': 40000,
        'US30': 40000, 'NAS100': 18000, 'SPX500': 5000
    }

    # Track price series for pullback simulation
    price_series = {t: base_prices.get(t, 5000) for t in tickers}

    # Simulate bar-by-bar price action
    for i in range(num_signals):
        ticker = random.choice(tickers)
        base = price_series[ticker]

        # Simulate OHLC bar
        change = random.uniform(-0.01, 0.015)  # Slight upward bias
        close = base * (1 + change)
        high = max(base, close) * (1 + random.uniform(0.001, 0.005))
        low = min(base, close) * (1 - random.uniform(0.001, 0.005))

        price_series[ticker] = close  # Update for next bar

        # Simulate regime and signals
        if change > 0.005:
            regime = 'trending_up'
        elif change < -0.005:
            regime = 'trending_down'
        else:
            regime = random.choice(['ranging', 'breakout'])

        ensemble_prob = random.uniform(0.45, 0.75)
        signal_strength = random.uniform(40, 75)

        # Check for entry (only if no position in this ticker)
        existing = [t for t in tester.session.open_trades.values() if t.ticker == ticker]
        if not existing:
            signal = tester.check_entry_signal(
                ticker=ticker,
                price=close,
                regime=regime,
                ensemble_prob=ensemble_prob,
                signal_strength=signal_strength
            )

            if signal:
                trade = tester.execute_entry(signal)
                print(f"  [{i}] ENTRY: {ticker} {signal['direction']} @ {close:.2f}")

        # Check for exits on all tickers
        for t in tickers:
            t_price = price_series[t]
            t_high = t_price * 1.003
            t_low = t_price * 0.997
            closed = tester.check_exits(t, t_high, t_low, t_price)
            for c in closed:
                result = "WIN" if c.pnl > 0 else "LOSS"
                print(f"  [{i}] EXIT: {c.ticker} {result} P&L=${c.pnl:.2f}")

        # Check for pyramid add-ons (pullback based)
        for t in tickers:
            t_close = price_series[t]
            t_high = t_close * (1 + random.uniform(0.001, 0.008))
            t_low = t_close * (1 - random.uniform(0.001, 0.008))

            addon = tester.check_pyramid_addon(
                ticker=t,
                high=t_high,
                low=t_low,
                close=t_close,
                regime=regime,
                ensemble_prob=ensemble_prob
            )
            if addon:
                trade = tester.execute_entry(addon)
                print(f"  [{i}] ADD-ON: {t} {addon['direction']} @ {t_close:.2f} (pullback entry)")

        await asyncio.sleep(0.02)  # Small delay

    # Final status
    status = tester.get_status()

    print("\n" + "=" * 70)
    print("SIMULATION RESULTS")
    print("=" * 70)
    print(f"\nSession ID: {status['session_id']}")
    print(f"Total Trades: {status['total_trades']}")
    print(f"Win Rate: {status['win_rate']:.1f}%")
    print(f"Total P&L: ${status['total_pnl']:.2f}")
    print(f"Capital: ${status['capital']:.2f}")
    print(f"Max Drawdown: {status['max_drawdown']:.1f}%")
    print(f"Open Positions: {status['open_positions']}")

    return status


def show_status():
    """Show current forward test status."""
    tester = ForwardTester()
    status = tester.get_status()

    print("\n" + "=" * 70)
    print("FORWARD TEST STATUS")
    print("=" * 70)

    if not status.get('active'):
        print("\nNo active session. Run with --simulate or start live.")
        return

    print(f"\nSession: {status['session_id']}")
    print(f"Started: {status['start_time']}")
    print(f"\nPerformance:")
    print(f"  Capital: ${status['capital']:,.2f}")
    print(f"  Total P&L: ${status['total_pnl']:,.2f}")
    print(f"  Total Trades: {status['total_trades']}")
    print(f"  Win Rate: {status['win_rate']:.1f}%")
    print(f"  Max Drawdown: {status['max_drawdown']:.1f}%")
    print(f"\nToday:")
    print(f"  Daily P&L: ${status['daily_pnl']:,.2f}")
    print(f"  Open Positions: {status['open_positions']}")


async def main():
    parser = argparse.ArgumentParser(description='SmartFlow Forward Test Runner')
    parser.add_argument('--tickers', nargs='+', default=['MNQ', 'MES', 'US30', 'MYM', 'NAS100'],
                       help='Tickers to trade')
    parser.add_argument('--status', action='store_true', help='Show current status')
    parser.add_argument('--simulate', action='store_true', help='Run simulation test')
    parser.add_argument('--signals', type=int, default=50, help='Number of signals to simulate')

    args = parser.parse_args()

    print_banner()

    if args.status:
        show_status()
        return

    if args.simulate:
        await simulate_forward_test(args.tickers, args.signals)
        return

    # Live forward test would connect to real data feeds
    print("\n[INFO] Live forward testing requires connection to data feeds.")
    print("[INFO] Use --simulate for testing, or integrate with SmartFlow service.")
    print(f"\nSelected tickers: {args.tickers}")


if __name__ == "__main__":
    asyncio.run(main())
