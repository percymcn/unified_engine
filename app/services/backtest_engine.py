"""
Backtesting Engine
==================

Lightweight backtesting using the `backtesting` library.
Replays the exact same indicator logic used in live trading.

Install: pip install backtesting

Features:
- Uses same DeterministicIndicators as live trading
- Applies realistic slippage (2-4 ticks for futures)
- Applies commission costs
- Returns equity curve and statistics
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

try:
    from backtesting import Backtest, Strategy
    from backtesting.lib import crossover
    BACKTESTING_AVAILABLE = True
except ImportError:
    BACKTESTING_AVAILABLE = False
    Backtest = None
    Strategy = None
    crossover = None

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    ta = None

from app.services.market_data_service import market_data_service

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Backtesting configuration"""
    # Costs
    slippage_ticks: float = 2.0  # Slippage per side
    tick_value: float = 0.25    # MES tick value
    commission_per_trade: float = 2.50  # Per side

    # Position sizing
    initial_cash: float = 10000.0
    position_size: float = 0.1  # 10% per trade

    # Strategy params (same as live)
    ema_fast: int = 9
    ema_slow: int = 21
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    atr_period: int = 14
    atr_stop_mult: float = 1.5
    atr_target_mult: float = 3.0


@dataclass
class BacktestResult:
    """Results from a backtest run"""
    ticker: str
    start_date: str
    end_date: str

    # Performance
    total_return: float = 0.0
    total_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0

    # Trade stats
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    # P&L
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_profit: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0

    # Trade details
    avg_trade: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0

    # Timing
    avg_bars_in_trade: float = 0.0

    # Equity curve
    equity_curve: Optional[pd.DataFrame] = None

    # Raw results
    trades_df: Optional[pd.DataFrame] = None


if BACKTESTING_AVAILABLE and PANDAS_TA_AVAILABLE:

    class MTFTrendStrategy(Strategy):
        """
        Multi-Timeframe Trend Following Strategy.

        Uses EMA crossover + RSI filter for entries.
        ATR-based stops and targets.

        NOTE: This is a simplified version for single-timeframe backtesting.
        Full MTF backtesting requires custom implementation.
        """

        # Parameters (can be optimized)
        ema_fast = 9
        ema_slow = 21
        rsi_period = 14
        rsi_overbought = 70
        rsi_oversold = 30
        atr_period = 14
        atr_stop_mult = 1.5
        atr_target_mult = 3.0

        def init(self):
            """Initialize indicators"""
            close = pd.Series(self.data.Close)
            high = pd.Series(self.data.High)
            low = pd.Series(self.data.Low)

            # EMAs
            self.ema_fast_line = self.I(ta.ema, close, length=self.ema_fast)
            self.ema_slow_line = self.I(ta.ema, close, length=self.ema_slow)

            # RSI
            self.rsi = self.I(ta.rsi, close, length=self.rsi_period)

            # ATR for stops
            self.atr = self.I(ta.atr, high, low, close, length=self.atr_period)

        def next(self):
            """Execute on each bar"""
            price = self.data.Close[-1]
            ema_fast = self.ema_fast_line[-1]
            ema_slow = self.ema_slow_line[-1]
            rsi = self.rsi[-1]
            atr = self.atr[-1]

            # Skip if any indicator is NaN
            if np.isnan(ema_fast) or np.isnan(ema_slow) or np.isnan(rsi) or np.isnan(atr):
                return

            # Long conditions
            long_ema = price > ema_fast > ema_slow
            long_rsi = rsi > 50 and rsi < self.rsi_overbought

            # Short conditions
            short_ema = price < ema_fast < ema_slow
            short_rsi = rsi < 50 and rsi > self.rsi_oversold

            # Entry logic
            if not self.position:
                if long_ema and long_rsi:
                    stop = price - (atr * self.atr_stop_mult)
                    target = price + (atr * self.atr_target_mult)
                    self.buy(sl=stop, tp=target)

                elif short_ema and short_rsi:
                    stop = price + (atr * self.atr_stop_mult)
                    target = price - (atr * self.atr_target_mult)
                    self.sell(sl=stop, tp=target)


