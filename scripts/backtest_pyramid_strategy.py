#!/usr/bin/env python3
"""
Pyramid Strategy Backtest
==========================

Backtests the 2%/2% Pullback Pyramid Dynamic Strategy with regime-based
parameter adjustment.

Features:
- Auto-adjusts stops/targets based on market regime
- Pullback-based pyramid entries (50% retracement + 2 bars continuation)
- Max 3 pyramid positions per trade
- Position sizing multipliers per regime

Regime-Based Parameters:
- TRENDING: 2%/2% stops, 1.0x size, trend-following
- RANGING: 1%/1% stops, 0.75x size, mean-reversion
- VOLATILE: 1.5%/2.5% stops, 0.5x size, reduced exposure
- BREAKOUT: 2.5%/3% stops, 1.25x size, momentum

Usage:
    python scripts/backtest_pyramid_strategy.py
    python scripts/backtest_pyramid_strategy.py --days 14
    python scripts/backtest_pyramid_strategy.py --tickers BTCUSD ETHUSD
"""

import sys
import os
import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('PyramidBacktest')

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    logger.warning("ccxt not available")

import pandas as pd
import numpy as np

ALL_INSTRUMENTS = [
    {"ticker": "BTCUSD", "source": "kraken", "type": "crypto"},
    {"ticker": "ETHUSD", "source": "kraken", "type": "crypto"},
]


@dataclass
class PyramidLevel:
    """Single pyramid position."""
    entry_price: float
    entry_bar: int
    size_mult: float
    stop_price: float
    target_price: float


@dataclass
class PyramidTrade:
    """Complete pyramid trade with multiple levels."""
    ticker: str
    direction: str
    regime: str
    levels: List[Dict] = field(default_factory=list)
    entry_bar: int = 0
    exit_bar: int = 0
    exit_price: float = 0.0
    exit_reason: str = ""
    total_pnl_pct: float = 0.0
    is_win: bool = False


@dataclass
class BacktestResult:
    ticker: str
    start_date: str
    end_date: str
    total_bars: int
    total_signals: int
    total_trades: int
    total_pyramid_levels: int
    avg_levels_per_trade: float
    winning_trades: int
    losing_trades: int
    win_rate: float
    gross_profit: float
    gross_loss: float
    net_pnl: float
    net_pnl_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    regime_breakdown: Dict
    errors: List[str]


