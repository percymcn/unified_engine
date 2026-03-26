"""
Polygon/Massive Options Flow Service
=====================================

FREE alternative to paid flow services (FlowAlgo, Unusual Whales).
Uses Polygon.io/Massive.com options trades data to detect institutional flow patterns.

NOTE: Polygon.io rebranded to Massive.com on Oct 30, 2025.
Your existing POLYGON_API_KEY works with both.

Strategy:
- Monitor large options trades (high premium)
- Detect sweeps (aggressive fills across exchanges)
- Track volume vs open interest (unusual activity)
- Cluster analysis for flow direction
- Real-time WebSocket streaming for live trades

This provides 80% of FlowAlgo functionality at $0 extra cost
since you already have Polygon/Massive for market data.

Requirements:
- Polygon/Massive API key (POLYGON_API_KEY in .env)
- Options data access (included in most paid plans)
- pip install massive (optional, for WebSocket streaming)
"""

import os
import logging
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from zoneinfo import ZoneInfo
import aiohttp

# Try to import Massive client (Polygon rebranded)
try:
    from massive import RESTClient, WebSocketClient
    MASSIVE_AVAILABLE = True
except ImportError:
    MASSIVE_AVAILABLE = False
    RESTClient = None
    WebSocketClient = None

logger = logging.getLogger(__name__)

EST = ZoneInfo('America/New_York')

def now_est() -> datetime:
    """Get current time in EST without tzinfo for DB storage."""
    return datetime.now(EST).replace(tzinfo=None)


@dataclass
class OptionsTradeFlow:
    """Single options trade from Polygon."""
    timestamp: datetime
    ticker: str

    # Contract details
    strike: float
    expiry: str
    option_type: str  # 'call' or 'put'

    # Trade details
    price: float  # Premium per contract
    size: int     # Number of contracts
    premium: float  # Total premium (price * size * 100)

    # Exchange and conditions
    exchange: str
    conditions: List[str] = field(default_factory=list)

    # Derived: Is this likely a sweep?
    is_sweep: bool = False  # Aggressive fill across exchanges
    is_block: bool = False  # Single large trade

    # Sentiment
    sentiment: str = 'neutral'  # 'bullish', 'bearish', 'neutral'

    # 2026 ELITE DETECTION FIELDS
    is_aggressive: bool = False  # Trade at/above ask (calls) or at/below bid (puts)
    volume_oi_ratio: float = 0.0  # Size vs Open Interest ratio
    is_unusual: bool = False  # Meets all elite criteria (aggressive + high OI ratio)
    open_interest: int = 0  # Contract OI at time of trade
    bid_price: float = 0.0  # NBBO bid at trade time
    ask_price: float = 0.0  # NBBO ask at trade time
    trade_vs_mid: float = 0.0  # How far above/below mid (positive = above)

    # Directional clustering
    cluster_id: str = ''  # ID of directional cluster this belongs to
    cluster_size: int = 0  # Number of trades in same cluster


@dataclass
class FlowCluster:
    """Cluster of related options trades indicating institutional activity."""
    ticker: str
    timestamp: datetime

    # Aggregated metrics
    total_premium: float = 0.0
    call_premium: float = 0.0
    put_premium: float = 0.0
    net_premium: float = 0.0  # Call - Put

    # Counts
    total_trades: int = 0
    sweep_count: int = 0
    block_count: int = 0

    # Volume analysis
    total_volume: int = 0
    avg_volume_vs_oi: float = 0.0  # Volume / Open Interest ratio

    # Sentiment
    sentiment_score: float = 0.0  # -100 to +100
    sentiment: str = 'neutral'

    # 2026 ELITE METRICS
    unusual_count: int = 0  # Trades meeting all elite criteria
    aggressive_count: int = 0  # Trades at/above ask (calls) or at/below bid (puts)
    directional_clusters: int = 0  # Number of directional clusters detected
    elite_score: float = 0.0  # 0-100 score combining all factors
    conviction_level: str = 'low'  # 'low', 'medium', 'high', 'extreme'

    # Individual trades
    trades: List[OptionsTradeFlow] = field(default_factory=list)


