#!/usr/bin/env python3
"""
Quick Strategy Backtest
========================

Backtests the Quick Mode (5-minute momentum scalping) strategy.

Quick Mode Criteria:
- EMA9/21 crossover (40 points)
- RSI momentum > 55 bullish, < 45 bearish (25 points)
- MACD histogram direction (20 points)
- 15m trend confirmation optional (15 points)
- Volume > 1.2x average (required)
- ATR-based stops (1.0x) and targets (1.5x)
- Min confidence: 60

Usage:
    python scripts/backtest_quick_strategy.py
    python scripts/backtest_quick_strategy.py --days 14
    python scripts/backtest_quick_strategy.py --tickers BTCUSD ETHUSD
"""

import sys
import os
import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('QuickBacktest')

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Data sources
try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    logger.warning("ccxt not available - crypto backtest disabled")

import pandas as pd
import numpy as np

# All instruments to backtest
ALL_INSTRUMENTS = [
    {"ticker": "BTCUSD", "source": "kraken", "type": "crypto"},
    {"ticker": "ETHUSD", "source": "kraken", "type": "crypto"},
]


@dataclass
class BacktestResult:
    """Result for a single instrument backtest."""
    ticker: str
    start_date: str
    end_date: str
    total_bars: int
    total_signals: int
    long_signals: int
    short_signals: int
    total_trades: int
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
    avg_trade_duration_bars: float
    errors: List[str]