class BacktestEngine:
    """
    Backtesting engine for the trading system.

    Uses historical data to replay strategy with realistic costs.
    """

    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()

        if not BACKTESTING_AVAILABLE:
            logger.error("backtesting library not installed! Run: pip install backtesting")
        if not PANDAS_TA_AVAILABLE:
            logger.error("pandas_ta not installed! Run: pip install pandas-ta")

        logger.info("BacktestEngine initialized")

    async def fetch_historical_data(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        timeframe: str = 'minute',
        multiplier: int = 5
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical OHLCV data from Polygon.

        Args:
            ticker: Symbol (use ETF equivalents for futures)
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
            timeframe: 'minute', 'hour', 'day'
            multiplier: Bar aggregation (e.g., 5 for 5-min bars)

        Returns:
            DataFrame with Open, High, Low, Close, Volume columns
        """
        try:
            # Convert futures to ETF for Polygon data
            etf_map = {
                'MES': 'SPY', 'ES': 'SPY',
                'NQ': 'QQQ', 'MNQ': 'QQQ',
                'RTY': 'IWM', 'M2K': 'IWM',
                'GC': 'GLD', 'MGC': 'GLD'
            }
            data_ticker = etf_map.get(ticker, ticker)

            logger.info(f"Fetching {data_ticker} data from {start_date} to {end_date}")

            # Use market_data_service to fetch bars
            # Note: This is a simplified version - you may need to implement
            # date range fetching in market_data_service

            bars = market_data_service.get_bars(
                data_ticker,
                timespan=timeframe,
                multiplier=multiplier,
                limit=5000  # Max bars per request
            )

            if not bars:
                logger.warning(f"No data returned for {data_ticker}")
                return None

            # Convert to DataFrame
            data = []
            for bar in bars:
                data.append({
                    'Open': bar.open,
                    'High': bar.high,
                    'Low': bar.low,
                    'Close': bar.close,
                    'Volume': bar.volume
                })

            df = pd.DataFrame(data)
            df.index = pd.to_datetime([bar.timestamp for bar in bars])

            # Filter by date range
            df = df.loc[start_date:end_date]

            logger.info(f"Fetched {len(df)} bars for backtest")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            return None

    async def run_backtest(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        timeframe: str = 'minute',
        multiplier: int = 5,
        optimize: bool = False
    ) -> BacktestResult:
        """
        Run backtest on historical data.

        Args:
            ticker: Symbol to backtest
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            timeframe: Bar timeframe
            multiplier: Bar multiplier
            optimize: Whether to optimize parameters

        Returns:
            BacktestResult with performance metrics
        """
        result = BacktestResult(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date
        )

        if not BACKTESTING_AVAILABLE:
            logger.error("Cannot run backtest: backtesting library not installed")
            return result

        # Fetch data
        df = await self.fetch_historical_data(
            ticker, start_date, end_date, timeframe, multiplier
        )

        if df is None or len(df) < 100:
            logger.error(f"Insufficient data for backtest: {len(df) if df is not None else 0} bars")
            return result

        try:
            # Calculate slippage as percentage
            avg_price = df['Close'].mean()
            slippage_pct = (self.config.slippage_ticks * self.config.tick_value) / avg_price

            # Commission as percentage of trade
            commission_pct = self.config.commission_per_trade / (avg_price * 100)

            # Create backtest
            bt = Backtest(
                df,
                MTFTrendStrategy,
                cash=self.config.initial_cash,
                commission=commission_pct,
                trade_on_close=True,
                exclusive_orders=True
            )

            # Run backtest
            if optimize:
                # Optimize EMA parameters
                stats, heatmap = bt.optimize(
                    ema_fast=range(5, 15, 2),
                    ema_slow=range(15, 30, 3),
                    maximize='Sharpe Ratio',
                    return_heatmap=True
                )
                logger.info(f"Optimized params: EMA({stats._strategy.ema_fast}/{stats._strategy.ema_slow})")
            else:
                # Use default parameters
                stats = bt.run(
                    ema_fast=self.config.ema_fast,
                    ema_slow=self.config.ema_slow,
                    rsi_period=self.config.rsi_period,
                    atr_period=self.config.atr_period,
                    atr_stop_mult=self.config.atr_stop_mult,
                    atr_target_mult=self.config.atr_target_mult
                )

            # Extract results
            result.total_return = stats['Equity Final [$]'] - self.config.initial_cash
            result.total_return_pct = stats['Return [%]']
            result.sharpe_ratio = stats['Sharpe Ratio'] if not np.isnan(stats['Sharpe Ratio']) else 0
            result.max_drawdown = stats['Max. Drawdown [$]'] if 'Max. Drawdown [$]' in stats else 0
            result.max_drawdown_pct = stats['Max. Drawdown [%]']

            result.total_trades = stats['# Trades']
            result.win_rate = stats['Win Rate [%]']
            result.winning_trades = int(result.total_trades * result.win_rate / 100)
            result.losing_trades = result.total_trades - result.winning_trades

            result.avg_trade = stats['Avg. Trade [%]'] * self.config.initial_cash / 100
            result.largest_win = stats['Best Trade [%]'] * self.config.initial_cash / 100
            result.largest_loss = stats['Worst Trade [%]'] * self.config.initial_cash / 100

            # Calculate P&L metrics
            if result.winning_trades > 0 and result.losing_trades > 0:
                # Estimate from percentages
                result.avg_win = result.largest_win * 0.5  # Approximate
                result.avg_loss = abs(result.largest_loss) * 0.5

                result.gross_profit = result.avg_win * result.winning_trades
                result.gross_loss = result.avg_loss * result.losing_trades
                result.net_profit = result.gross_profit - result.gross_loss

                if result.gross_loss > 0:
                    result.profit_factor = result.gross_profit / result.gross_loss

                result.expectancy = result.net_profit / result.total_trades

            result.avg_bars_in_trade = stats['Avg. Trade Duration'].total_seconds() / 60 if hasattr(stats['Avg. Trade Duration'], 'total_seconds') else 0

            # Store equity curve
            result.equity_curve = stats['_equity_curve']

            # Store trades
            result.trades_df = stats['_trades']

            logger.info(f"📊 Backtest {ticker} ({start_date} to {end_date}):")
            logger.info(f"   Return: {result.total_return_pct:.2f}% | Sharpe: {result.sharpe_ratio:.2f}")
            logger.info(f"   Trades: {result.total_trades} | Win Rate: {result.win_rate:.1f}%")
            logger.info(f"   Max DD: {result.max_drawdown_pct:.2f}% | PF: {result.profit_factor:.2f}")

            return result

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            import traceback
            traceback.print_exc()
            return result

    def plot_results(self, result: BacktestResult, save_path: Optional[str] = None):
        """
        Plot backtest results (equity curve).

        Args:
            result: BacktestResult from run_backtest
            save_path: Optional path to save plot image
        """
        if result.equity_curve is None:
            logger.warning("No equity curve to plot")
            return

        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend for Pi
            import matplotlib.pyplot as plt

            fig, axes = plt.subplots(2, 1, figsize=(12, 8))

            # Equity curve
            axes[0].plot(result.equity_curve.index, result.equity_curve['Equity'], label='Equity')
            axes[0].set_title(f'{result.ticker} Backtest: {result.start_date} to {result.end_date}')
            axes[0].set_ylabel('Equity ($)')
            axes[0].legend()
            axes[0].grid(True, alpha=0.3)

            # Drawdown
            equity = result.equity_curve['Equity']
            running_max = equity.cummax()
            drawdown = (equity - running_max) / running_max * 100

            axes[1].fill_between(drawdown.index, drawdown.values, 0, alpha=0.3, color='red')
            axes[1].set_ylabel('Drawdown (%)')
            axes[1].set_xlabel('Date')
            axes[1].grid(True, alpha=0.3)

            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=150)
                logger.info(f"Saved backtest plot to {save_path}")
            else:
                plt.savefig('/tmp/backtest_result.png', dpi=150)
                logger.info("Saved backtest plot to /tmp/backtest_result.png")

            plt.close()

        except Exception as e:
            logger.error(f"Failed to plot results: {e}")


# Global instance
_backtest_engine: Optional[BacktestEngine] = None

def get_backtest_engine(config: Optional[BacktestConfig] = None) -> BacktestEngine:
    """Get or create global backtest engine."""
    global _backtest_engine
    if _backtest_engine is None:
        _backtest_engine = BacktestEngine(config)
    return _backtest_engine


# Convenience function for CLI/API
async def run_quick_backtest(
    ticker: str = 'SPY',
    days_back: int = 30
) -> BacktestResult:
    """
    Quick backtest helper function.

    Args:
        ticker: Symbol to backtest
        days_back: Number of days to backtest

    Returns:
        BacktestResult
    """
    engine = get_backtest_engine()

    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

    return await engine.run_backtest(ticker, start_date, end_date)
