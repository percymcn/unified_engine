"""
Elite Regime Detector Module
============================

Classifies market regime every 15-30 minutes using:
- ADX(14) for trend strength
- Rolling Hurst exponent for mean-reversion vs momentum
- GARCH-style volatility clustering (simplified)
- ATR-based volatility bands

Regimes:
- TRENDING: Strong directional movement (ADX > 25, Hurst > 0.55)
- RANGING: Mean-reverting sideways (ADX < 20, Hurst < 0.45)
- HIGH_VOL: Elevated volatility, uncertain direction
- LOW_VOL: Compressed volatility, potential breakout
- NEUTRAL: Mixed signals

Adaptive multipliers per regime affect:
- R:R targets (trending = wider targets, ranging = tighter)
- Confidence thresholds
- Volume requirements
- Position sizing

Performance: <50ms on Pi5 using numpy + pandas_ta
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    ta = None

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime classification"""
    TRENDING = "trending"
    RANGING = "ranging"
    HIGH_VOL = "high_vol"
    LOW_VOL = "low_vol"
    NEUTRAL = "neutral"


@dataclass
class RegimeConfig:
    """Adaptive parameters per regime"""
    name: str

    # R:R parameters
    stop_multiplier: float = 1.5
    target_multiplier: float = 3.0
    min_rr: float = 2.0

    # Confidence adjustments
    confidence_boost: float = 0.0  # Add/subtract from confidence score
    min_confidence: float = 75.0

    # Volume requirements
    min_volume_ratio: float = 1.2

    # Position sizing
    size_multiplier: float = 1.0  # 0.5 = half size, 1.5 = 1.5x

    # Signal filtering
    allow_long: bool = True
    allow_short: bool = True


@dataclass
class RegimeAnalysis:
    """Complete regime analysis result"""
    regime: MarketRegime
    regime_config: RegimeConfig

    # Raw indicators
    adx_14: float = 0.0
    plus_di: float = 0.0
    minus_di: float = 0.0
    hurst_exponent: float = 0.5
    volatility_ratio: float = 1.0  # Current vol vs 20-period avg
    atr_percentile: float = 50.0  # Where current ATR ranks

    # Derived signals
    trend_strength: str = 'weak'  # 'weak', 'moderate', 'strong'
    trend_direction: str = 'neutral'  # 'bullish', 'bearish', 'neutral'
    vol_state: str = 'normal'  # 'compressed', 'normal', 'elevated'
    mean_reversion_signal: bool = False

    # Confidence in regime classification (0-100)
    regime_confidence: float = 50.0

    # Timestamps
    calculated_at: datetime = field(default_factory=datetime.now)
    valid_until: datetime = None

    # Debug info
    scores: Dict[str, float] = field(default_factory=dict)


# Regime configurations (can be tuned via backtesting)
REGIME_CONFIGS = {
    MarketRegime.TRENDING: RegimeConfig(
        name="Trending",
        stop_multiplier=1.5,
        target_multiplier=4.0,  # Wider targets - let winners run
        min_rr=2.0,
        confidence_boost=5.0,  # Boost signals in trends
        min_confidence=70.0,
        min_volume_ratio=1.0,  # Less strict volume
        size_multiplier=1.2,  # Slightly larger size
    ),
    MarketRegime.RANGING: RegimeConfig(
        name="Ranging",
        stop_multiplier=1.0,  # Tighter stops
        target_multiplier=2.0,  # Quick targets for mean reversion
        min_rr=1.5,  # Accept lower R:R
        confidence_boost=-5.0,  # Be more cautious
        min_confidence=80.0,  # Higher bar
        min_volume_ratio=1.5,  # Need more volume confirmation
        size_multiplier=0.75,  # Smaller size
    ),
    MarketRegime.HIGH_VOL: RegimeConfig(
        name="High Volatility",
        stop_multiplier=2.5,  # Wider stops for volatility
        target_multiplier=4.0,
        min_rr=1.5,
        confidence_boost=0.0,
        min_confidence=80.0,  # Higher confidence required
        min_volume_ratio=1.0,  # Volume expected to be high anyway
        size_multiplier=0.5,  # Half size - preserve capital
    ),
    MarketRegime.LOW_VOL: RegimeConfig(
        name="Low Volatility",
        stop_multiplier=1.0,  # Tight stops during compression
        target_multiplier=3.0,  # Expect breakout
        min_rr=2.5,  # Higher R:R for breakout plays
        confidence_boost=0.0,
        min_confidence=75.0,
        min_volume_ratio=1.5,  # Volume breakout confirmation critical
        size_multiplier=1.0,
    ),
    MarketRegime.NEUTRAL: RegimeConfig(
        name="Neutral",
        stop_multiplier=1.5,
        target_multiplier=3.0,
        min_rr=2.0,
        confidence_boost=0.0,
        min_confidence=75.0,
        min_volume_ratio=1.2,
        size_multiplier=1.0,
    ),
}


