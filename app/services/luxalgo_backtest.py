"""
LuxAlgo Backtest Engine
========================
Pulls 30 days of OHLCV history from Polygon, runs all 5 indicators,
simulates trades (enter on signal, exit on opposite or 2% stop),
and reports comprehensive performance metrics.

Usage:
    python -m app.services.luxalgo_backtest
    OR:
    from app.services.luxalgo_backtest import LuxAlgoBacktester
    bt = LuxAlgoBacktester()
    results = bt.run('SPY', timeframe='5m', days=30)
    bt.save_results(results)
"""

import json
import logging
import math
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', 'f402Q_wfDe7D1Q0GLjTzvBAvKoY7uEPV')
POLYGON_BASE_URL = 'https://api.polygon.io'
RESULTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'luxalgo_backtest_results.json'
)

TIMEFRAME_MAP = {
    '5m':  (5,  'minute'),
    '15m': (15, 'minute'),
    '1h':  (1,  'hour'),
}

TICKER_MAP = {
    'ES1!': 'SPY', 'NQ1!': 'QQQ', 'MES1!': 'SPY', 'MNQ1!': 'QQQ',
}


def _poly_ticker(symbol: str) -> str:
    return TICKER_MAP.get(symbol.upper(), symbol.upper())


def fetch_history(symbol: str, timeframe: str = '5m', days: int = 30,
                  api_key: str = POLYGON_API_KEY) -> Optional[pd.DataFrame]:
    ticker = _poly_ticker(symbol)
    mult, span = TIMEFRAME_MAP.get(timeframe, (5, 'minute'))
    end_dt   = datetime.utcnow()
    start_dt = end_dt - timedelta(days=days + 5)   # buffer for weekends

    url = (
        f"{POLYGON_BASE_URL}/v2/aggs/ticker/{ticker}/range/{mult}/{span}"
        f"/{start_dt.strftime('%Y-%m-%d')}/{end_dt.strftime('%Y-%m-%d')}"
    )
    params = {'adjusted': 'true', 'sort': 'asc', 'limit': 50000, 'apiKey': api_key}
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results = data.get('results', [])
        if not results:
            logger.warning(f"No data for {ticker} {timeframe}")
            return None
        df = pd.DataFrame(results)
        df.rename(columns={'t': 'timestamp', 'o': 'open', 'h': 'high',
                            'l': 'low', 'c': 'close', 'v': 'volume'}, inplace=True)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df = df[['timestamp', 'datetime', 'open', 'high', 'low', 'close', 'volume']].copy()
        df = df.reset_index(drop=True)
        logger.info(f"Fetched {len(df)} bars for {ticker} {timeframe}")
        return df
    except Exception as e:
        logger.error(f"fetch_history error: {e}")
        return None


def _get_signal(ind_results: Dict[str, Any]) -> Optional[str]:
    """Return consensus signal (buy/sell) if ≥ 2 indicators agree."""
    buy_c  = sum(1 for r in ind_results.values() if r.get('signal') == 'buy')
    sell_c = sum(1 for r in ind_results.values() if r.get('signal') == 'sell')
    if buy_c >= 2:
        return 'buy'
    if sell_c >= 2:
        return 'sell'
    return None


def _sharpe(returns: List[float], risk_free: float = 0.0) -> float:
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns, dtype=float)
    mean = arr.mean()
    std  = arr.std(ddof=1)
    if std == 0:
        return 0.0
    return float((mean - risk_free) / std * math.sqrt(252))


def _max_drawdown(equity_curve: List[float]) -> float:
    if len(equity_curve) < 2:
        return 0.0
    arr = np.array(equity_curve)
    peak = np.maximum.accumulate(arr)
    dd   = (arr - peak) / peak
    return float(dd.min())



