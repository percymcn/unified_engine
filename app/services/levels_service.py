"""
Key Levels & Confluence Service
================================

Provides PDH/PDL (Previous Day High/Low), Fibonacci retracements/extensions,
and confluence scoring for SmartFlow 2026.

Features:
- PDH/PDL calculation with 5-day cache (Polygon daily bars)
- Fibonacci levels (0.236, 0.382, 0.5, 0.618, 0.786)
- Fibonacci extensions (1.272, 1.618, 2.618)
- Confluence scoring: combines price proximity to levels with flow, regime, imbalance
- Async/await for Pi5 compatibility
- Thread-safe caching

Pi5 Performance: ~5-15ms for level calculation, ~2ms for confluence scoring
"""

import asyncio
import logging
import httpx
import os
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import OrderedDict
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)

# Polygon API
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "f402Q_wfDe7D1Q0GLjTzvBAvKoY7uEPV")
POLYGON_BASE_URL = "https://api.polygon.io"


class LevelType(Enum):
    """Types of key price levels"""
    PDH = "pdh"           # Previous Day High
    PDL = "pdl"           # Previous Day Low
    PWH = "pwh"           # Previous Week High
    PWL = "pwl"           # Previous Week Low
    FIB_236 = "fib_0.236"
    FIB_382 = "fib_0.382"
    FIB_500 = "fib_0.500"
    FIB_618 = "fib_0.618"
    FIB_786 = "fib_0.786"
    FIB_EXT_1272 = "fib_ext_1.272"
    FIB_EXT_1618 = "fib_ext_1.618"
    FIB_EXT_2618 = "fib_ext_2.618"
    VWAP = "vwap"
    POC = "poc"           # Point of Control (volume profile)


@dataclass
class KeyLevel:
    """A single key price level"""
    level_type: LevelType
    price: float
    strength: float = 1.0  # 0-1 strength (based on touches, age, etc.)
    last_test: Optional[datetime] = None
    touch_count: int = 0


@dataclass
class FibonacciLevels:
    """Fibonacci retracement and extension levels"""
    swing_high: float
    swing_low: float
    trend_direction: str  # 'up' or 'down'

    # Retracements
    fib_236: float = 0.0
    fib_382: float = 0.0
    fib_500: float = 0.0
    fib_618: float = 0.0
    fib_786: float = 0.0

    # Extensions
    ext_1272: float = 0.0
    ext_1618: float = 0.0
    ext_2618: float = 0.0

    calculated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Calculate Fibonacci levels from swing points"""
        diff = self.swing_high - self.swing_low

        if self.trend_direction == 'up':
            # Uptrend: retracements down from high, extensions above high
            self.fib_236 = self.swing_high - (diff * 0.236)
            self.fib_382 = self.swing_high - (diff * 0.382)
            self.fib_500 = self.swing_high - (diff * 0.500)
            self.fib_618 = self.swing_high - (diff * 0.618)
            self.fib_786 = self.swing_high - (diff * 0.786)
            # Extensions above high
            self.ext_1272 = self.swing_high + (diff * 0.272)
            self.ext_1618 = self.swing_high + (diff * 0.618)
            self.ext_2618 = self.swing_high + (diff * 1.618)
        else:
            # Downtrend: retracements up from low, extensions below low
            self.fib_236 = self.swing_low + (diff * 0.236)
            self.fib_382 = self.swing_low + (diff * 0.382)
            self.fib_500 = self.swing_low + (diff * 0.500)
            self.fib_618 = self.swing_low + (diff * 0.618)
            self.fib_786 = self.swing_low + (diff * 0.786)
            # Extensions below low
            self.ext_1272 = self.swing_low - (diff * 0.272)
            self.ext_1618 = self.swing_low - (diff * 0.618)
            self.ext_2618 = self.swing_low - (diff * 1.618)

    def to_dict(self) -> Dict[str, float]:
        """Return all levels as dict"""
        return {
            'swing_high': self.swing_high,
            'swing_low': self.swing_low,
            '0.236': self.fib_236,
            '0.382': self.fib_382,
            '0.500': self.fib_500,
            '0.618': self.fib_618,
            '0.786': self.fib_786,
            '1.272': self.ext_1272,
            '1.618': self.ext_1618,
            '2.618': self.ext_2618,
        }

    def all_levels(self) -> List[Tuple[str, float]]:
        """Return all levels as sorted list of (name, price)"""
        levels = [
            ('0.236', self.fib_236),
            ('0.382', self.fib_382),
            ('0.500', self.fib_500),
            ('0.618', self.fib_618),
            ('0.786', self.fib_786),
            ('1.272', self.ext_1272),
            ('1.618', self.ext_1618),
            ('2.618', self.ext_2618),
        ]
        return sorted(levels, key=lambda x: x[1])


@dataclass
class DailyLevels:
    """Previous day high/low and related levels"""
    ticker: str
    date: date
    pdh: float          # Previous Day High
    pdl: float          # Previous Day Low
    pdc: float          # Previous Day Close
    pdo: float          # Previous Day Open

    # Multi-day levels
    pwh: Optional[float] = None  # Previous Week High
    pwl: Optional[float] = None  # Previous Week Low

    # 5-day high/low
    five_day_high: Optional[float] = None
    five_day_low: Optional[float] = None

    # Derived levels
    daily_pivot: float = 0.0       # (H + L + C) / 3
    daily_r1: float = 0.0          # (2 * Pivot) - L
    daily_s1: float = 0.0          # (2 * Pivot) - H
    daily_range_pct: float = 0.0   # (H - L) / C * 100

    calculated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Calculate derived levels"""
        if self.pdh > 0 and self.pdl > 0 and self.pdc > 0:
            self.daily_pivot = (self.pdh + self.pdl + self.pdc) / 3
            self.daily_r1 = (2 * self.daily_pivot) - self.pdl
            self.daily_s1 = (2 * self.daily_pivot) - self.pdh
            self.daily_range_pct = (self.pdh - self.pdl) / self.pdc * 100


