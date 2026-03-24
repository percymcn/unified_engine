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

import asyncio
import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from app.services.projectx_sdk_service import ProjectXSDKService

logger = logging.getLogger(__name__)

_polygon_request_semaphore: Optional[asyncio.Semaphore] = None


def _get_polygon_request_semaphore() -> asyncio.Semaphore:
    global _polygon_request_semaphore
    if _polygon_request_semaphore is None:
        _polygon_request_semaphore = asyncio.Semaphore(2)
    return _polygon_request_semaphore


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
    CRYPTO_TICKERS = {'BTCUSD', 'ETHUSD', 'X:BTCUSD', 'X:ETHUSD'}
    KRAKEN_PAIR_MAP = {
        'BTCUSD': 'XXBTZUSD',
        'ETHUSD': 'XETHZUSD',
        'X:BTCUSD': 'XXBTZUSD',
        'X:ETHUSD': 'XETHZUSD',
    }
    FUTURES_TICKERS = {
        'MES', 'MNQ', 'MYM', 'MGC', 'M2K',
        'ES', 'NQ', 'YM', 'RTY', 'GC',
    }
    FOREX_TICKERS = {
        'XAUUSD', 'GBPJPY', 'USDJPY',
        'C:XAUUSD', 'C:GBPJPY', 'C:USDJPY',
    }
    POLYGON_CALLS_PER_MINUTE = 4
    FOREX_CALL_INTERVAL_SECONDS = 15
    FOREX_MAX_TICKERS_PER_MINUTE = 4

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
        self.cache_ttl = 300  # Cache for 5 minutes (aggressive caching for free tier)
        self.extended_cache_ttl = 600  # 10 min cache for less critical data (MTF analysis)
        self.realtime_cache_ttl = 30  # Cache real-time quotes for 30 seconds
        self.mtf_cache_ttl = 600  # Cache multi-timeframe analysis for 10 minutes

        # Rate limiter: 5 calls/min for free tier, 100+ for paid
        calls_per_min = int(os.getenv("POLYGON_RATE_LIMIT", "5"))
        self.rate_limiter = RateLimiter(calls_per_minute=calls_per_min)
        self._polygon_call_times: deque = deque()
        self._polygon_lock = threading.Lock()
        self._forex_last_call_time = 0.0
        self._forex_recent_tickers: deque = deque()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._http_client_loop: Optional[asyncio.AbstractEventLoop] = None
        self._http_loop: Optional[asyncio.AbstractEventLoop] = None
        self._http_thread: Optional[threading.Thread] = None

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

    def _ensure_http_loop(self) -> asyncio.AbstractEventLoop:
        if self._http_loop and self._http_loop.is_running():
            return self._http_loop

        loop = asyncio.new_event_loop()
        self._http_loop = loop
        ready = threading.Event()

        def _run_loop() -> None:
            asyncio.set_event_loop(loop)
            ready.set()
            loop.run_forever()

        self._http_thread = threading.Thread(
            target=_run_loop,
            name="market-data-http-loop",
            daemon=True,
        )
        self._http_thread.start()
        ready.wait()
        return loop

    async def _get_client(self) -> httpx.AsyncClient:
        current_loop = asyncio.get_running_loop()
        if (
            self._http_client is not None
            and not self._http_client.is_closed
            and self._http_client_loop is not current_loop
        ):
            logger.warning("Recreating AsyncClient on a new event loop for market data service")
            try:
                await self._http_client.aclose()
            except Exception:
                pass
            self._http_client = None
            self._http_client_loop = None

        if self._http_client is None or self._http_client.is_closed:
            limits = httpx.Limits(max_connections=20, max_keepalive_connections=5)
            self._http_client = httpx.AsyncClient(timeout=15.0, limits=limits)
            self._http_client_loop = current_loop
        return self._http_client

    def _run_http(self, coro):
        loop = self._ensure_http_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()

    def _get_cache(self, ticker: str, data_type: str) -> Optional[dict]:
        """Get cached data if still valid, using appropriate TTL for data type"""
        if ticker not in self.cache:
            return None

        cache_entry = self.cache[ticker].get(data_type)
        if not cache_entry:
            return None

        # Use appropriate TTL based on data type
        if data_type.startswith('realtime'):
            ttl = self.realtime_cache_ttl
        elif data_type.startswith('mtf') or data_type.startswith('multi'):
            ttl = self.mtf_cache_ttl
        elif data_type.startswith('fib') or data_type.startswith('ai_context'):
            ttl = self.extended_cache_ttl
        else:
            ttl = self.cache_ttl

        # Check if cache is still valid
        if time.time() - cache_entry['timestamp'] < ttl:
            logger.debug(f"Cache hit: {ticker}/{data_type} (age: {time.time() - cache_entry['timestamp']:.0f}s, ttl: {ttl}s)")
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

    def _is_crypto_ticker(self, ticker: str) -> bool:
        return ticker.upper() in self.CRYPTO_TICKERS

    def _is_futures_ticker(self, ticker: str) -> bool:
        return ticker.upper() in self.FUTURES_TICKERS

    def _is_forex_ticker(self, ticker: str) -> bool:
        return ticker.upper() in self.FOREX_TICKERS

    def _normalize_forex_ticker(self, ticker: str) -> str:
        symbol = ticker.upper()
        if symbol.startswith('C:'):
            return symbol
        return f"C:{symbol}"

    def normalize_forex_ticker(self, ticker: str) -> str:
        return self._normalize_forex_ticker(ticker)

    def is_polygon_only_ticker(self, ticker: str) -> bool:
        return self._is_forex_ticker(ticker)

    def is_supported_ticker(self, ticker: str) -> bool:
        return self._is_futures_ticker(ticker) or self._is_crypto_ticker(ticker) or self._is_forex_ticker(ticker)

    def _prune_polygon_calls(self, now: float) -> None:
        while self._polygon_call_times and (now - self._polygon_call_times[0]) > 60:
            self._polygon_call_times.popleft()

    def _polygon_calls_remaining(self) -> int:
        with self._polygon_lock:
            now = time.time()
            self._prune_polygon_calls(now)
            return max(0, self.POLYGON_CALLS_PER_MINUTE - len(self._polygon_call_times))

    def get_polygon_rate_limit_remaining(self) -> int:
        return self._polygon_calls_remaining()

    def _reserve_polygon_call(self) -> bool:
        with self._polygon_lock:
            now = time.time()
            self._prune_polygon_calls(now)
            if len(self._polygon_call_times) >= self.POLYGON_CALLS_PER_MINUTE:
                return False
            self._polygon_call_times.append(now)
            return True

    def _can_call_forex(self, ticker: str) -> bool:
        now = time.time()
        if (now - self._forex_last_call_time) < self.FOREX_CALL_INTERVAL_SECONDS:
            return False

        while self._forex_recent_tickers and (now - self._forex_recent_tickers[0][0]) > 60:
            self._forex_recent_tickers.popleft()

        active_tickers = {t for _, t in self._forex_recent_tickers}
        normalized = self._normalize_forex_ticker(ticker)
        if normalized not in active_tickers and len(active_tickers) >= self.FOREX_MAX_TICKERS_PER_MINUTE:
            return False

        return True

    def _record_forex_call(self, ticker: str) -> None:
        now = time.time()
        self._forex_last_call_time = now
        self._forex_recent_tickers.append((now, self._normalize_forex_ticker(ticker)))

    async def _get_kraken_bars(self, ticker: str, multiplier: int, limit: int) -> List[Bar]:
        """Get OHLCV bars from Kraken for crypto tickers."""
        pair = self.KRAKEN_PAIR_MAP.get(ticker.upper())
        if not pair:
            return []

        try:
            url = "https://api.kraken.com/0/public/OHLC"
            params = {'pair': pair, 'interval': multiplier}
            client = await self._get_client()
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            if data.get('error'):
                logger.warning(f"Kraken API error for {ticker}: {data.get('error')}")
                return []

            result = data.get('result', {})
            pair_key = next((key for key in result.keys() if key != 'last'), None)
            if not pair_key:
                logger.warning(f"Kraken response missing pair data for {ticker}")
                return []

            ohlc_data = result.get(pair_key, [])
            if not ohlc_data:
                return []

            bars = []
            for row in ohlc_data[-limit:]:
                bars.append(Bar(
                    timestamp=datetime.fromtimestamp(int(row[0])),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=int(float(row[6]))
                ))

            logger.debug(f"Fetched {len(bars)} Kraken bars for {ticker} ({pair})")
            return bars
        except Exception as e:
            logger.warning(f"Kraken fetch failed for {ticker}: {e}")
            return []

    async def _polygon_get_with_backoff(
        self,
        url: str,
        params: Dict[str, Any],
        timeout: int = 10,
        max_retries: int = 4,
        base_delay: float = 1.0
    ) -> Optional[httpx.Response]:
        """GET with exponential backoff on Polygon 429 responses."""
        response = None
        client = await self._get_client()
        for attempt in range(max_retries + 1):
            if not self._reserve_polygon_call():
                logger.warning("Polygon rate limit reached - skipping request")
                return None
            async with _get_polygon_request_semaphore():
                response = await client.get(url, params=params, timeout=float(timeout))
            if response.status_code != 429:
                return response

            retry_after = response.headers.get("Retry-After")
            try:
                delay = float(retry_after)
            except (TypeError, ValueError):
                delay = base_delay * (2 ** attempt)

            logger.warning(
                f"Polygon 429 for {url} (attempt {attempt + 1}/{max_retries + 1}); "
                f"backing off {delay:.1f}s"
            )
            await asyncio.sleep(delay)

        return response

    def get_bars(self, ticker: str, timespan: str = 'minute', multiplier: int = 5, limit: int = 50) -> List[Bar]:
        return self._run_http(self._get_bars_async(ticker, timespan, multiplier, limit))

    async def _get_bars_async(self, ticker: str, timespan: str = 'minute', multiplier: int = 5, limit: int = 50) -> List[Bar]:
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
        # Check cache first
        cache_key = f"bars_{timespan}_{multiplier}_{limit}"
        cached = self._get_cache(ticker, cache_key)
        if cached:
            return cached

        symbol = ticker.upper()

        if self._is_futures_ticker(symbol) and self.projectx_service:
            try:
                interval_minutes = multiplier if timespan == 'minute' else 60 * multiplier
                bars_data = await self.projectx_service.get_market_data(symbol, days=1, interval=interval_minutes)
                if bars_data:
                    bars = []
                    for row in bars_data[-limit:]:
                        ts = row.get('timestamp') or row.get('time') or row.get('datetime')
                        if isinstance(ts, (int, float)):
                            ts = datetime.fromtimestamp(ts)
                        elif isinstance(ts, str):
                            try:
                                ts = datetime.fromisoformat(ts)
                            except ValueError:
                                ts = datetime.now()
                        else:
                            ts = datetime.now()
                        bars.append(Bar(
                            timestamp=ts,
                            open=float(row.get('open', row.get('Open', 0))),
                            high=float(row.get('high', row.get('High', 0))),
                            low=float(row.get('low', row.get('Low', 0))),
                            close=float(row.get('close', row.get('Close', 0))),
                            volume=int(row.get('volume', row.get('Volume', 0))),
                        ))
                    if bars:
                        self._set_cache(ticker, cache_key, bars)
                        return bars
            except Exception as e:
                logger.debug(f"ProjectX bars failed for {symbol}: {e}")

        if self._is_crypto_ticker(symbol):
            if timespan != 'minute':
                logger.debug(f"Kraken only supports minute timespan via interval; using Polygon for {ticker}")
            else:
                bars = await self._get_kraken_bars(symbol, multiplier=multiplier, limit=limit)
                if bars:
                    self._set_cache(ticker, cache_key, bars)
                    return bars
                logger.info(f"Kraken unavailable for {ticker}, falling back to Polygon")

        if not self._is_futures_ticker(symbol) and not self._is_crypto_ticker(symbol) and not self._is_forex_ticker(symbol):
            return []

        if not self.api_key:
            return []

        try:
            if self._is_forex_ticker(symbol):
                data_ticker = self._normalize_forex_ticker(symbol)
            elif self._is_futures_ticker(symbol):
                data_ticker = self.FUTURES_TO_ETF.get(symbol, symbol)
            else:
                data_ticker = symbol

            if self._is_forex_ticker(symbol):
                if not self._can_call_forex(symbol):
                    logger.info(f"Forex rate limit reached - skipping {symbol}")
                    return []
                self._record_forex_call(symbol)

            # Get bars from last 2 days to ensure we have enough data
            to_date = datetime.now()
            from_date = to_date - timedelta(days=2)

            url = f"{self.base_url}/v2/aggs/ticker/{data_ticker}/range/{multiplier}/{timespan}/{from_date.strftime('%Y-%m-%d')}/{to_date.strftime('%Y-%m-%d')}"

            params = {
                'apiKey': self.api_key,
                'limit': limit,
                'sort': 'desc'  # Most recent first
            }

            max_retries = 0 if self._is_forex_ticker(symbol) else 4
            response = await self._polygon_get_with_backoff(url, params=params, timeout=10, max_retries=max_retries)
            if response is None:
                return []
            if response.status_code == 429:
                logger.error(f"Polygon rate limit exceeded for {ticker} after retries")
                return []
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
        if self.projectx_service and symbol in ['MES', 'MNQ', 'MYM', 'MGC', 'ES', 'NQ', 'YM', 'GC', 'RTY']:
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

        CACHED for 10 minutes to avoid rate limit issues on free tier.
        """
        # Check cache first
        cache_key = f"ai_context_{ticker}"
        cached = self._get_cache(ticker, cache_key)
        if cached:
            logger.debug(f"Using cached AI context for {ticker}")
            return cached

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

            # Add multi-timeframe analysis for day trading
            try:
                mtf_analysis = self.get_multi_timeframe_analysis(ticker)
                if mtf_analysis and 'error' not in mtf_analysis:
                    result['multi_timeframe'] = {
                        'overall_bias': mtf_analysis.get('overall', {}).get('bias', 'unknown'),
                        'bullish_alignment': mtf_analysis.get('overall', {}).get('bullish_alignment', 0),
                        'bearish_alignment': mtf_analysis.get('overall', {}).get('bearish_alignment', 0),
                        'timeframes': mtf_analysis.get('timeframes', {}),
                        'confluences': mtf_analysis.get('confluences', []),
                    }
                    logger.debug(f"Added MTF analysis for {ticker}: {result['multi_timeframe']['overall_bias']}")
            except Exception as e:
                logger.warning(f"Failed to get MTF analysis for {ticker}: {e}")

            # Cache the result
            self._set_cache(ticker, cache_key, result)
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

    def get_multi_timeframe_bars(self, ticker: str, force_minimal: bool = False) -> Dict[str, List[Bar]]:
        """
        Get bars for multiple timeframes for comprehensive day trading analysis.

        RATE LIMIT AWARE: Will reduce timeframes if rate limit is low.

        Timeframes (when not rate limited):
        - 5m: Short-term scalping/momentum (20 bars = ~1.5 hours)
        - 15m: Intraday momentum (20 bars = ~5 hours)
        - 1h: Daily structure context (20 bars = ~20 hours / 3 days)

        Minimal mode (rate limited or force_minimal=True):
        - Only 5m bars (single API call)

        Returns dict with timeframe keys and bar lists.
        """
        # Check cache first for the entire MTF result
        cache_key = f"mtf_bars_{ticker}"
        cached = self._get_cache(ticker, cache_key)
        if cached:
            logger.debug(f"Using cached MTF bars for {ticker}")
            return cached

        data_ticker = self._normalize_forex_ticker(ticker) if self._is_forex_ticker(ticker) else ticker

        timeframes = {}

        # Check rate limit status - be conservative for Polygon-only tickers
        use_polygon = self._is_forex_ticker(data_ticker) or (self._is_futures_ticker(ticker) and not self.projectx_service)
        remaining = self.get_polygon_rate_limit_remaining() if use_polygon else 999

        # Minimal mode: only 5m bars if rate limited or forced
        if force_minimal or remaining <= 2:
            logger.info(f"⚠️ Rate limit low ({remaining} remaining), using minimal MTF for {ticker}")
            bars_5m = self.get_bars(data_ticker, timespan='minute', multiplier=5, limit=20)
            if bars_5m:
                timeframes['5m'] = bars_5m
            self._set_cache(ticker, cache_key, timeframes)
            return timeframes

        # 5-minute bars (20 bars) - PRIMARY for day trading
        bars_5m = self.get_bars(data_ticker, timespan='minute', multiplier=5, limit=20)
        if bars_5m:
            timeframes['5m'] = bars_5m

        # Only fetch additional timeframes if we have calls remaining
        remaining = self.rate_limiter.calls_remaining()

        if remaining >= 2:
            # 15-minute bars (20 bars)
            bars_15m = self.get_bars(data_ticker, timespan='minute', multiplier=15, limit=20)
            if bars_15m:
                timeframes['15m'] = bars_15m

        remaining = self.rate_limiter.calls_remaining()

        if remaining >= 1:
            # 1-hour bars (20 bars) - skip 30m and 4h to save calls
            bars_1h = self.get_bars(data_ticker, timespan='hour', multiplier=1, limit=20)
            if bars_1h:
                timeframes['1h'] = bars_1h

        # Cache the result
        self._set_cache(ticker, cache_key, timeframes)

        logger.info(f"📊 Multi-TF bars for {ticker} (via {data_ticker}): " + ", ".join(f"{tf}={len(bars)}" for tf, bars in timeframes.items()))
        return timeframes

    def _analyze_timeframe(self, bars: List[Bar], timeframe: str) -> Dict:
        """
        Analyze a single timeframe's bars and return indicators.
        Used for multi-timeframe analysis.
        """
        if not bars or len(bars) < 2:
            return {'error': 'Insufficient data', 'timeframe': timeframe}

        current_price = bars[-1].close
        prev_price = bars[-2].close

        # Calculate indicators
        ema_9 = self.calculate_ema(bars, 9) if len(bars) >= 9 else None
        ema_20 = self.calculate_ema(bars, 20) if len(bars) >= 20 else None
        rsi = self.calculate_rsi(bars, 14) if len(bars) >= 14 else None

        # Determine trend
        if ema_9 and ema_20:
            ema_trend = 'bullish' if ema_9 > ema_20 else 'bearish'
        else:
            ema_trend = 'unknown'

        # Price change
        first_bar = bars[0]
        change_pct = ((current_price - first_bar.close) / first_bar.close) * 100

        # Candle analysis (last 5 candles)
        recent = bars[-5:] if len(bars) >= 5 else bars
        bullish_candles = sum(1 for b in recent if b.close > b.open)
        bearish_candles = len(recent) - bullish_candles

        # Volume trend
        if len(bars) >= 10:
            recent_vol_avg = sum(b.volume for b in bars[-5:]) / 5
            older_vol_avg = sum(b.volume for b in bars[-10:-5]) / 5
            vol_trend = 'increasing' if recent_vol_avg > older_vol_avg * 1.1 else ('decreasing' if recent_vol_avg < older_vol_avg * 0.9 else 'stable')
        else:
            vol_trend = 'unknown'

        return {
            'timeframe': timeframe,
            'price': round(current_price, 2),
            'change_pct': round(change_pct, 2),
            'ema_9': round(ema_9, 2) if ema_9 else None,
            'ema_20': round(ema_20, 2) if ema_20 else None,
            'ema_trend': ema_trend,
            'price_vs_ema9': 'above' if ema_9 and current_price > ema_9 else ('below' if ema_9 else 'unknown'),
            'price_vs_ema20': 'above' if ema_20 and current_price > ema_20 else ('below' if ema_20 else 'unknown'),
            'rsi_14': round(rsi, 1) if rsi else None,
            'rsi_signal': 'overbought' if rsi and rsi > 70 else ('oversold' if rsi and rsi < 30 else 'neutral') if rsi else 'unknown',
            'momentum': 'bullish' if bullish_candles > bearish_candles else ('bearish' if bearish_candles > bullish_candles else 'neutral'),
            'volume_trend': vol_trend,
            'bars_analyzed': len(bars),
        }

    def get_multi_timeframe_analysis(self, ticker: str) -> Dict:
        """
        Get comprehensive multi-timeframe technical analysis for day trading.

        CACHED for 10 minutes to avoid rate limit issues.

        Returns analysis for available timeframes (5m, 15m, 1h) with:
        - EMA 9/20 and trend
        - RSI 14
        - Momentum direction
        - Volume trend
        - Overall bias calculation
        """
        # Check cache first
        cache_key = f"mtf_analysis_{ticker}"
        cached = self._get_cache(ticker, cache_key)
        if cached:
            logger.debug(f"Using cached MTF analysis for {ticker}")
            return cached

        mtf_bars = self.get_multi_timeframe_bars(ticker)

        if not mtf_bars:
            return {'error': 'No multi-timeframe data available', 'ticker': ticker}

        analysis = {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'timeframes': {},
        }

        # Analyze each timeframe
        bullish_count = 0
        bearish_count = 0
        total_weight = 0

        # Weights for each timeframe (higher = more important for day trading)
        weights = {'5m': 3, '15m': 2.5, '30m': 2, '1h': 1.5, '4h': 1}

        for tf, bars in mtf_bars.items():
            tf_analysis = self._analyze_timeframe(bars, tf)
            analysis['timeframes'][tf] = tf_analysis

            # Calculate weighted bias
            weight = weights.get(tf, 1)
            if tf_analysis.get('ema_trend') == 'bullish':
                bullish_count += weight
            elif tf_analysis.get('ema_trend') == 'bearish':
                bearish_count += weight
            total_weight += weight

        # Calculate overall bias
        if total_weight > 0:
            bullish_pct = (bullish_count / total_weight) * 100
            bearish_pct = (bearish_count / total_weight) * 100

            if bullish_pct > 70:
                overall_bias = 'strong_bullish'
            elif bullish_pct > 55:
                overall_bias = 'bullish'
            elif bearish_pct > 70:
                overall_bias = 'strong_bearish'
            elif bearish_pct > 55:
                overall_bias = 'bearish'
            else:
                overall_bias = 'neutral'

            analysis['overall'] = {
                'bias': overall_bias,
                'bullish_alignment': round(bullish_pct, 1),
                'bearish_alignment': round(bearish_pct, 1),
                'timeframes_analyzed': len(mtf_bars),
            }

        # Add confluence signals
        confluences = []
        tfs = analysis['timeframes']

        # Check for EMA trend confluence (adjusted for 3 timeframes max)
        bullish_ema_tfs = [tf for tf, data in tfs.items() if data.get('ema_trend') == 'bullish']
        bearish_ema_tfs = [tf for tf, data in tfs.items() if data.get('ema_trend') == 'bearish']

        if len(bullish_ema_tfs) >= 2:
            confluences.append(f"✅ Bullish EMA confluence across {len(bullish_ema_tfs)} timeframes")
        if len(bearish_ema_tfs) >= 2:
            confluences.append(f"🔴 Bearish EMA confluence across {len(bearish_ema_tfs)} timeframes")

        # Check for RSI oversold/overbought across timeframes
        oversold_tfs = [tf for tf, data in tfs.items() if data.get('rsi_signal') == 'oversold']
        overbought_tfs = [tf for tf, data in tfs.items() if data.get('rsi_signal') == 'overbought']

        if len(oversold_tfs) >= 2:
            confluences.append(f"📈 RSI oversold on {oversold_tfs} - potential bounce")
        if len(overbought_tfs) >= 2:
            confluences.append(f"📉 RSI overbought on {overbought_tfs} - potential pullback")

        analysis['confluences'] = confluences

        # Cache the result
        self._set_cache(ticker, cache_key, analysis)

        logger.info(f"📊 Multi-TF Analysis {ticker}: {analysis['overall']['bias']} ({analysis['overall']['bullish_alignment']:.1f}% bull)")
        return analysis

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
            'polygon_calls_remaining': self.get_polygon_rate_limit_remaining(),
            'polygon_calls_per_minute': self.POLYGON_CALLS_PER_MINUTE,
        }


# Global instance
market_data_service = MarketDataService()