class PyramidBacktester:
    """Backtester for Pyramid Strategy."""

    def __init__(self, days: int = 14):
        self.days = days

        # Regime parameters
        self.regime_params = {
            'trending_up': {'stop_pct': 2.0, 'target_pct': 2.0, 'size_mult': 1.0},
            'trending_down': {'stop_pct': 2.0, 'target_pct': 2.0, 'size_mult': 1.0},
            'ranging': {'stop_pct': 1.0, 'target_pct': 1.0, 'size_mult': 0.75},
            'volatile': {'stop_pct': 1.5, 'target_pct': 2.5, 'size_mult': 0.5},
            'breakout': {'stop_pct': 2.5, 'target_pct': 3.0, 'size_mult': 1.25},
            'neutral': {'stop_pct': 1.5, 'target_pct': 1.5, 'size_mult': 0.75},
        }

        # Pyramid settings
        self.max_pyramid_levels = 3
        self.pullback_pct = 0.5  # 50% retracement
        self.continuation_bars = 2
        self.min_confidence = 0.55

        # Indicator periods
        self.ema_fast = 9
        self.ema_mid = 21
        self.ema_slow = 50
        self.rsi_period = 14
        self.atr_period = 14

        # Regime detection thresholds
        self.trending_threshold = 3.0
        self.ranging_threshold = 1.0
        self.volatile_threshold = 5.0

        # Data source
        self.kraken = None
        if CCXT_AVAILABLE:
            self.kraken = ccxt.kraken({'enableRateLimit': True})

        self.results: Dict[str, BacktestResult] = {}
        self.all_trades: List[PyramidTrade] = []

    def calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    def detect_regime(self, df: pd.DataFrame, idx: int) -> str:
        """Detect market regime based on price action and indicators."""
        if idx < 50:
            return 'neutral'

        try:
            # Get 24h price change (288 5-min bars)
            lookback = min(288, idx)
            price_now = df['close'].iloc[idx]
            price_then = df['close'].iloc[idx - lookback]
            price_change_pct = abs((price_now - price_then) / price_then * 100)

            # Get EMA alignment
            ema9 = df['ema9'].iloc[idx]
            ema21 = df['ema21'].iloc[idx]
            ema50 = df['ema50'].iloc[idx] if 'ema50' in df.columns else ema21

            # ATR for volatility
            atr = df['atr'].iloc[idx]
            avg_atr = df['atr'].iloc[max(0, idx-50):idx].mean()
            atr_ratio = atr / avg_atr if avg_atr > 0 else 1.0

            # Detect regime
            if price_change_pct > self.volatile_threshold:
                return 'volatile'

            if price_change_pct > self.trending_threshold:
                if price_now > price_then:
                    return 'trending_up' if ema9 > ema21 else 'neutral'
                else:
                    return 'trending_down' if ema9 < ema21 else 'neutral'

            if price_change_pct < self.ranging_threshold:
                return 'ranging'

            # Check for breakout (compression release)
            if atr_ratio < 0.6:  # Low recent volatility
                return 'breakout'

            return 'neutral'

        except Exception:
            return 'neutral'

    def check_entry_signal(self, df: pd.DataFrame, idx: int, regime: str) -> Optional[Dict]:
        """Check for entry signal based on regime."""
        if idx < 50:
            return None

        close = df['close'].iloc[idx]
        ema9 = df['ema9'].iloc[idx]
        ema21 = df['ema21'].iloc[idx]
        rsi = df['rsi'].iloc[idx]
        atr = df['atr'].iloc[idx]

        if pd.isna(ema9) or pd.isna(ema21) or pd.isna(rsi):
            return None

        params = self.regime_params.get(regime, self.regime_params['neutral'])
        direction = None
        confidence = 0.0

        if regime in ['trending_up', 'breakout']:
            # Look for pullback to EMA21 in uptrend
            if ema9 > ema21 and abs(close - ema21) / ema21 < 0.02:  # Near EMA21
                if rsi > 40 and rsi < 70:  # Not overbought
                    # Check for bullish bar
                    if df['close'].iloc[idx] > df['open'].iloc[idx]:
                        direction = 'long'
                        confidence = 0.6 + (rsi - 50) / 100

        elif regime in ['trending_down']:
            # Look for rally to EMA21 in downtrend
            if ema9 < ema21 and abs(close - ema21) / ema21 < 0.02:
                if rsi < 60 and rsi > 30:
                    if df['close'].iloc[idx] < df['open'].iloc[idx]:
                        direction = 'short'
                        confidence = 0.6 + (50 - rsi) / 100

        elif regime == 'ranging':
            # Mean reversion at extremes
            bb_upper = df['close'].rolling(20).mean() + 2 * df['close'].rolling(20).std()
            bb_lower = df['close'].rolling(20).mean() - 2 * df['close'].rolling(20).std()

            if close <= bb_lower.iloc[idx] and rsi < 35:
                direction = 'long'
                confidence = 0.55 + (35 - rsi) / 100
            elif close >= bb_upper.iloc[idx] and rsi > 65:
                direction = 'short'
                confidence = 0.55 + (rsi - 65) / 100

        elif regime == 'volatile':
            # Only trade at extremes in volatile markets
            if rsi < 25:
                direction = 'long'
                confidence = 0.5 + (25 - rsi) / 50
            elif rsi > 75:
                direction = 'short'
                confidence = 0.5 + (rsi - 75) / 50

        if direction and confidence >= self.min_confidence:
            stop_pct = params['stop_pct']
            target_pct = params['target_pct']

            if direction == 'long':
                stop_price = close * (1 - stop_pct / 100)
                target_price = close * (1 + target_pct / 100)
            else:
                stop_price = close * (1 + stop_pct / 100)
                target_price = close * (1 - target_pct / 100)

            return {
                'direction': direction,
                'confidence': confidence,
                'entry_price': close,
                'stop_price': stop_price,
                'target_price': target_price,
                'stop_pct': stop_pct,
                'target_pct': target_pct,
                'size_mult': params['size_mult'],
                'regime': regime
            }

        return None

    def check_pyramid_addon(self, df: pd.DataFrame, idx: int, position: Dict) -> bool:
        """Check if pyramid add-on conditions are met."""
        if position['pyramid_levels'] >= self.max_pyramid_levels:
            return False

        direction = position['direction']
        entry_price = position['avg_entry']

        # Find swing high/low since entry
        entry_bar = position['entry_bar']
        bars_since_entry = df.iloc[entry_bar:idx+1]

        if len(bars_since_entry) < 5:
            return False

        close = df['close'].iloc[idx]

        if direction == 'long':
            swing_high = bars_since_entry['high'].max()
            # 50% pullback target
            pullback_target = entry_price + (swing_high - entry_price) * self.pullback_pct

            if close <= pullback_target:
                # Check continuation (2 higher closes)
                if idx >= 2:
                    c1 = df['close'].iloc[idx-2]
                    c2 = df['close'].iloc[idx-1]
                    c3 = df['close'].iloc[idx]
                    if c3 > c2 > c1:
                        return True
        else:  # short
            swing_low = bars_since_entry['low'].min()
            pullback_target = entry_price - (entry_price - swing_low) * self.pullback_pct

            if close >= pullback_target:
                if idx >= 2:
                    c1 = df['close'].iloc[idx-2]
                    c2 = df['close'].iloc[idx-1]
                    c3 = df['close'].iloc[idx]
                    if c3 < c2 < c1:
                        return True

        return False

    async def fetch_data(self, instrument: Dict) -> Optional[pd.DataFrame]:
        """Fetch data for instrument."""
        if not self.kraken:
            return None

        ticker = instrument["ticker"]
        try:
            symbol = f"{ticker[:3]}/{ticker[3:]}"
            since = int((datetime.now() - timedelta(days=self.days)).timestamp() * 1000)
            ohlcv = self.kraken.fetch_ohlcv(symbol, '5m', since=since, limit=1000)

            if not ohlcv:
                return None

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            logger.info(f"Fetched {len(df)} bars for {ticker}")
            return df

        except Exception as e:
            logger.error(f"Error fetching {ticker}: {e}")
            return None

    def run_backtest(self, ticker: str, df: pd.DataFrame) -> BacktestResult:
        """Run pyramid backtest."""
        errors = []

        # Calculate indicators
        df = df.copy()
        df['ema9'] = self.calculate_ema(df['close'], self.ema_fast)
        df['ema21'] = self.calculate_ema(df['close'], self.ema_mid)
        df['ema50'] = self.calculate_ema(df['close'], self.ema_slow)
        df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)
        df['atr'] = self.calculate_atr(df, self.atr_period)

        trades: List[PyramidTrade] = []
        position = None
        equity_curve = [10000.0]
        total_signals = 0
        total_pyramid_levels = 0

        regime_stats = {r: {'signals': 0, 'trades': 0, 'wins': 0, 'pnl': 0.0}
                       for r in self.regime_params.keys()}

        for i in range(50, len(df)):
            bar = df.iloc[i]
            regime = self.detect_regime(df, i)

            # Check exits first
            if position:
                should_exit = False
                exit_reason = ""
                exit_price = 0.0

                # Check stop/target for all pyramid levels
                # Use the most recent level's stop/target
                latest_level = position['levels'][-1]

                if position['direction'] == 'long':
                    if bar['low'] <= latest_level['stop_price']:
                        should_exit = True
                        exit_reason = "stop_loss"
                        exit_price = latest_level['stop_price']
                    elif bar['high'] >= latest_level['target_price']:
                        should_exit = True
                        exit_reason = "take_profit"
                        exit_price = latest_level['target_price']
                else:
                    if bar['high'] >= latest_level['stop_price']:
                        should_exit = True
                        exit_reason = "stop_loss"
                        exit_price = latest_level['stop_price']
                    elif bar['low'] <= latest_level['target_price']:
                        should_exit = True
                        exit_reason = "take_profit"
                        exit_price = latest_level['target_price']

                if should_exit:
                    # Calculate total P&L across all pyramid levels
                    total_pnl = 0.0
                    total_size = 0.0

                    for level in position['levels']:
                        size = level['size_mult']
                        if position['direction'] == 'long':
                            level_pnl = (exit_price - level['entry_price']) / level['entry_price'] * 100 * size
                        else:
                            level_pnl = (level['entry_price'] - exit_price) / level['entry_price'] * 100 * size
                        total_pnl += level_pnl
                        total_size += size

                    # Normalize by total size
                    avg_pnl = total_pnl / total_size if total_size > 0 else total_pnl

                    trade = PyramidTrade(
                        ticker=ticker,
                        direction=position['direction'],
                        regime=position['regime'],
                        levels=position['levels'],
                        entry_bar=position['entry_bar'],
                        exit_bar=i,
                        exit_price=exit_price,
                        exit_reason=exit_reason,
                        total_pnl_pct=avg_pnl,
                        is_win=avg_pnl > 0
                    )
                    trades.append(trade)
                    total_pyramid_levels += len(position['levels'])

                    # Update equity
                    equity_curve.append(equity_curve[-1] * (1 + avg_pnl / 100))

                    # Update regime stats
                    r = position['regime']
                    if r in regime_stats:
                        regime_stats[r]['trades'] += 1
                        regime_stats[r]['pnl'] += avg_pnl
                        if avg_pnl > 0:
                            regime_stats[r]['wins'] += 1

                    position = None

                # Check for pyramid add-on (if not exiting)
                elif self.check_pyramid_addon(df, i, position):
                    close = bar['close']
                    params = self.regime_params.get(regime, self.regime_params['neutral'])

                    if position['direction'] == 'long':
                        stop_price = close * (1 - params['stop_pct'] / 100)
                        target_price = close * (1 + params['target_pct'] / 100)
                    else:
                        stop_price = close * (1 + params['stop_pct'] / 100)
                        target_price = close * (1 - params['target_pct'] / 100)

                    new_level = {
                        'entry_price': close,
                        'entry_bar': i,
                        'size_mult': params['size_mult'] * 0.5,  # Half size for add-ons
                        'stop_price': stop_price,
                        'target_price': target_price
                    }
                    position['levels'].append(new_level)
                    position['pyramid_levels'] += 1

                    # Update average entry
                    total_size = sum(l['size_mult'] for l in position['levels'])
                    weighted_entry = sum(l['entry_price'] * l['size_mult'] for l in position['levels'])
                    position['avg_entry'] = weighted_entry / total_size

                    logger.debug(f"Pyramid add-on #{position['pyramid_levels']} at {close:.2f}")

            # Check for new entry
            if not position:
                signal = self.check_entry_signal(df, i, regime)

                if signal:
                    total_signals += 1
                    regime_stats[regime]['signals'] += 1

                    position = {
                        'direction': signal['direction'],
                        'entry_bar': i,
                        'avg_entry': signal['entry_price'],
                        'regime': regime,
                        'pyramid_levels': 1,
                        'levels': [{
                            'entry_price': signal['entry_price'],
                            'entry_bar': i,
                            'size_mult': signal['size_mult'],
                            'stop_price': signal['stop_price'],
                            'target_price': signal['target_price']
                        }]
                    }

        # Close open position
        if position:
            final_bar = df.iloc[-1]
            total_pnl = 0.0
            total_size = 0.0

            for level in position['levels']:
                size = level['size_mult']
                if position['direction'] == 'long':
                    level_pnl = (final_bar['close'] - level['entry_price']) / level['entry_price'] * 100 * size
                else:
                    level_pnl = (level['entry_price'] - final_bar['close']) / level['entry_price'] * 100 * size
                total_pnl += level_pnl
                total_size += size

            avg_pnl = total_pnl / total_size if total_size > 0 else total_pnl

            trade = PyramidTrade(
                ticker=ticker,
                direction=position['direction'],
                regime=position['regime'],
                levels=position['levels'],
                entry_bar=position['entry_bar'],
                exit_bar=len(df)-1,
                exit_price=final_bar['close'],
                exit_reason='end_of_data',
                total_pnl_pct=avg_pnl,
                is_win=avg_pnl > 0
            )
            trades.append(trade)
            total_pyramid_levels += len(position['levels'])
            equity_curve.append(equity_curve[-1] * (1 + avg_pnl / 100))

        # Calculate metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.is_win)
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        gross_profit = sum(t.total_pnl_pct for t in trades if t.total_pnl_pct > 0)
        gross_loss = abs(sum(t.total_pnl_pct for t in trades if t.total_pnl_pct < 0))
        net_pnl = gross_profit - gross_loss

        final_equity = equity_curve[-1]
        net_pnl_pct = (final_equity - 10000.0) / 10000.0 * 100

        # Max drawdown
        peak = equity_curve[0]
        max_dd = 0.0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            if dd > max_dd:
                max_dd = dd

        # Sharpe
        if len(equity_curve) > 1:
            returns = pd.Series(equity_curve).pct_change().dropna()
            if len(returns) > 0 and returns.std() > 0:
                sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 78)
                sharpe = max(-100, min(100, sharpe))
            else:
                sharpe = 0.0
        else:
            sharpe = 0.0

        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float('inf') if gross_profit > 0 else 0.0)

        wins = [t.total_pnl_pct for t in trades if t.total_pnl_pct > 0]
        losses = [t.total_pnl_pct for t in trades if t.total_pnl_pct < 0]
        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0

        avg_levels = total_pyramid_levels / total_trades if total_trades > 0 else 0.0

        # Calculate regime win rates
        for r, stats in regime_stats.items():
            if stats['trades'] > 0:
                stats['win_rate'] = stats['wins'] / stats['trades']

        self.all_trades.extend(trades)

        return BacktestResult(
            ticker=ticker,
            start_date=str(df.index[0]),
            end_date=str(df.index[-1]),
            total_bars=len(df),
            total_signals=total_signals,
            total_trades=total_trades,
            total_pyramid_levels=total_pyramid_levels,
            avg_levels_per_trade=avg_levels,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            net_pnl=net_pnl,
            net_pnl_pct=net_pnl_pct,
            max_drawdown_pct=max_dd,
            sharpe_ratio=sharpe,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            regime_breakdown=regime_stats,
            errors=errors
        )

    async def run_all_backtests(self, instruments: List[Dict]) -> Dict[str, BacktestResult]:
        """Run backtests for all instruments."""
        for instrument in instruments:
            ticker = instrument["ticker"]
            logger.info(f"\n{'='*50}")
            logger.info(f"Backtesting PYRAMID strategy on {ticker}...")
            logger.info(f"{'='*50}")

            df = await self.fetch_data(instrument)

            if df is None or len(df) < 100:
                logger.warning(f"Insufficient data for {ticker}")
                continue

            result = self.run_backtest(ticker, df)
            self.results[ticker] = result

            logger.info(f"\n{ticker} Results:")
            logger.info(f"  Bars: {result.total_bars}")
            logger.info(f"  Signals: {result.total_signals}")
            logger.info(f"  Trades: {result.total_trades}")
            logger.info(f"  Pyramid Levels: {result.total_pyramid_levels} (avg {result.avg_levels_per_trade:.1f}/trade)")
            logger.info(f"  Win Rate: {result.win_rate:.1%}")
            logger.info(f"  Net P&L: {result.net_pnl_pct:.2f}%")
            logger.info(f"  Max DD: {result.max_drawdown_pct:.2f}%")
            logger.info(f"  Sharpe: {result.sharpe_ratio:.2f}")
            logger.info(f"  Profit Factor: {result.profit_factor:.2f}")

            await asyncio.sleep(0.5)

        return self.results

    def print_summary(self):
        """Print summary."""
        print("\n" + "="*80)
        print("PYRAMID STRATEGY BACKTEST SUMMARY")
        print("="*80)

        print("\nRegime Parameters:")
        for regime, params in self.regime_params.items():
            print(f"  {regime}: {params['stop_pct']}%/{params['target_pct']}% stops, {params['size_mult']}x size")

        print(f"\nPyramid Settings:")
        print(f"  Max Levels: {self.max_pyramid_levels}")
        print(f"  Pullback: {self.pullback_pct*100:.0f}%")
        print(f"  Continuation Bars: {self.continuation_bars}")

        total_trades = sum(r.total_trades for r in self.results.values())
        total_wins = sum(r.winning_trades for r in self.results.values())
        total_levels = sum(r.total_pyramid_levels for r in self.results.values())

        print(f"\nOverall Statistics:")
        print(f"  Total trades: {total_trades}")
        print(f"  Total pyramid levels: {total_levels}")
        print(f"  Avg levels/trade: {total_levels/total_trades if total_trades > 0 else 0:.1f}")
        print(f"  Win rate: {total_wins/total_trades if total_trades > 0 else 0:.1%}")
        print(f"  Total P&L: {sum(r.net_pnl_pct for r in self.results.values()):.2f}%")

        print(f"\n{'Ticker':<12} {'Trades':>8} {'Levels':>8} {'Win Rate':>10} {'Net P&L':>10} {'Max DD':>10} {'Sharpe':>8} {'PF':>8}")
        print("-"*80)

        for ticker, result in sorted(self.results.items()):
            pf = f"{result.profit_factor:.2f}" if result.profit_factor < float('inf') else "inf"
            print(f"{ticker:<12} {result.total_trades:>8} {result.total_pyramid_levels:>8} {result.win_rate:>10.1%} {result.net_pnl_pct:>10.2f}% {result.max_drawdown_pct:>9.2f}% {result.sharpe_ratio:>8.2f} {pf:>8}")

        # Regime breakdown
        print(f"\nRegime Breakdown:")
        print(f"{'Regime':<15} {'Signals':>10} {'Trades':>10} {'Win Rate':>10} {'P&L':>12}")
        print("-"*60)

        regime_totals = {}
        for result in self.results.values():
            for regime, stats in result.regime_breakdown.items():
                if regime not in regime_totals:
                    regime_totals[regime] = {'signals': 0, 'trades': 0, 'wins': 0, 'pnl': 0.0}
                regime_totals[regime]['signals'] += stats['signals']
                regime_totals[regime]['trades'] += stats['trades']
                regime_totals[regime]['wins'] += stats['wins']
                regime_totals[regime]['pnl'] += stats['pnl']

        for regime, stats in sorted(regime_totals.items(), key=lambda x: x[1]['trades'], reverse=True):
            wr = stats['wins'] / stats['trades'] if stats['trades'] > 0 else 0.0
            print(f"{regime:<15} {stats['signals']:>10} {stats['trades']:>10} {wr:>10.1%} {stats['pnl']:>12.2f}%")

        print("\n" + "="*80)

    def export_results(self, filename: str):
        """Export results."""
        export_data = {
            'strategy': 'pyramid_dynamic_v1',
            'backtest_days': self.days,
            'run_date': datetime.now().isoformat(),
            'instruments': {t: asdict(r) for t, r in self.results.items()},
            'trades': [asdict(t) for t in self.all_trades]
        }
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        logger.info(f"Results exported to {filename}")


async def main():
    parser = argparse.ArgumentParser(description="Pyramid Strategy Backtest")
    parser.add_argument('--days', type=int, default=14)
    parser.add_argument('--tickers', nargs='+')
    parser.add_argument('--output', type=str, default='pyramid_backtest.json')

    args = parser.parse_args()

    instruments = ALL_INSTRUMENTS
    if args.tickers:
        instruments = [i for i in ALL_INSTRUMENTS if i["ticker"] in args.tickers]

    print("\n" + "="*60)
    print(f"PYRAMID STRATEGY BACKTEST ({args.days} days)")
    print("="*60)

    backtester = PyramidBacktester(days=args.days)
    await backtester.run_all_backtests(instruments)
    backtester.print_summary()
    backtester.export_results(args.output)


if __name__ == "__main__":
    asyncio.run(main())
