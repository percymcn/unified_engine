"""
Elite Regime Detector v2 - 2026 Best Practices
===============================================

Advanced regime classification using:
- GJR-GARCH / EGARCH for asymmetric volatility modeling
- Rolling Hurst exponent with adaptive window
- Inter-asset regime propagation (correlation-based)
- 6-class regime states with probability vectors

Regimes (6 classes):
- TRENDING_UP: Strong bullish momentum
- TRENDING_DOWN: Strong bearish momentum
- MEAN_REVERTING: Oscillating, fade extremes
- VOL_EXPANSION: Volatility breakout, uncertainty
- VOL_CONTRACTION: Low vol squeeze, breakout pending
- CHAOTIC: Transition state, unclear direction

Output: Probability vector → feeds ensemble weights dynamically

Performance: ~100-200ms on Pi5 using arch/statsmodels (acceptable for 15-30min updates)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import arch library for GARCH models
try:
    from arch import arch_model
    from arch.univariate import GARCH, EGARCH, ZeroMean, ConstantMean
    ARCH_AVAILABLE = True
except ImportError:
    ARCH_AVAILABLE = False
    logger.warning("arch library not available - install with: pip install arch")

# Try to import statsmodels for additional statistical tests
try:
    from scipy import stats
    from scipy.signal import find_peaks
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class RegimeState(Enum):
    """6-class regime states for 2026 best practices"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    MEAN_REVERTING = "mean_reverting"
    VOL_EXPANSION = "vol_expansion"
    VOL_CONTRACTION = "vol_contraction"
    CHAOTIC = "chaotic"


@dataclass
class RegimeConfigV2:
    """Adaptive parameters per regime state"""
    name: str

    # R:R parameters
    stop_multiplier: float = 1.5
    target_multiplier: float = 3.0
    min_rr: float = 2.0

    # Confidence adjustments
    confidence_boost: float = 0.0
    min_confidence: float = 75.0

    # Volume requirements
    min_volume_ratio: float = 1.2

    # Position sizing (Kelly adjustment)
    kelly_fraction: float = 0.25  # Base Kelly fraction
    size_multiplier: float = 1.0

    # Signal filtering
    allow_long: bool = True
    allow_short: bool = True
    prefer_mean_reversion: bool = False
    prefer_momentum: bool = False


@dataclass
class RegimeAnalysisV2:
    """Complete regime analysis with probability vector"""
    ticker: str
    timestamp: datetime

    # Primary regime (highest probability)
    primary_regime: RegimeState
    regime_config: RegimeConfigV2

    # Probability vector (sums to 1.0)
    regime_probabilities: Dict[str, float] = field(default_factory=dict)

    # GARCH volatility forecast
    garch_vol_forecast: float = 0.0  # Next-period volatility forecast
    garch_vol_current: float = 0.0   # Current conditional volatility
    vol_asymmetry: float = 0.0       # Asymmetry parameter (leverage effect)

    # Hurst analysis
    hurst_exponent: float = 0.5
    hurst_confidence: float = 0.0
    hurst_window_used: int = 100

    # Trend indicators
    adx_14: float = 0.0
    plus_di: float = 0.0
    minus_di: float = 0.0
    trend_direction: str = 'neutral'  # 'bullish', 'bearish', 'neutral'
    trend_strength: float = 0.0       # 0-100

    # Volatility state
    vol_percentile: float = 50.0
    vol_zscore: float = 0.0
    is_vol_expanding: bool = False
    is_vol_contracting: bool = False

    # Cross-asset correlation (for regime propagation)
    correlation_matrix: Dict[str, float] = field(default_factory=dict)
    lead_lag_signal: str = 'none'  # 'leading', 'lagging', 'none'

    # Overall confidence in classification
    classification_confidence: float = 50.0

    # Validity
    valid_until: Optional[datetime] = None

    # Debug/audit
    feature_scores: Dict[str, float] = field(default_factory=dict)

    # ========================================
    # NEW: Enhanced features integration
    # ========================================

    # Microstructure analysis
    order_imbalance: float = 0.0          # -1 to +1
    vpin_toxicity: float = 0.0            # 0-1, >0.7 = toxic
    microstructure_bias: str = 'neutral'  # 'bullish', 'bearish', 'neutral'

    # Key levels confluence
    levels_confluence: float = 0.0        # 0-100
    nearest_level: str = ''
    level_distance_pct: float = 0.0

    # News sentiment
    news_sentiment: float = 0.0           # -1 to +1
    news_headline_count: int = 0

    # Crypto funding (for crypto only)
    funding_rate: float = 0.0
    funding_bias: str = 'neutral'         # 'long_crowded', 'short_crowded', 'neutral'

    # VWAP analysis (NEW)
    vwap_distance_pct: float = 0.0        # Distance from VWAP as %
    vwap_bias: float = 0.0                # -1 to +1 bias score
    vwap_confluence: float = 0.0          # 0 or 1 (within threshold)
    vwap_entry_quality: str = 'unknown'   # 'excellent', 'good', 'marginal', 'rejected'

    # Enhanced bias calculation (combining all factors)
    enhanced_bias: str = 'neutral'        # Final bias after all enhancements
    enhanced_confidence: float = 0.0      # 0-100


