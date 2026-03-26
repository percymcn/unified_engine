#!/usr/bin/env python3
"""
Multi-Timeframe Trendline Breakout Strategy
=============================================
Based on 10-year trendline trading methodology:

1. TOP-DOWN ANALYSIS: Draw trendlines from Monthly → Weekly → Daily → 4H
2. UPWARD TRENDLINES: Connect higher lows  
3. DOWNWARD TRENDLINES: Connect lower highs
4. ENTRY: Break of trendline signals reversal
   - Break DOWN trendline = LONG (anticipate reversal up)
   - Break UP trendline = SHORT (anticipate reversal down)
5. STOP LOSS: On opposing trendline
6. TRAIL: Move to breakeven, then trail into profit
7. EXIT: When price breaks opposing trendline

Author: SmartFlow Engine
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('TrendlineStrategy')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import json

# Suppress verbose logs
logging.getLogger('httpx').setLevel(logging.WARNING)


@dataclass
class Trendline:
    """Represents a trendline."""
    direction: str  # 'up' or 'down'
    slope: float
    intercept: float
    start_idx: int
    end_idx: int
    timeframe: str
    strength: int  # Number of touches
    
    def get_price_at(self, idx: int) -> float:
        """Get trendline price at given index."""
        return self.slope * idx + self.intercept
    
    def is_broken(self, idx: int, price: float, direction: str) -> bool:
        """Check if price has broken the trendline."""
        tl_price = self.get_price_at(idx)
        if self.direction == 'up':
            # Upward trendline broken when price closes below
            return price < tl_price
        else:
            # Downward trendline broken when price closes above
            return price > tl_price


@dataclass 
class TrendlineTrade:
    """Single trade from trendline strategy."""
    entry_time: datetime
    exit_time: Optional[datetime] = None
    direction: str = "long"
    entry_price: float = 0.0
    stop_loss: float = 0.0
    initial_stop: float = 0.0
    exit_price: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    exit_reason: str = ""
    trendline_broken: str = ""  # Which TL triggered entry
    trailing_stop_moved: bool = False
    moved_to_breakeven: bool = False


@dataclass
class TrendlineBacktestResult:
    """Backtest results."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    breakeven_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    net_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    max_drawdown_pct: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_rr_achieved: float = 0.0
    sharpe_ratio: float = 0.0
    trades: List[TrendlineTrade] = field(default_factory=list)


