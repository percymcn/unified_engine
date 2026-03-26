"""
Unusual Whales Options Flow Service
====================================

Premium institutional options flow data - replaces weak Polygon free-tier.

API Features:
- Flow Alerts (sweeps, blocks, unusual activity)
- Dark Pool trades
- Full tape access
- Greeks exposure (GEX, DEX, VEX)
- Market/Sector/ETF Tide indicators
- Real-time WebSocket streaming

API Docs: https://api.unusualwhales.com/docs
Pricing: ~$250/month for full market data (check for trial offers)

Set env: UNUSUAL_WHALES_API_KEY=your_api_key
"""

import os
import logging
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

import aiohttp

logger = logging.getLogger(__name__)

# Check if the official client is available
try:
    # Official client (when available): pip install unusualwhales-python-client
    # from unusualwhales import UnusualWhalesClient
    UW_CLIENT_AVAILABLE = False  # Set to True when client is installed
except ImportError:
    UW_CLIENT_AVAILABLE = False


class FlowSentiment(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class OptionsFlow:
    """Single options flow entry from Unusual Whales"""
    ticker: str
    timestamp: datetime

    # Contract details
    strike: float
    expiry: str
    option_type: str  # 'call' or 'put'

    # Flow details
    premium: float
    volume: int
    open_interest: int

    # Classification
    flow_type: str  # 'sweep', 'block', 'split', 'unusual'
    sentiment: FlowSentiment

    # UW-specific
    unusual_score: float = 0.0  # UW's proprietary score
    is_golden_sweep: bool = False
    is_whale_trade: bool = False  # >$1M premium

    # Computed
    delta: Optional[float] = None
    iv: Optional[float] = None


@dataclass
class FlowSummary:
    """Aggregated flow data for a ticker"""
    ticker: str
    timestamp: datetime

    # Net metrics
    net_premium: float = 0.0  # Call premium - Put premium
    net_volume: int = 0  # Call volume - Put volume

    # Breakdown
    call_premium: float = 0.0
    put_premium: float = 0.0
    call_volume: int = 0
    put_volume: int = 0

    # Large trades
    large_trades_count: int = 0  # >$100k
    whale_trades_count: int = 0  # >$1M
    golden_sweeps_count: int = 0

    # Sentiment score (-100 to +100)
    sentiment_score: float = 0.0

    # Overall
    overall_sentiment: FlowSentiment = FlowSentiment.NEUTRAL

    # Raw flows (for detailed analysis)
    flows: List[OptionsFlow] = field(default_factory=list)


class UnusualWhalesService:
    """
    Unusual Whales API integration for institutional options flow.

    Key endpoints (from https://api.unusualwhales.com/docs):
    - GET /api/option-trades/flow-alerts - Market-wide flow alerts
    - GET /api/stock/{ticker}/flow-alerts - Ticker-specific flow
    - GET /api/darkpool/recent - Recent dark pool trades
    - GET /api/darkpool/{ticker}/recent - Ticker dark pool
    - GET /api/market/market-tide - Market-wide sentiment
    - GET /api/market/sector-tide/{sector} - Sector sentiment
    - GET /api/stock/{ticker}/greek-exposure - GEX/DEX data
    - WebSocket: flow alerts, GEX, news, option trades, price data
    """

    def __init__(self):
        # Try Docker secret first, then environment variable
        self.api_key = None
        secret_path = "/run/secrets/unusual_whales_api_key"
        if os.path.exists(secret_path):
            try:
                with open(secret_path, "r") as f:
                    self.api_key = f.read().strip()
                logger.info("UnusualWhalesService: Loaded API key from Docker secret")
            except Exception as e:
                logger.error(f"Failed to read Unusual Whales API key from secret: {e}")

        if not self.api_key:
            self.api_key = os.getenv("UNUSUAL_WHALES_API_KEY", "")
            if self.api_key:
                logger.info("UnusualWhalesService: Loaded API key from env var")

        self.base_url = "https://api.unusualwhales.com"
        self.session: Optional[aiohttp.ClientSession] = None

        self._is_configured = bool(self.api_key)
        self._use_mock_data = not self._is_configured

        # Rate limiting
        self.requests_per_minute = 60
        self.request_count = 0
        self.last_reset = datetime.now()

        # Caching
        self.flow_cache: Dict[str, FlowSummary] = {}
        self.cache_ttl_seconds = 30
        self.last_cache_update: Dict[str, datetime] = {}

        # Status tracking
        self.last_error: Optional[str] = None
        self.total_requests = 0

        # Data delay tracking for verification
        self._delay_samples: List[float] = []
        self._max_delay_samples = 100
        # Use timezone-aware datetime to avoid comparison errors
        from zoneinfo import ZoneInfo
        EST_TZ = ZoneInfo("America/New_York")
        self._last_delay_log = datetime.now(EST_TZ)
        self._delay_log_interval = 60  # Log delay stats every 60 seconds

        if self._is_configured:
            logger.info("UnusualWhalesService initialized with API key")
        else:
            logger.warning("UnusualWhalesService running in MOCK mode (set UNUSUAL_WHALES_API_KEY)")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session

    async def close(self):
        """Close the session."""
        if self.session and not self.session.closed:
            await self.session.close()

    def _is_market_hours(self, check_time: datetime = None) -> bool:
        """Check if we're in options market hours (9:30 AM - 4:00 PM ET weekdays)."""
        from zoneinfo import ZoneInfo
        EST_TZ = ZoneInfo("America/New_York")

        if check_time is None:
            check_time = datetime.now(EST_TZ)
        elif check_time.tzinfo is None:
            check_time = check_time.replace(tzinfo=EST_TZ)
        else:
            check_time = check_time.astimezone(EST_TZ)

        # Weekday check (0=Monday, 6=Sunday)
        if check_time.weekday() >= 5:
            return False

        # Time check (9:30 AM - 4:00 PM ET)
        market_open = check_time.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = check_time.replace(hour=16, minute=0, second=0, microsecond=0)

        return market_open <= check_time <= market_close

    def _measure_data_delay(self, api_timestamp: datetime, source: str = "UW") -> float:
        """
        Measure and log data delay for verification.
        Only measures delay for TODAY's data during market hours.

        Args:
            api_timestamp: Timestamp from the API response
            source: Data source identifier

        Returns:
            Delay in seconds (or -1 if not applicable)
        """
        from zoneinfo import ZoneInfo
        EST_TZ = ZoneInfo("America/New_York")

        now = datetime.now(EST_TZ)

        # Ensure api_timestamp is timezone-aware
        if api_timestamp.tzinfo is None:
            api_timestamp = api_timestamp.replace(tzinfo=EST_TZ)
        else:
            api_timestamp = api_timestamp.astimezone(EST_TZ)

        # Only measure delay for TODAY's data
        if api_timestamp.date() != now.date():
            # Historical data from previous days - don't count as delay
            return -1

        delay_seconds = (now - api_timestamp).total_seconds()

        # Track delay samples (only today's data)
        self._delay_samples.append(delay_seconds)
        if len(self._delay_samples) > self._max_delay_samples:
            self._delay_samples = self._delay_samples[-self._max_delay_samples:]

        # Only log delay warnings during market hours
        is_market_open = self._is_market_hours(now)

        if delay_seconds > 300 and is_market_open:  # More than 5 minutes during market hours
            delay_str = f"{delay_seconds / 60:.1f} min"
            logger.warning(f"[{source}] Fresh data delayed: {api_timestamp.strftime('%H:%M:%S')} -> "
                          f"{now.strftime('%H:%M:%S')} ({delay_str})")
        elif delay_seconds <= 60:
            logger.debug(f"[{source}] Real-time: {api_timestamp.strftime('%H:%M:%S')} ({delay_seconds:.0f}s)")

        # Periodic summary logging (less frequent)
        if (now - self._last_delay_log).total_seconds() >= self._delay_log_interval:
            self._log_delay_summary(source)
            self._last_delay_log = now

        return delay_seconds

    def _log_delay_summary(self, source: str = "UW"):
        """Log summary of data delays (only for today's data)."""
        from zoneinfo import ZoneInfo
        EST_TZ = ZoneInfo("America/New_York")
        now = datetime.now(EST_TZ)

        is_market_open = self._is_market_hours(now)

        if not self._delay_samples:
            if is_market_open:
                logger.info(f"[{source}] Market open, no fresh data from today yet")
            else:
                logger.debug(f"[{source}] Market closed, showing historical data")
            return

        # Filter to positive samples only (today's data)
        valid_samples = [s for s in self._delay_samples if s >= 0]
        if not valid_samples:
            if is_market_open:
                logger.info(f"[{source}] Market open, awaiting today's flow data")
            return

        avg_delay = sum(valid_samples) / len(valid_samples)
        min_delay = min(valid_samples)

        # Determine status
        if not is_market_open:
            status = "Market Closed"
        elif avg_delay < 30:
            status = "Real-time"
        elif avg_delay < 120:
            status = "Near real-time"
        elif avg_delay < 300:
            status = "Slight delay (1-5 min)"
        else:
            status = f"Delayed ({avg_delay/60:.0f} min)"

        logger.info(f"[{source}] {status} | Today's samples: {len(valid_samples)} | "
                   f"Freshest: {min_delay:.0f}s ago")

    def get_delay_stats(self) -> Dict[str, Any]:
        """Get current delay statistics for dashboard display."""
        is_market_open = self._is_market_hours()

        # Filter to positive samples only (today's data)
        valid_samples = [s for s in self._delay_samples if s >= 0]

        if not valid_samples:
            return {
                "source": "unusual_whales",
                "status": "market_closed" if not is_market_open else "awaiting_data",
                "is_market_open": is_market_open,
                "samples": 0,
                "message": "Market closed - showing historical data" if not is_market_open else "Awaiting today's flow data"
            }

        avg_delay = sum(valid_samples) / len(valid_samples)
        min_delay = min(valid_samples)

        # Determine status
        if not is_market_open:
            status = "market_closed"
        elif avg_delay < 30:
            status = "real-time"
        elif avg_delay < 120:
            status = "near_real-time"
        else:
            status = "delayed"

        return {
            "source": "unusual_whales",
            "avg_delay_seconds": avg_delay,
            "min_delay_seconds": min_delay,
            "max_delay_seconds": max(valid_samples),
            "samples": len(valid_samples),
            "is_realtime": avg_delay < 30,
            "is_market_open": is_market_open,
            "status": status
        }

    async def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        now = datetime.now()
        if (now - self.last_reset).total_seconds() >= 60:
            self.request_count = 0
            self.last_reset = now

        if self.request_count >= self.requests_per_minute:
            wait_time = 60 - (now - self.last_reset).total_seconds()
            if wait_time > 0:
                logger.warning(f"UW rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                self.request_count = 0
                self.last_reset = datetime.now()

        self.request_count += 1
        self.total_requests += 1

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated API request with rate limiting."""
        if not self._is_configured:
            return None

        await self._check_rate_limit()
        session = await self._get_session()

        try:
            url = f"{self.base_url}{endpoint}"
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    self.last_error = None
                    return await response.json()
                elif response.status == 401:
                    self.last_error = "Invalid API key"
                    logger.error("UW API: Unauthorized - check API key")
                elif response.status == 429:
                    self.last_error = "Rate limited"
                    logger.warning("UW API: Rate limited")
                    await asyncio.sleep(60)
                else:
                    self.last_error = f"HTTP {response.status}"
                    logger.error(f"UW API error: {response.status}")
                return None

        except asyncio.TimeoutError:
            self.last_error = "Timeout"
            logger.error("UW API: Request timeout")
            return None
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"UW API error: {e}")
            return None

    async def get_market_tide(self) -> Optional[Dict[str, Any]]:
        """
        Get market-wide options sentiment (Market Tide).

        Returns bullish/bearish premium flow for overall market direction.
        """
        data = await self._make_request("/api/market/market-tide")
        if not data:
            return None

        try:
            # Handle both dict {'data': {...}} and list response formats
            raw = data.get("data", data) if isinstance(data, dict) else data
            tide = raw[0] if isinstance(raw, list) and raw else raw if isinstance(raw, dict) else {}
            bullish = float(tide.get("bullish_premium", 0))
            bearish = float(tide.get("bearish_premium", 0))
            total = bullish + bearish

            return {
                "bullish_premium": bullish,
                "bearish_premium": bearish,
                "net_premium": bullish - bearish,
                "sentiment_score": ((bullish - bearish) / total * 100) if total > 0 else 0,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error parsing market tide: {e}")
            return None

    async def get_gex(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get Gamma Exposure (GEX) for a ticker."""
        data = await self._make_request(f"/api/stock/{ticker}/greek-exposure")
        return data.get("data") if data else None

    async def get_dark_pool_recent(self, ticker: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get recent dark pool trades."""
        if ticker:
            endpoint = f"/api/darkpool/{ticker}/recent"
        else:
            endpoint = "/api/darkpool/recent"

        data = await self._make_request(endpoint, {"limit": limit})
        if not data:
            return []

        return data.get("data", [])

    async def get_flow_by_ticker(
        self,
        ticker: str,
        lookback_minutes: int = 30
    ) -> FlowSummary:
        """
        Get aggregated options flow for a ticker.

        Args:
            ticker: Stock symbol (e.g., 'SPY', 'QQQ')
            lookback_minutes: How far back to aggregate

        Returns:
            FlowSummary with net premium, volume, and sentiment
        """
        # Check cache first (use timezone-aware datetime to avoid comparison errors)
        from zoneinfo import ZoneInfo
        EST_TZ = ZoneInfo("America/New_York")
        now = datetime.now(EST_TZ)

        cache_key = ticker
        if cache_key in self.flow_cache:
            last_update = self.last_cache_update.get(cache_key)
            if last_update:
                # Ensure last_update is timezone-aware for comparison
                if last_update.tzinfo is None:
                    last_update = last_update.replace(tzinfo=EST_TZ)
                if (now - last_update).total_seconds() < self.cache_ttl_seconds:
                    return self.flow_cache[cache_key]

        if self._use_mock_data:
            result = self._generate_mock_flow(ticker)
        else:
            # Use real API endpoint: /api/stock/{ticker}/flow-alerts
            data = await self._make_request(f"/api/stock/{ticker}/flow-alerts", {"limit": 100})

            if not data:
                logger.warning(f"UW API: No data for {ticker}, using mock")
                result = self._generate_mock_flow(ticker)
            else:
                result = self._parse_flow_response(ticker, data)

        # Cache result (use timezone-aware datetime)
        self.flow_cache[cache_key] = result
        self.last_cache_update[cache_key] = now  # Use the EST-aware datetime from above

        return result

    async def get_live_flow(
        self,
        tickers: Optional[List[str]] = None,
        min_premium: float = 50000
    ) -> List[OptionsFlow]:
        """
        Get real-time options flow stream.

        Args:
            tickers: Filter by tickers (None for all)
            min_premium: Minimum premium filter

        Returns:
            List of recent large options flows
        """
        if self._use_mock_data:
            flows = []
            for ticker in (tickers or ['SPY', 'QQQ']):
                summary = self._generate_mock_flow(ticker)
                flows.extend(summary.flows)
            return flows

        # TODO: Real implementation with websocket or polling
        return []

    async def get_dark_pool(self, ticker: str) -> Dict[str, Any]:
        """
        Get dark pool activity for a ticker.

        Returns:
            Dict with dark pool metrics
        """
        if self._use_mock_data:
            return {
                'ticker': ticker,
                'timestamp': datetime.now().isoformat(),
                'dp_volume': 1_500_000,
                'dp_percent': 35.5,
                'net_premium': 2_500_000,
                'large_prints': 5,
                'is_mock': True
            }

        # TODO: Real implementation
        return {}

    async def get_net_flow_sentiment(self, ticker: str) -> Dict[str, Any]:
        """
        Get net flow sentiment analysis.

        Returns:
            Dict with sentiment metrics and score
        """
        flow = await self.get_flow_by_ticker(ticker)

        return {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'net_premium': flow.net_premium,
            'sentiment_score': flow.sentiment_score,
            'sentiment': flow.overall_sentiment.value,
            'call_premium': flow.call_premium,
            'put_premium': flow.put_premium,
            'large_trades': flow.large_trades_count,
            'whale_trades': flow.whale_trades_count,
            'golden_sweeps': flow.golden_sweeps_count
        }

    def _generate_mock_flow(self, ticker: str) -> FlowSummary:
        """
        Generate mock flow data for testing.

        This produces realistic-looking data to test the pipeline.
        Replace with real API data when subscribed.
        """
        import random
        from zoneinfo import ZoneInfo
        EST_TZ = ZoneInfo("America/New_York")

        now = datetime.now(EST_TZ)  # Use timezone-aware datetime

        # Generate some mock flows
        flows = []
        num_flows = random.randint(5, 15)

        call_premium = 0.0
        put_premium = 0.0
        call_volume = 0
        put_volume = 0
        large_trades = 0
        whale_trades = 0
        golden_sweeps = 0

        for i in range(num_flows):
            is_call = random.random() > 0.45  # Slight call bias
            premium = random.uniform(25000, 500000)
            volume = random.randint(100, 5000)

            if premium > 100000:
                large_trades += 1
            if premium > 1000000:
                whale_trades += 1

            is_sweep = random.random() > 0.7
            is_golden = is_sweep and premium > 200000 and random.random() > 0.8
            if is_golden:
                golden_sweeps += 1

            flow = OptionsFlow(
                ticker=ticker,
                timestamp=now - timedelta(minutes=random.randint(0, 30)),
                strike=round(random.uniform(400, 600), 0),
                expiry=(now + timedelta(days=random.randint(1, 45))).strftime('%Y-%m-%d'),
                option_type='call' if is_call else 'put',
                premium=premium,
                volume=volume,
                open_interest=random.randint(1000, 50000),
                flow_type='sweep' if is_sweep else 'block',
                sentiment=FlowSentiment.BULLISH if is_call else FlowSentiment.BEARISH,
                unusual_score=random.uniform(50, 100),
                is_golden_sweep=is_golden,
                is_whale_trade=premium > 1000000
            )
            flows.append(flow)

            if is_call:
                call_premium += premium
                call_volume += volume
            else:
                put_premium += premium
                put_volume += volume

        net_premium = call_premium - put_premium

        # Calculate sentiment score (-100 to +100)
        total_premium = call_premium + put_premium
        if total_premium > 0:
            sentiment_score = ((call_premium - put_premium) / total_premium) * 100
        else:
            sentiment_score = 0.0

        # Determine overall sentiment
        if sentiment_score > 20:
            overall = FlowSentiment.BULLISH
        elif sentiment_score < -20:
            overall = FlowSentiment.BEARISH
        else:
            overall = FlowSentiment.NEUTRAL

        return FlowSummary(
            ticker=ticker,
            timestamp=now,
            net_premium=net_premium,
            net_volume=call_volume - put_volume,
            call_premium=call_premium,
            put_premium=put_premium,
            call_volume=call_volume,
            put_volume=put_volume,
            large_trades_count=large_trades,
            whale_trades_count=whale_trades,
            golden_sweeps_count=golden_sweeps,
            sentiment_score=sentiment_score,
            overall_sentiment=overall,
            flows=flows
        )

    def _parse_flow_response(self, ticker: str, data: Dict) -> FlowSummary:
        """
        Parse real API response into FlowSummary.

        Handles the /api/stock/{ticker}/flow-alerts response format.

        Actual API fields (from UW docs/testing):
        - type: "call" or "put"
        - ticker: stock symbol
        - total_premium: premium amount (may be string)
        - volume: trade volume
        - strike_price: option strike
        - expiration_date: expiry date
        - side: "ask", "bid", "mid"
        - execution_estimate: "at_ask", "above_ask", etc.
        - date: trade date/time
        """
        from zoneinfo import ZoneInfo
        EST_TZ = ZoneInfo("America/New_York")
        now = datetime.now(EST_TZ)  # Use timezone-aware datetime
        flows = []

        call_premium = 0.0
        put_premium = 0.0
        call_volume = 0
        put_volume = 0
        large_trades = 0
        whale_trades = 0
        golden_sweeps = 0

        raw_alerts = data.get("data", [])
        if raw_alerts:
            logger.info(f"UW PARSING: {ticker} - received {len(raw_alerts)} flow alerts from API")
            # Log first alert for debugging field names
            if raw_alerts and len(raw_alerts) > 0:
                logger.debug(f"UW SAMPLE ALERT FIELDS: {list(raw_alerts[0].keys())}")

        for alert in raw_alerts:
            try:
                # Parse individual flow alert
                # API returns "type": "call" or "put" (not "put_call")
                option_type = alert.get("type", alert.get("put_call", "call")).lower()
                is_call = option_type in ("call", "c")

                # API returns "total_premium" (not "premium") - may be string
                premium_raw = alert.get("total_premium", alert.get("premium", 0))
                premium = float(str(premium_raw).replace(",", "")) if premium_raw else 0.0

                # API returns "volume" (not "size")
                volume = int(alert.get("volume", alert.get("size", 0)))

                if premium > 100_000:
                    large_trades += 1
                if premium > 1_000_000:
                    whale_trades += 1

                # Determine flow type and golden sweep status
                # API may use "alert_type", "trade_type", or "execution_estimate"
                alert_type = alert.get("alert_type", alert.get("trade_type", "")).lower()
                execution = alert.get("execution_estimate", alert.get("side", "")).lower()
                is_sweep = "sweep" in alert_type or "sweep" in execution
                at_ask = "ask" in execution or alert.get("side", "").lower() == "ask"
                is_golden = is_sweep and premium > 500_000 and at_ask

                if is_golden:
                    golden_sweeps += 1

                # Determine sentiment
                # API may provide explicit sentiment or we infer from call/put + side
                sentiment_str = alert.get("sentiment", "").lower()
                if "bullish" in sentiment_str:
                    sentiment = FlowSentiment.BULLISH
                elif "bearish" in sentiment_str:
                    sentiment = FlowSentiment.BEARISH
                else:
                    # Calls bought at ask = bullish, puts bought at ask = bearish
                    if is_call and at_ask:
                        sentiment = FlowSentiment.BULLISH
                    elif not is_call and at_ask:
                        sentiment = FlowSentiment.BEARISH
                    else:
                        sentiment = FlowSentiment.BULLISH if is_call else FlowSentiment.BEARISH

                # Parse timestamp - API may use "date", "timestamp", "created_at", or "trade_date"
                flow_timestamp = now
                timestamp_str = alert.get("date", alert.get("timestamp", alert.get("created_at", "")))
                if timestamp_str:
                    try:
                        # Handle various timestamp formats
                        if isinstance(timestamp_str, str):
                            timestamp_str = timestamp_str.replace("Z", "+00:00")
                            flow_timestamp = datetime.fromisoformat(timestamp_str)
                    except Exception as te:
                        logger.debug(f"Could not parse timestamp '{timestamp_str}': {te}")
                        flow_timestamp = now

                # Parse strike - API may use "strike_price" or "strike"
                strike_raw = alert.get("strike_price", alert.get("strike", 0))
                strike = float(str(strike_raw).replace(",", "")) if strike_raw else 0.0

                # Parse expiry - API may use "expiration_date" or "expiry"
                expiry = alert.get("expiration_date", alert.get("expiry", ""))

                flow = OptionsFlow(
                    ticker=ticker,
                    timestamp=flow_timestamp,
                    strike=strike,
                    expiry=expiry,
                    option_type='call' if is_call else 'put',
                    premium=premium,
                    volume=volume,
                    open_interest=int(alert.get("open_interest", alert.get("oi", 0))),
                    flow_type='sweep' if is_sweep else 'block',
                    sentiment=sentiment,
                    unusual_score=float(alert.get("unusual_score", alert.get("score", 50))),
                    is_golden_sweep=is_golden,
                    is_whale_trade=premium > 1_000_000,
                    delta=float(alert.get("delta", 0)) if alert.get("delta") else None,
                    iv=float(alert.get("iv", alert.get("implied_volatility", 0))) if alert.get("iv") or alert.get("implied_volatility") else None,
                )
                flows.append(flow)

                if is_call:
                    call_premium += premium
                    call_volume += volume
                else:
                    put_premium += premium
                    put_volume += volume

            except Exception as e:
                logger.debug(f"Error parsing flow alert: {e}")
                continue

        net_premium = call_premium - put_premium

        # Calculate sentiment score (-100 to +100)
        total_premium = call_premium + put_premium
        if total_premium > 0:
            sentiment_score = ((call_premium - put_premium) / total_premium) * 100
        else:
            sentiment_score = 0.0

        # Determine overall sentiment
        if sentiment_score > 20:
            overall = FlowSentiment.BULLISH
        elif sentiment_score < -20:
            overall = FlowSentiment.BEARISH
        else:
            overall = FlowSentiment.NEUTRAL

        # Measure delay for the MOST RECENT flow only (once per ticker fetch)
        if flows:
            newest_flow = max(flows, key=lambda f: f.timestamp)
            self._measure_data_delay(newest_flow.timestamp, f"UW_{ticker}")

        return FlowSummary(
            ticker=ticker,
            timestamp=now,
            net_premium=net_premium,
            net_volume=call_volume - put_volume,
            call_premium=call_premium,
            put_premium=put_premium,
            call_volume=call_volume,
            put_volume=put_volume,
            large_trades_count=large_trades,
            whale_trades_count=whale_trades,
            golden_sweeps_count=golden_sweeps,
            sentiment_score=sentiment_score,
            overall_sentiment=overall,
            flows=flows
        )


# Global instance
_uw_service: Optional[UnusualWhalesService] = None


async def get_unusual_whales_service() -> UnusualWhalesService:
    """Get or create global UW service instance (async)."""
    global _uw_service
    if _uw_service is None:
        _uw_service = UnusualWhalesService()
    return _uw_service


def get_unusual_whales_service_sync() -> UnusualWhalesService:
    """Get or create global UW service instance (synchronous for smartflow_data_connector)."""
    global _uw_service
    if _uw_service is None:
        _uw_service = UnusualWhalesService()
    return _uw_service
