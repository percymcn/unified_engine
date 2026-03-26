"""
Strategy Engine Base Class
===========================

Abstract base for all SmartFlow strategy engines.
Provides common utilities and interface for signal generation.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    ta = None


@dataclass
class SignalContext:
    """Context information for a trading signal."""
    ticker: str
    timestamp: datetime
    close: float
    high: float
    low: float
    open: float
    volume: float

    # OHLCV data for calculations
    df: Optional[pd.DataFrame] = None  # Full OHLCV dataframe

    # Market structure
    vwap: float = 0.0
    prior_day_high: float = 0.0
    prior_day_low: float = 0.0
    prior_day_close: float = 0.0

    # Volatility
    atr: float = 0.0
    atr_period: int = 14

    # Trend
    ema_9: float = 0.0
    ema_21: float = 0.0
    ema_50: float = 0.0

    # Mean reversion
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0
    rsi: float = 50.0

    # Additional context
    regime: str = "neutral"
    market_session: str = "regular"  # pre, regular, post


@dataclass
class TradingSignal:
    """A trading signal from a strategy engine."""
    # Identification
    strategy_id: str
    strategy_type: str  # breakout, trend, mean_reversion, liquidity_reversal
    ticker: str
    timestamp: datetime

    # Signal
    direction: str  # 'long', 'short', 'close', 'none'
    confidence: float = 0.0  # 0-1

    # Entry
    entry_price: float = 0.0
    entry_condition: str = ""

    # Risk management
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_reward_ratio: float = 0.0

    # Position sizing
    position_size_pct: float = 1.0  # Percentage of allocated capital

    # Context
    setup_description: str = ""
    regime: str = "neutral"
    timeframe: str = "5m"

    # Supporting data
    key_levels: List[float] = field(default_factory=list)
    indicators: Dict[str, float] = field(default_factory=dict)

    # Metadata
    is_valid: bool = True
    invalidation_reason: str = ""


class StrategyEngine(ABC):
    """
    Abstract base class for strategy engines.

    All strategy engines must implement:
    1. generate_signal() - produce trading signals
    2. validate_setup() - check if current conditions meet entry criteria
    3. calculate_risk_params() - determine stop loss and take profit
    """

    def __init__(self, strategy_id: str, strategy_type: str):
        self.strategy_id = strategy_id
        self.strategy_type = strategy_type
        self.logger = logging.getLogger(f"{__name__}.{strategy_type}")

        # Default parameters (override in subclasses)
        self.min_risk_reward = 1.5
        self.atr_period = 14
        self.default_position_size_pct = 1.0

    @abstractmethod
    def generate_signal(self, context: SignalContext) -> TradingSignal:
        """
        Generate a trading signal based on current market context.

        Args:
            context: Current market data and indicators

        Returns:
            TradingSignal with direction, entry, stops, targets
        """
        pass

    @abstractmethod
    def validate_setup(self, context: SignalContext) -> Tuple[bool, str]:
        """
        Check if current market conditions meet strategy entry criteria.

        Args:
            context: Current market data and indicators

        Returns:
            (is_valid, reason) tuple
        """
        pass

    @abstractmethod
    def calculate_risk_params(
        self,
        context: SignalContext,
        direction: str
    ) -> Tuple[float, float, float]:
        """
        Calculate stop loss, take profit, and risk:reward ratio.

        Args:
            context: Current market data
            direction: 'long' or 'short'

        Returns:
            (stop_loss, take_profit, risk_reward_ratio)
        """
        pass

    # ========================
    # Common Utility Methods
    # ========================

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        if df is None or len(df) < period:
            return 0.0

        if not PANDAS_TA_AVAILABLE:
            # Fallback: simple high-low range
            return df['high'].tail(period).mean() - df['low'].tail(period).mean()

        atr = ta.atr(df['high'], df['low'], df['close'], length=period)
        if atr is None or atr.isna().all():
            return 0.0

        return float(atr.iloc[-1])

    def calculate_ema(self, df: pd.DataFrame, period: int) -> float:
        """Calculate Exponential Moving Average."""
        if df is None or len(df) < period:
            return 0.0

        if not PANDAS_TA_AVAILABLE:
            # Fallback: simple moving average
            return float(df['close'].tail(period).mean())

        ema = ta.ema(df['close'], length=period)
        if ema is None or ema.isna().all():
            return 0.0

        return float(ema.iloc[-1])

    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Relative Strength Index."""
        if df is None or len(df) < period + 1:
            return 50.0

        if not PANDAS_TA_AVAILABLE:
            # Fallback: return neutral
            return 50.0

        rsi = ta.rsi(df['close'], length=period)
        if rsi is None or rsi.isna().all():
            return 50.0

        return float(rsi.iloc[-1])

    def calculate_bollinger_bands(
        self,
        df: pd.DataFrame,
        period: int = 20,
        std: float = 2.0
    ) -> Tuple[float, float, float]:
        """
        Calculate Bollinger Bands.

        Returns:
            (upper, middle, lower)
        """
        if df is None or len(df) < period:
            return (0.0, 0.0, 0.0)

        if not PANDAS_TA_AVAILABLE:
            # Fallback: simple calculation
            middle = df['close'].tail(period).mean()
            std_dev = df['close'].tail(period).std()
            upper = middle + (std * std_dev)
            lower = middle - (std * std_dev)
            return (float(upper), float(middle), float(lower))

        bb = ta.bbands(df['close'], length=period, std=std)
        if bb is None or bb.empty:
            return (0.0, 0.0, 0.0)

        upper = float(bb[f'BBU_{period}_{std}'].iloc[-1]) if f'BBU_{period}_{std}' in bb.columns else 0.0
        middle = float(bb[f'BBM_{period}_{std}'].iloc[-1]) if f'BBM_{period}_{std}' in bb.columns else 0.0
        lower = float(bb[f'BBL_{period}_{std}'].iloc[-1]) if f'BBL_{period}_{std}' in bb.columns else 0.0

        return (upper, middle, lower)

    def calculate_vwap(self, df: pd.DataFrame) -> float:
        """Calculate Volume Weighted Average Price."""
        if df is None or len(df) == 0:
            return 0.0

        # Simple VWAP: cumsum(price * volume) / cumsum(volume)
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).sum() / df['volume'].sum()

        return float(vwap)

    def find_prior_day_levels(self, df: pd.DataFrame) -> Tuple[float, float, float]:
        """
        Find prior day high, low, close.

        Returns:
            (high, low, close)
        """
        if df is None or len(df) < 2:
            return (0.0, 0.0, 0.0)

        # Assume df has daily bars or we need to resample
        # For now, use last N bars as "prior day"
        prior_bars = df.iloc[:-1].tail(78)  # Last ~6.5 hours (78 * 5min bars)

        if len(prior_bars) == 0:
            return (0.0, 0.0, 0.0)

        pdh = float(prior_bars['high'].max())
        pdl = float(prior_bars['low'].min())
        pdc = float(prior_bars['close'].iloc[-1])

        return (pdh, pdl, pdc)

    def detect_compression(self, df: pd.DataFrame, lookback: int = 20) -> bool:
        """
        Detect price compression (consolidation).
        Returns True if ATR is contracting.
        """
        if df is None or len(df) < lookback + self.atr_period:
            return False

        # Calculate recent ATR vs historical ATR
        atr_current = self.calculate_atr(df.tail(self.atr_period), self.atr_period)
        atr_historical = self.calculate_atr(df.tail(lookback + self.atr_period).head(lookback), self.atr_period)

        if atr_historical == 0:
            return False

        # Compression if current ATR is < 70% of historical
        return atr_current < (0.7 * atr_historical)

    def detect_volume_expansion(self, df: pd.DataFrame, threshold: float = 1.3) -> bool:
        """
        Detect volume expansion.
        Returns True if current volume > threshold * average volume.
        """
        if df is None or len(df) < 21:
            return False

        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].tail(20).mean()

        if avg_volume == 0:
            return False

        return current_volume > (threshold * avg_volume)

    def find_equal_highs_lows(
        self,
        df: pd.DataFrame,
        tolerance_pct: float = 0.002,
        lookback: int = 20
    ) -> Tuple[List[float], List[float]]:
        """
        Find equal highs and equal lows (liquidity pools).

        Args:
            df: OHLCV dataframe
            tolerance_pct: Price tolerance for "equal" (0.2% default)
            lookback: Bars to look back

        Returns:
            (equal_highs, equal_lows) as lists of price levels
        """
        if df is None or len(df) < lookback:
            return ([], [])

        recent_df = df.tail(lookback)

        # Find swing highs and lows
        highs = recent_df['high'].tolist()
        lows = recent_df['low'].tolist()

        # Group similar highs
        equal_highs = []
        for i, h in enumerate(highs):
            for j in range(i + 1, len(highs)):
                if abs(highs[j] - h) / h < tolerance_pct:
                    equal_highs.append(h)
                    break

        # Group similar lows
        equal_lows = []
        for i, l in enumerate(lows):
            for j in range(i + 1, len(lows)):
                if abs(lows[j] - l) / l < tolerance_pct:
                    equal_lows.append(l)
                    break

        return (list(set(equal_highs)), list(set(equal_lows)))

    def is_trending(self, df: pd.DataFrame, period: int = 50) -> Tuple[bool, str]:
        """
        Detect if market is trending.

        Returns:
            (is_trending, direction) where direction is 'up', 'down', or 'sideways'
        """
        if df is None or len(df) < period:
            return (False, 'sideways')

        # Use EMA slopes
        ema_fast = self.calculate_ema(df, 9)
        ema_slow = self.calculate_ema(df, 21)

        if ema_fast == 0 or ema_slow == 0:
            return (False, 'sideways')

        # Trending up: fast > slow and both rising
        if ema_fast > ema_slow * 1.005:  # 0.5% above
            return (True, 'up')
        elif ema_fast < ema_slow * 0.995:  # 0.5% below
            return (True, 'down')
        else:
            return (False, 'sideways')

    def is_ranging(self, df: pd.DataFrame, lookback: int = 20) -> bool:
        """
        Detect if market is ranging (not trending).
        Returns True if price is bouncing within a defined range.
        """
        if df is None or len(df) < lookback:
            return False

        recent_df = df.tail(lookback)

        # Check if price is staying within a range
        range_high = recent_df['high'].max()
        range_low = recent_df['low'].min()
        range_size = range_high - range_low

        if range_size == 0:
            return False

        # Calculate how much price moved vs range size
        price_change = abs(recent_df['close'].iloc[-1] - recent_df['close'].iloc[0])

        # Ranging if price didn't move much relative to the range
        return price_change < (0.3 * range_size)

    def enrich_context(self, context: SignalContext) -> SignalContext:
        """
        Enrich context with calculated indicators.
        This is a helper to ensure all common indicators are available.
        """
        if context.df is None or len(context.df) < 50:
            self.logger.warning(f"Insufficient data for {context.ticker}, context will be incomplete")
            return context

        df = context.df

        # Calculate ATR if not provided
        if context.atr == 0.0:
            context.atr = self.calculate_atr(df, self.atr_period)

        # Calculate EMAs
        if context.ema_9 == 0.0:
            context.ema_9 = self.calculate_ema(df, 9)
        if context.ema_21 == 0.0:
            context.ema_21 = self.calculate_ema(df, 21)
        if context.ema_50 == 0.0:
            context.ema_50 = self.calculate_ema(df, 50)

        # Calculate Bollinger Bands
        if context.bb_upper == 0.0:
            bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(df, 20, 2.0)
            context.bb_upper = bb_upper
            context.bb_middle = bb_middle
            context.bb_lower = bb_lower

        # Calculate RSI
        if context.rsi == 50.0:
            context.rsi = self.calculate_rsi(df, 14)

        # Calculate VWAP
        if context.vwap == 0.0:
            context.vwap = self.calculate_vwap(df)

        # Find prior day levels
        if context.prior_day_high == 0.0:
            pdh, pdl, pdc = self.find_prior_day_levels(df)
            context.prior_day_high = pdh
            context.prior_day_low = pdl
            context.prior_day_close = pdc

        return context