class TrendlineDetector:
    """Detects trendlines using swing highs/lows."""
    
    def __init__(self, lookback: int = 20, min_touches: int = 2):
        self.lookback = lookback
        self.min_touches = min_touches
    
    def find_swing_highs(self, df: pd.DataFrame, window: int = 5) -> List[int]:
        """Find swing high indices."""
        highs = []
        for i in range(window, len(df) - window):
            if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
                highs.append(i)
        return highs
    
    def find_swing_lows(self, df: pd.DataFrame, window: int = 5) -> List[int]:
        """Find swing low indices."""
        lows = []
        for i in range(window, len(df) - window):
            if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
                lows.append(i)
        return lows
    
    def fit_trendline(self, points: List[Tuple[int, float]]) -> Tuple[float, float]:
        """Fit a line through points using least squares."""
        if len(points) < 2:
            return 0, 0
        x = np.array([p[0] for p in points])
        y = np.array([p[1] for p in points])
        
        # Linear regression
        n = len(points)
        sum_x = np.sum(x)
        sum_y = np.sum(y)
        sum_xy = np.sum(x * y)
        sum_x2 = np.sum(x * x)
        
        denom = n * sum_x2 - sum_x * sum_x
        if denom == 0:
            return 0, y.mean()
        
        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n
        
        return slope, intercept
    
    def detect_trendlines(self, df: pd.DataFrame, timeframe: str = '4H') -> List[Trendline]:
        """Detect all valid trendlines in the data."""
        trendlines = []
        
        # Find swing points
        swing_highs = self.find_swing_highs(df, window=5)
        swing_lows = self.find_swing_lows(df, window=5)
        
        # Build upward trendlines (connecting higher lows)
        if len(swing_lows) >= 2:
            for i in range(len(swing_lows) - 1):
                for j in range(i + 1, min(i + 5, len(swing_lows))):
                    idx1, idx2 = swing_lows[i], swing_lows[j]
                    price1, price2 = df['low'].iloc[idx1], df['low'].iloc[idx2]
                    
                    # Only valid if making higher lows (uptrend)
                    if price2 > price1:
                        slope, intercept = self.fit_trendline([
                            (idx1, price1), (idx2, price2)
                        ])
                        
                        # Count touches (price coming close to trendline)
                        touches = self._count_touches(df, slope, intercept, 'up', idx1, idx2)
                        
                        if touches >= self.min_touches:
                            trendlines.append(Trendline(
                                direction='up',
                                slope=slope,
                                intercept=intercept,
                                start_idx=idx1,
                                end_idx=idx2,
                                timeframe=timeframe,
                                strength=touches
                            ))
        
        # Build downward trendlines (connecting lower highs)
        if len(swing_highs) >= 2:
            for i in range(len(swing_highs) - 1):
                for j in range(i + 1, min(i + 5, len(swing_highs))):
                    idx1, idx2 = swing_highs[i], swing_highs[j]
                    price1, price2 = df['high'].iloc[idx1], df['high'].iloc[idx2]
                    
                    # Only valid if making lower highs (downtrend)
                    if price2 < price1:
                        slope, intercept = self.fit_trendline([
                            (idx1, price1), (idx2, price2)
                        ])
                        
                        touches = self._count_touches(df, slope, intercept, 'down', idx1, idx2)
                        
                        if touches >= self.min_touches:
                            trendlines.append(Trendline(
                                direction='down',
                                slope=slope,
                                intercept=intercept,
                                start_idx=idx1,
                                end_idx=idx2,
                                timeframe=timeframe,
                                strength=touches
                            ))
        
        return trendlines
    
    def _count_touches(self, df: pd.DataFrame, slope: float, intercept: float, 
                       direction: str, start_idx: int, end_idx: int) -> int:
        """Count how many times price touches the trendline."""
        touches = 0
        tolerance = df['close'].std() * 0.1  # 10% of price std dev
        
        for i in range(start_idx, min(end_idx + 20, len(df))):
            tl_price = slope * i + intercept
            if direction == 'up':
                if abs(df['low'].iloc[i] - tl_price) < tolerance:
                    touches += 1
            else:
                if abs(df['high'].iloc[i] - tl_price) < tolerance:
                    touches += 1
        
        return touches


