#!/usr/bin/env python3
"""
SMB 2025 Scalp Strategy Backtest
=================================
Converted from TradingView Pine Script

Entry Conditions:
LONG:
  - close > VWAP AND higher_low (low > lowest(5)[1])
  - ATR > EMA(ATR, 20) (volatility filter)
  - RSI > 50
  - ADX > 20 AND (BB_pos < 0.2 OR BB_pos > 0.8)

SHORT:
  - VWAP crosses over close OR midday_fail OR (close < EMA AND close < VWAP AND RSI < 50)
  - ATR > EMA(ATR, 20)
  - ADX > 20 AND (BB_pos < 0.2 OR BB_pos > 0.8)

Exit:
  - TP1: 0.5% (partial)
  - TP2: 1.0% (full)
  - SL: 0.5% long, 0.45% short
  - Shorts get 1.2x TP
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('SMB2025')
logging.getLogger('httpx').setLevel(logging.WARNING)

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import json


@dataclass
class SMBTrade:
    """Single trade from SMB strategy."""
    entry_time: datetime
    exit_time: Optional[datetime] = None
    direction: str = "long"
    entry_price: float = 0.0
    stop_loss: float = 0.0
    tp1_price: float = 0.0
    tp2_price: float = 0.0
    exit_price: float = 0.0
    
    # Partial exits
    tp1_hit: bool = False
    tp1_pnl: float = 0.0
    
    # Final
    pnl: float = 0.0
    pnl_pct: float = 0.0
    exit_reason: str = ""
    
    # Entry signals
    entry_signals: str = ""


@dataclass
class SMBBacktestResult:
    """Backtest results."""
    total_trades: int = 0
    long_trades: int = 0
    short_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    long_win_rate: float = 0.0
    short_win_rate: float = 0.0
    profit_factor: float = 0.0
    net_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    avg_trade: float = 0.0
    trades: List[SMBTrade] = field(default_factory=list)


class SMB2025Backtester:
    """
    SMB 2025 Scalp Strategy Backtester.
    """
    
    def __init__(self, initial_capital: float = 25000.0, risk_pct: float = 2.0):
        self.initial_capital = initial_capital
        self.risk_pct = risk_pct
        self.capital = initial_capital
        self.trades: List[SMBTrade] = []
        self.equity_curve: List[float] = [initial_capital]
        
        # Strategy parameters (from Pine Script)
        self.ema_length = 9
        self.atr_period = 14
        self.tp_percent = 1.0
        self.sl_percent = 0.5
        self.cooldown_bars = 5
        self.adx_period = 14
        self.adx_threshold = 20
        self.bb_length = 20
        self.bb_mult = 2.0
        self.rsi_period = 14
        
        # Partial TP (50% at TP1, rest at TP2)
        self.tp1_pct = 0.5  # 50% of position at TP1
        
    async def fetch_data(self, ticker: str, days: int = 90) -> Optional[pd.DataFrame]:
        """Fetch price data."""
        try:
            import httpx
            
            ticker_map = {
                'MES': 'SPY', 'NQ': 'QQQ', 'MNQ': 'QQQ',
                'RTY': 'IWM', 'GC': 'GLD', 'MYM': 'DIA'
            }
            symbol = ticker_map.get(ticker, ticker)
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            api_key = os.getenv('POLYGON_API_KEY', 'f402Q_wfDe7D1Q0GLjTzvBAvKoY7uEPV')
            
            # Fetch 5-minute data for scalping
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/5/minute/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
            
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params={'apiKey': api_key, 'limit': 50000})
                data = resp.json()
            
            if 'results' not in data or not data['results']:
                # Fallback to hourly
                url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/hour/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, params={'apiKey': api_key, 'limit': 50000})
                    data = resp.json()
                
                if 'results' not in data:
                    logger.warning(f"No data for {ticker}")
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
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all strategy indicators."""
        
        # EMA
        df['ema'] = df['close'].ewm(span=self.ema_length, adjust=False).mean()
        
        # VWAP (cumulative)
        df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
        
        # Reset VWAP daily
        df['date'] = df.index.date
        df['vwap'] = df.groupby('date').apply(
            lambda x: (x['volume'] * (x['high'] + x['low'] + x['close']) / 3).cumsum() / x['volume'].cumsum()
        ).values
        
        # ATR
        tr = pd.DataFrame()
        tr['h-l'] = df['high'] - df['low']
        tr['h-pc'] = abs(df['high'] - df['close'].shift(1))
        tr['l-pc'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = tr.max(axis=1)
        df['atr'] = df['tr'].rolling(window=self.atr_period).mean()
        df['atr_ema'] = df['atr'].ewm(span=20, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ADX
        df['plus_dm'] = np.where(
            (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
            np.maximum(df['high'] - df['high'].shift(1), 0), 0
        )
        df['minus_dm'] = np.where(
            (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
            np.maximum(df['low'].shift(1) - df['low'], 0), 0
        )
        
        df['tr_smooth'] = df['tr'].ewm(span=self.adx_period, adjust=False).mean()
        df['plus_di'] = 100 * df['plus_dm'].ewm(span=self.adx_period, adjust=False).mean() / df['tr_smooth']
        df['minus_di'] = 100 * df['minus_dm'].ewm(span=self.adx_period, adjust=False).mean() / df['tr_smooth']
        
        dx = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = dx.ewm(span=self.adx_period, adjust=False).mean()
        
        # Bollinger Bands
        df['bb_mid'] = df['close'].rolling(window=self.bb_length).mean()
        df['bb_std'] = df['close'].rolling(window=self.bb_length).std()
        df['bb_upper'] = df['bb_mid'] + self.bb_mult * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - self.bb_mult * df['bb_std']
        df['bb_pos'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Lowest low for higher_low check
        df['lowest_5'] = df['low'].rolling(window=5).min().shift(1)
        
        # Hour for midday check
        df['hour'] = df.index.hour
        
        return df
    
    def check_long_entry(self, row: pd.Series, prev_row: pd.Series) -> Tuple[bool, str]:
        """Check long entry conditions."""
        signals = []
        
        # Backside long: close > VWAP and higher_low
        backside_long = row['close'] > row['vwap'] and row['low'] > row['lowest_5']
        if backside_long:
            signals.append("backside_long")
        
        # Volatility filter
        valid_vol = row['atr'] > row['atr_ema']
        if valid_vol:
            signals.append("vol_ok")
        
        # RSI > 50
        rsi_ok = row['rsi'] > 50
        if rsi_ok:
            signals.append("rsi>50")
        
        # Trend filter: ADX > 20 AND (BB pos < 0.2 OR > 0.8)
        adx_ok = row['adx'] > self.adx_threshold
        boll_ok = row['bb_pos'] < 0.2 or row['bb_pos'] > 0.8
        trend_ok = adx_ok and boll_ok
        if trend_ok:
            signals.append(f"trend_ok(ADX={row['adx']:.1f})")
        
        entry = backside_long and valid_vol and rsi_ok and trend_ok
        return entry, " | ".join(signals)
    
    def check_short_entry(self, row: pd.Series, prev_row: pd.Series) -> Tuple[bool, str]:
        """Check short entry conditions."""
        signals = []
        
        # VWAP reject short: VWAP crosses over close
        vwap_reject = prev_row['vwap'] <= prev_row['close'] and row['vwap'] > row['close'] and row['close'] < row['vwap']
        if vwap_reject:
            signals.append("vwap_reject")
        
        # Midday fail: 1pm-3pm AND close crosses under EMA
        midday_cross = prev_row['close'] >= prev_row['ema'] and row['close'] < row['ema']
        midday_fail = (13 <= row['hour'] <= 15) and midday_cross
        if midday_fail:
            signals.append("midday_fail")
        
        # Alternative short: close < EMA and close < VWAP and RSI < 50
        alt_short = row['close'] < row['ema'] and row['close'] < row['vwap'] and row['rsi'] < 50
        if alt_short:
            signals.append("below_ema_vwap")
        
        # Volatility filter
        valid_vol = row['atr'] > row['atr_ema']
        if valid_vol:
            signals.append("vol_ok")
        
        # Trend filter
        adx_ok = row['adx'] > self.adx_threshold
        boll_ok = row['bb_pos'] < 0.2 or row['bb_pos'] > 0.8
        trend_ok = adx_ok and boll_ok
        if trend_ok:
            signals.append(f"trend_ok(ADX={row['adx']:.1f})")
        
        short_signal = vwap_reject or midday_fail or alt_short
        entry = short_signal and valid_vol and trend_ok
        return entry, " | ".join(signals)
    
    async def run_backtest(self, ticker: str = 'MES', days: int = 90) -> SMBBacktestResult:
        """Run the SMB 2025 backtest."""
        logger.info(f"Starting SMB 2025 backtest for {ticker}, {days} days")
        
        # Fetch data
        df = await self.fetch_data(ticker, days)
        if df is None or len(df) < 100:
            logger.error("Insufficient data")
            return SMBBacktestResult()
        
        # Calculate indicators
        df = self.calculate_indicators(df)
        df = df.dropna()
        logger.info(f"Calculated indicators on {len(df)} bars")
        
        # Trading loop
        position = None
        last_exit_bar = -100
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            current_time = df.index[i]
            price = row['close']
            
            # Manage existing position
            if position is not None:
                if position.direction == 'long':
                    # Check TP1 (partial)
                    if not position.tp1_hit and row['high'] >= position.tp1_price:
                        position.tp1_hit = True
                        position.tp1_pnl = (position.tp1_price - position.entry_price) * self.tp1_pct
                    
                    # Check TP2 (full exit)
                    if row['high'] >= position.tp2_price:
                        position.exit_price = position.tp2_price
                        position.exit_time = current_time
                        remaining_pct = 1.0 - (self.tp1_pct if position.tp1_hit else 0)
                        position.pnl = position.tp1_pnl + (position.tp2_price - position.entry_price) * remaining_pct
                        position.pnl_pct = (position.pnl / position.entry_price) * 100
                        position.exit_reason = 'tp2'
                        self._close_position(position)
                        position = None
                        last_exit_bar = i
                        continue
                    
                    # Check SL
                    if row['low'] <= position.stop_loss:
                        position.exit_price = position.stop_loss
                        position.exit_time = current_time
                        position.pnl = position.tp1_pnl + (position.stop_loss - position.entry_price) * (1.0 - (self.tp1_pct if position.tp1_hit else 0))
                        position.pnl_pct = (position.pnl / position.entry_price) * 100
                        position.exit_reason = 'stop_loss'
                        self._close_position(position)
                        position = None
                        last_exit_bar = i
                        continue
                
                else:  # Short
                    # Check TP1 (partial)
                    if not position.tp1_hit and row['low'] <= position.tp1_price:
                        position.tp1_hit = True
                        position.tp1_pnl = (position.entry_price - position.tp1_price) * self.tp1_pct
                    
                    # Check TP2 (full exit)
                    if row['low'] <= position.tp2_price:
                        position.exit_price = position.tp2_price
                        position.exit_time = current_time
                        remaining_pct = 1.0 - (self.tp1_pct if position.tp1_hit else 0)
                        position.pnl = position.tp1_pnl + (position.entry_price - position.tp2_price) * remaining_pct
                        position.pnl_pct = (position.pnl / position.entry_price) * 100
                        position.exit_reason = 'tp2'
                        self._close_position(position)
                        position = None
                        last_exit_bar = i
                        continue
                    
                    # Check SL
                    if row['high'] >= position.stop_loss:
                        position.exit_price = position.stop_loss
                        position.exit_time = current_time
                        position.pnl = position.tp1_pnl + (position.entry_price - position.stop_loss) * (1.0 - (self.tp1_pct if position.tp1_hit else 0))
                        position.pnl_pct = (position.pnl / position.entry_price) * 100
                        position.exit_reason = 'stop_loss'
                        self._close_position(position)
                        position = None
                        last_exit_bar = i
                        continue
            
            # Check for new entries (with cooldown)
            if position is None and (i - last_exit_bar) > self.cooldown_bars:
                # Check long
                long_entry, long_signals = self.check_long_entry(row, prev_row)
                if long_entry:
                    tp_pct = self.tp_percent
                    sl_pct = self.sl_percent
                    
                    position = SMBTrade(
                        entry_time=current_time,
                        direction='long',
                        entry_price=price,
                        stop_loss=price * (1 - sl_pct / 100),
                        tp1_price=price * (1 + tp_pct / 100 * 0.5),
                        tp2_price=price * (1 + tp_pct / 100),
                        entry_signals=long_signals
                    )
                    continue
                
                # Check short (half cooldown)
                if (i - last_exit_bar) > self.cooldown_bars // 2:
                    short_entry, short_signals = self.check_short_entry(row, prev_row)
                    if short_entry:
                        tp_pct = self.tp_percent * 1.2  # Shorts get 1.2x TP
                        sl_pct = self.sl_percent * 0.9  # Tighter SL for shorts
                        
                        position = SMBTrade(
                            entry_time=current_time,
                            direction='short',
                            entry_price=price,
                            stop_loss=price * (1 + sl_pct / 100),
                            tp1_price=price * (1 - tp_pct / 100 * 0.5),
                            tp2_price=price * (1 - tp_pct / 100),
                            entry_signals=short_signals
                        )
        
        # Close any open position
        if position is not None:
            position.exit_price = df['close'].iloc[-1]
            position.exit_time = df.index[-1]
            if position.direction == 'long':
                position.pnl = position.exit_price - position.entry_price
            else:
                position.pnl = position.entry_price - position.exit_price
            position.pnl_pct = (position.pnl / position.entry_price) * 100
            position.exit_reason = 'end_of_data'
            self._close_position(position)
        
        return self._calculate_results()
    
    def _close_position(self, trade: SMBTrade):
        """Close position and update capital."""
        self.trades.append(trade)
        
        # Calculate position size based on risk
        risk_amount = self.initial_capital * self.risk_pct / 100
        risk_per_unit = abs(trade.entry_price - trade.stop_loss)
        
        if risk_per_unit > 0:
            position_size = risk_amount / risk_per_unit
            dollar_pnl = trade.pnl * position_size
            self.capital += dollar_pnl
        
        self.equity_curve.append(self.capital)
    
    def _calculate_results(self) -> SMBBacktestResult:
        """Calculate backtest metrics."""
        result = SMBBacktestResult()
        result.trades = self.trades
        result.total_trades = len(self.trades)
        
        if result.total_trades == 0:
            return result
        
        # Separate by direction
        longs = [t for t in self.trades if t.direction == 'long']
        shorts = [t for t in self.trades if t.direction == 'short']
        
        result.long_trades = len(longs)
        result.short_trades = len(shorts)
        
        # Wins/losses
        wins = [t for t in self.trades if t.pnl > 0]
        losses = [t for t in self.trades if t.pnl < 0]
        
        result.winning_trades = len(wins)
        result.losing_trades = len(losses)
        result.win_rate = (len(wins) / len(self.trades)) * 100 if self.trades else 0
        
        long_wins = [t for t in longs if t.pnl > 0]
        short_wins = [t for t in shorts if t.pnl > 0]
        result.long_win_rate = (len(long_wins) / len(longs)) * 100 if longs else 0
        result.short_win_rate = (len(short_wins) / len(shorts)) * 100 if shorts else 0
        
        # P&L
        result.gross_profit = sum(t.pnl for t in wins) if wins else 0
        result.gross_loss = abs(sum(t.pnl for t in losses)) if losses else 0
        result.net_pnl = self.capital - self.initial_capital
        result.profit_factor = result.gross_profit / result.gross_loss if result.gross_loss > 0 else float('inf')
        result.avg_trade = result.net_pnl / len(self.trades) if self.trades else 0
        
        # Drawdown
        peak = self.initial_capital
        max_dd = 0
        for eq in self.equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            if dd > max_dd:
                max_dd = dd
        result.max_drawdown_pct = max_dd
        
        # Sharpe
        if len(self.equity_curve) > 1:
            returns = np.diff(self.equity_curve) / np.array(self.equity_curve[:-1])
            if len(returns) > 0 and np.std(returns) > 0:
                result.sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252)
        
        return result


async def main():
    """Run the SMB 2025 backtest."""
    print("=" * 70)
    print("  SMB 2025 SCALP STRATEGY BACKTEST")
    print("=" * 70)
    print("""
    Strategy Rules:
    ---------------
    LONG:
      - Close > VWAP AND higher_low (low > lowest(5)[1])
      - ATR > EMA(ATR, 20) - volatility confirmation
      - RSI > 50
      - ADX > 20 AND (BB_pos < 0.2 OR > 0.8)
    
    SHORT:
      - VWAP reject OR midday_fail OR (close < EMA & VWAP, RSI < 50)
      - Same volatility and trend filters
      - 1.2x TP, 0.9x SL (tighter)
    
    Exit:
      - TP1: 0.5% (50% partial close)
      - TP2: 1.0% (remaining position)
      - SL: 0.5% long, 0.45% short
    """)
    
    bt = SMB2025Backtester(initial_capital=25000.0, risk_pct=2.0)
    
    result = await bt.run_backtest('MES', days=90)
    
    print("\n" + "=" * 70)
    print("  RESULTS")
    print("=" * 70)
    print(f"""
    Total Trades: {result.total_trades}
      - Longs:  {result.long_trades} ({result.long_win_rate:.1f}% WR)
      - Shorts: {result.short_trades} ({result.short_win_rate:.1f}% WR)
    
    Overall Win Rate: {result.win_rate:.1f}%
    Profit Factor: {result.profit_factor:.2f}
    
    Net P&L: ${result.net_pnl:.2f}
    Avg Trade: ${result.avg_trade:.2f}
    
    Max Drawdown: {result.max_drawdown_pct:.2f}%
    Sharpe Ratio: {result.sharpe_ratio:.2f}
    """)
    
    # Exit breakdown
    print("  EXIT BREAKDOWN:")
    print("-" * 40)
    exit_reasons = {}
    for t in result.trades:
        exit_reasons[t.exit_reason] = exit_reasons.get(t.exit_reason, 0) + 1
    for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
        pct = count / result.total_trades * 100 if result.total_trades > 0 else 0
        print(f"    {reason}: {count} ({pct:.1f}%)")
    
    # TP1 hit rate
    tp1_hits = len([t for t in result.trades if t.tp1_hit])
    print(f"\n    TP1 Hit Rate: {tp1_hits}/{result.total_trades} ({100*tp1_hits/result.total_trades:.1f}%)" if result.total_trades > 0 else "")
    
    # Sample trades
    print("\n  SAMPLE TRADES (last 5):")
    print("-" * 70)
    for t in result.trades[-5:]:
        print(f"    {t.direction.upper():5} | Entry: ${t.entry_price:.2f} | Exit: ${t.exit_price:.2f} | P&L: {t.pnl_pct:.2f}% | {t.exit_reason}")
        print(f"           Signals: {t.entry_signals[:60]}...")
    
    # Export
    output = {
        'strategy': 'SMB 2025 Scalp',
        'ticker': 'MES',
        'period_days': 90,
        'total_trades': result.total_trades,
        'long_trades': result.long_trades,
        'short_trades': result.short_trades,
        'win_rate': result.win_rate,
        'long_win_rate': result.long_win_rate,
        'short_win_rate': result.short_win_rate,
        'profit_factor': result.profit_factor,
        'net_pnl': result.net_pnl,
        'max_drawdown': result.max_drawdown_pct,
        'sharpe': result.sharpe_ratio,
    }
    
    with open('smb_2025_backtest_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n  Results exported to smb_2025_backtest_results.json")
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