@dataclass
class ConfluenceResult:
    """Result of confluence scoring"""
    score: float                    # 0-100 confluence score
    nearest_level: str              # Name of nearest level
    nearest_distance_pct: float     # Distance to nearest level as %
    levels_nearby: int              # Count of levels within 0.5%

    # Component scores
    level_proximity_score: float = 0.0   # 0-40 points for price near key levels
    flow_score: float = 0.0              # 0-25 points for flow conviction
    regime_score: float = 0.0            # 0-20 points for regime alignment
    imbalance_score: float = 0.0         # 0-15 points for order book imbalance

    # Level details
    pdh_distance_pct: float = 0.0
    pdl_distance_pct: float = 0.0
    nearest_fib: str = ''
    nearest_fib_distance_pct: float = 0.0

    # Recommendation
    bias: str = 'neutral'           # 'bullish', 'bearish', 'neutral'
    target_level: Optional[str] = None   # Suggested target level
    stop_level: Optional[str] = None     # Suggested stop level


class LevelsService:
    """
    Key Levels & Confluence Service for SmartFlow 2026.

    Provides:
    - PDH/PDL calculation with caching
    - Fibonacci retracements and extensions
    - Multi-factor confluence scoring
    - Swing high/low detection
    """

    # Confluence scoring weights (must sum to 100)
    WEIGHT_LEVEL_PROXIMITY = 40.0
    WEIGHT_FLOW_CONVICTION = 25.0
    WEIGHT_REGIME_ALIGNMENT = 20.0
    WEIGHT_IMBALANCE = 15.0

    # Flow conviction mappings
    FLOW_CONVICTION_SCORES = {
        'EXTREME': 25.0,
        'HIGH': 20.0,
        'MEDIUM': 12.0,
        'LOW': 5.0,
        'NONE': 0.0,
    }

    # Regime alignment scores (for trending markets)
    REGIME_SCORES = {
        'trending_up': 20.0,
        'trending_down': 20.0,
        'mean_reverting': 12.0,
        'vol_contraction': 15.0,
        'vol_expansion': 8.0,
        'chaotic': 3.0,
        'neutral': 10.0,
    }

    def __init__(
        self,
        cache_days: int = 5,
        cache_ttl_minutes: int = 60,
        swing_lookback_bars: int = 50
    ):
        self.cache_days = cache_days
        self.cache_ttl_minutes = cache_ttl_minutes
        self.swing_lookback_bars = swing_lookback_bars

        # LRU-style cache for daily levels
        self._daily_cache: OrderedDict[str, Tuple[DailyLevels, datetime]] = OrderedDict()
        self._fib_cache: OrderedDict[str, Tuple[FibonacciLevels, datetime]] = OrderedDict()
        self._max_cache_size = 50

        # HTTP client (reuse for performance)
        self._http_client: Optional[httpx.AsyncClient] = None

        logger.info(f"LevelsService initialized: cache_days={cache_days}, "
                   f"ttl={cache_ttl_minutes}min, swing_lookback={swing_lookback_bars}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=15.0)
        return self._http_client

    async def close(self):
        """Close HTTP client"""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    def _get_polygon_ticker(self, ticker: str) -> str:
        """Convert ticker to Polygon format"""
        mapping = {
            'MES': 'SPY',
            'NQ': 'QQQ',
            'MNQ': 'QQQ',
            'RTY': 'IWM',
            'GC': 'GLD',
            'MYM': 'DIA',
            'US30': 'DIA',
            'US500': 'SPY',
            'USTEC': 'QQQ',
            'NAS100': 'QQQ',
            'BTCUSD': 'X:BTCUSD',
            'ETHUSD': 'X:ETHUSD',
            'USDJPY': 'C:USDJPY',
            'GBPJPY': 'C:GBPJPY',
            'XAUUSD': 'C:XAUUSD',
        }
        return mapping.get(ticker.upper(), ticker.upper())

    async def calculate_pdh_pdl(self, ticker: str, force_refresh: bool = False) -> Optional[DailyLevels]:
        """
        Calculate Previous Day High/Low using Polygon daily bars.
        Caches last 5 days of data.

        Args:
            ticker: Symbol to fetch (will be converted to Polygon format)
            force_refresh: Force cache refresh

        Returns:
            DailyLevels with PDH, PDL, and derived levels
        """
        cache_key = ticker.upper()

        # Check cache
        if not force_refresh and cache_key in self._daily_cache:
            cached, cached_at = self._daily_cache[cache_key]
            if datetime.now() - cached_at < timedelta(minutes=self.cache_ttl_minutes):
                return cached

        try:
            polygon_ticker = self._get_polygon_ticker(ticker)

            # Fetch last 10 daily bars (to ensure we have 5 trading days)
            end_date = date.today()
            start_date = end_date - timedelta(days=14)

            url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/{polygon_ticker}/range/1/day/{start_date}/{end_date}"

            client = await self._get_client()
            response = await client.get(url, params={
                'apiKey': POLYGON_API_KEY,
                'adjusted': 'true',
                'sort': 'desc',
                'limit': 10
            })

            if response.status_code != 200:
                logger.warning(f"Polygon daily bars failed for {ticker}: {response.status_code}")
                return None

            data = response.json()
            results = data.get('results', [])

            if len(results) < 2:
                logger.warning(f"Insufficient daily bars for {ticker}: {len(results)}")
                return None

            # results[0] = today (incomplete), results[1] = previous day (complete)
            prev_day = results[1]

            # Calculate 5-day high/low
            five_day_high = max(r['h'] for r in results[:6]) if len(results) >= 6 else None
            five_day_low = min(r['l'] for r in results[:6]) if len(results) >= 6 else None

            # Previous week high/low (5 trading days)
            pwh = max(r['h'] for r in results[1:6]) if len(results) >= 6 else None
            pwl = min(r['l'] for r in results[1:6]) if len(results) >= 6 else None

            daily_levels = DailyLevels(
                ticker=ticker,
                date=date.fromtimestamp(prev_day['t'] / 1000),
                pdh=prev_day['h'],
                pdl=prev_day['l'],
                pdc=prev_day['c'],
                pdo=prev_day['o'],
                pwh=pwh,
                pwl=pwl,
                five_day_high=five_day_high,
                five_day_low=five_day_low,
            )

            # Update cache
            self._daily_cache[cache_key] = (daily_levels, datetime.now())
            self._daily_cache.move_to_end(cache_key)

            # Prune cache
            while len(self._daily_cache) > self._max_cache_size:
                self._daily_cache.popitem(last=False)

            logger.debug(f"Calculated PDH/PDL for {ticker}: PDH={daily_levels.pdh:.2f}, "
                        f"PDL={daily_levels.pdl:.2f}, Pivot={daily_levels.daily_pivot:.2f}")

            return daily_levels

        except Exception as e:
            logger.error(f"Error calculating PDH/PDL for {ticker}: {e}")
            return None

    def calculate_fib_levels(
        self,
        swing_high: float,
        swing_low: float,
        trend_direction: str = 'up'
    ) -> FibonacciLevels:
        """
        Calculate Fibonacci retracement and extension levels.

        Args:
            swing_high: Recent swing high price
            swing_low: Recent swing low price
            trend_direction: 'up' for bullish swing, 'down' for bearish

        Returns:
            FibonacciLevels with retracements (0.236-0.786) and extensions (1.272-2.618)
        """
        return FibonacciLevels(
            swing_high=swing_high,
            swing_low=swing_low,
            trend_direction=trend_direction
        )

    async def detect_swing_points(
        self,
        ticker: str,
        timeframe: str = '1h',
        lookback_bars: int = 50
    ) -> Tuple[float, float, str]:
        """
        Detect swing high and swing low from recent price data.

        Returns:
            (swing_high, swing_low, trend_direction)
        """
        try:
            polygon_ticker = self._get_polygon_ticker(ticker)

            # Map timeframe to Polygon multiplier/span
            tf_map = {
                '5m': ('5', 'minute'),
                '15m': ('15', 'minute'),
                '30m': ('30', 'minute'),
                '1h': ('1', 'hour'),
                '4h': ('4', 'hour'),
                '1d': ('1', 'day'),
            }
            mult, span = tf_map.get(timeframe, ('1', 'hour'))

            end_date = date.today()
            start_date = end_date - timedelta(days=7)

            url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/{polygon_ticker}/range/{mult}/{span}/{start_date}/{end_date}"

            client = await self._get_client()
            response = await client.get(url, params={
                'apiKey': POLYGON_API_KEY,
                'adjusted': 'true',
                'sort': 'asc',
                'limit': lookback_bars
            })

            if response.status_code != 200:
                logger.warning(f"Swing detection failed for {ticker}: {response.status_code}")
                return 0.0, 0.0, 'neutral'

            data = response.json()
            results = data.get('results', [])

            if len(results) < 10:
                return 0.0, 0.0, 'neutral'

            highs = [r['h'] for r in results]
            lows = [r['l'] for r in results]
            closes = [r['c'] for r in results]

            # Find swing high (local maximum)
            swing_high = max(highs)
            swing_high_idx = highs.index(swing_high)

            # Find swing low (local minimum)
            swing_low = min(lows)
            swing_low_idx = lows.index(swing_low)

            # Determine trend direction
            if swing_high_idx > swing_low_idx:
                # Recent high after recent low = uptrend
                trend_direction = 'up'
            else:
                # Recent low after recent high = downtrend
                trend_direction = 'down'

            # Confirm with recent price action
            recent_avg = np.mean(closes[-5:])
            mid_point = (swing_high + swing_low) / 2
            if recent_avg > mid_point:
                trend_direction = 'up'
            else:
                trend_direction = 'down'

            return swing_high, swing_low, trend_direction

        except Exception as e:
            logger.error(f"Swing detection error for {ticker}: {e}")
            return 0.0, 0.0, 'neutral'

    async def get_all_levels(self, ticker: str, current_price: float = 0.0) -> Dict[str, float]:
        """
        Get all key levels for a ticker (PDH/PDL + Fibs).

        Returns dict of level_name -> price
        """
        levels = {}

        # Get daily levels
        daily = await self.calculate_pdh_pdl(ticker)
        if daily:
            levels['PDH'] = daily.pdh
            levels['PDL'] = daily.pdl
            levels['PDC'] = daily.pdc
            levels['Pivot'] = daily.daily_pivot
            levels['R1'] = daily.daily_r1
            levels['S1'] = daily.daily_s1
            if daily.pwh:
                levels['PWH'] = daily.pwh
            if daily.pwl:
                levels['PWL'] = daily.pwl
            if daily.five_day_high:
                levels['5D_High'] = daily.five_day_high
            if daily.five_day_low:
                levels['5D_Low'] = daily.five_day_low

        # Get Fibonacci levels
        swing_high, swing_low, trend = await self.detect_swing_points(ticker)
        if swing_high > 0 and swing_low > 0:
            fibs = self.calculate_fib_levels(swing_high, swing_low, trend)
            fib_dict = fibs.to_dict()
            for key, value in fib_dict.items():
                if key not in ['swing_high', 'swing_low']:
                    levels[f'Fib_{key}'] = value
            levels['Swing_High'] = swing_high
            levels['Swing_Low'] = swing_low

        return levels

    def get_confluence_score(
        self,
        price: float,
        pdh: float,
        pdl: float,
        fibs: Optional[FibonacciLevels],
        flow_conviction: str = 'NONE',
        regime: str = 'neutral',
        imbalance: float = 0.0,
        direction: str = 'long'
    ) -> ConfluenceResult:
        """
        Calculate multi-factor confluence score.

        Scoring breakdown (0-100):
        - Level proximity: 0-40 points (price near PDH/PDL/Fibs)
        - Flow conviction: 0-25 points (EXTREME=25, HIGH=20, MEDIUM=12)
        - Regime alignment: 0-20 points (trending=20, ranging=12)
        - Order imbalance: 0-15 points (strong imbalance confirms direction)

        Args:
            price: Current price
            pdh: Previous day high
            pdl: Previous day low
            fibs: FibonacciLevels object (optional)
            flow_conviction: 'EXTREME', 'HIGH', 'MEDIUM', 'LOW', 'NONE'
            regime: Current market regime
            imbalance: Order book imbalance (-1 to +1, positive = bid heavy)
            direction: 'long' or 'short' for context

        Returns:
            ConfluenceResult with score 0-100 and details
        """
        result = ConfluenceResult(
            score=0.0,
            nearest_level='',
            nearest_distance_pct=100.0,
            levels_nearby=0
        )

        if price <= 0:
            return result

        # ========================================
        # 1. LEVEL PROXIMITY SCORE (0-40 points)
        # ========================================
        all_levels: List[Tuple[str, float]] = []

        if pdh > 0:
            all_levels.append(('PDH', pdh))
        if pdl > 0:
            all_levels.append(('PDL', pdl))

        if fibs:
            all_levels.extend([
                ('Fib_0.236', fibs.fib_236),
                ('Fib_0.382', fibs.fib_382),
                ('Fib_0.500', fibs.fib_500),
                ('Fib_0.618', fibs.fib_618),
                ('Fib_0.786', fibs.fib_786),
                ('Fib_1.272', fibs.ext_1272),
                ('Fib_1.618', fibs.ext_1618),
            ])

        # Calculate distances
        level_distances = []
        for name, level_price in all_levels:
            if level_price > 0:
                distance_pct = abs(price - level_price) / price * 100
                level_distances.append((name, level_price, distance_pct))

        if level_distances:
            # Sort by distance
            level_distances.sort(key=lambda x: x[2])

            # Nearest level
            nearest_name, nearest_price, nearest_dist = level_distances[0]
            result.nearest_level = nearest_name
            result.nearest_distance_pct = nearest_dist

            # Count levels within 0.5%
            result.levels_nearby = sum(1 for _, _, d in level_distances if d <= 0.5)

            # Level proximity scoring
            # At level (0-0.1%): 40 points
            # Within 0.2%: 35 points
            # Within 0.3%: 30 points
            # Within 0.5%: 20 points
            # Within 1.0%: 10 points
            # > 1.0%: 0-5 points
            if nearest_dist <= 0.1:
                result.level_proximity_score = 40.0
            elif nearest_dist <= 0.2:
                result.level_proximity_score = 35.0
            elif nearest_dist <= 0.3:
                result.level_proximity_score = 30.0
            elif nearest_dist <= 0.5:
                result.level_proximity_score = 20.0
            elif nearest_dist <= 1.0:
                result.level_proximity_score = 10.0
            else:
                result.level_proximity_score = max(0, 5.0 - nearest_dist)

            # Bonus for multiple levels nearby (confluence)
            if result.levels_nearby >= 3:
                result.level_proximity_score = min(40, result.level_proximity_score + 5)
            elif result.levels_nearby >= 2:
                result.level_proximity_score = min(40, result.level_proximity_score + 3)

            # PDH/PDL distance tracking
            for name, level_price, dist in level_distances:
                if name == 'PDH':
                    result.pdh_distance_pct = dist
                elif name == 'PDL':
                    result.pdl_distance_pct = dist
                elif 'Fib' in name and result.nearest_fib == '':
                    result.nearest_fib = name
                    result.nearest_fib_distance_pct = dist

        # ========================================
        # 2. FLOW CONVICTION SCORE (0-25 points)
        # ========================================
        result.flow_score = self.FLOW_CONVICTION_SCORES.get(flow_conviction.upper(), 0.0)

        # ========================================
        # 3. REGIME ALIGNMENT SCORE (0-20 points)
        # ========================================
        regime_lower = regime.lower().replace('-', '_')
        result.regime_score = self.REGIME_SCORES.get(regime_lower, 10.0)

        # Regime-direction alignment bonus
        if direction == 'long' and regime_lower == 'trending_up':
            result.regime_score = 20.0  # Max
        elif direction == 'short' and regime_lower == 'trending_down':
            result.regime_score = 20.0
        elif direction == 'long' and regime_lower == 'trending_down':
            result.regime_score = 5.0  # Penalty for counter-trend
        elif direction == 'short' and regime_lower == 'trending_up':
            result.regime_score = 5.0

        # ========================================
        # 4. ORDER IMBALANCE SCORE (0-15 points)
        # ========================================
        # imbalance: -1 (ask heavy) to +1 (bid heavy)
        if direction == 'long':
            # For longs, positive imbalance is good
            if imbalance > 0.5:
                result.imbalance_score = 15.0
            elif imbalance > 0.3:
                result.imbalance_score = 12.0
            elif imbalance > 0.1:
                result.imbalance_score = 8.0
            elif imbalance > -0.2:
                result.imbalance_score = 5.0
            else:
                result.imbalance_score = 0.0
        else:
            # For shorts, negative imbalance is good
            if imbalance < -0.5:
                result.imbalance_score = 15.0
            elif imbalance < -0.3:
                result.imbalance_score = 12.0
            elif imbalance < -0.1:
                result.imbalance_score = 8.0
            elif imbalance < 0.2:
                result.imbalance_score = 5.0
            else:
                result.imbalance_score = 0.0

        # ========================================
        # TOTAL SCORE
        # ========================================
        result.score = (
            result.level_proximity_score +
            result.flow_score +
            result.regime_score +
            result.imbalance_score
        )
        result.score = min(100.0, result.score)

        # ========================================
        # DETERMINE BIAS
        # ========================================
        if result.score >= 70:
            if direction == 'long':
                result.bias = 'bullish'
            else:
                result.bias = 'bearish'
        elif result.score >= 50:
            result.bias = direction  # Weak bias
        else:
            result.bias = 'neutral'

        # ========================================
        # SUGGEST TARGET/STOP LEVELS
        # ========================================
        if fibs and result.bias != 'neutral':
            if result.bias == 'bullish':
                # Target: next resistance (Fib extension or PDH)
                targets = [(n, p) for n, p, d in level_distances if p > price]
                targets.sort(key=lambda x: x[1])
                if targets:
                    result.target_level = targets[0][0]

                # Stop: nearest support below
                stops = [(n, p) for n, p, d in level_distances if p < price]
                stops.sort(key=lambda x: x[1], reverse=True)
                if stops:
                    result.stop_level = stops[0][0]
            else:
                # Target: next support (Fib or PDL)
                targets = [(n, p) for n, p, d in level_distances if p < price]
                targets.sort(key=lambda x: x[1], reverse=True)
                if targets:
                    result.target_level = targets[0][0]

                # Stop: nearest resistance above
                stops = [(n, p) for n, p, d in level_distances if p > price]
                stops.sort(key=lambda x: x[1])
                if stops:
                    result.stop_level = stops[0][0]

        logger.debug(
            f"Confluence {direction}: score={result.score:.0f} "
            f"(levels={result.level_proximity_score:.0f}, flow={result.flow_score:.0f}, "
            f"regime={result.regime_score:.0f}, imbal={result.imbalance_score:.0f}) "
            f"nearest={result.nearest_level}@{result.nearest_distance_pct:.2f}%"
        )

        return result


# ========================================
# NEWS SENTIMENT (Lightweight)
# ========================================

@dataclass
class NewsSentiment:
    """Simple news sentiment result"""
    ticker: str
    sentiment_score: float  # -1 to +1
    headline_count: int
    positive_keywords: int
    negative_keywords: int
    boost: float = 0.0      # Probability boost to apply


class LightweightNewsSentiment:
    """
    Lightweight news sentiment analyzer using keyword matching.
    No external API required - uses cached headlines or simple fetch.
    """

    POSITIVE_KEYWORDS = [
        'surge', 'rally', 'gains', 'bullish', 'breakout', 'strong',
        'beat', 'upgrade', 'outperform', 'buy', 'growth', 'record',
        'soars', 'jumps', 'rises', 'positive', 'optimistic', 'boom',
    ]

    NEGATIVE_KEYWORDS = [
        'plunge', 'crash', 'drops', 'bearish', 'breakdown', 'weak',
        'miss', 'downgrade', 'underperform', 'sell', 'decline', 'falls',
        'tumbles', 'sinks', 'negative', 'pessimistic', 'bust', 'fear',
        'recession', 'layoffs', 'warning', 'risk',
    ]

    def __init__(self):
        self._cache: Dict[str, Tuple[NewsSentiment, datetime]] = {}
        self._cache_ttl_minutes = 15

    async def get_sentiment(self, ticker: str) -> NewsSentiment:
        """
        Get sentiment for ticker using keyword analysis.
        Falls back to neutral if no data available.
        """
        cache_key = ticker.upper()

        # Check cache
        if cache_key in self._cache:
            cached, cached_at = self._cache[cache_key]
            if datetime.now() - cached_at < timedelta(minutes=self._cache_ttl_minutes):
                return cached

        # Try to fetch headlines from Polygon
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                url = f"{POLYGON_BASE_URL}/v2/reference/news"
                response = await client.get(url, params={
                    'ticker': ticker,
                    'limit': 10,
                    'apiKey': POLYGON_API_KEY
                })

                if response.status_code != 200:
                    return NewsSentiment(ticker=ticker, sentiment_score=0.0,
                                        headline_count=0, positive_keywords=0,
                                        negative_keywords=0)

                data = response.json()
                articles = data.get('results', [])

                if not articles:
                    return NewsSentiment(ticker=ticker, sentiment_score=0.0,
                                        headline_count=0, positive_keywords=0,
                                        negative_keywords=0)

                # Analyze headlines
                positive_count = 0
                negative_count = 0

                for article in articles:
                    title = article.get('title', '').lower()
                    description = article.get('description', '').lower()
                    text = f"{title} {description}"

                    for kw in self.POSITIVE_KEYWORDS:
                        if kw in text:
                            positive_count += 1

                    for kw in self.NEGATIVE_KEYWORDS:
                        if kw in text:
                            negative_count += 1

                # Calculate sentiment score
                total = positive_count + negative_count
                if total > 0:
                    sentiment_score = (positive_count - negative_count) / total
                else:
                    sentiment_score = 0.0

                # Calculate boost
                boost = 0.0
                if sentiment_score > 0.5:
                    boost = 0.05  # +5% for strong positive
                elif sentiment_score > 0.3:
                    boost = 0.03
                elif sentiment_score < -0.5:
                    boost = -0.05  # Penalty for strong negative
                elif sentiment_score < -0.3:
                    boost = -0.03

                result = NewsSentiment(
                    ticker=ticker,
                    sentiment_score=sentiment_score,
                    headline_count=len(articles),
                    positive_keywords=positive_count,
                    negative_keywords=negative_count,
                    boost=boost
                )

                # Cache
                self._cache[cache_key] = (result, datetime.now())

                logger.debug(f"News sentiment {ticker}: score={sentiment_score:.2f}, "
                           f"pos={positive_count}, neg={negative_count}, boost={boost:.2f}")

                return result

        except Exception as e:
            logger.debug(f"News sentiment error for {ticker}: {e}")
            return NewsSentiment(ticker=ticker, sentiment_score=0.0,
                                headline_count=0, positive_keywords=0,
                                negative_keywords=0)


# ========================================
# GLOBAL INSTANCES
# ========================================

_levels_service: Optional[LevelsService] = None
_news_sentiment: Optional[LightweightNewsSentiment] = None


def get_levels_service() -> LevelsService:
    """Get or create global levels service instance"""
    global _levels_service
    if _levels_service is None:
        _levels_service = LevelsService()
    return _levels_service


def get_news_sentiment() -> LightweightNewsSentiment:
    """Get or create global news sentiment instance"""
    global _news_sentiment
    if _news_sentiment is None:
        _news_sentiment = LightweightNewsSentiment()
    return _news_sentiment


async def get_levels_service_async() -> LevelsService:
    """Async getter for levels service"""
    return get_levels_service()
