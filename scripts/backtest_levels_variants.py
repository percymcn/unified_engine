#!/usr/bin/env python3
"""
Backtest Levels + Trailing + Sentiment Variants
================================================

Tests 3 variants:
1. Current (baseline) - PCT 0.2%/0.6% (1:3 R:R)
2. Levels + Trailing + Sentiment - With new features
3. High-Flow Uptrend - Regime-asymmetric 1:4-1:5 R:R

Usage:
    python scripts/backtest_levels_variants.py
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import httpx
import json

# API Key
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "f402Q_wfDe7D1Q0GLjTzvBAvKoY7uEPV")


@dataclass
class BacktestConfig:
    """Configuration for backtest variant."""
    name: str
    pct_stop: float = 0.2
    pct_target: float = 0.6

    # Levels confluence
    levels_enabled: bool = False
    levels_min: float = 65.0

    # Trailing stops
    trailing_enabled: bool = False
    trailing_breakeven: float = 2.0
    trailing_partial: float = 3.0
    trailing_partial_pct: float = 50.0

    # News sentiment
    news_enabled: bool = False
    news_boost_max: float = 0.05

    # Regime-asymmetric
    regime_asymmetric: bool = False
    uptrend_target_pct: float = 0.6
    uptrend_flow_require: str = 'MEDIUM'
    uptrend_imbalance_min: float = 0.0


@dataclass
class Trade:
    """Single backtest trade."""
    direction: str
    entry: float
    stop: float
    target: float
    exit: float = 0.0
    pnl: float = 0.0
    reason: str = ''
    levels_confluence: float = 0.0
    trailing_hit_be: bool = False
    partial_exit: bool = False
    partial_pnl: float = 0.0


# Variant configurations
VARIANTS = {
    'current': BacktestConfig(
        name='Current (PCT 0.2/0.6)',
        pct_stop=0.2,
        pct_target=0.6,
        levels_enabled=False,
        trailing_enabled=False,
        news_enabled=False,
        regime_asymmetric=False,
    ),
    'levels_trailing': BacktestConfig(
        name='Levels + Trailing + Sentiment',
        pct_stop=0.2,
        pct_target=0.6,
        levels_enabled=True,
        levels_min=65.0,
        trailing_enabled=True,
        trailing_breakeven=2.0,
        trailing_partial=3.0,
        trailing_partial_pct=50.0,
        news_enabled=True,
        news_boost_max=0.05,
        regime_asymmetric=False,
    ),
    'high_flow_uptrend': BacktestConfig(
        name='High-Flow Uptrend (1:4)',
        pct_stop=0.2,
        pct_target=0.8,  # 1:4 R:R
        levels_enabled=True,
        levels_min=70.0,
        trailing_enabled=True,
        trailing_breakeven=2.0,
        trailing_partial=3.0,
        trailing_partial_pct=50.0,
        news_enabled=True,
        regime_asymmetric=True,
        uptrend_target_pct=0.8,
        uptrend_flow_require='HIGH',
        uptrend_imbalance_min=0.45,
    ),
}


async def fetch_data(ticker: str, days: int = 90) -> Optional[pd.DataFrame]:
    """Fetch hourly bars from Polygon."""
    end = datetime.now()
    start = end - timedelta(days=days)

    url = f'https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/hour/{start.strftime("%Y-%m-%d")}/{end.strftime("%Y-%m-%d")}'

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params={'apiKey': POLYGON_API_KEY, 'limit': 50000})
        data = resp.json()

    if 'results' not in data:
        print(f'No data for {ticker}')
        return None

    df = pd.DataFrame(data['results'])
    df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
    df = df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'})
    df = df.set_index('timestamp')
    return df


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate technical indicators."""
    # EMAs
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()

    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + gain / (loss + 0.0001)))

    # ATR
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()

    # Volume
    df['vol_avg'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_avg']

    # ADX (simplified)
    df['plus_dm'] = np.where((df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
                             np.maximum(df['high'] - df['high'].shift(1), 0), 0)
    df['minus_dm'] = np.where((df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
                              np.maximum(df['low'].shift(1) - df['low'], 0), 0)
    df['tr'] = np.maximum(df['high'] - df['low'],
                          np.maximum(abs(df['high'] - df['close'].shift(1)),
                                    abs(df['low'] - df['close'].shift(1))))
    df['atr_14'] = df['tr'].rolling(14).mean()
    df['plus_di'] = 100 * df['plus_dm'].rolling(14).sum() / (df['atr_14'] * 14 + 0.0001)
    df['minus_di'] = 100 * df['minus_dm'].rolling(14).sum() / (df['atr_14'] * 14 + 0.0001)
    dx = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'] + 0.0001)
    df['adx'] = dx.rolling(14).mean()

    # Swing high/low (5-bar)
    df['swing_high'] = df['high'].rolling(5).max()
    df['swing_low'] = df['low'].rolling(5).min()

    # PDH/PDL (simplified - use 24h rolling)
    df['pdh'] = df['high'].rolling(24).max().shift(1)
    df['pdl'] = df['low'].rolling(24).min().shift(1)

    return df.dropna()


def calculate_levels_confluence(price: float, pdh: float, pdl: float, swing_high: float, swing_low: float) -> float:
    """Calculate simple levels confluence score."""
    score = 0.0

    # Check proximity to PDH/PDL
    pdh_dist = abs(price - pdh) / price * 100
    pdl_dist = abs(price - pdl) / price * 100

    if pdh_dist < 0.3:
        score += 30  # Near PDH
    elif pdh_dist < 0.5:
        score += 20
    elif pdh_dist < 1.0:
        score += 10

    if pdl_dist < 0.3:
        score += 30  # Near PDL
    elif pdl_dist < 0.5:
        score += 20
    elif pdl_dist < 1.0:
        score += 10

    # Fibonacci levels (0.618 of swing)
    swing_range = swing_high - swing_low
    fib_618 = swing_low + swing_range * 0.618
    fib_382 = swing_low + swing_range * 0.382

    fib_618_dist = abs(price - fib_618) / price * 100
    fib_382_dist = abs(price - fib_382) / price * 100

    if fib_618_dist < 0.3:
        score += 25
    elif fib_618_dist < 0.5:
        score += 15

    if fib_382_dist < 0.3:
        score += 15
    elif fib_382_dist < 0.5:
        score += 10

    return min(100.0, score)


def detect_regime(df: pd.DataFrame, i: int) -> str:
    """Detect market regime."""
    row = df.iloc[i]
    adx = row['adx']
    plus_di = row['plus_di']
    minus_di = row['minus_di']

    if adx > 25:
        if plus_di > minus_di + 5:
            return 'trending_up'
        elif minus_di > plus_di + 5:
            return 'trending_down'
    return 'ranging'


async def run_backtest(df: pd.DataFrame, config: BacktestConfig) -> Dict:
    """Run backtest with given configuration."""
    print(f'\n{"="*60}')
    print(f'  {config.name}')
    print(f'{"="*60}')

    trades: List[Trade] = []
    position: Optional[Trade] = None
    last_exit = -100
    cooldown = 3
    capital = 25000.0
    initial_capital = 25000.0
    risk_pct = 2.0
    equity = [capital]

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        price = row['close']
        high = row['high']
        low = row['low']

        # Detect regime
        regime = detect_regime(df, i)

        # ========================================
        # MANAGE OPEN POSITION
        # ========================================
        if position:
            # Calculate current P&L in R-multiples
            risk = abs(position.entry - position.stop)

            if position.direction == 'long':
                current_pnl = price - position.entry
                profit_r = current_pnl / risk if risk > 0 else 0

                # ========================================
                # TRAILING STOP LOGIC (if enabled)
                # ========================================
                if config.trailing_enabled and not position.trailing_hit_be:
                    if profit_r >= config.trailing_breakeven:
                        # Move stop to breakeven
                        position.stop = position.entry + (risk * 0.1)  # Small buffer
                        position.trailing_hit_be = True
                        # print(f'  📊 Trailing: BE hit at {position.stop:.2f}')

                if config.trailing_enabled and not position.partial_exit:
                    if profit_r >= config.trailing_partial:
                        # Partial exit
                        position.partial_exit = True
                        position.partial_pnl = (position.target - position.entry) * (config.trailing_partial_pct / 100)

                # Check TP
                if high >= position.target:
                    position.exit = position.target
                    position.pnl = position.target - position.entry
                    if position.partial_exit:
                        position.pnl *= (1 - config.trailing_partial_pct / 100)  # Remaining position
                        position.pnl += position.partial_pnl
                    position.reason = 'tp'
                    trades.append(position)
                    risk_val = abs(position.entry - position.stop)
                    if risk_val > 0:
                        capital += (position.pnl / risk_val) * (initial_capital * risk_pct / 100)
                    equity.append(capital)
                    position = None
                    last_exit = i
                # Check SL
                elif low <= position.stop:
                    position.exit = position.stop
                    position.pnl = position.stop - position.entry
                    position.reason = 'sl'
                    trades.append(position)
                    risk_val = abs(position.entry - position.stop)
                    if risk_val > 0:
                        capital += (position.pnl / risk_val) * (initial_capital * risk_pct / 100)
                    equity.append(capital)
                    position = None
                    last_exit = i

            else:  # short
                current_pnl = position.entry - price
                profit_r = current_pnl / risk if risk > 0 else 0

                if config.trailing_enabled and not position.trailing_hit_be:
                    if profit_r >= config.trailing_breakeven:
                        position.stop = position.entry - (risk * 0.1)
                        position.trailing_hit_be = True

                if config.trailing_enabled and not position.partial_exit:
                    if profit_r >= config.trailing_partial:
                        position.partial_exit = True
                        position.partial_pnl = (position.entry - position.target) * (config.trailing_partial_pct / 100)

                if low <= position.target:
                    position.exit = position.target
                    position.pnl = position.entry - position.target
                    if position.partial_exit:
                        position.pnl *= (1 - config.trailing_partial_pct / 100)
                        position.pnl += position.partial_pnl
                    position.reason = 'tp'
                    trades.append(position)
                    risk_val = abs(position.stop - position.entry)
                    if risk_val > 0:
                        capital += (position.pnl / risk_val) * (initial_capital * risk_pct / 100)
                    equity.append(capital)
                    position = None
                    last_exit = i
                elif high >= position.stop:
                    position.exit = position.stop
                    position.pnl = position.entry - position.stop
                    position.reason = 'sl'
                    trades.append(position)
                    risk_val = abs(position.stop - position.entry)
                    if risk_val > 0:
                        capital += (position.pnl / risk_val) * (initial_capital * risk_pct / 100)
                    equity.append(capital)
                    position = None
                    last_exit = i

        # ========================================
        # LOOK FOR NEW ENTRY
        # ========================================
        if position is None and (i - last_exit) > cooldown:
            # Signal conditions
            ema_bullish = row['ema9'] > row['ema21']
            price_above_ema9 = price > row['ema9']
            rsi_bullish = row['rsi'] > 50
            adx_ok = row['adx'] > 20
            vol_ok = row['vol_ratio'] > 1.0

            # Calculate levels confluence
            levels_confluence = 0.0
            if config.levels_enabled:
                levels_confluence = calculate_levels_confluence(
                    price, row['pdh'], row['pdl'], row['swing_high'], row['swing_low']
                )

            # Determine target based on config
            pct_target = config.pct_target

            # ========================================
            # REGIME-ASYMMETRIC LOGIC
            # ========================================
            if config.regime_asymmetric:
                if regime == 'trending_up' and ema_bullish:
                    pct_target = config.uptrend_target_pct  # 1:4 R:R

            # ========================================
            # LONG ENTRY
            # ========================================
            if ema_bullish and price_above_ema9 and rsi_bullish and adx_ok and vol_ok:
                # Apply levels filter if enabled
                if config.levels_enabled and levels_confluence < config.levels_min:
                    continue  # Skip - insufficient confluence

                stop = price * (1 - config.pct_stop / 100)
                target = price * (1 + pct_target / 100)

                position = Trade(
                    direction='long',
                    entry=price,
                    stop=stop,
                    target=target,
                    levels_confluence=levels_confluence
                )
                continue

            # ========================================
            # SHORT ENTRY
            # ========================================
            ema_bearish = row['ema9'] < row['ema21']
            price_below_ema9 = price < row['ema9']
            rsi_bearish = row['rsi'] < 50

            if ema_bearish and price_below_ema9 and rsi_bearish and adx_ok and vol_ok:
                if config.levels_enabled and levels_confluence < config.levels_min:
                    continue

                stop = price * (1 + config.pct_stop / 100)
                target = price * (1 - pct_target / 100)

                position = Trade(
                    direction='short',
                    entry=price,
                    stop=stop,
                    target=target,
                    levels_confluence=levels_confluence
                )

    # ========================================
    # CALCULATE RESULTS
    # ========================================
    if not trades:
        print('  No trades generated')
        return {'name': config.name, 'trades': 0}

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]
    longs = [t for t in trades if t.direction == 'long']
    shorts = [t for t in trades if t.direction == 'short']

    gp = sum(t.pnl for t in wins) if wins else 0
    gl = abs(sum(t.pnl for t in losses)) if losses else 0

    # Max drawdown
    peak = initial_capital
    max_dd = 0
    for eq in equity:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100
        max_dd = max(max_dd, dd)

    # Sharpe
    if len(equity) > 1:
        returns = np.diff(equity) / np.array(equity[:-1])
        sharpe = (np.mean(returns) / (np.std(returns) + 0.0001)) * np.sqrt(252)
    else:
        sharpe = 0

    # Trailing stats
    trailing_be_hits = sum(1 for t in trades if t.trailing_hit_be)
    partial_exits = sum(1 for t in trades if t.partial_exit)

    result = {
        'name': config.name,
        'trades': len(trades),
        'longs': len(longs),
        'shorts': len(shorts),
        'wins': len(wins),
        'losses': len(losses),
        'wr': len(wins) / len(trades) * 100 if trades else 0,
        'long_wr': len([t for t in longs if t.pnl > 0]) / len(longs) * 100 if longs else 0,
        'short_wr': len([t for t in shorts if t.pnl > 0]) / len(shorts) * 100 if shorts else 0,
        'pf': gp / gl if gl > 0 else 0,
        'pnl': capital - initial_capital,
        'dd': max_dd,
        'sharpe': sharpe,
        'tp_exits': len([t for t in trades if t.reason == 'tp']),
        'sl_exits': len([t for t in trades if t.reason == 'sl']),
        'trailing_be_hits': trailing_be_hits,
        'partial_exits': partial_exits,
    }

    print(f'''
  Trades: {result["trades"]} (L:{result["longs"]} S:{result["shorts"]})
  Win Rate: {result["wr"]:.1f}% (L:{result["long_wr"]:.1f}% S:{result["short_wr"]:.1f}%)
  Profit Factor: {result["pf"]:.2f}
  Sharpe: {result["sharpe"]:.2f}
  Net P&L: ${result["pnl"]:.2f}
  Max DD: {result["dd"]:.2f}%
  Exits: TP={result["tp_exits"]} SL={result["sl_exits"]}
  Trailing BE Hits: {trailing_be_hits} | Partial Exits: {partial_exits}
''')

    return result


async def main():
    print('='*70)
    print('  BACKTEST LEVELS + TRAILING + SENTIMENT VARIANTS')
    print('='*70)

    # Fetch data
    print('\nFetching SPY data (90 days, hourly)...')
    df = await fetch_data('SPY', days=90)
    if df is None:
        print('Failed to fetch data')
        return

    print(f'Data: {len(df)} hourly bars')

    # Calculate indicators
    df = calculate_indicators(df)
    print(f'Indicators calculated: {len(df)} bars')

    # Run all variants
    results = []
    for variant_name, config in VARIANTS.items():
        result = await run_backtest(df, config)
        result['variant'] = variant_name
        results.append(result)

    # Comparison table
    print('\n' + '='*80)
    print('  COMPARISON TABLE')
    print('='*80)
    print(f'{"Variant":<30} {"Trades":>7} {"WR%":>7} {"PF":>7} {"Sharpe":>8} {"MaxDD":>8} {"P&L":>12}')
    print('-'*80)

    for r in results:
        print(f'{r["name"]:<30} {r["trades"]:>7} {r["wr"]:>6.1f}% {r["pf"]:>7.2f} {r["sharpe"]:>8.2f} {r["dd"]:>7.2f}% ${r["pnl"]:>11.2f}')

    # Save results
    output_file = 'backtest_levels_variants_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f'\nResults saved to {output_file}')


if __name__ == '__main__':
    asyncio.run(main())