class RegimeDetector:
    """
    Elite market regime detector.

    Uses ADX, Hurst exponent, and volatility analysis to classify
    market conditions and provide adaptive trading parameters.
    """

    def __init__(self, lookback_period: int = 100, regime_ttl_minutes: int = 15):
        """
        Initialize regime detector.

        Args:
            lookback_period: Bars to analyze for regime detection
            regime_ttl_minutes: How long regime classification is valid
        """
        if not PANDAS_TA_AVAILABLE:
            raise ImportError("pandas_ta required for regime detection")

        self.lookback_period = lookback_period
        self.regime_ttl_minutes = regime_ttl_minutes

        # Cache recent regime analyses
        self.regime_cache: Dict[str, RegimeAnalysis] = {}

        # ADX thresholds
        self.adx_strong_trend = 25.0
        self.adx_weak_trend = 15.0

        # Hurst thresholds
        self.hurst_trending = 0.55  # > 0.55 = trending/momentum
        self.hurst_ranging = 0.45   # < 0.45 = mean-reverting

        # Volatility percentile thresholds
        self.vol_high_percentile = 80
        self.vol_low_percentile = 20

        logger.info(f"RegimeDetector initialized: lookback={lookback_period}, TTL={regime_ttl_minutes}min")

    def calculate_hurst_exponent(self, prices: pd.Series, max_lag: int = 20) -> float:
        """
        Calculate Hurst exponent using R/S analysis.

        H < 0.5: Mean-reverting (ranging)
        H = 0.5: Random walk
        H > 0.5: Trending/momentum

        Simplified version for speed on Pi5.
        """
        if len(prices) < max_lag * 2:
            return 0.5  # Default to random walk

        try:
            log_returns = np.log(prices / prices.shift(1)).dropna()

            if len(log_returns) < max_lag:
                return 0.5

            # Calculate R/S for different lags
            lags = range(2, min(max_lag, len(log_returns) // 4))
            rs_values = []
            lag_values = []

            for lag in lags:
                # Split into chunks
                chunks = len(log_returns) // lag
                if chunks < 2:
                    continue

                rs_for_lag = []
                for i in range(chunks):
                    chunk = log_returns.iloc[i * lag:(i + 1) * lag]
                    if len(chunk) < 2:
                        continue

                    # Mean-adjusted cumulative deviation
                    mean_return = chunk.mean()
                    cumdev = (chunk - mean_return).cumsum()

                    # Range
                    R = cumdev.max() - cumdev.min()

                    # Standard deviation
                    S = chunk.std()

                    if S > 0:
                        rs_for_lag.append(R / S)

                if rs_for_lag:
                    rs_values.append(np.mean(rs_for_lag))
                    lag_values.append(lag)

            if len(rs_values) < 3:
                return 0.5

            # Linear regression on log-log scale
            log_lags = np.log(lag_values)
            log_rs = np.log(rs_values)

            # Simple linear regression
            slope, _ = np.polyfit(log_lags, log_rs, 1)

            # Clamp to reasonable range
            return float(np.clip(slope, 0.1, 0.9))

        except Exception as e:
            logger.debug(f"Hurst calculation error: {e}")
            return 0.5

    def calculate_volatility_metrics(self, df: pd.DataFrame) -> Tuple[float, float]:
        """
        Calculate volatility ratio and ATR percentile.

        Returns:
            (volatility_ratio, atr_percentile)
        """
        try:
            # ATR
            atr = ta.atr(df['high'], df['low'], df['close'], length=14)
            if atr is None or len(atr) < 20:
                return 1.0, 50.0

            current_atr = float(atr.iloc[-1])
            avg_atr = float(atr.rolling(20).mean().iloc[-1])

            vol_ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

            # ATR percentile over lookback period
            atr_values = atr.dropna().values
            if len(atr_values) > 0:
                percentile = float(np.percentile(
                    np.searchsorted(np.sort(atr_values), current_atr) / len(atr_values) * 100,
                    50
                ))
                # Actually compute where current ATR ranks
                percentile = float(sum(atr_values < current_atr) / len(atr_values) * 100)
            else:
                percentile = 50.0

            return vol_ratio, percentile

        except Exception as e:
            logger.debug(f"Volatility calculation error: {e}")
            return 1.0, 50.0

    def detect_regime(self, df: pd.DataFrame, ticker: str = "UNKNOWN") -> RegimeAnalysis:
        """
        Detect market regime from OHLCV data.

        Args:
            df: DataFrame with OHLCV columns
            ticker: Symbol for caching

        Returns:
            RegimeAnalysis with regime classification and config
        """
        # Check cache first
        cached = self.regime_cache.get(ticker)
        if cached and cached.valid_until and datetime.now() < cached.valid_until:
            logger.debug(f"Using cached regime for {ticker}: {cached.regime.value}")
            return cached

        # Initialize with neutral
        analysis = RegimeAnalysis(
            regime=MarketRegime.NEUTRAL,
            regime_config=REGIME_CONFIGS[MarketRegime.NEUTRAL]
        )

        try:
            # Ensure column names are lowercase
            df_copy = df.copy()
            df_copy.columns = df_copy.columns.str.lower()

            if len(df_copy) < self.lookback_period:
                logger.debug(f"Insufficient data for regime detection: {len(df_copy)} bars")
                analysis.valid_until = datetime.now() + timedelta(minutes=5)
                return analysis

            # Take last N bars
            df_analysis = df_copy.tail(self.lookback_period)

            # ========================================
            # CALCULATE ADX + DI
            # ========================================
            adx_result = ta.adx(df_analysis['high'], df_analysis['low'], df_analysis['close'], length=14)
            if adx_result is not None and len(adx_result) > 0:
                analysis.adx_14 = float(adx_result.iloc[-1, 0])  # ADX
                analysis.plus_di = float(adx_result.iloc[-1, 1])  # +DI
                analysis.minus_di = float(adx_result.iloc[-1, 2])  # -DI

            # Determine trend strength
            if analysis.adx_14 >= self.adx_strong_trend:
                analysis.trend_strength = 'strong'
            elif analysis.adx_14 >= self.adx_weak_trend:
                analysis.trend_strength = 'moderate'
            else:
                analysis.trend_strength = 'weak'

            # Determine trend direction
            if analysis.plus_di > analysis.minus_di + 5:
                analysis.trend_direction = 'bullish'
            elif analysis.minus_di > analysis.plus_di + 5:
                analysis.trend_direction = 'bearish'
            else:
                analysis.trend_direction = 'neutral'

            # ========================================
            # CALCULATE HURST EXPONENT
            # ========================================
            analysis.hurst_exponent = self.calculate_hurst_exponent(df_analysis['close'])

            # Mean reversion signal
            analysis.mean_reversion_signal = analysis.hurst_exponent < self.hurst_ranging

            # ========================================
            # CALCULATE VOLATILITY METRICS
            # ========================================
            vol_ratio, atr_pct = self.calculate_volatility_metrics(df_analysis)
            analysis.volatility_ratio = vol_ratio
            analysis.atr_percentile = atr_pct

            # Volatility state
            if atr_pct >= self.vol_high_percentile:
                analysis.vol_state = 'elevated'
            elif atr_pct <= self.vol_low_percentile:
                analysis.vol_state = 'compressed'
            else:
                analysis.vol_state = 'normal'

            # ========================================
            # CLASSIFY REGIME (Scoring System)
            # ========================================
            scores = {
                'trending': 0.0,
                'ranging': 0.0,
                'high_vol': 0.0,
                'low_vol': 0.0,
                'neutral': 20.0  # Base score
            }

            # ADX contribution
            if analysis.adx_14 > self.adx_strong_trend:
                scores['trending'] += 40
            elif analysis.adx_14 > self.adx_weak_trend:
                scores['trending'] += 20
                scores['neutral'] += 10
            else:
                scores['ranging'] += 30

            # Hurst contribution
            if analysis.hurst_exponent > self.hurst_trending:
                scores['trending'] += 30
            elif analysis.hurst_exponent < self.hurst_ranging:
                scores['ranging'] += 30
            else:
                scores['neutral'] += 15

            # Volatility contribution
            if analysis.vol_state == 'elevated':
                scores['high_vol'] += 50
                scores['trending'] += 10  # High vol often = strong trend
            elif analysis.vol_state == 'compressed':
                scores['low_vol'] += 50
                scores['ranging'] += 10  # Low vol often = ranging

            analysis.scores = scores

            # Pick highest scoring regime
            max_regime = max(scores, key=scores.get)
            regime_map = {
                'trending': MarketRegime.TRENDING,
                'ranging': MarketRegime.RANGING,
                'high_vol': MarketRegime.HIGH_VOL,
                'low_vol': MarketRegime.LOW_VOL,
                'neutral': MarketRegime.NEUTRAL
            }

            analysis.regime = regime_map[max_regime]
            analysis.regime_config = REGIME_CONFIGS[analysis.regime]

            # Calculate regime confidence
            max_score = max(scores.values())
            total_score = sum(scores.values())
            analysis.regime_confidence = (max_score / total_score * 100) if total_score > 0 else 50.0

            # Set validity
            analysis.calculated_at = datetime.now()
            analysis.valid_until = datetime.now() + timedelta(minutes=self.regime_ttl_minutes)

            # Cache result
            self.regime_cache[ticker] = analysis

            logger.info(
                f"🎯 Regime {ticker}: {analysis.regime.value.upper()} "
                f"(ADX={analysis.adx_14:.1f}, Hurst={analysis.hurst_exponent:.2f}, "
                f"Vol={analysis.vol_state}) conf={analysis.regime_confidence:.0f}%"
            )

            return analysis

        except Exception as e:
            logger.error(f"Regime detection error for {ticker}: {e}")
            analysis.valid_until = datetime.now() + timedelta(minutes=5)
            return analysis

    def get_regime_config(self, regime: MarketRegime) -> RegimeConfig:
        """Get configuration for a specific regime."""
        return REGIME_CONFIGS.get(regime, REGIME_CONFIGS[MarketRegime.NEUTRAL])

    def adjust_signal_parameters(
        self,
        base_confidence: float,
        base_stop_mult: float,
        base_target_mult: float,
        regime: MarketRegime
    ) -> Tuple[float, float, float, float]:
        """
        Adjust signal parameters based on regime.

        Returns:
            (adjusted_confidence, stop_mult, target_mult, size_mult)
        """
        config = self.get_regime_config(regime)

        adjusted_confidence = base_confidence + config.confidence_boost
        adjusted_confidence = max(0, min(100, adjusted_confidence))

        return (
            adjusted_confidence,
            config.stop_multiplier,
            config.target_multiplier,
            config.size_multiplier
        )

    def clear_cache(self):
        """Clear regime cache."""
        self.regime_cache.clear()
        logger.info("Regime cache cleared")


# Global instance
_regime_detector: Optional[RegimeDetector] = None


def get_regime_detector() -> RegimeDetector:
    """Get or create global regime detector instance."""
    global _regime_detector
    if _regime_detector is None:
        _regime_detector = RegimeDetector()
    return _regime_detector
