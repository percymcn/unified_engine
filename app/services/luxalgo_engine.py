"""
LuxAlgo Autonomous Signal Engine
==================================
Pulls OHLCV data from Polygon.io, runs all 5 LuxAlgo indicators,
produces consensus signals, and feeds them into SmartFlow.

Usage:
    from app.services.luxalgo_engine import LuxAlgoEngine, get_luxalgo_engine

    engine = get_luxalgo_engine()
    results = await engine.run_once()          # single pass
    await engine.run_loop(interval_seconds=60) # continuous loop
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

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

# Timeframe map: label → (multiplier, timespan)
TIMEFRAME_MAP = {
    '5m':  (5,  'minute'),
    '15m': (15, 'minute'),
    '1h':  (1,  'hour'),
    '4h':  (4,  'hour'),
    '1d':  (1,  'day'),
}

# Polygon ticker normalisation (futures symbols aren't supported directly)
TICKER_MAP = {
    'ES1!': 'SPY',
    'NQ1!': 'QQQ',
    'MES1!': 'SPY',
    'MNQ1!': 'QQQ',
}


def _polygon_ticker(symbol: str) -> str:
    return TICKER_MAP.get(symbol.upper(), symbol.upper())


def fetch_ohlcv(
    symbol: str,
    timeframe: str = '5m',
    bars: int = 200,
    api_key: str = POLYGON_API_KEY,
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV bars from Polygon.io REST API.
    Returns a DataFrame with columns: timestamp, open, high, low, close, volume, datetime.
    """
    ticker = _polygon_ticker(symbol)
    mult, span = TIMEFRAME_MAP.get(timeframe, (5, 'minute'))

    end_dt = datetime.utcnow()
    # Fetch enough history to cover the requested bars
    lookback_days = max(7, bars // 78 + 5)  # ~78 5m bars per day
    start_dt = end_dt - timedelta(days=lookback_days)

    url = (
        f"{POLYGON_BASE_URL}/v2/aggs/ticker/{ticker}/range/{mult}/{span}"
        f"/{start_dt.strftime('%Y-%m-%d')}/{end_dt.strftime('%Y-%m-%d')}"
    )
    params = {'adjusted': 'true', 'sort': 'asc', 'limit': bars + 50, 'apiKey': api_key}

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = data.get('results', [])
        if not results:
            logger.warning(f"Polygon: no results for {ticker} {timeframe}")
            return None

        df = pd.DataFrame(results)
        df.rename(columns={'t': 'timestamp', 'o': 'open', 'h': 'high',
                            'l': 'low', 'c': 'close', 'v': 'volume'}, inplace=True)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df = df[['timestamp', 'datetime', 'open', 'high', 'low', 'close', 'volume']].copy()
        df = df.tail(bars).reset_index(drop=True)
        return df

    except Exception as e:
        logger.error(f"Polygon fetch error for {ticker} {timeframe}: {e}")
        return None


def _consensus(results: Dict[str, Dict[str, Any]], min_agree: int = 2) -> Optional[str]:
    """
    Given per-indicator results, return 'buy'/'sell' if ≥ min_agree indicators agree,
    else None.
    """
    buy_count = sum(1 for r in results.values() if r.get('signal') == 'buy')
    sell_count = sum(1 for r in results.values() if r.get('signal') == 'sell')
    if buy_count >= min_agree:
        return 'buy'
    if sell_count >= min_agree:
        return 'sell'
    return None


class LuxAlgoEngine:
    """
    Autonomous engine: fetch data → run indicators → consensus → feed SmartFlow.
    """

    DEFAULT_SYMBOLS = ['SPY', 'QQQ']
    DEFAULT_TIMEFRAMES = ['5m', '15m', '1h']
    MIN_AGREE = 2

    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
        api_key: str = POLYGON_API_KEY,
    ):
        self.symbols = symbols or self.DEFAULT_SYMBOLS
        self.timeframes = timeframes or self.DEFAULT_TIMEFRAMES
        self.api_key = api_key
        self._running = False

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def _run_indicators_on_df(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """Run all 5 indicators on a DataFrame."""
        try:
            from app.services.luxalgo_indicators import run_all
            return run_all(df)
        except ImportError:
            logger.error("luxalgo_indicators not importable")
            return {}

    def _process_symbol_timeframe(
        self, symbol: str, timeframe: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch data and run indicators for one symbol/timeframe combo."""
        df = fetch_ohlcv(symbol, timeframe, bars=200, api_key=self.api_key)
        if df is None or len(df) < 50:
            logger.debug(f"Insufficient data for {symbol} {timeframe}")
            return None

        results = self._run_indicators_on_df(df)
        consensus = _consensus(results, self.MIN_AGREE)

        # Average confidence across agreeing signals
        if consensus:
            conf_vals = [
                r.get('confidence', 0.65)
                for r in results.values()
                if r.get('signal') == consensus
            ]
            avg_conf = sum(conf_vals) / len(conf_vals) if conf_vals else 0.65
        else:
            avg_conf = 0.0

        current_price = float(df['close'].iloc[-1])

        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'consensus': consensus,
            'confidence': round(avg_conf, 3),
            'price': current_price,
            'indicator_results': results,
            'timestamp': datetime.utcnow().isoformat(),
        }

    def _feed_to_smartflow(self, result: Dict[str, Any]) -> None:
        """Feed consensus signal into SmartFlow via luxalgo_integration bridge."""
        if not result or not result.get('consensus'):
            return

        try:
            from app.services.luxalgo_integration import get_luxalgo_bridge
            bridge = get_luxalgo_bridge()

            # Determine highest-quality indicator that agrees
            ind_results = result.get('indicator_results', {})
            best_ind = 'smc'
            best_conf = 0.0
            for ind, r in ind_results.items():
                if r.get('signal') == result['consensus']:
                    c = r.get('confidence', 0.65)
                    if c > best_conf:
                        best_conf = c
                        best_ind = ind

            payload = {
                'indicator': best_ind,
                'signal': result['consensus'],
                'symbol': result['symbol'],
                'price': result['price'],
                'timeframe': result['timeframe'].replace('m', '').replace('h', ''),
                'details': {
                    'type':            ind_results.get(best_ind, {}).get('signal_type') or ind_results.get(best_ind, {}).get('type'),
                    'strength':        ind_results.get('oscillator_matrix', {}).get('strength', 'normal'),
                    'confluence_count': ind_results.get('oscillator_matrix', {}).get('confluence_count', 0),
                    'flip':            ind_results.get('evasive_supertrend', {}).get('flip', False),
                    'evasion_event':   ind_results.get('evasive_supertrend', {}).get('evasion_event', False),
                    'order_block':     ind_results.get('pac', {}).get('order_block', False),
                    'r_squared':       ind_results.get('poly_regression', {}).get('r_squared', 0.5),
                    'consensus_count': sum(1 for r in ind_results.values() if r.get('signal') == result['consensus']),
                    'overbought':      ind_results.get('oscillator_matrix', {}).get('overbought', False),
                    'oversold':        ind_results.get('oscillator_matrix', {}).get('oversold', False),
                },
            }

            sf_signal = bridge.process_webhook(payload)
            if sf_signal:
                logger.info(
                    f"🤖 LuxAlgo→SmartFlow: {result['symbol']} {result['timeframe']} "
                    f"{result['consensus'].upper()} conf={result['confidence']:.0%} "
                    f"via {best_ind}"
                )
            else:
                logger.debug(f"LuxAlgo: signal filtered by bridge for {result['symbol']}")

        except Exception as e:
            logger.error(f"LuxAlgo bridge feed error: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_once(self) -> Dict[str, Any]:
        """
        Run all symbols × timeframes once.
        Returns dict of results keyed by 'SYMBOL_TIMEFRAME'.
        """
        all_results = {}
        for symbol in self.symbols:
            for tf in self.timeframes:
                key = f"{symbol}_{tf}"
                try:
                    result = self._process_symbol_timeframe(symbol, tf)
                    all_results[key] = result
                    if result and result.get('consensus'):
                        self._feed_to_smartflow(result)
                        logger.info(
                            f"📊 {key}: consensus={result['consensus']} "
                            f"conf={result['confidence']:.0%} "
                            f"indicators={result['indicator_results'].keys()}"
                        )
                    else:
                        logger.debug(f"📊 {key}: no consensus")
                except Exception as e:
                    logger.error(f"LuxAlgoEngine error for {key}: {e}")
                    all_results[key] = None

        return all_results

    async def run_once_async(self) -> Dict[str, Any]:
        """Async wrapper around run_once (runs in thread pool)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.run_once)

    async def run_loop(self, interval_seconds: int = 60) -> None:
        """Run continuously every interval_seconds until stopped."""
        self._running = True
        logger.info(f"🚀 LuxAlgoEngine starting loop (interval={interval_seconds}s, "
                    f"symbols={self.symbols}, timeframes={self.timeframes})")
        while self._running:
            try:
                results = await self.run_once_async()
                consensus_count = sum(1 for r in results.values() if r and r.get('consensus'))
                logger.info(f"LuxAlgoEngine cycle complete: {consensus_count}/{len(results)} with consensus")
            except Exception as e:
                logger.error(f"LuxAlgoEngine loop error: {e}", exc_info=True)
            await asyncio.sleep(interval_seconds)

    def stop(self) -> None:
        """Stop the run_loop."""
        self._running = False
        logger.info("LuxAlgoEngine stopped")


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_engine_instance: Optional[LuxAlgoEngine] = None


def get_luxalgo_engine(
    symbols: Optional[List[str]] = None,
    timeframes: Optional[List[str]] = None,
) -> LuxAlgoEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = LuxAlgoEngine(symbols=symbols, timeframes=timeframes)
    return _engine_instance