def _calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range."""
    high = df['high']
    low  = df['low']
    prev_close = df['close'].shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, min_periods=period).mean()


class LuxAlgoBacktester:
    STOP_LOSS_PCT = 0.02   # 2% stop loss

    def run(
        self,
        symbol: str = 'SPY',
        timeframe: str = '5m',
        days: int = 30,
        api_key: str = POLYGON_API_KEY,
        warmup_bars: int = 50,
        use_atr_stops: bool = False,
        atr_multiplier: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Run the backtest.
        Returns a comprehensive results dict.
        """
        try:
            from app.services.luxalgo_indicators import run_all
        except ImportError as e:
            return {'error': f'luxalgo_indicators import failed: {e}'}

        logger.info(f"LuxAlgo backtest: {symbol} {timeframe} {days}d")

        df = fetch_history(symbol, timeframe, days, api_key)
        if df is None or len(df) < warmup_bars + 10:
            return {'error': f'Insufficient data: {len(df) if df is not None else 0} bars'}

        # Pre-compute ATR series for dynamic stop loss
        atr_series = _calc_atr(df, period=14) if use_atr_stops else None

        trades: List[Dict[str, Any]] = []
        equity  = [1.0]
        trade_returns: List[float] = []

        position     = None   # None, 'long', 'short'
        entry_price  = None
        entry_bar    = None

        WINDOW_SIZE = 200   # fixed look-back window for indicators
        STEP        = 3     # evaluate every 3 bars for speed
        for i in range(warmup_bars, len(df), STEP):
            window = df.iloc[max(0, i - WINDOW_SIZE + 1):i + 1]
            bar    = df.iloc[i]
            price  = float(bar['close'])

            # Exit check first (stop loss)
            if position is not None:
                # Compute dynamic or fixed stop distance
                if use_atr_stops and atr_series is not None and not pd.isna(atr_series.iloc[i]):
                    stop_dist = atr_multiplier * float(atr_series.iloc[i])
                else:
                    stop_dist = entry_price * self.STOP_LOSS_PCT
                if position == 'long':
                    stop = entry_price - stop_dist
                    if price <= stop:
                        ret = (price - entry_price) / entry_price
                        self._record_trade(trades, trade_returns, equity,
                                           entry_bar, bar, position, entry_price, price, ret, 'stop')
                        position = None
                elif position == 'short':
                    stop = entry_price + stop_dist
                    if price >= stop:
                        ret = (entry_price - price) / entry_price
                        self._record_trade(trades, trade_returns, equity,
                                           entry_bar, bar, position, entry_price, price, ret, 'stop')
                        position = None

            # Run indicators every bar
            try:
                ind_results = run_all(window)
                signal = _get_signal(ind_results)
            except Exception as e:
                logger.debug(f"Indicator error at bar {i}: {e}")
                continue

            # Exit on opposite signal
            if position == 'long' and signal == 'sell':
                ret = (price - entry_price) / entry_price
                self._record_trade(trades, trade_returns, equity,
                                   entry_bar, bar, position, entry_price, price, ret, 'signal')
                position = None

            elif position == 'short' and signal == 'buy':
                ret = (entry_price - price) / entry_price
                self._record_trade(trades, trade_returns, equity,
                                   entry_bar, bar, position, entry_price, price, ret, 'signal')
                position = None

            # Enter new position
            if position is None and signal in ('buy', 'sell'):
                position    = 'long' if signal == 'buy' else 'short'
                entry_price = price
                entry_bar   = bar

        # Close any open position at end
        if position is not None and entry_price is not None:
            price = float(df['close'].iloc[-1])
            ret   = (price - entry_price) / entry_price if position == 'long' else (entry_price - price) / entry_price
            self._record_trade(trades, trade_returns, equity,
                               entry_bar, df.iloc[-1], position, entry_price, price, ret, 'eod')

        # ── Metrics ──────────────────────────────────────────────────────────
        n_trades    = len(trades)
        wins        = [t for t in trades if t['pnl_pct'] > 0]
        losses      = [t for t in trades if t['pnl_pct'] <= 0]
        win_rate    = len(wins) / n_trades if n_trades > 0 else 0.0
        avg_win     = float(np.mean([t['pnl_pct'] for t in wins])) if wins else 0.0
        avg_loss    = float(np.mean([t['pnl_pct'] for t in losses])) if losses else 0.0
        total_ret   = float(equity[-1] - 1.0) if equity else 0.0
        sharpe      = _sharpe(trade_returns)
        max_dd      = _max_drawdown(equity)

        results = {
            'symbol':        symbol,
            'stop_type':     f'ATR({atr_multiplier}x)' if use_atr_stops else 'fixed_2pct',
            'timeframe':     timeframe,
            'days':          days,
            'bars_analysed': len(df) - warmup_bars,
            'total_trades':  n_trades,
            'win_rate':      round(win_rate, 4),
            'avg_win_pct':   round(avg_win * 100, 3),
            'avg_loss_pct':  round(avg_loss * 100, 3),
            'sharpe_ratio':  round(sharpe, 3),
            'max_drawdown_pct': round(max_dd * 100, 3),
            'total_return_pct': round(total_ret * 100, 3),
            'final_equity':  round(float(equity[-1]), 6),
            'profit_factor': round(-avg_win / avg_loss, 3) if avg_loss < 0 else None,
            'run_timestamp': datetime.utcnow().isoformat(),
            'trades':        trades[-20:],   # last 20 trades for inspection
        }

        logger.info(
            f"Backtest complete: {n_trades} trades | "
            f"WR={win_rate:.1%} | Sharpe={sharpe:.2f} | "
            f"Return={total_ret:.1%} | MaxDD={max_dd:.1%}"
        )
        return results

    # ------------------------------------------------------------------

    def _record_trade(
        self, trades, trade_returns, equity,
        entry_bar, exit_bar, direction, entry_price, exit_price, ret, reason
    ):
        equity.append(equity[-1] * (1 + ret))
        trade_returns.append(ret)
        trades.append({
            'direction':   direction,
            'entry_price': round(float(entry_price), 4),
            'exit_price':  round(float(exit_price), 4),
            'pnl_pct':     round(ret * 100, 4),
            'exit_reason': reason,
            'entry_time':  str(entry_bar['datetime']) if entry_bar is not None else None,
            'exit_time':   str(exit_bar['datetime']),
        })

    def save_results(
        self, results: Dict[str, Any], path: str = RESULTS_PATH
    ) -> str:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Backtest results saved to {path}")
            return path
        except Exception as e:
            logger.error(f"Failed to save backtest results: {e}")
            return ''


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s'
    )

    symbol    = sys.argv[1] if len(sys.argv) > 1 else 'SPY'
    timeframe = sys.argv[2] if len(sys.argv) > 2 else '5m'
    days      = int(sys.argv[3]) if len(sys.argv) > 3 else 30

    bt      = LuxAlgoBacktester()
    results = bt.run(symbol, timeframe, days)
    path    = bt.save_results(results)

    print("\n" + "=" * 60)
    print(f"  LuxAlgo Backtest: {symbol} {timeframe} ({days}d)")
    print("=" * 60)
    for k, v in results.items():
        if k != 'trades':
            print(f"  {k:25s}: {v}")
    print(f"\n  Results saved → {path}")
    print("=" * 60)