# Regime configurations (tuned for each state)
REGIME_CONFIGS_V2 = {
    RegimeState.TRENDING_UP: RegimeConfigV2(
        name="Trending Up",
        stop_multiplier=1.5,
        target_multiplier=4.5,  # Let winners run in strong trends
        min_rr=2.0,
        confidence_boost=10.0,  # Boost signals in clear trends
        min_confidence=65.0,
        min_volume_ratio=1.0,
        kelly_fraction=0.30,    # Higher Kelly in trends
        size_multiplier=1.3,
        allow_long=True,
        allow_short=False,      # Don't short uptrends
        prefer_momentum=True,
    ),
    RegimeState.TRENDING_DOWN: RegimeConfigV2(
        name="Trending Down",
        stop_multiplier=1.5,
        target_multiplier=4.5,
        min_rr=2.0,
        confidence_boost=10.0,
        min_confidence=65.0,
        min_volume_ratio=1.0,
        kelly_fraction=0.30,
        size_multiplier=1.3,
        allow_long=False,       # Don't buy downtrends
        allow_short=True,
        prefer_momentum=True,
    ),
    RegimeState.MEAN_REVERTING: RegimeConfigV2(
        name="Mean Reverting",
        stop_multiplier=1.0,    # Tighter stops for quick reversals
        target_multiplier=2.0,  # Quick targets
        min_rr=1.5,
        confidence_boost=-5.0,  # Be more cautious
        min_confidence=80.0,    # Higher bar
        min_volume_ratio=1.5,   # Need volume confirmation
        kelly_fraction=0.20,
        size_multiplier=0.75,
        allow_long=True,
        allow_short=True,
        prefer_mean_reversion=True,
    ),
    RegimeState.VOL_EXPANSION: RegimeConfigV2(
        name="Volatility Expansion",
        stop_multiplier=2.5,    # Wide stops for volatility
        target_multiplier=4.0,
        min_rr=1.5,
        confidence_boost=-10.0, # Very cautious
        min_confidence=85.0,
        min_volume_ratio=1.0,
        kelly_fraction=0.15,    # Reduce size significantly
        size_multiplier=0.5,
        allow_long=True,
        allow_short=True,
    ),
    RegimeState.VOL_CONTRACTION: RegimeConfigV2(
        name="Volatility Contraction",
        stop_multiplier=1.0,    # Tight stops during compression
        target_multiplier=4.0,  # Expect breakout
        min_rr=3.0,             # Higher R:R for breakout plays
        confidence_boost=5.0,
        min_confidence=70.0,
        min_volume_ratio=2.0,   # Volume breakout critical
        kelly_fraction=0.25,
        size_multiplier=1.0,
        allow_long=True,
        allow_short=True,
    ),
    RegimeState.CHAOTIC: RegimeConfigV2(
        name="Chaotic/Transition",
        stop_multiplier=2.0,
        target_multiplier=2.5,
        min_rr=1.5,
        confidence_boost=-20.0, # Heavy penalty
        min_confidence=90.0,    # Very high bar
        min_volume_ratio=2.0,
        kelly_fraction=0.10,    # Minimal size
        size_multiplier=0.25,
        allow_long=True,
        allow_short=True,
    ),
}