class QuickStrategyBacktester:
    """Backtester for Quick Mode Strategy."""

    def __init__(self, days: int = 14):
        self.days = days

        # Quick mode parameters (from SmartFlowService)
        self.min_confidence = 60.0
        self.rsi_momentum_threshold = 55  # RSI > 55 bullish, < 45 bearish
        self.atr_stop_multiplier = 1.0
        self.atr_target_multiplier = 1.5
        self.require_volume = True
        self.min_volume_ratio = 1.2

        # Indicator periods
        self.ema_fast = 9
        self.ema_slow = 21
        self.rsi_period = 14
        self.atr_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.volume_ma_period = 20

        # Initialize data sources
        self.kraken = None
        if CCXT_AVAILABLE:
            self.kraken = ccxt.kraken({'enableRateLimit': True})

        # Results storage
        self.results: Dict[str, BacktestResult] = {}
        self.all_trades: List[Dict] = []

    def calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate EMA."""
        return series.ewm(span=period, adjust=False).mean()

    def calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI."""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_macd(self, series: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD line, signal, and histogram."""
        ema_fast = self.calculate_ema(series, self.macd_fast)
        ema_slow = self.calculate_ema(series, self.macd_slow)
        macd_line = ema_fast - ema_slow
        signal_line = self.calculate_ema(macd_line, self.macd_signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ATR."""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    def calculate_volume_ratio(self, volume: pd.Series, period: int = 20) -> pd.Series:
        """Calculate volume ratio vs average."""
        vol_ma = volume.rolling(window=period).mean()
        return volume / vol_ma

    async def fetch_crypto_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """Fetch crypto data from Kraken."""
        if not self.kraken:
            return None

        try:
            symbol = f"{ticker[:3]}/{ticker[3:]}"
            since = int((datetime.now() - timedelta(days=self.days)).timestamp() * 1000)
            ohlcv = self.kraken.fetch_ohlcv(symbol, '5m', since=since, limit=1000)

            if not ohlcv:
                return None

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            logger.info(f"Fetched {len(df)} bars for {ticker} from Kraken")
            return df

        except Exception as e:
            logger.error(f"Error fetching {ticker} from Kraken: {e}")
            return None

    async def fetch_data(self, instrument: Dict) -> Optional[pd.DataFrame]:
        """Fetch data for an instrument."""
        ticker = instrument["ticker"]
        source = instrument["source"]

        if source == "kraken":
            return await self.fetch_crypto_data(ticker)
        return None

    def analyze_quick_signal(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """
        Analyze bar for Quick mode signal.

        Returns signal dict or None.
        """
        if idx < 30:
            return None

        # Get current values
        close = df['close'].iloc[idx]
        ema9 = df['ema9'].iloc[idx]
        ema21 = df['ema21'].iloc[idx]
        rsi = df['rsi'].iloc[idx]
        macd_hist = df['macd_hist'].iloc[idx]
        atr = df['atr'].iloc[idx]
        volume_ratio = df['volume_ratio'].iloc[idx]

        # Skip if NaN
        if pd.isna(ema9) or pd.isna(ema21) or pd.isna(rsi) or pd.isna(atr):
            return None

        # Volume confirmation (required)
        if self.require_volume and volume_ratio < self.min_volume_ratio:
            return None

        # Check bullish setup
        bullish_ema = ema9 > ema21
        bullish_rsi = 40 < rsi < 70
        bullish_macd = macd_hist > 0
        rsi_momentum_bull = rsi > self.rsi_momentum_threshold

        # Check bearish setup
        bearish_ema = ema9 < ema21
        bearish_rsi = 30 < rsi < 60
        bearish_macd = macd_hist < 0
        rsi_momentum_bear = rsi < (100 - self.rsi_momentum_threshold)

        # Calculate scores
        bullish_score = 0
        bearish_score = 0

        # EMA crossover (40 points)
        if bullish_ema:
            bullish_score += 40
        if bearish_ema:
            bearish_score += 40

        # RSI momentum (25 points)
        if rsi_momentum_bull and bullish_rsi:
            bullish_score += 25
        if rsi_momentum_bear and bearish_rsi:
            bearish_score += 25

        # MACD direction (20 points)
        if bullish_macd:
            bullish_score += 20
        if bearish_macd:
            bearish_score += 20

        # 15m confirmation would add 15 points but we skip for single-timeframe test
        # Adding base 15 points if overall conditions align
        if bullish_ema and bullish_macd:
            bullish_score += 15
        if bearish_ema and bearish_macd:
            bearish_score += 15

        # Determine signal
        action = None
        confidence = 0

        if bullish_score >= self.min_confidence and bullish_score > bearish_score:
            action = 'long'
            confidence = bullish_score
        elif bearish_score >= self.min_confidence and bearish_score > bullish_score:
            action = 'short'
            confidence = bearish_score

        if not action:
            return None

        # Calculate stop and target using ATR
        if action == 'long':
            stop_loss = close - (atr * self.atr_stop_multiplier)
            take_profit = close + (atr * self.atr_target_multiplier)
        else:
            stop_loss = close + (atr * self.atr_stop_multiplier)
            take_profit = close - (atr * self.atr_target_multiplier)

        return {
            'action': action,
            'confidence': confidence,
            'entry_price': close,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'atr': atr,
            'rsi': rsi,
            'volume_ratio': volume_ratio
        }

    def run_backtest(self, ticker: str, df: pd.DataFrame) -> BacktestResult:
        """Run backtest on a single instrument."""
        errors = []

        # Calculate all indicators upfront
        df = df.copy()
        df['ema9'] = self.calculate_ema(df['close'], self.ema_fast)
        df['ema21'] = self.calculate_ema(df['close'], self.ema_slow)
        df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)
        df['atr'] = self.calculate_atr(df, self.atr_period)
        _, _, df['macd_hist'] = self.calculate_macd(df['close'])
        df['volume_ratio'] = self.calculate_volume_ratio(df['volume'], self.volume_ma_period)

        # Initialize tracking
        trades = []
        position = None
        equity_curve = [10000.0]

        total_signals = 0
        long_signals = 0
        short_signals = 0
        trade_durations = []

        # Walk through data
        for i in range(50, len(df)):
            bar = df.iloc[i]

            # Check for exit first (if in position)
            if position:
                should_exit = False
                exit_reason = ""
                exit_price = 0.0

                if position['direction'] == 'long':
                    if bar['low'] <= position['stop_loss']:
                        should_exit = True
                        exit_reason = "stop_loss"
                        exit_price = position['stop_loss']
                    elif bar['high'] >= position['take_profit']:
                        should_exit = True
                        exit_reason = "take_profit"
                        exit_price = position['take_profit']
                else:  # short
                    if bar['high'] >= position['stop_loss']:
                        should_exit = True
                        exit_reason = "stop_loss"
                        exit_price = position['stop_loss']
                    elif bar['low'] <= position['take_profit']:
                        should_exit = True
                        exit_reason = "take_profit"
                        exit_price = position['take_profit']

                if should_exit:
                    # Calculate P&L
                    if position['direction'] == 'long':
                        exit_pnl = (exit_price - position['entry_price']) / position['entry_price'] * 100
                    else:
                        exit_pnl = (position['entry_price'] - exit_price) / position['entry_price'] * 100

                    is_win = exit_pnl > 0
                    duration = i - position['entry_bar']
                    trade_durations.append(duration)

                    trade = {
                        'ticker': ticker,
                        'direction': position['direction'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'entry_bar': position['entry_bar'],
                        'exit_bar': i,
                        'duration_bars': duration,
                        'pnl_pct': exit_pnl,
                        'exit_reason': exit_reason,
                        'is_win': is_win,
                        'confidence': position['confidence']
                    }
                    trades.append(trade)

                    # Update equity
                    equity_curve.append(equity_curve[-1] * (1 + exit_pnl / 100))
                    position = None

            # Check for new entry (if not in position)
            if not position:
                signal = self.analyze_quick_signal(df, i)

                if signal:
                    total_signals += 1
                    if signal['action'] == 'long':
                        long_signals += 1
                    else:
                        short_signals += 1

                    # Enter position
                    position = {
                        'direction': signal['action'],
                        'entry_price': signal['entry_price'],
                        'stop_loss': signal['stop_loss'],
                        'take_profit': signal['take_profit'],
                        'entry_bar': i,
                        'confidence': signal['confidence']
                    }

        # Close any open position at end
        if position:
            final_bar = df.iloc[-1]
            if position['direction'] == 'long':
                exit_pnl = (final_bar['close'] - position['entry_price']) / position['entry_price'] * 100
            else:
                exit_pnl = (position['entry_price'] - final_bar['close']) / position['entry_price'] * 100

            duration = len(df) - 1 - position['entry_bar']
            trade_durations.append(duration)

            trade = {
                'ticker': ticker,
                'direction': position['direction'],
                'entry_price': position['entry_price'],
                'exit_price': final_bar['close'],
                'entry_bar': position['entry_bar'],
                'exit_bar': len(df) - 1,
                'duration_bars': duration,
                'pnl_pct': exit_pnl,
                'exit_reason': 'end_of_data',
                'is_win': exit_pnl > 0,
                'confidence': position['confidence']
            }
            trades.append(trade)
            equity_curve.append(equity_curve[-1] * (1 + exit_pnl / 100))

        # Calculate metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t['is_win'])
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        gross_profit = sum(t['pnl_pct'] for t in trades if t['pnl_pct'] > 0)
        gross_loss = abs(sum(t['pnl_pct'] for t in trades if t['pnl_pct'] < 0))
        net_pnl = gross_profit - gross_loss

        final_equity = equity_curve[-1] if equity_curve else 10000.0
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

        # Sharpe ratio
        if len(equity_curve) > 1:
            returns = pd.Series(equity_curve).pct_change().dropna()
            if len(returns) > 0 and returns.std() > 0:
                sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 78)
            else:
                sharpe = 0.0
        else:
            sharpe = 0.0

        # Cap extreme sharpe values
        if abs(sharpe) > 100:
            sharpe = 0.0 if np.isnan(sharpe) or np.isinf(sharpe) else max(-100, min(100, sharpe))

        # Profit factor
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float('inf') if gross_profit > 0 else 0.0)

        # Average win/loss
        wins = [t['pnl_pct'] for t in trades if t['pnl_pct'] > 0]
        losses = [t['pnl_pct'] for t in trades if t['pnl_pct'] < 0]
        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0

        # Average trade duration
        avg_duration = np.mean(trade_durations) if trade_durations else 0.0

        # Store trades globally
        self.all_trades.extend(trades)

        return BacktestResult(
            ticker=ticker,
            start_date=str(df.index[0]) if len(df) > 0 else "",
            end_date=str(df.index[-1]) if len(df) > 0 else "",
            total_bars=len(df),
            total_signals=total_signals,
            long_signals=long_signals,
            short_signals=short_signals,
            total_trades=total_trades,
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
            avg_trade_duration_bars=avg_duration,
            errors=errors
        )

    async def run_all_backtests(self, instruments: List[Dict]) -> Dict[str, BacktestResult]:
        """Run backtests for all instruments."""
        for instrument in instruments:
            ticker = instrument["ticker"]
            logger.info(f"\n{'='*50}")
            logger.info(f"Backtesting QUICK strategy on {ticker}...")
            logger.info(f"{'='*50}")

            df = await self.fetch_data(instrument)

            if df is None or len(df) < 100:
                logger.warning(f"Insufficient data for {ticker} - skipping")
                self.results[ticker] = BacktestResult(
                    ticker=ticker, start_date="", end_date="", total_bars=0,
                    total_signals=0, long_signals=0, short_signals=0,
                    total_trades=0, winning_trades=0, losing_trades=0,
                    win_rate=0.0, gross_profit=0.0, gross_loss=0.0,
                    net_pnl=0.0, net_pnl_pct=0.0, max_drawdown_pct=0.0,
                    sharpe_ratio=0.0, profit_factor=0.0, avg_win=0.0, avg_loss=0.0,
                    avg_trade_duration_bars=0.0, errors=["Insufficient data"]
                )
                continue

            result = self.run_backtest(ticker, df)
            self.results[ticker] = result

            # Print summary
            logger.info(f"\n{ticker} Results:")
            logger.info(f"  Bars: {result.total_bars}")
            logger.info(f"  Signals: {result.total_signals} (L:{result.long_signals}, S:{result.short_signals})")
            logger.info(f"  Trades: {result.total_trades}")
            logger.info(f"  Win Rate: {result.win_rate:.1%}")
            logger.info(f"  Net P&L: {result.net_pnl_pct:.2f}%")
            logger.info(f"  Max DD: {result.max_drawdown_pct:.2f}%")
            logger.info(f"  Sharpe: {result.sharpe_ratio:.2f}")
            logger.info(f"  Profit Factor: {result.profit_factor:.2f}")
            logger.info(f"  Avg Duration: {result.avg_trade_duration_bars:.1f} bars")

            await asyncio.sleep(0.5)

        return self.results

    def print_summary(self):
        """Print overall backtest summary."""
        print("\n" + "="*80)
        print("QUICK MODE STRATEGY BACKTEST SUMMARY")
        print("="*80)

        print("\nStrategy Parameters:")
        print(f"  Min Confidence: {self.min_confidence}")
        print(f"  RSI Momentum Threshold: {self.rsi_momentum_threshold}")
        print(f"  ATR Stop Multiplier: {self.atr_stop_multiplier}x")
        print(f"  ATR Target Multiplier: {self.atr_target_multiplier}x")
        print(f"  Volume Confirmation: {self.require_volume} (>{self.min_volume_ratio}x)")

        # Aggregate metrics
        total_trades = sum(r.total_trades for r in self.results.values())
        total_wins = sum(r.winning_trades for r in self.results.values())
        total_pnl = sum(r.net_pnl for r in self.results.values())

        avg_win_rate = total_wins / total_trades if total_trades > 0 else 0.0
        valid_sharpes = [r.sharpe_ratio for r in self.results.values() if r.total_trades > 0 and abs(r.sharpe_ratio) < 100]
        avg_sharpe = np.mean(valid_sharpes) if valid_sharpes else 0.0
        valid_pfs = [r.profit_factor for r in self.results.values() if r.profit_factor < float('inf') and r.total_trades > 0]
        avg_pf = np.mean(valid_pfs) if valid_pfs else 0.0

        print(f"\nOverall Statistics:")
        print(f"  Instruments tested: {len(self.results)}")
        print(f"  Total trades: {total_trades}")
        print(f"  Overall win rate: {avg_win_rate:.1%}")
        print(f"  Total P&L: {total_pnl:.2f}%")
        print(f"  Avg Sharpe: {avg_sharpe:.2f}")
        print(f"  Avg Profit Factor: {avg_pf:.2f}")

        # Per-instrument table
        print(f"\n{'Ticker':<12} {'Trades':>8} {'Win Rate':>10} {'Net P&L':>10} {'Max DD':>10} {'Sharpe':>8} {'PF':>8} {'Avg Dur':>10}")
        print("-"*80)

        for ticker, result in sorted(self.results.items()):
            pf_str = f"{result.profit_factor:.2f}" if result.profit_factor < float('inf') else "inf"
            print(f"{ticker:<12} {result.total_trades:>8} {result.win_rate:>10.1%} {result.net_pnl_pct:>10.2f}% {result.max_drawdown_pct:>9.2f}% {result.sharpe_ratio:>8.2f} {pf_str:>8} {result.avg_trade_duration_bars:>9.1f}b")

        print("\n" + "="*80)

    def export_results(self, filename: str):
        """Export results to JSON."""
        export_data = {
            'strategy': 'quick_mode_v1',
            'parameters': {
                'min_confidence': self.min_confidence,
                'rsi_momentum_threshold': self.rsi_momentum_threshold,
                'atr_stop_multiplier': self.atr_stop_multiplier,
                'atr_target_multiplier': self.atr_target_multiplier,
                'require_volume': self.require_volume,
                'min_volume_ratio': self.min_volume_ratio
            },
            'backtest_days': self.days,
            'run_date': datetime.now().isoformat(),
            'summary': {
                'total_instruments': len(self.results),
                'total_trades': sum(r.total_trades for r in self.results.values()),
                'overall_pnl_pct': sum(r.net_pnl_pct for r in self.results.values())
            },
            'instruments': {ticker: asdict(result) for ticker, result in self.results.items()},
            'trades': self.all_trades
        }

        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"Results exported to {filename}")


async def main():
    parser = argparse.ArgumentParser(description="Quick Strategy Backtest")
    parser.add_argument('--days', type=int, default=14, help='Number of days to backtest')
    parser.add_argument('--tickers', nargs='+', help='Specific tickers to test')
    parser.add_argument('--output', type=str, default='quick_backtest.json', help='Output file')

    args = parser.parse_args()

    # Filter instruments
    instruments = ALL_INSTRUMENTS
    if args.tickers:
        instruments = [i for i in ALL_INSTRUMENTS if i["ticker"] in args.tickers]
        if not instruments:
            print(f"No matching instruments for: {args.tickers}")
            print(f"Available: {[i['ticker'] for i in ALL_INSTRUMENTS]}")
            return

    print("\n" + "="*60)
    print(f"QUICK MODE STRATEGY BACKTEST ({args.days} days)")
    print("="*60)

    backtester = QuickStrategyBacktester(days=args.days)
    await backtester.run_all_backtests(instruments)
    backtester.print_summary()
    backtester.export_results(args.output)


if __name__ == "__main__":
    asyncio.run(main())
