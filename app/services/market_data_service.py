"""
Market Data Service
===================

Provides technical indicators and price data from Polygon.io (Massive.com) and ProjectX
real-time data for SmartFlow confirmation filters and AI Strategy Suite.

Features:
- **HYBRID DATA**: ProjectX real-time prices + Polygon historical patterns
- Real-time current prices from ProjectX futures (MES, MNQ, MYM, MGC)
- Historical 5-min bars from Polygon.io for pattern analysis
- EMA calculation (9/20 periods)
- RSI calculation (14 periods)
- Volume analysis (20-period average)
- Fibonacci retracement levels (auto swing detection)
- Price confirmation for SmartFlow signals
- Rate limiting: Free tier = 5 calls/min, caches aggressively

Data Sources:
- ProjectX: Real-time bid/ask/last for futures (MES, MNQ, MYM, MGC)
- Polygon: Historical bars for ETFs (SPY, QQQ, DIA, GLD) - 15-30min delayed

Rate Limit Strategy (Free Tier - 5 calls/min):
- Cache TTL: 2 minutes for intraday data
- Batch requests: Get all tickers in sequence with delays
- Pre-fetch: Load all SmartFlow tickers on startup
- Smart refresh: Only refresh stale data
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, asdict
import time
import threading
from collections import deque

if TYPE_CHECKING:
    from app.services.projectx_sdk_service import ProjectXSDKService

logger = logging.getLogger(__name__)


class RateLimiter:
    """Thread-safe rate limiter for API calls"""

    def __init__(self, calls_per_minute: int = 5):
        self.calls_per_minute = calls_per_minute
        self.call_times = deque(maxlen=calls_per_minute)
        self.lock = threading.Lock()

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        with self.lock:
            now = time.time()

            # Remove calls older than 1 minute
            while self.call_times and (now - self.call_times[0]) > 60:
                self.call_times.popleft()

            # If at limit, wait until oldest call expires
            if len(self.call_times) >= self.calls_per_minute:
                sleep_time = 60 - (now - self.call_times[0]) + 0.5
                if sleep_time > 0:
                    logger.debug(f"Rate limit: waiting {sleep_time:.1f}s")
                    time.sleep(sleep_time)

            # Record this call
            self.call_times.append(time.time())

    def calls_remaining(self) -> int:
        """Get remaining calls in current window"""
        with self.lock:
            now = time.time()
            recent = sum(1 for t in self.call_times if (now - t) < 60)
            return max(0, self.calls_per_minute - recent)


@dataclass
class Bar:
    """OHLCV bar data"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class FibLevels:
    """Fibonacci retracement levels"""
    swing_high: float
    swing_low: float
    level_0_236: float
    level_0_382: float
    level_0_5: float
    level_0_618: float
    level_0_786: float
    trend: str  # 'uptrend' or 'downtrend'
    swing_high_time: datetime
    swing_low_time: datetime


@dataclass
class RealtimeQuote:
    """Real-time price quote from ProjectX"""
    symbol: str
    last_price: float
    bid: float
    ask: float
    volume: int
    timestamp: datetime
    source: str  # 'projectx' or 'polygon'