class TrendlineStrategyBacktester:
    """
    Backtests the multi-timeframe trendline breakout strategy.
    """
    
    def __init__(self, initial_capital: float = 25000.0, risk_pct: float = 2.0):
        self.initial_capital = initial_capital
        self.risk_pct = risk_pct
        self.capital = initial_capital
        self.detector = TrendlineDetector(lookback=20, min_touches=2)
        self.trades: List[TrendlineTrade] = []
        self.equity_curve: List[float] = [initial_capital]
        
        # Strategy parameters
        self.breakeven_threshold = 1.0  # Move to BE after 1R profit
        self.trail_threshold = 1.5  # Start trailing after 1.5R
        
    async def fetch_data(self, ticker: str, days: int = 90) -> Optional[pd.DataFrame]:
        """Fetch price data from Polygon."""
        try:
            import httpx
            from dotenv import load_dotenv
            load_dotenv()
            
            api_key = os.getenv('POLYGON_API_KEY', 'f402Q_wfDe7D1Q0GLjTzvBAvKoY7uEPV')
            
            # Map futures to ETF
            ticker_map = {
                'MES': 'SPY', 'NQ': 'QQQ', 'MNQ': 'QQQ',
                'RTY': 'IWM', 'GC': 'GLD', 'MYM': 'DIA'
            }
            symbol = ticker_map.get(ticker, ticker)
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Fetch 1-hour data for 4H simulation
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/hour/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
            
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params={'apiKey': api_key, 'limit': 50000})
                data = resp.json()
            
            if 'results' not in data or not data['results']:
                logger.warning(f"No data from Polygon for {ticker}")
                return None
            
            df = pd.DataFrame(data['results'])
            df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
            df = df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'})
            df = df.set_index('timestamp')
            
            logger.info(f"Fetched {len(df)} bars for {ticker}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return None
    
    def resample_to_timeframe(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Resample data to different timeframes."""
        tf_map = {
            '4H': '4h',
            'D': '1D',
            'W': '1W'
        }
        
        rule = tf_map.get(timeframe, '4h')
        
        resampled = df.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        return resampled
    
    def find_active_trendlines(self, df: pd.DataFrame, current_idx: int, 
                                trendlines: List[Trendline]) -> Tuple[Optional[Trendline], Optional[Trendline]]:
        """Find the most relevant up and down trendlines at current bar."""
        up_tl = None
        down_tl = None
        
        current_price = df['close'].iloc[current_idx]
        
        for tl in trendlines:
            # Only consider trendlines that started before current bar
            if tl.end_idx >= current_idx:
                continue
            
            tl_price = tl.get_price_at(current_idx)
            
            # Check if trendline is still valid (not already broken)
            if tl.direction == 'up':
                # Upward TL should be below current price
                if tl_price < current_price:
                    if up_tl is None or tl.strength > up_tl.strength:
                        up_tl = tl
            else:
                # Downward TL should be above current price
                if tl_price > current_price:
                    if down_tl is None or tl.strength > down_tl.strength:
                        down_tl = tl
        
        return up_tl, down_tl
    
    async def run_backtest(self, ticker: str = 'MES', days: int = 90) -> TrendlineBacktestResult:
        """Run the trendline breakout backtest."""
        logger.info(f"Starting trendline backtest for {ticker}, {days} days")
        
        # Fetch data
        df_1h = await self.fetch_data(ticker, days)
        if df_1h is None or len(df_1h) < 100:
            logger.error("Insufficient data for backtest")
            return TrendlineBacktestResult()
        
        # Resample to 4H (trading timeframe)
        df = self.resample_to_timeframe(df_1h, '4H')
        logger.info(f"Resampled to {len(df)} 4H bars")
        
        # Detect trendlines
        trendlines = self.detector.detect_trendlines(df, '4H')
        logger.info(f"Detected {len(trendlines)} trendlines ({sum(1 for t in trendlines if t.direction == 'up')} up, {sum(1 for t in trendlines if t.direction == 'down')} down)")
        
        # Backtest loop
        position = None  # Current open position
        
        for i in range(50, len(df)):  # Start after enough history
            current_bar = df.iloc[i]
            current_price = current_bar['close']
            current_time = df.index[i]
            
            # Find active trendlines
            up_tl, down_tl = self.find_active_trendlines(df, i, trendlines)
            
            # Manage existing position
            if position is not None:
                # Check stop loss
                if position.direction == 'long':
                    if current_bar['low'] <= position.stop_loss:
                        # Stopped out
                        position.exit_price = position.stop_loss
                        position.exit_time = current_time
                        position.pnl = position.exit_price - position.entry_price
                        position.pnl_pct = (position.pnl / position.entry_price) * 100
                        
                        if position.stop_loss == position.entry_price:
                            position.exit_reason = 'breakeven_stop'
                        elif position.stop_loss > position.entry_price:
                            position.exit_reason = 'trailing_stop_profit'
                        else:
                            position.exit_reason = 'stop_loss'
                        
                        self.trades.append(position)
                        self.capital += position.pnl * (self.initial_capital * self.risk_pct / 100) / abs(position.entry_price - position.initial_stop)
                        self.equity_curve.append(self.capital)
                        position = None
                        continue
                    
                    # Trail stop logic
                    risk = abs(position.entry_price - position.initial_stop)
                    current_profit = current_price - position.entry_price
                    
                    # Move to breakeven after 1R profit
                    if not position.moved_to_breakeven and current_profit >= risk * self.breakeven_threshold:
                        position.stop_loss = position.entry_price
                        position.moved_to_breakeven = True
                    
                    # Trail into profit using opposing trendline
                    if position.moved_to_breakeven and up_tl is not None:
                        new_stop = up_tl.get_price_at(i)
                        if new_stop > position.stop_loss and new_stop < current_price:
                            position.stop_loss = new_stop
                            position.trailing_stop_moved = True
                
                else:  # Short position
                    if current_bar['high'] >= position.stop_loss:
                        position.exit_price = position.stop_loss
                        position.exit_time = current_time
                        position.pnl = position.entry_price - position.exit_price
                        position.pnl_pct = (position.pnl / position.entry_price) * 100
                        
                        if position.stop_loss == position.entry_price:
                            position.exit_reason = 'breakeven_stop'
                        elif position.stop_loss < position.entry_price:
                            position.exit_reason = 'trailing_stop_profit'
                        else:
                            position.exit_reason = 'stop_loss'
                        
                        self.trades.append(position)
                        self.capital += position.pnl * (self.initial_capital * self.risk_pct / 100) / abs(position.entry_price - position.initial_stop)
                        self.equity_curve.append(self.capital)
                        position = None
                        continue
                    
                    # Trail stop for shorts
                    risk = abs(position.initial_stop - position.entry_price)
                    current_profit = position.entry_price - current_price
                    
                    if not position.moved_to_breakeven and current_profit >= risk * self.breakeven_threshold:
                        position.stop_loss = position.entry_price
                        position.moved_to_breakeven = True
                    
                    if position.moved_to_breakeven and down_tl is not None:
                        new_stop = down_tl.get_price_at(i)
                        if new_stop < position.stop_loss and new_stop > current_price:
                            position.stop_loss = new_stop
                            position.trailing_stop_moved = True
            
            # Look for new entries (only if no position)
            if position is None:
                # Check for downward trendline break (LONG entry)
                if down_tl is not None:
                    tl_price = down_tl.get_price_at(i)
                    prev_close = df['close'].iloc[i-1]
                    
                    # Break = close above the downward trendline
                    if prev_close <= tl_price and current_price > tl_price:
                        # Entry signal: LONG
                        if up_tl is not None:
                            stop_price = up_tl.get_price_at(i)
                            if stop_price < current_price:
                                position = TrendlineTrade(
                                    entry_time=current_time,
                                    direction='long',
                                    entry_price=current_price,
                                    stop_loss=stop_price,
                                    initial_stop=stop_price,
                                    trendline_broken='down'
                                )
                                logger.debug(f"LONG entry at {current_price:.2f}, stop at {stop_price:.2f}")
                
                # Check for upward trendline break (SHORT entry)
                if position is None and up_tl is not None:
                    tl_price = up_tl.get_price_at(i)
                    prev_close = df['close'].iloc[i-1]
                    
                    # Break = close below the upward trendline
                    if prev_close >= tl_price and current_price < tl_price:
                        # Entry signal: SHORT
                        if down_tl is not None:
                            stop_price = down_tl.get_price_at(i)
                            if stop_price > current_price:
                                position = TrendlineTrade(
                                    entry_time=current_time,
                                    direction='short',
                                    entry_price=current_price,
                                    stop_loss=stop_price,
                                    initial_stop=stop_price,
                                    trendline_broken='up'
                                )
                                logger.debug(f"SHORT entry at {current_price:.2f}, stop at {stop_price:.2f}")
        
        # Close any open position at end
        if position is not None:
            position.exit_price = df['close'].iloc[-1]
            position.exit_time = df.index[-1]
            position.pnl = (position.exit_price - position.entry_price) if position.direction == 'long' else (position.entry_price - position.exit_price)
            position.pnl_pct = (position.pnl / position.entry_price) * 100
            position.exit_reason = 'end_of_data'
            self.trades.append(position)
        
        # Calculate results
        return self._calculate_results()
    
    def _calculate_results(self) -> TrendlineBacktestResult:
        """Calculate backtest metrics."""
        result = TrendlineBacktestResult()
        result.trades = self.trades
        result.total_trades = len(self.trades)
        
        if result.total_trades == 0:
            return result
        
        # Separate wins/losses
        wins = [t for t in self.trades if t.pnl > 0]
        losses = [t for t in self.trades if t.pnl < 0]
        breakevens = [t for t in self.trades if t.pnl == 0]
        
        result.winning_trades = len(wins)
        result.losing_trades = len(losses)
        result.breakeven_trades = len(breakevens)
        result.win_rate = (result.winning_trades / result.total_trades) * 100 if result.total_trades > 0 else 0
        
        result.gross_profit = sum(t.pnl for t in wins) if wins else 0
        result.gross_loss = abs(sum(t.pnl for t in losses)) if losses else 0
        result.net_pnl = result.gross_profit - result.gross_loss
        
        result.profit_factor = result.gross_profit / result.gross_loss if result.gross_loss > 0 else float('inf')
        
        result.avg_win = result.gross_profit / len(wins) if wins else 0
        result.avg_loss = result.gross_loss / len(losses) if losses else 0
        
        # Average R:R achieved
        rr_list = []
        for t in self.trades:
            risk = abs(t.entry_price - t.initial_stop)
            if risk > 0:
                rr_list.append(t.pnl / risk)
        result.avg_rr_achieved = np.mean(rr_list) if rr_list else 0
        
        # Max drawdown
        peak = self.initial_capital
        max_dd = 0
        for eq in self.equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            if dd > max_dd:
                max_dd = dd
        result.max_drawdown_pct = max_dd
        
        # Sharpe (simplified)
        if len(self.equity_curve) > 1:
            returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
            if len(returns) > 0 and np.std(returns) > 0:
                result.sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252)
        
        return result


async def main():
    """Run the trendline backtest."""
    print("=" * 70)
    print("  MULTI-TIMEFRAME TRENDLINE BREAKOUT STRATEGY BACKTEST")
    print("=" * 70)
    print("""
    Strategy Rules:
    1. Detect trendlines (higher lows = UP, lower highs = DOWN)
    2. LONG: Break above downward trendline (anticipate reversal up)
    3. SHORT: Break below upward trendline (anticipate reversal down)  
    4. Stop Loss: Opposing trendline
    5. Trail: Move to breakeven at 1R, then trail on opposing TL
    """)
    
    bt = TrendlineStrategyBacktester(initial_capital=25000.0, risk_pct=2.0)
    
    result = await bt.run_backtest('MES', days=90)
    
    print("\n" + "=" * 70)
    print("  RESULTS")
    print("=" * 70)
    print(f"""
    Total Trades: {result.total_trades}
    Winning Trades: {result.winning_trades}
    Losing Trades: {result.losing_trades}
    Breakeven Trades: {result.breakeven_trades}
    
    Win Rate: {result.win_rate:.1f}%
    Profit Factor: {result.profit_factor:.2f}
    Net P&L: ${result.net_pnl:.2f}
    
    Avg Win: ${result.avg_win:.2f}
    Avg Loss: ${result.avg_loss:.2f}
    Avg R:R Achieved: {result.avg_rr_achieved:.2f}
    
    Max Drawdown: {result.max_drawdown_pct:.2f}%
    Sharpe Ratio: {result.sharpe_ratio:.2f}
    """)
    
    # Trade breakdown
    print("  TRADE BREAKDOWN:")
    print("-" * 70)
    
    exit_reasons = {}
    for t in result.trades:
        exit_reasons[t.exit_reason] = exit_reasons.get(t.exit_reason, 0) + 1
    
    for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
        print(f"    {reason}: {count} trades")
    
    # Direction breakdown
    longs = [t for t in result.trades if t.direction == 'long']
    shorts = [t for t in result.trades if t.direction == 'short']
    
    long_wins = len([t for t in longs if t.pnl > 0])
    short_wins = len([t for t in shorts if t.pnl > 0])
    
    print(f"\n    Longs: {len(longs)} trades, {long_wins} wins ({100*long_wins/len(longs):.1f}% WR)" if longs else "    Longs: 0 trades")
    print(f"    Shorts: {len(shorts)} trades, {short_wins} wins ({100*short_wins/len(shorts):.1f}% WR)" if shorts else "    Shorts: 0 trades")
    
    # Sample trades
    print("\n  SAMPLE TRADES (last 5):")
    print("-" * 70)
    for t in result.trades[-5:]:
        print(f"    {t.direction.upper():5} | Entry: ${t.entry_price:.2f} | Exit: ${t.exit_price:.2f} | P&L: ${t.pnl:.2f} | {t.exit_reason}")
    
    # Export results
    output = {
        'strategy': 'Multi-TF Trendline Breakout',
        'ticker': 'MES',
        'period_days': 90,
        'total_trades': result.total_trades,
        'win_rate': result.win_rate,
        'profit_factor': result.profit_factor,
        'net_pnl': result.net_pnl,
        'max_drawdown': result.max_drawdown_pct,
        'sharpe': result.sharpe_ratio,
        'avg_rr': result.avg_rr_achieved,
    }
    
    with open('trendline_backtest_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n  Results exported to trendline_backtest_results.json")
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