class RegimeDetectorV2:
    """
    Elite regime detector with 2026 best practices.

    Uses:
    - GJR-GARCH for asymmetric volatility (leverage effect)
    - Adaptive Hurst exponent with confidence bands
    - 6-class regime states with probability vectors
    - Cross-asset correlation for regime propagation
    """

    def __init__(
        self,
        lookback_period: int = 252,  # ~1 year of daily data, or 252 5-min bars
        regime_ttl_minutes: int = 15,
        garch_model: str = 'gjr-garch'  # 'garch', 'gjr-garch', 'egarch'
    ):
        self.lookback_period = lookback_period
        self.regime_ttl_minutes = regime_ttl_minutes
        self.garch_model_type = garch_model

        # Cache
        self.regime_cache: Dict[str, RegimeAnalysisV2] = {}

        # Cross-asset correlation tracking
        self.returns_history: Dict[str, List[float]] = {}
        self.max_returns_history = 500

        # Adaptive Hurst windows
        self.hurst_windows = [20, 50, 100, 200]  # Multiple windows for robustness

        # Regime transition tracking
        self.regime_history: Dict[str, List[Tuple[datetime, RegimeState]]] = {}

        logger.info(f"RegimeDetectorV2 initialized: GARCH={garch_model}, "
                   f"lookback={lookback_period}, TTL={regime_ttl_minutes}min, "
                   f"ARCH_AVAILABLE={ARCH_AVAILABLE}")

    def calculate_garch_volatility(
        self,
        returns: np.ndarray,
        model_type: str = 'gjr-garch'
    ) -> Tuple[float, float, float]:
        """
        Fit GARCH model and get volatility forecast.

        GJR-GARCH captures asymmetric volatility (leverage effect):
        - Bad news (negative returns) increases volatility more than good news

        Returns:
            (current_vol, forecast_vol, asymmetry_param)
        """
        if not ARCH_AVAILABLE:
            # Fallback to simple rolling volatility
            current_vol = np.std(returns[-20:]) if len(returns) >= 20 else np.std(returns)
            return current_vol, current_vol, 0.0

        if len(returns) < 50:
            current_vol = np.std(returns)
            return current_vol, current_vol, 0.0

        try:
            # Scale returns to percentage for numerical stability
            returns_pct = returns * 100

            if model_type == 'gjr-garch':
                # GJR-GARCH(1,1) - captures leverage effect
                model = arch_model(
                    returns_pct,
                    vol='Garch',
                    p=1, o=1, q=1,  # o=1 for GJR asymmetry
                    mean='Constant',
                    rescale=True
                )
            elif model_type == 'egarch':
                # EGARCH - exponential GARCH, naturally handles asymmetry
                model = arch_model(
                    returns_pct,
                    vol='EGARCH',
                    p=1, q=1,
                    mean='Constant',
                    rescale=True
                )
            else:
                # Standard GARCH(1,1)
                model = arch_model(
                    returns_pct,
                    vol='Garch',
                    p=1, q=1,
                    mean='Constant',
                    rescale=True
                )

            # Fit with limited iterations for speed
            result = model.fit(disp='off', options={'maxiter': 100})

            # Current conditional volatility (last observation)
            conditional_vol = result.conditional_volatility
            current_vol = conditional_vol.iloc[-1] / 100  # Scale back

            # Forecast next period
            forecast = result.forecast(horizon=1)
            forecast_vol = np.sqrt(forecast.variance.iloc[-1, 0]) / 100

            # Asymmetry parameter (gamma for GJR, leverage for EGARCH)
            params = result.params
            if model_type == 'gjr-garch' and 'gamma[1]' in params:
                asymmetry = float(params['gamma[1]'])
            elif model_type == 'egarch' and 'gamma[1]' in params:
                asymmetry = float(params['gamma[1]'])
            else:
                asymmetry = 0.0

            return float(current_vol), float(forecast_vol), float(asymmetry)

        except Exception as e:
            logger.debug(f"GARCH fitting failed: {e}")
            current_vol = np.std(returns[-20:]) if len(returns) >= 20 else np.std(returns)
            return current_vol, current_vol, 0.0

    def calculate_adaptive_hurst(
        self,
        prices: np.ndarray,
        windows: Optional[List[int]] = None
    ) -> Tuple[float, float, int]:
        """
        Calculate Hurst exponent with adaptive window selection.

        Uses multiple windows and selects most confident estimate.

        Returns:
            (hurst_exponent, confidence, window_used)
        """
        if windows is None:
            windows = self.hurst_windows

        if len(prices) < max(windows):
            # Not enough data - use what we have
            windows = [w for w in windows if w <= len(prices) // 2]
            if not windows:
                return 0.5, 0.0, 0

        hurst_estimates = []

        for window in windows:
            try:
                # Use the last 'window' prices
                sample = prices[-window:]
                h = self._calculate_hurst_rs(sample)

                # Confidence based on sample size and R² of fit
                confidence = min(1.0, window / 200)  # More data = more confidence

                hurst_estimates.append((h, confidence, window))

            except Exception as e:
                logger.debug(f"Hurst calculation failed for window {window}: {e}")
                continue

        if not hurst_estimates:
            return 0.5, 0.0, 0

        # Weight estimates by confidence
        total_weight = sum(conf for _, conf, _ in hurst_estimates)
        if total_weight == 0:
            return 0.5, 0.0, 0

        weighted_hurst = sum(h * conf for h, conf, _ in hurst_estimates) / total_weight
        avg_confidence = total_weight / len(hurst_estimates)

        # Return the window that gave closest estimate to weighted average
        best_window = min(hurst_estimates, key=lambda x: abs(x[0] - weighted_hurst))[2]

        return float(weighted_hurst), float(avg_confidence), best_window

    def _calculate_hurst_rs(self, prices: np.ndarray, max_lag: int = None) -> float:
        """
        Calculate Hurst exponent using R/S analysis.

        H < 0.5: Mean-reverting
        H = 0.5: Random walk
        H > 0.5: Trending/persistent
        """
        if max_lag is None:
            max_lag = len(prices) // 4

        if len(prices) < 20:
            return 0.5

        log_returns = np.diff(np.log(prices))

        if len(log_returns) < max_lag:
            max_lag = len(log_returns) // 2

        lags = range(10, min(max_lag, len(log_returns) // 2))
        if len(list(lags)) < 3:
            return 0.5

        rs_values = []
        lag_values = []

        for lag in lags:
            chunks = len(log_returns) // lag
            if chunks < 2:
                continue

            rs_for_lag = []
            for i in range(chunks):
                chunk = log_returns[i * lag:(i + 1) * lag]
                if len(chunk) < 2:
                    continue

                mean_return = np.mean(chunk)
                cumdev = np.cumsum(chunk - mean_return)
                R = np.max(cumdev) - np.min(cumdev)
                S = np.std(chunk, ddof=1)

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

        try:
            slope, _ = np.polyfit(log_lags, log_rs, 1)
            return float(np.clip(slope, 0.1, 0.9))
        except:
            return 0.5

    def calculate_regime_probabilities(
        self,
        adx: float,
        plus_di: float,
        minus_di: float,
        hurst: float,
        vol_zscore: float,
        vol_expanding: bool,
        vol_contracting: bool,
        garch_asymmetry: float
    ) -> Dict[str, float]:
        """
        Calculate probability distribution over regime states.

        Uses fuzzy logic / soft classification to get probability vector.
        """
        probs = {state.value: 0.0 for state in RegimeState}

        # ========================================
        # TRENDING_UP
        # ========================================
        # High ADX + bullish DI + persistent Hurst
        trending_up_score = 0.0
        if adx > 25 and plus_di > minus_di + 5:
            trending_up_score += 0.4
        if adx > 35 and plus_di > minus_di + 10:
            trending_up_score += 0.2
        if hurst > 0.55:
            trending_up_score += 0.3
        if hurst > 0.65:
            trending_up_score += 0.1
        probs[RegimeState.TRENDING_UP.value] = min(1.0, trending_up_score)

        # ========================================
        # TRENDING_DOWN
        # ========================================
        trending_down_score = 0.0
        if adx > 25 and minus_di > plus_di + 5:
            trending_down_score += 0.4
        if adx > 35 and minus_di > plus_di + 10:
            trending_down_score += 0.2
        if hurst > 0.55:
            trending_down_score += 0.3
        if hurst > 0.65:
            trending_down_score += 0.1
        probs[RegimeState.TRENDING_DOWN.value] = min(1.0, trending_down_score)

        # ========================================
        # MEAN_REVERTING
        # ========================================
        mean_rev_score = 0.0
        if hurst < 0.45:
            mean_rev_score += 0.5
        if hurst < 0.35:
            mean_rev_score += 0.2
        if adx < 20:
            mean_rev_score += 0.3
        probs[RegimeState.MEAN_REVERTING.value] = min(1.0, mean_rev_score)

        # ========================================
        # VOL_EXPANSION
        # ========================================
        vol_exp_score = 0.0
        if vol_expanding:
            vol_exp_score += 0.4
        if vol_zscore > 1.5:
            vol_exp_score += 0.3
        if vol_zscore > 2.0:
            vol_exp_score += 0.2
        if abs(garch_asymmetry) > 0.1:  # Significant asymmetry during expansion
            vol_exp_score += 0.1
        probs[RegimeState.VOL_EXPANSION.value] = min(1.0, vol_exp_score)

        # ========================================
        # VOL_CONTRACTION
        # ========================================
        vol_con_score = 0.0
        if vol_contracting:
            vol_con_score += 0.4
        if vol_zscore < -1.0:
            vol_con_score += 0.3
        if vol_zscore < -1.5:
            vol_con_score += 0.2
        if adx < 15:  # Low trend = consolidation
            vol_con_score += 0.1
        probs[RegimeState.VOL_CONTRACTION.value] = min(1.0, vol_con_score)

        # ========================================
        # CHAOTIC
        # ========================================
        # High uncertainty: conflicting signals, unstable Hurst, vol spikes
        chaotic_score = 0.0
        if 0.45 <= hurst <= 0.55:  # Near random walk
            chaotic_score += 0.2
        if adx < 20 and abs(plus_di - minus_di) < 5:  # No clear direction
            chaotic_score += 0.2
        if abs(vol_zscore) > 2.5:  # Extreme volatility
            chaotic_score += 0.2

        # If no other regime is strong, increase chaotic
        max_other = max([v for k, v in probs.items() if k != RegimeState.CHAOTIC.value])
        if max_other < 0.4:
            chaotic_score += 0.3

        probs[RegimeState.CHAOTIC.value] = min(1.0, chaotic_score)

        # ========================================
        # NORMALIZE TO PROBABILITY DISTRIBUTION
        # ========================================
        total = sum(probs.values())
        if total > 0:
            probs = {k: v / total for k, v in probs.items()}
        else:
            # Uniform distribution if all zero
            probs = {k: 1.0 / len(probs) for k in probs}

        return probs

    def detect_regime(
        self,
        df: pd.DataFrame,
        ticker: str,
        correlation_tickers: Optional[Dict[str, pd.DataFrame]] = None
    ) -> RegimeAnalysisV2:
        """
        Detect market regime with probability vector output.

        Args:
            df: DataFrame with OHLCV columns
            ticker: Symbol being analyzed
            correlation_tickers: Optional dict of {ticker: df} for cross-asset analysis

        Returns:
            RegimeAnalysisV2 with probability vector and config
        """
        # Check cache
        cached = self.regime_cache.get(ticker)
        if cached and cached.valid_until and datetime.now() < cached.valid_until:
            return cached

        now = datetime.now()

        # Initialize with CHAOTIC (uncertain)
        analysis = RegimeAnalysisV2(
            ticker=ticker,
            timestamp=now,
            primary_regime=RegimeState.CHAOTIC,
            regime_config=REGIME_CONFIGS_V2[RegimeState.CHAOTIC]
        )

        try:
            # Ensure lowercase columns
            df_copy = df.copy()
            df_copy.columns = df_copy.columns.str.lower()

            if len(df_copy) < 50:
                analysis.valid_until = now + timedelta(minutes=5)
                return analysis

            # Calculate returns
            close_prices = df_copy['close'].values
            returns = np.diff(np.log(close_prices))

            # ========================================
            # GARCH VOLATILITY ANALYSIS
            # ========================================
            current_vol, forecast_vol, asymmetry = self.calculate_garch_volatility(
                returns, self.garch_model_type
            )
            analysis.garch_vol_current = current_vol
            analysis.garch_vol_forecast = forecast_vol
            analysis.vol_asymmetry = asymmetry

            # Volatility z-score (how unusual is current vol?)
            vol_history = pd.Series(returns).rolling(20).std().dropna().values
            if len(vol_history) > 20:
                vol_mean = np.mean(vol_history)
                vol_std = np.std(vol_history)
                analysis.vol_zscore = (current_vol - vol_mean) / vol_std if vol_std > 0 else 0
                analysis.vol_percentile = float(np.percentile(
                    np.searchsorted(np.sort(vol_history), current_vol) / len(vol_history) * 100, 50
                ))

            # Volatility expansion/contraction
            if len(vol_history) >= 10:
                recent_vol = np.mean(vol_history[-5:])
                older_vol = np.mean(vol_history[-10:-5])
                vol_change = (recent_vol - older_vol) / older_vol if older_vol > 0 else 0
                analysis.is_vol_expanding = vol_change > 0.2
                analysis.is_vol_contracting = vol_change < -0.2

            # ========================================
            # ADAPTIVE HURST EXPONENT
            # ========================================
            hurst, hurst_conf, hurst_window = self.calculate_adaptive_hurst(close_prices)
            analysis.hurst_exponent = hurst
            analysis.hurst_confidence = hurst_conf
            analysis.hurst_window_used = hurst_window

            # ========================================
            # ADX + DIRECTIONAL INDICATORS
            # ========================================
            # Calculate ADX manually (pandas_ta might not be available)
            try:
                import pandas_ta as ta
                adx_result = ta.adx(df_copy['high'], df_copy['low'], df_copy['close'], length=14)
                if adx_result is not None and len(adx_result) > 0:
                    analysis.adx_14 = float(adx_result.iloc[-1, 0])
                    analysis.plus_di = float(adx_result.iloc[-1, 1])
                    analysis.minus_di = float(adx_result.iloc[-1, 2])
            except:
                # Fallback: estimate trend strength from price action
                sma_20 = np.mean(close_prices[-20:])
                sma_50 = np.mean(close_prices[-50:]) if len(close_prices) >= 50 else sma_20

                if close_prices[-1] > sma_20 > sma_50:
                    analysis.adx_14 = 30.0
                    analysis.plus_di = 30.0
                    analysis.minus_di = 15.0
                elif close_prices[-1] < sma_20 < sma_50:
                    analysis.adx_14 = 30.0
                    analysis.plus_di = 15.0
                    analysis.minus_di = 30.0
                else:
                    analysis.adx_14 = 15.0
                    analysis.plus_di = 20.0
                    analysis.minus_di = 20.0

            # Trend direction and strength
            if analysis.plus_di > analysis.minus_di + 5:
                analysis.trend_direction = 'bullish'
                analysis.trend_strength = min(100, analysis.adx_14 * 2)
            elif analysis.minus_di > analysis.plus_di + 5:
                analysis.trend_direction = 'bearish'
                analysis.trend_strength = min(100, analysis.adx_14 * 2)
            else:
                analysis.trend_direction = 'neutral'
                analysis.trend_strength = 0

            # ========================================
            # CROSS-ASSET CORRELATION (if provided)
            # ========================================
            if correlation_tickers:
                for other_ticker, other_df in correlation_tickers.items():
                    try:
                        other_returns = np.diff(np.log(other_df['close'].values[-100:]))
                        our_returns = returns[-len(other_returns):]
                        if len(our_returns) == len(other_returns) and len(our_returns) > 20:
                            corr = np.corrcoef(our_returns, other_returns)[0, 1]
                            analysis.correlation_matrix[other_ticker] = float(corr)
                    except:
                        continue

            # ========================================
            # CALCULATE REGIME PROBABILITIES
            # ========================================
            analysis.regime_probabilities = self.calculate_regime_probabilities(
                adx=analysis.adx_14,
                plus_di=analysis.plus_di,
                minus_di=analysis.minus_di,
                hurst=analysis.hurst_exponent,
                vol_zscore=analysis.vol_zscore,
                vol_expanding=analysis.is_vol_expanding,
                vol_contracting=analysis.is_vol_contracting,
                garch_asymmetry=analysis.vol_asymmetry
            )

            # Primary regime = highest probability
            primary_regime_name = max(analysis.regime_probabilities, key=analysis.regime_probabilities.get)
            analysis.primary_regime = RegimeState(primary_regime_name)
            analysis.regime_config = REGIME_CONFIGS_V2[analysis.primary_regime]

            # Classification confidence = probability of primary regime
            analysis.classification_confidence = analysis.regime_probabilities[primary_regime_name] * 100

            # Store feature scores for debugging
            analysis.feature_scores = {
                'adx': analysis.adx_14,
                'hurst': analysis.hurst_exponent,
                'vol_zscore': analysis.vol_zscore,
                'garch_asymmetry': analysis.vol_asymmetry,
                'trend_strength': analysis.trend_strength
            }

            # Set validity
            analysis.valid_until = now + timedelta(minutes=self.regime_ttl_minutes)

            # Cache result
            self.regime_cache[ticker] = analysis

            # Log
            logger.info(
                f"🎯 RegimeV2 {ticker}: {analysis.primary_regime.value.upper()} "
                f"(prob={analysis.classification_confidence:.0f}%) "
                f"ADX={analysis.adx_14:.1f} Hurst={analysis.hurst_exponent:.2f} "
                f"Vol-Z={analysis.vol_zscore:.1f} GARCH-asym={analysis.vol_asymmetry:.3f}"
            )

            return analysis

        except Exception as e:
            logger.error(f"RegimeV2 detection failed for {ticker}: {e}")
            analysis.valid_until = now + timedelta(minutes=5)
            return analysis

    def get_dynamic_ensemble_weights(
        self,
        regime_probs: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Get dynamic ensemble weights based on regime probabilities.

        Returns weights for: deterministic, quick, flow, ai
        """
        # Base weights
        weights = {
            'deterministic': 0.35,
            'quick': 0.25,
            'flow': 0.25,
            'ai': 0.15
        }

        # Trending regimes: boost deterministic (MTF alignment)
        trending_prob = (
            regime_probs.get(RegimeState.TRENDING_UP.value, 0) +
            regime_probs.get(RegimeState.TRENDING_DOWN.value, 0)
        )
        if trending_prob > 0.5:
            weights['deterministic'] = 0.45
            weights['quick'] = 0.30
            weights['flow'] = 0.15
            weights['ai'] = 0.10

        # Mean-reverting: boost quick mode
        mean_rev_prob = regime_probs.get(RegimeState.MEAN_REVERTING.value, 0)
        if mean_rev_prob > 0.5:
            weights['deterministic'] = 0.25
            weights['quick'] = 0.40
            weights['flow'] = 0.20
            weights['ai'] = 0.15

        # Vol expansion: be very cautious, boost deterministic
        vol_exp_prob = regime_probs.get(RegimeState.VOL_EXPANSION.value, 0)
        if vol_exp_prob > 0.5:
            weights['deterministic'] = 0.50
            weights['quick'] = 0.15
            weights['flow'] = 0.20
            weights['ai'] = 0.15

        # Vol contraction: flow breakouts
        vol_con_prob = regime_probs.get(RegimeState.VOL_CONTRACTION.value, 0)
        if vol_con_prob > 0.5:
            weights['deterministic'] = 0.30
            weights['quick'] = 0.20
            weights['flow'] = 0.35
            weights['ai'] = 0.15

        # Chaotic: reduce all, increase ai (maybe it sees something)
        chaotic_prob = regime_probs.get(RegimeState.CHAOTIC.value, 0)
        if chaotic_prob > 0.5:
            weights['deterministic'] = 0.30
            weights['quick'] = 0.20
            weights['flow'] = 0.20
            weights['ai'] = 0.30

        return weights

    def get_regime_config(self, regime: RegimeState) -> RegimeConfigV2:
        """Get configuration for a specific regime."""
        return REGIME_CONFIGS_V2.get(regime, REGIME_CONFIGS_V2[RegimeState.CHAOTIC])

    def clear_cache(self):
        """Clear regime cache."""
        self.regime_cache.clear()

    def calculate_enhanced_bias(
        self,
        analysis: RegimeAnalysisV2,
        order_imbalance: float = 0.0,
        vpin: float = 0.0,
        levels_confluence: float = 0.0,
        nearest_level: str = '',
        level_distance_pct: float = 0.0,
        news_sentiment: float = 0.0,
        funding_rate: float = 0.0,
        vwap_distance_pct: float = 0.0,
        vwap_bias: float = 0.0,
        vwap_confluence: float = 0.0,
        vwap_entry_quality: str = 'unknown'
    ) -> Tuple[str, float]:
        """
        Calculate enhanced bias by combining regime analysis with:
        - Microstructure (order imbalance, VPIN)
        - Levels confluence
        - News sentiment
        - Crypto funding rate
        - VWAP confluence (NEW)

        Returns:
            (enhanced_bias, enhanced_confidence)
        """
        # Store raw values in analysis
        analysis.order_imbalance = order_imbalance
        analysis.vpin_toxicity = vpin
        analysis.levels_confluence = levels_confluence
        analysis.nearest_level = nearest_level
        analysis.level_distance_pct = level_distance_pct
        analysis.news_sentiment = news_sentiment
        analysis.funding_rate = funding_rate
        analysis.vwap_distance_pct = vwap_distance_pct
        analysis.vwap_bias = vwap_bias
        analysis.vwap_confluence = vwap_confluence
        analysis.vwap_entry_quality = vwap_entry_quality

        # Start with regime trend direction
        base_bias = analysis.trend_direction
        bias_score = 0.0  # -100 to +100

        # ========================================
        # 1. REGIME CONTRIBUTION (40 points max)
        # ========================================
        if analysis.primary_regime == RegimeState.TRENDING_UP:
            bias_score += 40.0
        elif analysis.primary_regime == RegimeState.TRENDING_DOWN:
            bias_score -= 40.0
        elif analysis.primary_regime == RegimeState.MEAN_REVERTING:
            # Mean reverting: bias opposite to recent move
            if analysis.trend_direction == 'bullish':
                bias_score -= 20.0  # Fade the move
            elif analysis.trend_direction == 'bearish':
                bias_score += 20.0

        # ========================================
        # 2. MICROSTRUCTURE CONTRIBUTION (25 points max)
        # ========================================
        # Order imbalance: positive = bullish, negative = bearish
        imbalance_contribution = order_imbalance * 20.0
        bias_score += imbalance_contribution

        # VPIN toxicity: high VPIN reduces confidence, doesn't change direction
        if vpin > 0.7:
            # High toxicity - reduce confidence
            analysis.microstructure_bias = 'toxic'
        elif order_imbalance > 0.3:
            analysis.microstructure_bias = 'bullish'
            bias_score += 5.0
        elif order_imbalance < -0.3:
            analysis.microstructure_bias = 'bearish'
            bias_score -= 5.0

        # ========================================
        # 3. LEVELS CONFLUENCE CONTRIBUTION (20 points max)
        # ========================================
        if levels_confluence >= 70:
            # Strong confluence - boost bias in current direction
            if bias_score > 0:
                bias_score += 15.0
            elif bias_score < 0:
                bias_score -= 15.0
            else:
                # If at a level but no clear bias, slight bearish (resistance)
                # or bullish (support) based on level type
                if 'PDH' in nearest_level or 'upper' in nearest_level.lower():
                    bias_score -= 10.0  # Resistance
                elif 'PDL' in nearest_level or 'lower' in nearest_level.lower():
                    bias_score += 10.0  # Support
        elif levels_confluence >= 50:
            # Moderate confluence - small boost
            if bias_score > 0:
                bias_score += 5.0
            elif bias_score < 0:
                bias_score -= 5.0

        # ========================================
        # 4. NEWS SENTIMENT CONTRIBUTION (10 points max)
        # ========================================
        news_contribution = news_sentiment * 10.0
        bias_score += news_contribution

        # ========================================
        # 5. CRYPTO FUNDING CONTRIBUTION (5 points max, crypto only)
        # ========================================
        if funding_rate != 0:
            # Positive funding = crowded long = bearish bias (fade)
            # Negative funding = crowded short = bullish bias (fade)
            if funding_rate > 0.03:
                analysis.funding_bias = 'long_crowded'
                bias_score -= 5.0  # Fade crowded long
            elif funding_rate < -0.01:
                analysis.funding_bias = 'short_crowded'
                bias_score += 5.0  # Fade crowded short

        # ========================================
        # 6. VWAP CONTRIBUTION (15 points max, NEW)
        # ========================================
        # VWAP bias contributes to overall direction
        vwap_contribution = vwap_bias * 10.0  # -10 to +10 based on VWAP bias
        bias_score += vwap_contribution

        # Extra boost for excellent VWAP setups
        if vwap_confluence > 0:
            if vwap_entry_quality == 'excellent':
                # Excellent VWAP setup - add 5 points in direction
                if vwap_bias > 0:
                    bias_score += 5.0
                elif vwap_bias < 0:
                    bias_score -= 5.0
            elif vwap_entry_quality == 'good':
                # Good setup - add 2.5 points
                if vwap_bias > 0:
                    bias_score += 2.5
                elif vwap_bias < 0:
                    bias_score -= 2.5

        # Mean-reversion regime + tight VWAP = stronger signal
        if analysis.primary_regime == RegimeState.MEAN_REVERTING:
            if abs(vwap_distance_pct) < 0.3 and vwap_confluence > 0:
                # Very tight to VWAP in mean-reverting regime
                # Fade the recent move more aggressively
                if analysis.trend_direction == 'bullish' and vwap_bias < 0:
                    bias_score -= 5.0  # Extra bearish (fade up move)
                elif analysis.trend_direction == 'bearish' and vwap_bias > 0:
                    bias_score += 5.0  # Extra bullish (fade down move)

        # ========================================
        # DETERMINE FINAL BIAS
        # ========================================
        if bias_score >= 25:
            enhanced_bias = 'bullish'
        elif bias_score <= -25:
            enhanced_bias = 'bearish'
        else:
            enhanced_bias = 'neutral'

        # Calculate confidence (0-100)
        enhanced_confidence = min(100.0, abs(bias_score))

        # Apply VPIN penalty to confidence
        if vpin > 0.7:
            enhanced_confidence *= 0.7  # 30% penalty for toxic flow

        analysis.enhanced_bias = enhanced_bias
        analysis.enhanced_confidence = enhanced_confidence

        logger.debug(
            f"Enhanced bias {analysis.ticker}: {enhanced_bias} "
            f"(score={bias_score:.0f}, conf={enhanced_confidence:.0f}%) "
            f"[imbal={order_imbalance:.2f}, levels={levels_confluence:.0f}, "
            f"news={news_sentiment:.2f}, funding={funding_rate:.4f}, "
            f"vwap_bias={vwap_bias:.2f}, vwap_dist={vwap_distance_pct:.3f}%]"
        )

        return enhanced_bias, enhanced_confidence


# Global instance
_regime_detector_v2: Optional[RegimeDetectorV2] = None


def get_regime_detector_v2() -> RegimeDetectorV2:
    """Get or create global regime detector v2 instance."""
    global _regime_detector_v2
    if _regime_detector_v2 is None:
        _regime_detector_v2 = RegimeDetectorV2()
    return _regime_detector_v2