@dataclass
class HybridMarketData:
    """Combined real-time + historical market data"""
    symbol: str
    current_price: float  # Real-time from ProjectX
    bid: float
    ask: float
    spread: float
    bars: List[Bar]  # Historical from Polygon
    ema_9: Optional[float] = None
    ema_20: Optional[float] = None
    rsi: Optional[float] = None
    fib_levels: Optional[FibLevels] = None
    realtime_source: str = 'projectx'  # Which source provided real-time data
    historical_source: str = 'polygon'  # Which source provided historical data
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MarketDataService:
    """
    Hybrid market data service using ProjectX (real-time) + Polygon.io (historical patterns)

    Data Sources:
    - ProjectX: Real-time futures prices (MES, MNQ, MYM, MGC) - zero delay
    - Polygon: Historical bars for pattern analysis - 15-30min delayed but good for indicators

    Symbol Mapping:
    - MES (ProjectX real-time) ↔ SPY (Polygon patterns)
    - MNQ (ProjectX real-time) ↔ QQQ (Polygon patterns)
    - MYM (ProjectX real-time) ↔ DIA (Polygon patterns)
    - MGC (ProjectX real-time) ↔ GLD (Polygon patterns)

    Rate limiting strategy for free tier (5 calls/min):
    - Aggressive caching (2-5 min TTL)
    - Rate limiter with automatic waiting
    - Batch pre-fetching for known tickers
    """

    # SmartFlow tickers to pre-fetch
    SMARTFLOW_TICKERS = ['SPY', 'QQQ', 'GLD', 'IWM', 'DIA', 'VIX', 'UVXY']

    # Common futures/forex tickers for AI analysis
    EXTENDED_TICKERS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMD', 'META', 'GOOGL', 'AMZN']

    # ProjectX futures → ETF mapping (for pattern analysis)
    FUTURES_TO_ETF = {
        'MES': 'SPY',    # E-mini S&P 500 → SPDR S&P 500
        'MNQ': 'QQQ',    # E-mini Nasdaq → Invesco QQQ
        'MYM': 'DIA',    # E-mini Dow → SPDR Dow Jones
        'MGC': 'GLD',    # E-mini Gold → SPDR Gold
        'ES': 'SPY',     # Full-size S&P 500
        'NQ': 'QQQ',     # Full-size Nasdaq
        'YM': 'DIA',     # Full-size Dow
        'GC': 'GLD',     # Full-size Gold
    }

    # Reverse mapping
    ETF_TO_FUTURES = {v: k for k, v in FUTURES_TO_ETF.items() if k.startswith('M')}  # Prefer micros

    def __init__(self, projectx_service: Optional['ProjectXSDKService'] = None):
        # ProjectX service for real-time data
        self.projectx_service = projectx_service

        # Try Docker secret first, then environment variable
        self.api_key = None
        secret_path = "/run/secrets/polygon_api_key"
        if os.path.exists(secret_path):
            try:
                with open(secret_path, "r") as f:
                    self.api_key = f.read().strip()
                logger.info("Market Data Service: Loaded Polygon API key from Docker secret")
            except Exception as e:
                logger.error(f"Failed to read Polygon API key from secret: {e}")

        if not self.api_key:
            self.api_key = os.getenv("POLYGON_API_KEY", "")

        self.base_url = "https://api.polygon.io"
        self.cache: Dict[str, Dict] = {}  # ticker -> data cache
        self.cache_ttl = 120  # Cache for 2 minutes (balance freshness vs rate limits)
        self.extended_cache_ttl = 300  # 5 min cache for less critical data
        self.realtime_cache_ttl = 10  # Cache real-time quotes for 10 seconds only

        # Rate limiter: 5 calls/min for free tier, 100+ for paid
        calls_per_min = int(os.getenv("POLYGON_RATE_LIMIT", "5"))
        self.rate_limiter = RateLimiter(calls_per_minute=calls_per_min)

        data_sources = []
        if self.projectx_service:
            data_sources.append("ProjectX (real-time)")
        if self.api_key:
            data_sources.append(f"Polygon ({calls_per_min}/min)")

        if not data_sources:
            logger.warning("No market data sources configured")
        else:
            logger.info(f"Hybrid Market Data Service initialized: {', '.join(data_sources)}")

    def set_projectx_service(self, projectx_service: 'ProjectXSDKService'):
        """
        Inject ProjectX service after initialization.
        Allows lazy loading of ProjectX without circular dependencies.
        """
        self.projectx_service = projectx_service
        logger.info("✅ ProjectX real-time data integration enabled")

    def _get_cache(self, ticker: str, data_type: str) -> Optional[dict]:
        """Get cached data if still valid"""
        if ticker not in self.cache:
            return None

        cache_entry = self.cache[ticker].get(data_type)
        if not cache_entry:
            return None

        # Check if cache is still valid
        if time.time() - cache_entry['timestamp'] < self.cache_ttl:
            return cache_entry['data']

        return None

    def _set_cache(self, ticker: str, data_type: str, data: dict):
        """Cache data with timestamp"""
        if ticker not in self.cache:
            self.cache[ticker] = {}

        self.cache[ticker][data_type] = {
            'data': data,
            'timestamp': time.time()
        }

    def get_bars(self, ticker: str, timespan: str = 'minute', multiplier: int = 5, limit: int = 50) -> List[Bar]:
        """
        Get OHLCV bars from Polygon.io

        Args:
            ticker: Stock ticker (SPY, QQQ, GLD, IWM)
            timespan: 'minute', 'hour', 'day'
            multiplier: Aggregate bars (5 for 5-min bars)
            limit: Number of bars to fetch (max 50 on free tier)

        Returns:
            List of Bar objects
        """
        if not self.api_key:
            return []

        # Check cache first
        cache_key = f"bars_{timespan}_{multiplier}_{limit}"
        cached = self._get_cache(ticker, cache_key)
        if cached:
            return cached

        try:
            # Wait for rate limiter before making API call
            self.rate_limiter.wait_if_needed()

            # Get bars from last 2 days to ensure we have enough data
            to_date = datetime.now()
            from_date = to_date - timedelta(days=2)

            url = f"{self.base_url}/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date.strftime('%Y-%m-%d')}/{to_date.strftime('%Y-%m-%d')}"

            params = {
                'apiKey': self.api_key,
                'limit': limit,
                'sort': 'desc'  # Most recent first
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Accept both OK and DELAYED status (DELAYED is normal after market close)
            if data.get('status') not in ['OK', 'DELAYED']:
                logger.error(f"Polygon API error: {data}")
                return []

            bars = []
            for result in data.get('results', [])[:limit]:
                bars.append(Bar(
                    timestamp=datetime.fromtimestamp(result['t'] / 1000),
                    open=result['o'],
                    high=result['h'],
                    low=result['l'],
                    close=result['c'],
                    volume=result['v']
                ))

            # Reverse to get chronological order
            bars.reverse()

            # Cache the result
            self._set_cache(ticker, cache_key, bars)

            logger.debug(f"Fetched {len(bars)} bars for {ticker}")
            return bars

        except Exception as e:
            logger.error(f"Failed to fetch bars for {ticker}: {e}")
            return []

    def calculate_ema(self, bars: List[Bar], period: int) -> float:
        """
        Calculate Exponential Moving Average

        Args:
            bars: List of Bar objects (chronological order)
            period: EMA period (e.g., 9, 20)

        Returns:
            Current EMA value
        """
        if len(bars) < period:
            return 0.0

        # Get closing prices
        closes = [bar.close for bar in bars]

        # Calculate SMA for first value
        sma = sum(closes[:period]) / period

        # Calculate EMA
        multiplier = 2 / (period + 1)
        ema = sma

        for close in closes[period:]:
            ema = (close * multiplier) + (ema * (1 - multiplier))

        return ema

    def calculate_rsi(self, bars: List[Bar], period: int = 14) -> float:
        """
        Calculate Relative Strength Index

        Args:
            bars: List of Bar objects (chronological order)
            period: RSI period (default 14)

        Returns:
            Current RSI value (0-100)
        """
        if len(bars) < period + 1:
            return 50.0  # Neutral if not enough data

        # Get closing prices
        closes = [bar.close for bar in bars]

        # Calculate price changes
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]

        # Separate gains and losses
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]

        # Calculate initial average gain/loss (SMA)
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # Calculate subsequent average gain/loss (EMA style)
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        # Calculate RSI
        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_volume_avg(self, bars: List[Bar], period: int = 20) -> float:
        """
        Calculate average volume

        Args:
            bars: List of Bar objects
            period: Lookback period

        Returns:
            Average volume
        """
        if len(bars) < period:
            return 0.0

        recent_bars = bars[-period:]
        total_volume = sum(bar.volume for bar in recent_bars)
        return total_volume / period

    def detect_swing_points(self, bars: List[Bar], lookback: int = 20) -> Tuple[float, float, datetime, datetime]:
        """
        Auto-detect swing high and swing low

        Args:
            bars: List of Bar objects
            lookback: Number of bars to analyze (20-50)

        Returns:
            (swing_high, swing_low, high_time, low_time)
        """
        if len(bars) < lookback:
            lookback = len(bars)

        recent_bars = bars[-lookback:]

        # Find highest high and lowest low
        swing_high_bar = max(recent_bars, key=lambda b: b.high)
        swing_low_bar = min(recent_bars, key=lambda b: b.low)

        return (
            swing_high_bar.high,
            swing_low_bar.low,
            swing_high_bar.timestamp,
            swing_low_bar.timestamp
        )

    def calculate_fibonacci_levels(self, high: float, low: float) -> Dict[str, float]:
        """
        Calculate Fibonacci retracement levels

        Args:
            high: Swing high
            low: Swing low

        Returns:
            Dict of Fibonacci levels
        """
        diff = high - low

        return {
            '0.236': high - (diff * 0.236),
            '0.382': high - (diff * 0.382),
            '0.5': high - (diff * 0.5),
            '0.618': high - (diff * 0.618),
            '0.786': high - (diff * 0.786)
        }

    def get_fib_levels(self, ticker: str, lookback: int = 50) -> Optional[FibLevels]:
        """
        Get Fibonacci retracement levels for a ticker

        Args:
            ticker: Stock ticker
            lookback: Number of bars to analyze (20-50)

        Returns:
            FibLevels object or None
        """
        # Check cache
        cache_key = f"fib_{lookback}"
        cached = self._get_cache(ticker, cache_key)
        if cached:
            return cached

        # Get bars
        bars = self.get_bars(ticker, timespan='minute', multiplier=5, limit=lookback)
        if len(bars) < 20:
            return None

        # Detect swing points
        swing_high, swing_low, high_time, low_time = self.detect_swing_points(bars, lookback)

        # Calculate Fibonacci levels
        fib_dict = self.calculate_fibonacci_levels(swing_high, swing_low)

        # Determine trend (which came first - high or low?)
        trend = 'uptrend' if low_time < high_time else 'downtrend'

        fib_levels = FibLevels(
            swing_high=swing_high,
            swing_low=swing_low,
            level_0_236=fib_dict['0.236'],
            level_0_382=fib_dict['0.382'],
            level_0_5=fib_dict['0.5'],
            level_0_618=fib_dict['0.618'],
            level_0_786=fib_dict['0.786'],
            trend=trend,
            swing_high_time=high_time,
            swing_low_time=low_time
        )

        # Cache the result
        self._set_cache(ticker, cache_key, fib_levels)

        return fib_levels

    def check_fib_confluence(self, ticker: str, current_price: float, signal_direction: str) -> Tuple[bool, float]:
        """
        Check if price is near key Fibonacci level and aligned with signal

        Args:
            ticker: Stock ticker
            current_price: Current price
            signal_direction: 'buy' or 'sell'

        Returns:
            (is_confluent, bonus_score)
        """
        fib = self.get_fib_levels(ticker)
        if not fib:
            return False, 0.0

        # Define "near" as within 0.5% of level
        tolerance = current_price * 0.005

        # Check key Fibonacci levels (0.5 and 0.618 most important)
        key_levels = [
            (fib.level_0_5, 1.5),    # 50% retracement: +1.5 bonus
            (fib.level_0_618, 2.0),  # 61.8% golden ratio: +2.0 bonus
            (fib.level_0_382, 1.0),  # 38.2% retracement: +1.0 bonus
        ]

        for level, bonus in key_levels:
            if abs(current_price - level) <= tolerance:
                # Check if signal direction aligns with Fib bounce
                if signal_direction == 'buy':
                    # Bullish: Price should be bouncing up from Fib level in uptrend
                    if fib.trend == 'uptrend' and current_price >= level:
                        logger.info(f"✨ Fib confluence: {ticker} @ ${current_price:.2f} bouncing off {level:.2f} ({bonus:+.1f} bonus)")
                        return True, bonus
                elif signal_direction == 'sell':
                    # Bearish: Price should be rejecting Fib level in downtrend
                    if fib.trend == 'downtrend' and current_price <= level:
                        logger.info(f"✨ Fib confluence: {ticker} @ ${current_price:.2f} rejecting {level:.2f} ({bonus:+.1f} bonus)")
                        return True, bonus

        return False, 0.0

    def get_market_data(self, ticker: str) -> Dict:
        """
        Get comprehensive market data for confirmation filters

        Returns:
            {
                'current_price': float,
                'ema_9': float,
                'ema_20': float,
                'rsi_14': float,
                'volume': int,
                'volume_avg_20': float,
                'volume_spike': bool,
                'fib_levels': FibLevels or None
            }
        """
        bars = self.get_bars(ticker, timespan='minute', multiplier=5, limit=50)
        if not bars:
            return {}

        current_bar = bars[-1]

        ema_9 = self.calculate_ema(bars, 9)
        ema_20 = self.calculate_ema(bars, 20)
        rsi_14 = self.calculate_rsi(bars, 14)
        volume_avg = self.calculate_volume_avg(bars, 20)
        volume_spike = current_bar.volume > (volume_avg * 1.5) if volume_avg > 0 else False
        fib_levels = self.get_fib_levels(ticker, lookback=50)

        return {
            'current_price': current_bar.close,
            'ema_9': ema_9,
            'ema_20': ema_20,
            'rsi_14': rsi_14,
            'volume': current_bar.volume,
            'volume_avg_20': volume_avg,
            'volume_spike': volume_spike,
            'fib_levels': fib_levels,
            'bars': bars  # For additional analysis
        }

    async def get_realtime_quote(self, symbol: str) -> Optional[RealtimeQuote]:
        """
        Get real-time quote from ProjectX.
        Falls back to Polygon if ProjectX unavailable.

        Args:
            symbol: Futures contract (MES, MNQ, MYM, MGC) or stock ticker

        Returns:
            RealtimeQuote or None
        """
        # Check cache first (10 second TTL for real-time)
        cache_key = f"realtime_{symbol}"
        cached = self._get_cache(symbol, cache_key)
        if cached:
            # Check if cache is fresh (10 seconds)
            if time.time() - self.cache.get(symbol, {}).get(cache_key, {}).get('timestamp', 0) < self.realtime_cache_ttl:
                return cached

        # Try ProjectX first for futures
        if self.projectx_service and symbol in ['MES', 'MNQ', 'MYM', 'MGC', 'ES', 'NQ', 'YM', 'GC']:
            try:
                # Get 1-minute bars to get current price
                bars_data = await self.projectx_service.get_market_data(symbol, days=1, interval=1)
                if bars_data and len(bars_data) > 0:
                    last_bar = bars_data[-1]
                    quote = RealtimeQuote(
                        symbol=symbol,
                        last_price=float(last_bar.get('close', last_bar.get('Close', 0))),
                        bid=float(last_bar.get('close', last_bar.get('Close', 0))) - 0.25,  # Estimate
                        ask=float(last_bar.get('close', last_bar.get('Close', 0))) + 0.25,  # Estimate
                        volume=int(last_bar.get('volume', last_bar.get('Volume', 0))),
                        timestamp=datetime.now(),
                        source='projectx'
                    )
                    self._set_cache(symbol, cache_key, quote)
                    logger.debug(f"📊 Real-time quote: {symbol} @ ${quote.last_price:.2f} (ProjectX)")
                    return quote
            except Exception as e:
                logger.debug(f"ProjectX quote failed for {symbol}: {e}")

        # Fallback to Polygon (delayed but still useful)
        if self.api_key:
            try:
                bars = self.get_bars(symbol, timespan='minute', multiplier=1, limit=1)
                if bars:
                    last_bar = bars[-1]
                    quote = RealtimeQuote(
                        symbol=symbol,
                        last_price=last_bar.close,
                        bid=last_bar.close - 0.01,  # Estimate
                        ask=last_bar.close + 0.01,  # Estimate
                        volume=last_bar.volume,
                        timestamp=last_bar.timestamp,
                        source='polygon'
                    )
                    self._set_cache(symbol, cache_key, quote)
                    logger.debug(f"📊 Real-time quote: {symbol} @ ${quote.last_price:.2f} (Polygon)")
                    return quote
            except Exception as e:
                logger.debug(f"Polygon quote failed for {symbol}: {e}")

        return None

    async def get_hybrid_data(self, symbol: str) -> Optional[HybridMarketData]:
        """
        Get hybrid market data: Real-time price from ProjectX + Historical patterns from Polygon.

        This is the key method that combines both data sources for AI analysis.

        Args:
            symbol: Symbol to analyze (MES, SPY, etc.)

        Returns:
            HybridMarketData with real-time + historical combined
        """
        # Determine futures/ETF pair
        futures_symbol = symbol if symbol in self.FUTURES_TO_ETF else self.ETF_TO_FUTURES.get(symbol)
        etf_symbol = self.FUTURES_TO_ETF.get(symbol, symbol)

        logger.debug(f"🔄 Hybrid data: {symbol} → real-time:{futures_symbol or symbol}, patterns:{etf_symbol}")

        # Get real-time quote (prefer futures if available)
        realtime_symbol = futures_symbol if futures_symbol and self.projectx_service else symbol
        quote = await self.get_realtime_quote(realtime_symbol)

        if not quote:
            logger.warning(f"No real-time data for {symbol}")
            return None

        # Get historical bars for patterns (use ETF for better Polygon compatibility)
        bars = self.get_bars(etf_symbol, timespan='minute', multiplier=5, limit=50)
        if not bars:
            logger.warning(f"No historical bars for {etf_symbol}")
            # Still return with just real-time data
            bars = []

        # Calculate indicators from historical data
        ema_9 = self.calculate_ema(bars, 9) if len(bars) >= 9 else None
        ema_20 = self.calculate_ema(bars, 20) if len(bars) >= 20 else None
        rsi = self.calculate_rsi(bars, 14) if len(bars) >= 14 else None
        fib = self.get_fib_levels(etf_symbol, lookback=50) if len(bars) >= 50 else None

        hybrid = HybridMarketData(
            symbol=symbol,
            current_price=quote.last_price,
            bid=quote.bid,
            ask=quote.ask,
            spread=quote.ask - quote.bid,
            bars=bars,
            ema_9=ema_9,
            ema_20=ema_20,
            rsi=rsi,
            fib_levels=fib,
            realtime_source=quote.source,
            historical_source='polygon' if bars else 'none',
            timestamp=datetime.now()
        )

        logger.info(
            f"✅ Hybrid data: {symbol} @ ${quote.last_price:.2f} "
            f"(RT:{quote.source}, Hist:{len(bars)} bars from {etf_symbol})"
        )

        return hybrid

    def get_ai_context(self, ticker: str) -> Dict:
        """
        Get comprehensive market context for AI Strategy Suite analysis.
        Returns human-readable data that Claude can use for analysis.

        This uses cached data aggressively to avoid hitting rate limits.
        """
        if not self.api_key:
            return {'error': 'Polygon API key not configured', 'ticker': ticker}

        try:
            # Get basic market data (uses cache)
            data = self.get_market_data(ticker)
            if not data:
                return {'error': 'No market data available', 'ticker': ticker}

            bars = data.get('bars', [])
            fib = data.get('fib_levels')

            # Calculate additional indicators for AI
            result = {
                'ticker': ticker,
                'timestamp': datetime.now().isoformat(),
                'price': {
                    'current': round(data['current_price'], 2),
                    'change_15m': self._calc_change(bars, 3) if len(bars) >= 3 else None,  # 3 x 5min = 15min (day trading)
                    'change_30m': self._calc_change(bars, 6) if len(bars) >= 6 else None,  # 6 x 5min = 30min (day trading)
                    'change_1h': self._calc_change(bars, 12) if len(bars) >= 12 else None,  # 12 x 5min = 1hr
                    'change_4h': self._calc_change(bars, 48) if len(bars) >= 48 else None,  # 48 x 5min = 4hr
                    'change_daily': self._calc_change(bars, min(len(bars), 78)) if len(bars) >= 78 else self._calc_change(bars, len(bars)),  # 78 x 5min = 6.5hr (trading day)
                    'change_today': self._calc_change(bars, len(bars)) if bars else None,
                },
                'technicals': {
                    'ema_9': round(data['ema_9'], 2),
                    'ema_20': round(data['ema_20'], 2),
                    'ema_trend': 'bullish' if data['ema_9'] > data['ema_20'] else 'bearish',
                    'price_vs_ema9': 'above' if data['current_price'] > data['ema_9'] else 'below',
                    'price_vs_ema20': 'above' if data['current_price'] > data['ema_20'] else 'below',
                    'rsi_14': round(data['rsi_14'], 1),
                    'rsi_signal': 'overbought' if data['rsi_14'] > 70 else ('oversold' if data['rsi_14'] < 30 else 'neutral'),
                },
                'volume': {
                    'current': data['volume'],
                    'avg_20': round(data['volume_avg_20'], 0),
                    'spike': data['volume_spike'],
                    'ratio': round(data['volume'] / data['volume_avg_20'], 2) if data['volume_avg_20'] > 0 else 1.0,
                },
                'fibonacci': None,
                'recent_bars': self._summarize_bars(bars[-10:]) if len(bars) >= 10 else None,
            }

            # Add Fibonacci if available
            if fib:
                result['fibonacci'] = {
                    'trend': fib.trend,
                    'swing_high': round(fib.swing_high, 2),
                    'swing_low': round(fib.swing_low, 2),
                    'levels': {
                        '23.6%': round(fib.level_0_236, 2),
                        '38.2%': round(fib.level_0_382, 2),
                        '50.0%': round(fib.level_0_5, 2),
                        '61.8%': round(fib.level_0_618, 2),
                        '78.6%': round(fib.level_0_786, 2),
                    },
                    'nearest_level': self._find_nearest_fib(data['current_price'], fib),
                }

            return result

        except Exception as e:
            logger.error(f"Error getting AI context for {ticker}: {e}")
            return {'error': str(e), 'ticker': ticker}

    def _calc_change(self, bars: List[Bar], periods: int) -> Optional[float]:
        """Calculate percentage change over N periods"""
        if len(bars) < periods:
            return None
        start_price = bars[-periods].close
        end_price = bars[-1].close
        if start_price == 0:
            return None
        return round(((end_price - start_price) / start_price) * 100, 2)

    def _summarize_bars(self, bars: List[Bar]) -> List[Dict]:
        """Summarize recent bars for AI context"""
        return [{
            'time': bar.timestamp.strftime('%H:%M'),
            'o': round(bar.open, 2),
            'h': round(bar.high, 2),
            'l': round(bar.low, 2),
            'c': round(bar.close, 2),
            'v': bar.volume,
        } for bar in bars]

    def _find_nearest_fib(self, price: float, fib: FibLevels) -> Dict:
        """Find nearest Fibonacci level to current price"""
        levels = [
            ('23.6%', fib.level_0_236),
            ('38.2%', fib.level_0_382),
            ('50.0%', fib.level_0_5),
            ('61.8%', fib.level_0_618),
            ('78.6%', fib.level_0_786),
        ]
        nearest = min(levels, key=lambda x: abs(price - x[1]))
        distance = ((price - nearest[1]) / price) * 100
        return {
            'level': nearest[0],
            'price': round(nearest[1], 2),
            'distance_pct': round(distance, 2),
            'position': 'above' if price > nearest[1] else 'below',
        }

    def get_multi_ticker_context(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Get AI context for multiple tickers efficiently.
        Uses cached data to minimize API calls.
        """
        results = {}
        for ticker in tickers:
            results[ticker] = self.get_ai_context(ticker)
        return results

    def get_rate_limit_status(self) -> Dict:
        """Get current rate limit status"""
        return {
            'calls_remaining': self.rate_limiter.calls_remaining(),
            'calls_per_minute': self.rate_limiter.calls_per_minute,
            'cache_ttl_seconds': self.cache_ttl,
        }


# Global instance
market_data_service = MarketDataService()