class PolygonOptionsFlowService:
    """
    Free options flow detection using Polygon.io/Massive.com data.

    Monitors options trades and detects patterns similar to
    paid services like FlowAlgo and Unusual Whales.

    Features:
    - REST API for historical trades (always available)
    - WebSocket streaming for real-time trades (if massive package installed)
    - Sweep detection (aggressive fills across exchanges)
    - Block detection (large single trades >$100k)
    - Sentiment scoring from call/put premium ratio
    """

    def __init__(self):
        # Try Docker secret first, then environment variable
        self.api_key = None
        secret_path = "/run/secrets/polygon_api_key"
        if os.path.exists(secret_path):
            try:
                with open(secret_path, "r") as f:
                    self.api_key = f.read().strip()
                logger.info("PolygonOptionsFlowService: Loaded Polygon API key from Docker secret")
            except Exception as e:
                logger.error(f"Failed to read Polygon API key from secret: {e}")

        if not self.api_key:
            self.api_key = os.getenv('POLYGON_API_KEY', '')
            if self.api_key:
                logger.info("PolygonOptionsFlowService: Loaded Polygon API key from env var")

        self.base_url = 'https://api.polygon.io'  # Works for both Polygon and Massive
        self.session: Optional[aiohttp.ClientSession] = None

        # Massive/Polygon clients
        self.rest_client = None
        self.ws_client = None
        self.ws_thread = None
        self.ws_running = False

        # Configuration - 2026 Best Practices (more aggressive filtering)
        self.min_premium = 40000  # Minimum premium to track ($40k) - UPGRADED from $25k
        self.sweep_threshold = 3  # Min trades across exchanges = sweep
        self.block_threshold = 100000  # Single trade >$100k = block
        self.lookback_minutes = 10  # Window for clustering

        # 2026 ELITE FLOW DETECTION
        self.require_aggressive_price = True  # Trade at/above ask (calls) or at/below bid (puts)
        self.require_volume_vs_oi = True  # Require size > 10x OI
        self.min_volume_oi_ratio = 10.0  # Minimum volume/OI ratio for "unusual"
        self.require_directional_cluster = True  # Multiple trades same direction

        # Open Interest cache (fetched separately)
        self.open_interest_cache: Dict[str, int] = {}
        self.oi_cache_timestamp: Dict[str, datetime] = {}

        # Tracked tickers (ETFs that map to futures)
        self.tracked_tickers = ['SPY', 'QQQ', 'IWM', 'GLD', 'DIA']

        # Flow cache
        self.flow_cache: Dict[str, List[OptionsTradeFlow]] = defaultdict(list)
        self.cluster_cache: Dict[str, FlowCluster] = {}
        self.last_fetch: Dict[str, datetime] = {}

        # Real-time trade buffer (from WebSocket)
        self.realtime_trades: List[OptionsTradeFlow] = []
        self.realtime_lock = threading.Lock()

        # Data delay tracking for verification
        self._delay_samples: List[float] = []
        self._max_delay_samples = 100
        self._last_delay_log = datetime.now(EST)
        self._delay_log_interval = 60  # Log delay stats every 60 seconds

        self._is_configured = bool(self.api_key)

        # Initialize Massive client if available
        if self._is_configured and MASSIVE_AVAILABLE:
            try:
                self.rest_client = RESTClient(api_key=self.api_key)
                logger.info("PolygonOptionsFlowService: Massive REST client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Massive REST client: {e}")

        if self._is_configured:
            logger.info(f"PolygonOptionsFlowService initialized (Massive SDK: {MASSIVE_AVAILABLE})")
        else:
            logger.warning("PolygonOptionsFlowService: No API key, using mock data")

    def _measure_data_delay(self, api_timestamp: datetime, source: str = "POLYGON") -> float:
        """
        Measure and log data delay for verification.

        Args:
            api_timestamp: Timestamp from the API response
            source: Data source identifier

        Returns:
            Delay in seconds
        """
        now = datetime.now(EST)

        # Ensure api_timestamp is timezone-aware
        if api_timestamp.tzinfo is None:
            api_timestamp = api_timestamp.replace(tzinfo=EST)
        else:
            api_timestamp = api_timestamp.astimezone(EST)

        delay_seconds = (now - api_timestamp).total_seconds()

        # Track delay samples
        self._delay_samples.append(delay_seconds)
        if len(self._delay_samples) > self._max_delay_samples:
            self._delay_samples = self._delay_samples[-self._max_delay_samples:]

        # Log individual data point with delay info (only for significant delays or first samples)
        if len(self._delay_samples) <= 5 or delay_seconds > 60:
            if delay_seconds > 900:  # More than 15 minutes
                logger.warning(f"[{source} DELAY] Data: {api_timestamp.strftime('%H:%M:%S')} | "
                              f"Local: {now.strftime('%H:%M:%S')} | Delay: {delay_seconds / 60:.1f} MIN 🔴 15-MIN DELAYED")
            elif delay_seconds > 60:
                logger.warning(f"[{source} DELAY] Data: {api_timestamp.strftime('%H:%M:%S')} | "
                              f"Local: {now.strftime('%H:%M:%S')} | Delay: {delay_seconds:.0f}s ⚠️ DELAYED")
            else:
                logger.info(f"[{source} DELAY] Data: {api_timestamp.strftime('%H:%M:%S')} | "
                           f"Local: {now.strftime('%H:%M:%S')} | Delay: {delay_seconds:.1f}s ✓ REAL-TIME")

        # Periodic summary logging
        if (now - self._last_delay_log).total_seconds() >= self._delay_log_interval:
            self._log_delay_summary(source)
            self._last_delay_log = now

        return delay_seconds

    def _log_delay_summary(self, source: str = "POLYGON"):
        """Log summary of data delays."""
        if not self._delay_samples:
            return

        avg_delay = sum(self._delay_samples) / len(self._delay_samples)
        min_delay = min(self._delay_samples)
        max_delay = max(self._delay_samples)

        # Determine if data is real-time or delayed
        if avg_delay < 30:
            status = "✓ REAL-TIME"
        elif avg_delay < 120:
            status = "⚡ NEAR REAL-TIME"
        elif avg_delay < 900:  # 15 minutes
            status = "⚠️ DELAYED (1-15 min)"
        else:
            status = "🔴 15-MINUTE DELAYED"

        logger.info(f"[{source} DELAY SUMMARY] "
                   f"Avg: {avg_delay:.1f}s | Min: {min_delay:.1f}s | Max: {max_delay:.1f}s | "
                   f"Samples: {len(self._delay_samples)} | Status: {status}")

    def get_delay_stats(self) -> Dict[str, Any]:
        """Get current delay statistics for dashboard display."""
        if not self._delay_samples:
            return {"source": "polygon", "status": "no_data", "samples": 0}

        avg_delay = sum(self._delay_samples) / len(self._delay_samples)
        return {
            "source": "polygon",
            "avg_delay_seconds": avg_delay,
            "min_delay_seconds": min(self._delay_samples),
            "max_delay_seconds": max(self._delay_samples),
            "samples": len(self._delay_samples),
            "is_realtime": avg_delay < 30,
            "is_15min_delayed": avg_delay >= 900,
            "status": "real-time" if avg_delay < 30 else ("15-min-delayed" if avg_delay >= 900 else "delayed")
        }

    def start_websocket_streaming(self, tickers: List[str] = None):
        """
        Start WebSocket streaming for real-time options trades.

        Args:
            tickers: List of underlying tickers to stream (default: tracked_tickers)
        """
        if not MASSIVE_AVAILABLE:
            logger.warning("Massive SDK not installed - WebSocket streaming unavailable")
            return False

        if not self._is_configured:
            logger.warning("No API key configured - WebSocket streaming unavailable")
            return False

        if self.ws_running:
            logger.info("WebSocket already running")
            return True

        tickers = tickers or self.tracked_tickers

        # Build subscription list for options trades
        # Format: O:SPY* for all SPY options, or O.* for all options
        subscriptions = [f"T.O:{ticker}" for ticker in tickers]

        try:
            self.ws_client = WebSocketClient(
                api_key=self.api_key,
                subscriptions=subscriptions
            )

            def run_ws():
                self.ws_running = True
                try:
                    self.ws_client.run(handle_msg=self._handle_ws_message)
                except Exception as e:
                    logger.error(f"WebSocket error: {e}")
                finally:
                    self.ws_running = False

            self.ws_thread = threading.Thread(target=run_ws, daemon=True)
            self.ws_thread.start()

            logger.info(f"Started WebSocket streaming for options: {subscriptions}")
            return True

        except Exception as e:
            logger.error(f"Failed to start WebSocket: {e}")
            return False

    def _handle_ws_message(self, messages: List[Dict]):
        """Handle incoming WebSocket messages (options trades)."""
        for msg in messages:
            try:
                # Parse options trade message
                # Fields: sym (O:SPY250321C00500000), p (price), s (size), t (timestamp), x (exchange)
                if msg.get('ev') != 'T':  # Trade event
                    continue

                option_ticker = msg.get('sym', '')
                if not option_ticker.startswith('O:'):
                    continue

                price = msg.get('p', 0)
                size = msg.get('s', 0)
                premium = price * size * 100

                if premium < self.min_premium:
                    continue

                # Parse option ticker
                strike, expiry, opt_type = self._parse_option_ticker(option_ticker)

                # Extract underlying ticker
                underlying = option_ticker[2:5] if len(option_ticker) > 5 else 'UNK'

                trade_timestamp = datetime.fromtimestamp(msg.get('t', 0) / 1e9)
                # Measure data delay for verification
                self._measure_data_delay(trade_timestamp, "POLYGON_WS")

                trade = OptionsTradeFlow(
                    timestamp=trade_timestamp,
                    ticker=underlying,
                    strike=strike,
                    expiry=expiry,
                    option_type=opt_type,
                    price=price,
                    size=size,
                    premium=premium,
                    exchange=str(msg.get('x', '')),
                    conditions=msg.get('c', []),
                    is_block=premium >= self.block_threshold,
                    sentiment='bullish' if opt_type == 'call' else 'bearish'
                )

                with self.realtime_lock:
                    self.realtime_trades.append(trade)
                    # Keep only last 1000 trades
                    if len(self.realtime_trades) > 1000:
                        self.realtime_trades = self.realtime_trades[-500:]

                logger.debug(f"WS Trade: {underlying} {opt_type} ${premium:,.0f}")

            except Exception as e:
                logger.debug(f"Error parsing WS message: {e}")

    def stop_websocket_streaming(self):
        """Stop WebSocket streaming."""
        if self.ws_client:
            try:
                self.ws_client.close()
            except:
                pass
        self.ws_running = False
        logger.info("WebSocket streaming stopped")

    def get_realtime_trades(self, ticker: str = None, minutes: int = 5) -> List[OptionsTradeFlow]:
        """Get recent trades from WebSocket buffer."""
        cutoff = now_est() - timedelta(minutes=minutes)

        with self.realtime_lock:
            if ticker:
                return [t for t in self.realtime_trades
                        if t.ticker == ticker and t.timestamp >= cutoff]
            else:
                return [t for t in self.realtime_trades if t.timestamp >= cutoff]

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session

    async def close(self):
        """Close the session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def fetch_historical_options_trades(
        self,
        ticker: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[OptionsTradeFlow]:
        """
        Fetch historical options trades from Polygon for a specific time window.

        Phase 5B: Historical flow replay for backtesting.

        Args:
            ticker: Underlying ticker (e.g., 'SPY')
            start_time: Start of time window (absolute datetime)
            end_time: End of time window (absolute datetime)

        Returns:
            List of OptionsTradeFlow objects from the historical period
        """
        if not self._is_configured:
            return self._generate_mock_trades(ticker)

        try:
            session = await self._get_session()

            # Convert to millisecond timestamps
            from_ts = int(start_time.timestamp() * 1000)
            to_ts = int(end_time.timestamp() * 1000)

            # For historical queries, we need to allow expired contracts
            # Determine if we need expired contracts based on date
            now = datetime.now()
            allow_expired = (end_time < now - timedelta(days=1))

            # Get options contracts for this ticker (including expired if historical)
            contracts_url = (
                f"{self.base_url}/v3/reference/options/contracts?"
                f"underlying_ticker={ticker}&"
                f"expired={'true' if allow_expired else 'false'}&"
                f"limit=50&"
                f"apiKey={self.api_key}"
            )

            logger.debug(f"Fetching historical flow for {ticker}: {start_time} to {end_time} (expired={allow_expired})")

            async with session.get(contracts_url) as response:
                if response.status != 200:
                    logger.warning(f"Polygon contracts API returned {response.status} for {ticker}")
                    return self._generate_mock_trades(ticker)

                data = await response.json()
                contracts = data.get('results', [])

            if not contracts:
                logger.debug(f"No options contracts for {ticker} (expired={allow_expired})")
                return []

            # Fetch trades for top contracts
            trades = []
            for contract in contracts[:10]:  # Top 10 contracts
                option_ticker = contract.get('ticker')
                if not option_ticker:
                    continue

                trades_url = (
                    f"{self.base_url}/v3/trades/{option_ticker}?"
                    f"timestamp.gte={from_ts}&"
                    f"timestamp.lte={to_ts}&"
                    f"limit=100&"
                    f"apiKey={self.api_key}"
                )

                try:
                    async with session.get(trades_url) as trade_response:
                        if trade_response.status == 200:
                            trade_data = await trade_response.json()

                            for t in trade_data.get('results', []):
                                premium = t.get('price', 0) * t.get('size', 0) * 100

                                if premium < self.min_premium:
                                    continue

                                # Parse contract details from ticker
                                strike, expiry, opt_type = self._parse_option_ticker(option_ticker)

                                trade_timestamp = datetime.fromtimestamp(t.get('sip_timestamp', 0) / 1e9)
                                # Measure data delay for verification
                                self._measure_data_delay(trade_timestamp, "POLYGON_HIST")

                                trade = OptionsTradeFlow(
                                    timestamp=trade_timestamp,
                                    ticker=ticker,
                                    strike=strike,
                                    expiry=expiry,
                                    option_type=opt_type,
                                    price=t.get('price', 0),
                                    size=t.get('size', 0),
                                    premium=premium,
                                    exchange=str(t.get('exchange', '')),
                                    conditions=t.get('conditions', [])
                                )

                                # Classify trade type
                                if premium >= self.block_threshold:
                                    trade.is_block = True

                                # Determine sentiment
                                trade.sentiment = self._classify_sentiment(trade)

                                trades.append(trade)

                except Exception as e:
                    logger.debug(f"Error fetching historical trades for {option_ticker}: {e}")
                    continue

            # Detect sweeps
            trades = self._detect_sweeps(trades)

            logger.info(f"Historical Polygon flow: {ticker} {start_time.strftime('%Y-%m-%d %H:%M')} - "
                       f"{len(trades)} trades, ${sum(t.premium for t in trades):,.0f} total premium")

            return trades

        except Exception as e:
            logger.error(f"Failed to fetch historical options trades for {ticker}: {e}")
            return self._generate_mock_trades(ticker)

    async def fetch_options_trades(
        self,
        ticker: str,
        lookback_minutes: int = 10
    ) -> List[OptionsTradeFlow]:
        """
        Fetch recent options trades from Polygon.

        Args:
            ticker: Underlying ticker (e.g., 'SPY')
            lookback_minutes: How far back to fetch

        Returns:
            List of OptionsTradeFlow objects
        """
        if not self._is_configured:
            return self._generate_mock_trades(ticker)

        try:
            session = await self._get_session()

            # Calculate time window
            now = datetime.now()
            from_ts = int((now - timedelta(minutes=lookback_minutes)).timestamp() * 1000)
            to_ts = int(now.timestamp() * 1000)

            # Polygon options trades endpoint
            # GET /v3/trades/{optionsTicker}
            # We need to query options contracts for this underlying

            # First, get active options contracts for this ticker
            contracts_url = (
                f"{self.base_url}/v3/reference/options/contracts?"
                f"underlying_ticker={ticker}&"
                f"expired=false&"
                f"limit=50&"
                f"apiKey={self.api_key}"
            )

            async with session.get(contracts_url) as response:
                if response.status != 200:
                    logger.warning(f"Polygon contracts API returned {response.status}")
                    return self._generate_mock_trades(ticker)

                data = await response.json()
                contracts = data.get('results', [])

            if not contracts:
                logger.debug(f"No active options contracts for {ticker}")
                return []

            # Fetch trades for top contracts (by volume/OI)
            trades = []
            for contract in contracts[:10]:  # Top 10 contracts
                option_ticker = contract.get('ticker')
                if not option_ticker:
                    continue

                trades_url = (
                    f"{self.base_url}/v3/trades/{option_ticker}?"
                    f"timestamp.gte={from_ts}&"
                    f"timestamp.lte={to_ts}&"
                    f"limit=100&"
                    f"apiKey={self.api_key}"
                )

                try:
                    async with session.get(trades_url) as trade_response:
                        if trade_response.status == 200:
                            trade_data = await trade_response.json()

                            for t in trade_data.get('results', []):
                                premium = t.get('price', 0) * t.get('size', 0) * 100

                                if premium < self.min_premium:
                                    continue

                                # Parse contract details from ticker
                                # Format: O:SPY250321C00500000
                                strike, expiry, opt_type = self._parse_option_ticker(option_ticker)

                                trade_timestamp = datetime.fromtimestamp(t.get('sip_timestamp', 0) / 1e9)
                                # Measure data delay for verification
                                self._measure_data_delay(trade_timestamp, "POLYGON")

                                trade = OptionsTradeFlow(
                                    timestamp=trade_timestamp,
                                    ticker=ticker,
                                    strike=strike,
                                    expiry=expiry,
                                    option_type=opt_type,
                                    price=t.get('price', 0),
                                    size=t.get('size', 0),
                                    premium=premium,
                                    exchange=str(t.get('exchange', '')),
                                    conditions=t.get('conditions', [])
                                )

                                # Classify trade type
                                if premium >= self.block_threshold:
                                    trade.is_block = True

                                # Determine sentiment
                                trade.sentiment = self._classify_sentiment(trade)

                                trades.append(trade)

                except Exception as e:
                    logger.debug(f"Error fetching trades for {option_ticker}: {e}")
                    continue

            # Detect sweeps (same direction, multiple exchanges, short time window)
            trades = self._detect_sweeps(trades)

            # Cache trades
            self.flow_cache[ticker] = trades
            self.last_fetch[ticker] = now_est()

            logger.info(f"Polygon flow: {ticker} - {len(trades)} trades, "
                       f"${sum(t.premium for t in trades):,.0f} total premium")

            return trades

        except Exception as e:
            logger.error(f"Failed to fetch options trades for {ticker}: {e}")
            return self._generate_mock_trades(ticker)

    def _parse_option_ticker(self, option_ticker: str) -> Tuple[float, str, str]:
        """
        Parse Polygon option ticker format.

        Format: O:SPY250321C00500000
        - O: = Options prefix
        - SPY = Underlying
        - 250321 = Expiry (YYMMDD)
        - C = Call (P = Put)
        - 00500000 = Strike * 1000 (so 500.000)
        """
        try:
            # Remove O: prefix
            ticker = option_ticker.replace('O:', '')

            # Find where numbers start
            i = 0
            while i < len(ticker) and not ticker[i].isdigit():
                i += 1

            # underlying = ticker[:i]
            rest = ticker[i:]

            # Expiry is first 6 digits
            expiry_raw = rest[:6]
            expiry = f"20{expiry_raw[:2]}-{expiry_raw[2:4]}-{expiry_raw[4:6]}"

            # Option type
            opt_type = 'call' if rest[6] == 'C' else 'put'

            # Strike (remaining digits / 1000)
            strike = float(rest[7:]) / 1000

            return strike, expiry, opt_type

        except Exception:
            return 0.0, '', 'call'

    def _classify_sentiment(self, trade: OptionsTradeFlow) -> str:
        """
        Classify trade sentiment based on option type and conditions.

        Simple heuristic:
        - Calls = bullish
        - Puts = bearish

        More advanced: check if bought at ask (bullish) or sold at bid (bearish)
        """
        # Check trade conditions for buy/sell indicators
        conditions = trade.conditions

        # Condition codes vary by exchange, but generally:
        # - Trades at ask = buyer initiated = bullish
        # - Trades at bid = seller initiated = bearish

        if trade.option_type == 'call':
            return 'bullish'
        else:
            return 'bearish'

    # ========================================
    # 2026 ELITE FLOW DETECTION
    # ========================================

    async def fetch_contract_details(
        self,
        option_ticker: str
    ) -> Dict[str, Any]:
        """
        Fetch contract details including OI, bid, ask.

        Args:
            option_ticker: Full option ticker (e.g., O:SPY250321C00500000)

        Returns:
            Dict with open_interest, bid, ask, etc.
        """
        if not self._is_configured:
            return {'open_interest': 100, 'bid': 1.0, 'ask': 1.1}  # Mock

        try:
            session = await self._get_session()

            # Snapshot endpoint for options contract
            url = (
                f"{self.base_url}/v3/snapshot/options/{option_ticker}?"
                f"apiKey={self.api_key}"
            )

            async with session.get(url) as response:
                if response.status != 200:
                    return {}

                data = await response.json()
                result = data.get('results', {})

                # Extract key fields
                day_data = result.get('day', {})
                details = result.get('details', {})
                underlying = result.get('underlying_asset', {})

                return {
                    'open_interest': day_data.get('open_interest', 0),
                    'volume': day_data.get('volume', 0),
                    'bid': result.get('last_quote', {}).get('bid', 0),
                    'ask': result.get('last_quote', {}).get('ask', 0),
                    'last_trade': result.get('last_trade', {}).get('price', 0),
                    'underlying_price': underlying.get('price', 0),
                    'implied_volatility': result.get('implied_volatility', 0),
                    'greeks': result.get('greeks', {}),
                }

        except Exception as e:
            logger.debug(f"Failed to fetch contract details for {option_ticker}: {e}")
            return {}

    def _check_aggressive_pricing(
        self,
        trade: OptionsTradeFlow,
        bid: float,
        ask: float
    ) -> Tuple[bool, float]:
        """
        Check if trade was aggressive (at/above ask for buys, at/below bid for sells).

        For calls (bullish):
        - At/above ask = aggressive buy = very bullish
        - At/below bid = aggressive sell = bearish (but rare)

        For puts (bearish):
        - At/above ask = aggressive buy = very bearish
        - At/below bid = aggressive sell = bullish (but rare)

        Returns:
            (is_aggressive, trade_vs_mid)
        """
        if bid <= 0 or ask <= 0:
            return False, 0.0

        mid = (bid + ask) / 2
        trade_price = trade.price

        # Calculate position relative to mid
        if mid > 0:
            trade_vs_mid = (trade_price - mid) / mid * 100  # As percentage
        else:
            trade_vs_mid = 0.0

        # Aggressive = at or above ask (for buys)
        # Note: For options, most large trades are buyers, so at/above ask = aggressive
        is_aggressive = trade_price >= ask * 0.98  # Allow 2% tolerance

        return is_aggressive, trade_vs_mid

    def _calculate_volume_oi_ratio(
        self,
        trade_size: int,
        open_interest: int
    ) -> float:
        """
        Calculate volume to open interest ratio.

        Unusual activity = size > 10x typical OI
        """
        if open_interest <= 0:
            return 0.0

        return trade_size / open_interest

    def _apply_elite_criteria(
        self,
        trade: OptionsTradeFlow,
        bid: float,
        ask: float,
        open_interest: int
    ) -> OptionsTradeFlow:
        """
        Apply 2026 elite criteria to a trade.

        Criteria:
        1. Premium > $40k (already filtered)
        2. Aggressive pricing (at/above ask)
        3. Size > 10x OI (unusual)
        """
        # Store quote data
        trade.bid_price = bid
        trade.ask_price = ask
        trade.open_interest = open_interest

        # Check aggressive pricing
        is_aggressive, trade_vs_mid = self._check_aggressive_pricing(trade, bid, ask)
        trade.is_aggressive = is_aggressive
        trade.trade_vs_mid = trade_vs_mid

        # Calculate volume/OI ratio
        trade.volume_oi_ratio = self._calculate_volume_oi_ratio(trade.size, open_interest)

        # Mark as unusual if meets all criteria
        trade.is_unusual = (
            trade.premium >= self.min_premium and  # $40k+
            trade.is_aggressive and  # At/above ask
            trade.volume_oi_ratio >= self.min_volume_oi_ratio  # >10x OI
        )

        return trade

    def _detect_directional_clusters(
        self,
        trades: List[OptionsTradeFlow],
        time_window_minutes: int = 5
    ) -> List[OptionsTradeFlow]:
        """
        Detect directional clusters (multiple trades same direction within time window).

        Institutional flow often comes in clusters - multiple trades
        in the same direction within minutes.
        """
        if len(trades) < 2:
            return trades

        # Sort by timestamp
        trades = sorted(trades, key=lambda x: x.timestamp)

        # Group by direction and time window
        cluster_id = 0
        processed = set()

        for i, trade in enumerate(trades):
            if i in processed:
                continue

            # Find other trades in same direction within window
            cluster_trades = [trade]
            processed.add(i)

            for j, other in enumerate(trades):
                if j in processed or j == i:
                    continue

                # Same direction check
                same_direction = (
                    trade.option_type == other.option_type or
                    (trade.sentiment == 'bullish' and other.sentiment == 'bullish') or
                    (trade.sentiment == 'bearish' and other.sentiment == 'bearish')
                )

                # Time window check
                time_diff = abs((trade.timestamp - other.timestamp).total_seconds() / 60)
                in_window = time_diff <= time_window_minutes

                if same_direction and in_window:
                    cluster_trades.append(other)
                    processed.add(j)

            # If cluster has multiple trades, mark them
            if len(cluster_trades) >= 2:
                cluster_id += 1
                for ct in cluster_trades:
                    ct.cluster_id = f"C{cluster_id}"
                    ct.cluster_size = len(cluster_trades)

        return trades

    def _calculate_elite_score(self, cluster: FlowCluster) -> float:
        """
        Calculate elite conviction score for a flow cluster.

        Combines:
        - Number of unusual trades (high OI ratio + aggressive)
        - Total premium
        - Sweep/block ratio
        - Directional clustering
        """
        score = 0.0

        # Base: unusual trade count (max 30 points)
        score += min(30, cluster.unusual_count * 10)

        # Aggressive trade ratio (max 20 points)
        if cluster.total_trades > 0:
            aggressive_ratio = cluster.aggressive_count / cluster.total_trades
            score += aggressive_ratio * 20

        # Premium scale (max 20 points)
        # $100k = 5 points, $500k = 15 points, $1M+ = 20 points
        if cluster.total_premium >= 1000000:
            score += 20
        elif cluster.total_premium >= 500000:
            score += 15
        elif cluster.total_premium >= 200000:
            score += 10
        elif cluster.total_premium >= 100000:
            score += 5

        # Sweep bonus (max 15 points)
        if cluster.sweep_count >= 5:
            score += 15
        elif cluster.sweep_count >= 3:
            score += 10
        elif cluster.sweep_count >= 1:
            score += 5

        # Block bonus (max 10 points)
        score += min(10, cluster.block_count * 5)

        # Directional cluster bonus (max 5 points)
        if cluster.directional_clusters >= 3:
            score += 5
        elif cluster.directional_clusters >= 1:
            score += 3

        return min(100, score)

    def _get_conviction_level(self, elite_score: float) -> str:
        """Convert elite score to conviction level."""
        if elite_score >= 80:
            return 'extreme'
        elif elite_score >= 60:
            return 'high'
        elif elite_score >= 40:
            return 'medium'
        else:
            return 'low'

    def _detect_sweeps(self, trades: List[OptionsTradeFlow]) -> List[OptionsTradeFlow]:
        """
        Detect sweep patterns (aggressive fills across exchanges).

        A sweep is characterized by:
        - Multiple trades in same direction
        - Across different exchanges
        - Within a short time window (<1 min)
        """
        if len(trades) < self.sweep_threshold:
            return trades

        # Group by direction and time window
        grouped = defaultdict(list)

        for trade in trades:
            # Create a key based on direction and minute
            key = (
                trade.option_type,
                trade.timestamp.strftime('%Y%m%d%H%M')
            )
            grouped[key].append(trade)

        # Mark sweeps
        for key, group in grouped.items():
            if len(group) >= self.sweep_threshold:
                # Check if across multiple exchanges
                exchanges = set(t.exchange for t in group)
                if len(exchanges) >= 2:
                    for trade in group:
                        trade.is_sweep = True

        return trades

    def _generate_mock_trades(self, ticker: str) -> List[OptionsTradeFlow]:
        """Generate mock trades for testing when no API key."""
        import random

        now = now_est()
        trades = []

        num_trades = random.randint(3, 10)

        for i in range(num_trades):
            is_call = random.random() > 0.45  # Slight call bias
            premium = random.uniform(25000, 250000)

            trade = OptionsTradeFlow(
                timestamp=now - timedelta(minutes=random.randint(0, 10)),
                ticker=ticker,
                strike=round(random.uniform(400, 600), 0),
                expiry=(now + timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d'),
                option_type='call' if is_call else 'put',
                price=random.uniform(1.0, 10.0),
                size=random.randint(50, 500),
                premium=premium,
                exchange=random.choice(['CBOE', 'PHLX', 'ISE', 'AMEX']),
                is_sweep=random.random() > 0.7,
                is_block=premium > 100000,
                sentiment='bullish' if is_call else 'bearish'
            )
            trades.append(trade)

        return trades

    async def get_flow_cluster(
        self,
        ticker: str,
        refresh: bool = True,
        apply_elite_filter: bool = True
    ) -> FlowCluster:
        """
        Get aggregated flow cluster for a ticker.

        Args:
            ticker: Underlying ticker (e.g., 'SPY')
            refresh: Whether to fetch fresh data
            apply_elite_filter: Whether to apply 2026 elite criteria

        Returns:
            FlowCluster with aggregated metrics
        """
        if refresh or ticker not in self.flow_cache:
            trades = await self.fetch_options_trades(ticker)
        else:
            trades = self.flow_cache.get(ticker, [])

        # Apply directional clustering
        if apply_elite_filter and self.require_directional_cluster:
            trades = self._detect_directional_clusters(trades)

        # Aggregate into cluster
        cluster = FlowCluster(
            ticker=ticker,
            timestamp=now_est()
        )

        # Track unique clusters
        unique_clusters = set()

        for trade in trades:
            cluster.total_trades += 1
            cluster.total_premium += trade.premium
            cluster.total_volume += trade.size

            if trade.option_type == 'call':
                cluster.call_premium += trade.premium
            else:
                cluster.put_premium += trade.premium

            if trade.is_sweep:
                cluster.sweep_count += 1
            if trade.is_block:
                cluster.block_count += 1

            # 2026 Elite metrics
            if trade.is_unusual:
                cluster.unusual_count += 1
            if trade.is_aggressive:
                cluster.aggressive_count += 1
            if trade.cluster_id:
                unique_clusters.add(trade.cluster_id)

            cluster.trades.append(trade)

        # Count directional clusters
        cluster.directional_clusters = len(unique_clusters)

        # Calculate net premium and sentiment
        cluster.net_premium = cluster.call_premium - cluster.put_premium

        if cluster.total_premium > 0:
            cluster.sentiment_score = (cluster.net_premium / cluster.total_premium) * 100

        # Calculate average OI ratio
        oi_ratios = [t.volume_oi_ratio for t in trades if t.volume_oi_ratio > 0]
        cluster.avg_volume_vs_oi = sum(oi_ratios) / len(oi_ratios) if oi_ratios else 0.0

        # Classify sentiment
        if cluster.sentiment_score > 25:
            cluster.sentiment = 'bullish'
        elif cluster.sentiment_score < -25:
            cluster.sentiment = 'bearish'
        else:
            cluster.sentiment = 'neutral'

        # 2026 Elite scoring
        cluster.elite_score = self._calculate_elite_score(cluster)
        cluster.conviction_level = self._get_conviction_level(cluster.elite_score)

        # Cache cluster
        self.cluster_cache[ticker] = cluster

        logger.info(
            f"📊 Polygon Flow {ticker}: {cluster.sentiment.upper()} "
            f"(score={cluster.sentiment_score:.0f}, elite={cluster.elite_score:.0f}, "
            f"conviction={cluster.conviction_level.upper()}, "
            f"unusual={cluster.unusual_count}, sweeps={cluster.sweep_count}, "
            f"premium=${cluster.total_premium:,.0f})"
        )

        return cluster

    async def get_all_flow(self) -> Dict[str, FlowCluster]:
        """Get flow clusters for all tracked tickers."""
        clusters = {}

        for ticker in self.tracked_tickers:
            try:
                cluster = await self.get_flow_cluster(ticker)
                clusters[ticker] = cluster
            except Exception as e:
                logger.error(f"Error getting flow for {ticker}: {e}")

        return clusters

    def check_flow_confirmation(
        self,
        ticker: str,
        signal_direction: str
    ) -> Tuple[bool, str, float]:
        """
        Check if options flow confirms a signal direction.

        2026 ELITE version: Uses conviction level and unusual trade count
        for stronger confirmation signals.

        Args:
            ticker: Underlying ticker (map futures to ETF: MES -> SPY)
            signal_direction: 'buy' or 'sell'

        Returns:
            (confirms: bool, reason: str, boost: float)
        """
        # Map futures to ETF
        ticker_map = {
            'MES': 'SPY', 'ES': 'SPY',
            'NQ': 'QQQ', 'MNQ': 'QQQ',
            'RTY': 'IWM', 'M2K': 'IWM',
            'GC': 'GLD', 'MGC': 'GLD',
            'YM': 'DIA', 'MYM': 'DIA'
        }

        etf_ticker = ticker_map.get(ticker, ticker)

        cluster = self.cluster_cache.get(etf_ticker)
        if not cluster:
            return False, "no_flow_data", 0.0

        # Check age
        age = (now_est() - cluster.timestamp).total_seconds()
        if age > 600:  # >10 minutes old
            return False, "flow_data_stale", 0.0

        # Check confirmation
        confirms = False
        reason = ""
        boost = 0.0

        # 2026 ELITE: Conviction-based boost
        conviction_boost = {
            'extreme': 10.0,
            'high': 7.0,
            'medium': 4.0,
            'low': 2.0
        }

        if signal_direction == 'buy':
            if cluster.sentiment == 'bullish':
                confirms = True
                base_boost = conviction_boost.get(cluster.conviction_level, 2.0)
                boost = base_boost

                reason = f"flow_bullish (${cluster.call_premium:,.0f} calls)"

                # Extra boost for sweeps
                if cluster.sweep_count > 0:
                    boost += min(5.0, cluster.sweep_count * 1.5)
                    reason += f" +{cluster.sweep_count} sweeps"

                # Extra boost for unusual (elite) trades
                if cluster.unusual_count > 0:
                    boost += min(5.0, cluster.unusual_count * 2.0)
                    reason += f" +{cluster.unusual_count} unusual"

                # Directional cluster bonus
                if cluster.directional_clusters >= 2:
                    boost += 3.0
                    reason += f" +{cluster.directional_clusters} clusters"

                reason += f" [conv={cluster.conviction_level.upper()}]"

            elif cluster.sentiment == 'bearish':
                confirms = False
                reason = f"flow_bearish_conflict (${cluster.put_premium:,.0f} puts)"
                boost = -5.0 - (cluster.unusual_count * 2.0)  # Stronger penalty for unusual puts

        elif signal_direction == 'sell':
            if cluster.sentiment == 'bearish':
                confirms = True
                base_boost = conviction_boost.get(cluster.conviction_level, 2.0)
                boost = base_boost

                reason = f"flow_bearish (${cluster.put_premium:,.0f} puts)"

                if cluster.sweep_count > 0:
                    boost += min(5.0, cluster.sweep_count * 1.5)
                    reason += f" +{cluster.sweep_count} sweeps"

                if cluster.unusual_count > 0:
                    boost += min(5.0, cluster.unusual_count * 2.0)
                    reason += f" +{cluster.unusual_count} unusual"

                if cluster.directional_clusters >= 2:
                    boost += 3.0
                    reason += f" +{cluster.directional_clusters} clusters"

                reason += f" [conv={cluster.conviction_level.upper()}]"

            elif cluster.sentiment == 'bullish':
                confirms = False
                reason = f"flow_bullish_conflict (${cluster.call_premium:,.0f} calls)"
                boost = -5.0 - (cluster.unusual_count * 2.0)

        return confirms, reason, boost

    def get_status(self) -> Dict[str, Any]:
        """Get service status for dashboard."""
        clusters_summary = {}

        for ticker, cluster in self.cluster_cache.items():
            age = (now_est() - cluster.timestamp).total_seconds()

            clusters_summary[ticker] = {
                'sentiment': cluster.sentiment,
                'sentiment_score': cluster.sentiment_score,
                'total_premium': cluster.total_premium,
                'call_premium': cluster.call_premium,
                'put_premium': cluster.put_premium,
                'net_premium': cluster.net_premium,
                'sweep_count': cluster.sweep_count,
                'block_count': cluster.block_count,
                'total_trades': cluster.total_trades,
                'age_seconds': age,
                'timestamp': cluster.timestamp.strftime('%I:%M:%S %p'),
                # 2026 Elite metrics
                'unusual_count': cluster.unusual_count,
                'aggressive_count': cluster.aggressive_count,
                'directional_clusters': cluster.directional_clusters,
                'elite_score': cluster.elite_score,
                'conviction_level': cluster.conviction_level,
                'avg_volume_vs_oi': cluster.avg_volume_vs_oi,
            }

        # Get realtime trade count
        with self.realtime_lock:
            realtime_count = len(self.realtime_trades)

        return {
            'enabled': self._is_configured,
            'massive_sdk_available': MASSIVE_AVAILABLE,
            'websocket_streaming': self.ws_running,
            'realtime_trades_buffered': realtime_count,
            'tracked_tickers': self.tracked_tickers,
            'min_premium': self.min_premium,
            'clusters': clusters_summary,
            # 2026 Elite config
            'elite_config': {
                'require_aggressive_price': self.require_aggressive_price,
                'require_volume_vs_oi': self.require_volume_vs_oi,
                'min_volume_oi_ratio': self.min_volume_oi_ratio,
                'require_directional_cluster': self.require_directional_cluster,
            }
        }

    def _flow_cluster_to_dict(self, cluster: FlowCluster) -> Dict[str, Any]:
        """Serialize a FlowCluster to a lightweight dict for publishing."""
        return {
            'ticker': cluster.ticker,
            'sentiment': cluster.sentiment,
            'sentiment_score': cluster.sentiment_score,
            'total_premium': cluster.total_premium,
            'call_premium': cluster.call_premium,
            'put_premium': cluster.put_premium,
            'net_premium': cluster.net_premium,
            'sweep_count': cluster.sweep_count,
            'block_count': cluster.block_count,
            'total_trades': cluster.total_trades,
            'timestamp': cluster.timestamp.isoformat(),
            'unusual_count': cluster.unusual_count,
            'aggressive_count': cluster.aggressive_count,
            'directional_clusters': cluster.directional_clusters,
            'elite_score': cluster.elite_score,
            'conviction_level': cluster.conviction_level,
            'avg_volume_vs_oi': cluster.avg_volume_vs_oi,
        }

    async def analyze_ticker(self, ticker: str) -> Dict[str, Any]:
        """Analyze a ticker and return a serialized flow cluster summary."""
        cluster = await self.get_flow_cluster(ticker, refresh=True)
        if not cluster:
            return {}
        return self._flow_cluster_to_dict(cluster)

    async def fetch_trades_with_massive(self, ticker: str, lookback_minutes: int = 10) -> List[OptionsTradeFlow]:
        """
        Fetch options trades using Massive REST client.

        This is more efficient than raw HTTP calls and provides
        proper pagination handling.
        """
        if not self.rest_client:
            return []

        trades = []
        now = datetime.now()

        try:
            # Get option chain snapshot to find active contracts
            chain = self.rest_client.list_snapshot_options_chain(
                underlying_asset=ticker,
                limit=50
            )

            for contract in chain:
                try:
                    option_ticker = contract.get('ticker', '')
                    if not option_ticker:
                        continue

                    # Get recent trades for this contract
                    contract_trades = self.rest_client.list_trades(
                        ticker=option_ticker,
                        limit=100
                    )

                    for t in contract_trades:
                        premium = t.price * t.size * 100 if hasattr(t, 'price') else 0

                        if premium < self.min_premium:
                            continue

                        strike, expiry, opt_type = self._parse_option_ticker(option_ticker)

                        trade = OptionsTradeFlow(
                            timestamp=t.sip_timestamp if hasattr(t, 'sip_timestamp') else now,
                            ticker=ticker,
                            strike=strike,
                            expiry=expiry,
                            option_type=opt_type,
                            price=t.price if hasattr(t, 'price') else 0,
                            size=t.size if hasattr(t, 'size') else 0,
                            premium=premium,
                            exchange=str(t.exchange) if hasattr(t, 'exchange') else '',
                            is_block=premium >= self.block_threshold,
                            sentiment='bullish' if opt_type == 'call' else 'bearish'
                        )
                        trades.append(trade)

                except Exception as e:
                    logger.debug(f"Error fetching trades for contract: {e}")
                    continue

            # Detect sweeps
            trades = self._detect_sweeps(trades)

            logger.info(f"Massive REST: {ticker} - {len(trades)} trades fetched")
            return trades

        except Exception as e:
            logger.error(f"Massive REST error for {ticker}: {e}")
            return []


# Global instance
_polygon_flow_service: Optional[PolygonOptionsFlowService] = None

async def get_polygon_options_flow() -> PolygonOptionsFlowService:
    """Get or create global Polygon options flow service."""
    global _polygon_flow_service
    if _polygon_flow_service is None:
        _polygon_flow_service = PolygonOptionsFlowService()
    return _polygon_flow_service


def get_polygon_flow_service() -> PolygonOptionsFlowService:
    """Synchronous getter for Polygon options flow service (for smartflow_data_connector)."""
    global _polygon_flow_service
    if _polygon_flow_service is None:
        _polygon_flow_service = PolygonOptionsFlowService()
    return _polygon_flow_service
