"""
VWAP Service - Volume Weighted Average Price for SmartFlow 2026

Features:
- Session-based VWAP calculation (resets daily for futures)
- VWAP bias scoring for trend/mean-reversion detection
- Confluence boost integration for ensemble scoring
- ProjectX realtime data integration

Config Flags:
- VWAP_DISTANCE_THRESHOLD_PCT: 0.5% (max distance for confluence)
- VWAP_CONFLUENCE_BOOST: 0.12 (prob boost when near VWAP)
- VWAP_TRAILING_ENABLED: True (use VWAP for trailing reference)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class VWAPConfig:
    """VWAP service configuration"""
    # Distance thresholds
    distance_threshold_pct: float = 0.5        # Max distance for confluence (0.5%)
    tight_distance_pct: float = 0.3            # Tight distance for extra boost (0.3%)
    very_tight_distance_pct: float = 0.15      # Very tight for mean-reversion (0.15%)

    # Confluence boosts
    confluence_boost: float = 0.12             # Base probability boost
    tight_confluence_boost: float = 0.15       # Boost when < 0.3% distance
    mean_reversion_boost: float = 0.18         # Boost for mean-reversion regime

    # Bias thresholds
    bullish_bias_threshold: float = 0.3        # Price > VWAP by 0.3%+ = bullish
    bearish_bias_threshold: float = -0.3       # Price < VWAP by 0.3%+ = bearish
    strong_bullish_threshold: float = 0.6      # Strong bullish signal
    strong_bearish_threshold: float = -0.6     # Strong bearish signal

    # Session timing (futures - CME)
    session_start_hour: int = 17               # 5pm CT previous day
    session_start_minute: int = 0
    session_end_hour: int = 16                 # 4pm CT
    session_end_minute: int = 0

    # Gating requirements
    min_vwap_bias_for_long: float = 0.4        # Min bias for long in trending up
    min_vwap_bias_for_short: float = -0.4      # Max bias for short in trending down

    # Feature weights
    vwap_weight_in_ensemble: float = 0.10      # 10% weight in ensemble

    # Trailing stop integration
    trailing_enabled: bool = True
    trailing_vwap_offset_pct: float = 0.1      # Trail 0.1% below VWAP for longs


class VWAPBiasLevel(str, Enum):
    """VWAP bias classification"""
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class VWAPResult:
    """VWAP calculation result"""
    vwap: float                                # Current VWAP value
    vwap_upper_1std: float = 0.0               # VWAP + 1 std dev
    vwap_lower_1std: float = 0.0               # VWAP - 1 std dev
    vwap_upper_2std: float = 0.0               # VWAP + 2 std dev
    vwap_lower_2std: float = 0.0               # VWAP - 2 std dev
    session_volume: float = 0.0                # Total session volume
    session_start: Optional[datetime] = None   # Session start time
    bars_in_session: int = 0                   # Number of bars in session
    typical_price: float = 0.0                 # Current typical price (H+L+C)/3


@dataclass
class VWAPBias:
    """VWAP bias analysis result"""
    bias_level: VWAPBiasLevel                  # Categorical bias
    bias_score: float                          # Numeric score (-1 to +1)
    distance_pct: float                        # Distance from VWAP as %
    distance_stddev: float = 0.0               # Distance in standard deviations
    is_above_vwap: bool = True                 # Price above VWAP
    confluence_eligible: bool = False          # Within distance threshold
    confluence_boost: float = 0.0              # Probability boost to apply
    vwap_value: float = 0.0                    # Current VWAP
    current_price: float = 0.0                 # Current price
    regime: str = ""                           # Current regime
    reason: str = ""                           # Human-readable explanation


@dataclass
class VWAPConfluence:
    """VWAP confluence with other signals"""
    passes_filter: bool = False                # Passes VWAP gating
    reason: str = ""                           # Why passed/failed
    bias: Optional[VWAPBias] = None            # Full bias analysis
    probability_boost: float = 0.0             # Ensemble prob boost
    trailing_reference: float = 0.0            # VWAP-based trailing stop
    entry_quality: str = ""                    # "excellent", "good", "marginal"


# ============================================================
# VWAP SERVICE
# ============================================================

class VWAPService:
    """
    VWAP calculation and bias scoring service.

    Features:
    - Session-based VWAP with daily reset
    - Standard deviation bands
    - Bias scoring for trend/mean-reversion
    - Confluence integration for ensemble
    """

    def __init__(self, config: Optional[VWAPConfig] = None):
        self.config = config or VWAPConfig()
        self._cache: Dict[str, VWAPResult] = {}
        self._cache_timestamps: Dict[str, datetime] = {}

    def calculate_vwap(
        self,
        df: pd.DataFrame,
        session_reset: bool = True,
        inplace: bool = False
    ) -> pd.DataFrame:
        """
        Calculate VWAP with optional session reset.

        Args:
            df: DataFrame with columns: high, low, close, volume, timestamp/datetime
            session_reset: If True, reset VWAP each trading session
            inplace: If True, modify df in place

        Returns:
            DataFrame with VWAP, VWAP_Upper_1Std, VWAP_Lower_1Std columns added
        """
        if df.empty:
            logger.warning("Empty DataFrame passed to calculate_vwap")
            return df

        result_df = df if inplace else df.copy()

        # Ensure required columns exist
        required_cols = ['high', 'low', 'close', 'volume']
        for col in required_cols:
            col_lower = col.lower()
            if col_lower not in result_df.columns and col not in result_df.columns:
                logger.error(f"Missing required column: {col}")
                return result_df

        # Normalize column names to lowercase
        result_df.columns = result_df.columns.str.lower()

        # Calculate typical price (H+L+C)/3
        result_df['typical_price'] = (
            result_df['high'] + result_df['low'] + result_df['close']
        ) / 3

        # Calculate price * volume
        result_df['pv'] = result_df['typical_price'] * result_df['volume']

        if session_reset:
            # Get session boundaries
            result_df['session_id'] = self._get_session_ids(result_df)

            # Calculate cumulative sums within each session
            result_df['cum_pv'] = result_df.groupby('session_id')['pv'].cumsum()
            result_df['cum_vol'] = result_df.groupby('session_id')['volume'].cumsum()
        else:
            # Simple cumulative VWAP
            result_df['cum_pv'] = result_df['pv'].cumsum()
            result_df['cum_vol'] = result_df['volume'].cumsum()

        # Calculate VWAP
        result_df['VWAP'] = result_df['cum_pv'] / result_df['cum_vol'].replace(0, np.nan)

        # Calculate standard deviation bands
        self._calculate_vwap_bands(result_df, session_reset)

        # Cleanup intermediate columns
        cleanup_cols = ['pv', 'cum_pv', 'cum_vol']
        if session_reset:
            cleanup_cols.append('session_id')
        result_df.drop(columns=[c for c in cleanup_cols if c in result_df.columns],
                       inplace=True, errors='ignore')

        return result_df

    def _get_session_ids(self, df: pd.DataFrame) -> pd.Series:
        """
        Assign session IDs based on futures trading session boundaries.

        CME Futures: Session starts 5pm CT, ends 4pm CT next day
        """
        # Determine timestamp column
        time_col = None
        for col in ['timestamp', 'datetime', 'time', 'date']:
            if col in df.columns:
                time_col = col
                break

        if time_col is None:
            # Try index
            if isinstance(df.index, pd.DatetimeIndex):
                timestamps = df.index
            else:
                # Fallback: single session
                return pd.Series(0, index=df.index)
        else:
            timestamps = pd.to_datetime(df[time_col])

        session_ids = []
        current_session = 0
        session_start = None

        for ts in timestamps:
            # Check if this timestamp starts a new session (after 5pm)
            ts_time = ts.time()
            session_start_time = time(self.config.session_start_hour,
                                      self.config.session_start_minute)
            session_end_time = time(self.config.session_end_hour,
                                    self.config.session_end_minute)

            # New session starts at 5pm
            if ts_time >= session_start_time:
                if session_start is None or ts.date() > session_start.date():
                    current_session += 1
                    session_start = ts
            elif ts_time < session_end_time:
                # Same session continues until 4pm next day
                pass
            else:
                # Between 4pm and 5pm - brief maintenance window
                pass

            session_ids.append(current_session)

        return pd.Series(session_ids, index=df.index)

    def _calculate_vwap_bands(
        self,
        df: pd.DataFrame,
        session_reset: bool
    ) -> None:
        """
        Calculate VWAP standard deviation bands.

        Uses rolling squared deviation from VWAP, then applies band multipliers.
        """
        # Calculate squared deviation from VWAP
        df['vwap_dev_sq'] = (df['typical_price'] - df['VWAP']) ** 2

        if session_reset and 'session_id' in df.columns:
            # Rolling variance within session
            df['vwap_var'] = df.groupby('session_id')['vwap_dev_sq'].transform(
                lambda x: x.expanding().mean()
            )
        else:
            df['vwap_var'] = df['vwap_dev_sq'].expanding().mean()

        # Standard deviation
        df['vwap_std'] = np.sqrt(df['vwap_var'])

        # Calculate bands
        df['VWAP_Upper_1Std'] = df['VWAP'] + df['vwap_std']
        df['VWAP_Lower_1Std'] = df['VWAP'] - df['vwap_std']
        df['VWAP_Upper_2Std'] = df['VWAP'] + (2 * df['vwap_std'])
        df['VWAP_Lower_2Std'] = df['VWAP'] - (2 * df['vwap_std'])

        # Cleanup
        df.drop(columns=['vwap_dev_sq', 'vwap_var', 'vwap_std'],
                inplace=True, errors='ignore')

    def get_current_vwap(
        self,
        df: pd.DataFrame,
        session_reset: bool = True
    ) -> VWAPResult:
        """
        Get current VWAP value and bands from latest bar.

        Args:
            df: Price data DataFrame
            session_reset: Reset VWAP per session

        Returns:
            VWAPResult with current values
        """
        if df.empty:
            return VWAPResult(vwap=0.0)

        # Calculate VWAP
        vwap_df = self.calculate_vwap(df, session_reset=session_reset)

        if vwap_df.empty or 'VWAP' not in vwap_df.columns:
            return VWAPResult(vwap=0.0)

        # Get latest values
        latest = vwap_df.iloc[-1]

        # Calculate session volume
        if session_reset:
            # Volume in current session
            session_volume = vwap_df['volume'].sum()  # Simplified
        else:
            session_volume = vwap_df['volume'].sum()

        return VWAPResult(
            vwap=float(latest.get('VWAP', 0.0)),
            vwap_upper_1std=float(latest.get('VWAP_Upper_1Std', 0.0)),
            vwap_lower_1std=float(latest.get('VWAP_Lower_1Std', 0.0)),
            vwap_upper_2std=float(latest.get('VWAP_Upper_2Std', 0.0)),
            vwap_lower_2std=float(latest.get('VWAP_Lower_2Std', 0.0)),
            session_volume=float(session_volume),
            bars_in_session=len(vwap_df),
            typical_price=float(latest.get('typical_price', 0.0))
        )

    def get_vwap_bias(
        self,
        current_price: float,
        vwap: float,
        regime: str = "",
        distance_threshold: Optional[float] = None,
        vwap_std: float = 0.0
    ) -> VWAPBias:
        """
        Calculate VWAP bias score and confluence eligibility.

        Args:
            current_price: Current price
            vwap: Current VWAP value
            regime: Current regime ('trending_up', 'trending_down', 'mean_reverting', etc.)
            distance_threshold: Override default distance threshold
            vwap_std: VWAP standard deviation (for stddev-based distance)

        Returns:
            VWAPBias with score, level, and confluence info
        """
        if vwap <= 0:
            return VWAPBias(
                bias_level=VWAPBiasLevel.NEUTRAL,
                bias_score=0.0,
                distance_pct=0.0,
                reason="VWAP not available"
            )

        threshold = distance_threshold or self.config.distance_threshold_pct

        # Calculate distance from VWAP
        distance_pct = ((current_price - vwap) / vwap) * 100
        is_above = current_price > vwap

        # Calculate distance in standard deviations
        distance_stddev = 0.0
        if vwap_std > 0:
            distance_stddev = (current_price - vwap) / vwap_std

        # Determine bias level
        if distance_pct >= self.config.strong_bullish_threshold:
            bias_level = VWAPBiasLevel.STRONG_BULLISH
            bias_score = min(1.0, 0.7 + (distance_pct - 0.6) * 0.5)
        elif distance_pct >= self.config.bullish_bias_threshold:
            bias_level = VWAPBiasLevel.BULLISH
            bias_score = 0.4 + (distance_pct / self.config.strong_bullish_threshold) * 0.3
        elif distance_pct <= self.config.strong_bearish_threshold:
            bias_level = VWAPBiasLevel.STRONG_BEARISH
            bias_score = max(-1.0, -0.7 + (distance_pct + 0.6) * 0.5)
        elif distance_pct <= self.config.bearish_bias_threshold:
            bias_level = VWAPBiasLevel.BEARISH
            bias_score = -0.4 + (distance_pct / abs(self.config.strong_bearish_threshold)) * 0.3
        else:
            bias_level = VWAPBiasLevel.NEUTRAL
            # Scale linearly from -0.4 to 0.4 within neutral zone
            bias_score = distance_pct / self.config.bullish_bias_threshold * 0.4

        # Determine confluence eligibility
        abs_distance = abs(distance_pct)
        confluence_eligible = abs_distance <= threshold

        # Calculate probability boost
        confluence_boost = 0.0
        if confluence_eligible:
            if abs_distance <= self.config.very_tight_distance_pct:
                # Very tight - mean reversion potential
                if regime in ['mean_reverting', 'vol_contraction', 'choppy']:
                    confluence_boost = self.config.mean_reversion_boost
                else:
                    confluence_boost = self.config.tight_confluence_boost
            elif abs_distance <= self.config.tight_distance_pct:
                confluence_boost = self.config.tight_confluence_boost
            else:
                confluence_boost = self.config.confluence_boost

        # Build reason
        direction = "above" if is_above else "below"
        reason = f"Price {direction} VWAP by {abs_distance:.3f}%"
        if confluence_eligible:
            reason += f" | Confluence: +{confluence_boost:.1%} boost"
        if regime:
            reason += f" | Regime: {regime}"

        return VWAPBias(
            bias_level=bias_level,
            bias_score=bias_score,
            distance_pct=distance_pct,
            distance_stddev=distance_stddev,
            is_above_vwap=is_above,
            confluence_eligible=confluence_eligible,
            confluence_boost=confluence_boost,
            vwap_value=vwap,
            current_price=current_price,
            regime=regime,
            reason=reason
        )

    def check_vwap_confluence(
        self,
        current_price: float,
        vwap_result: VWAPResult,
        direction: str,
        regime: str,
        flow_conviction: str = "",
        imbalance: float = 0.0
    ) -> VWAPConfluence:
        """
        Check VWAP confluence for trade entry.

        Implements regime-aware VWAP gating:
        - Trending Up + Long: Require price near/above VWAP (bias >= 0.4)
        - Trending Down + Short: Require price near/below VWAP (bias <= -0.4)
        - Mean Reverting: Prefer price very close to VWAP for mean-reversion

        Args:
            current_price: Current price
            vwap_result: VWAP calculation result
            direction: Trade direction ('long' or 'short')
            regime: Current regime
            flow_conviction: Flow conviction level (for extra filtering)
            imbalance: Order book imbalance

        Returns:
            VWAPConfluence with pass/fail and details
        """
        if vwap_result.vwap <= 0:
            return VWAPConfluence(
                passes_filter=True,  # Pass if no VWAP data
                reason="No VWAP data available",
                entry_quality="unknown"
            )

        # Get bias analysis
        vwap_std = 0.0
        if vwap_result.vwap_upper_1std > 0:
            vwap_std = vwap_result.vwap_upper_1std - vwap_result.vwap

        bias = self.get_vwap_bias(
            current_price=current_price,
            vwap=vwap_result.vwap,
            regime=regime,
            vwap_std=vwap_std
        )

        # Check regime-specific requirements
        passes_filter = True
        reason = ""
        entry_quality = "good"

        if direction.lower() == 'long':
            if regime == 'trending_up':
                # For longs in uptrend: require bias >= 0.4 (price at/above VWAP)
                if bias.bias_score < self.config.min_vwap_bias_for_long:
                    passes_filter = False
                    reason = (f"Long in uptrend rejected: VWAP bias {bias.bias_score:.2f} "
                              f"< {self.config.min_vwap_bias_for_long}")
                    entry_quality = "rejected"
                elif bias.bias_level == VWAPBiasLevel.STRONG_BULLISH:
                    entry_quality = "excellent"
                    reason = f"Strong bullish VWAP bias: {bias.bias_score:.2f}"
                else:
                    reason = f"VWAP bias acceptable: {bias.bias_score:.2f}"

            elif regime in ['mean_reverting', 'choppy', 'vol_contraction']:
                # For mean-reversion: prefer price very close to VWAP
                if abs(bias.distance_pct) <= self.config.very_tight_distance_pct:
                    entry_quality = "excellent"
                    reason = f"Tight VWAP setup: {bias.distance_pct:.3f}% distance"
                elif abs(bias.distance_pct) <= self.config.tight_distance_pct:
                    entry_quality = "good"
                    reason = f"Near VWAP: {bias.distance_pct:.3f}% distance"
                else:
                    entry_quality = "marginal"
                    reason = f"Extended from VWAP: {bias.distance_pct:.3f}% distance"

        elif direction.lower() == 'short':
            if regime == 'trending_down':
                # For shorts in downtrend: require bias <= -0.4 (price at/below VWAP)
                if bias.bias_score > self.config.min_vwap_bias_for_short:
                    passes_filter = False
                    reason = (f"Short in downtrend rejected: VWAP bias {bias.bias_score:.2f} "
                              f"> {self.config.min_vwap_bias_for_short}")
                    entry_quality = "rejected"
                elif bias.bias_level == VWAPBiasLevel.STRONG_BEARISH:
                    entry_quality = "excellent"
                    reason = f"Strong bearish VWAP bias: {bias.bias_score:.2f}"
                else:
                    reason = f"VWAP bias acceptable: {bias.bias_score:.2f}"

            elif regime in ['mean_reverting', 'choppy', 'vol_contraction']:
                # For mean-reversion: prefer price very close to VWAP
                if abs(bias.distance_pct) <= self.config.very_tight_distance_pct:
                    entry_quality = "excellent"
                    reason = f"Tight VWAP setup: {bias.distance_pct:.3f}% distance"
                elif abs(bias.distance_pct) <= self.config.tight_distance_pct:
                    entry_quality = "good"
                    reason = f"Near VWAP: {bias.distance_pct:.3f}% distance"
                else:
                    entry_quality = "marginal"
                    reason = f"Extended from VWAP: {bias.distance_pct:.3f}% distance"

        # Calculate probability boost
        prob_boost = 0.0
        if passes_filter and bias.confluence_eligible:
            prob_boost = bias.confluence_boost

        # Calculate trailing reference (for longs: VWAP - offset)
        trailing_ref = 0.0
        if self.config.trailing_enabled:
            offset_pct = self.config.trailing_vwap_offset_pct / 100
            if direction.lower() == 'long':
                trailing_ref = vwap_result.vwap * (1 - offset_pct)
            else:
                trailing_ref = vwap_result.vwap * (1 + offset_pct)

        return VWAPConfluence(
            passes_filter=passes_filter,
            reason=reason,
            bias=bias,
            probability_boost=prob_boost,
            trailing_reference=trailing_ref,
            entry_quality=entry_quality
        )

    def get_vwap_for_symbol(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        cache_minutes: int = 1
    ) -> VWAPResult:
        """
        Get VWAP for a symbol with caching.

        Args:
            symbol: Trading symbol
            price_data: Price data DataFrame
            cache_minutes: Cache expiry in minutes

        Returns:
            VWAPResult with current VWAP values
        """
        cache_key = symbol

        # Check cache
        if cache_key in self._cache:
            cached_time = self._cache_timestamps.get(cache_key)
            if cached_time and (datetime.now() - cached_time).seconds < (cache_minutes * 60):
                return self._cache[cache_key]

        # Calculate fresh VWAP
        result = self.get_current_vwap(price_data, session_reset=True)

        # Update cache
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = datetime.now()

        return result

    def clear_cache(self) -> None:
        """Clear VWAP cache"""
        self._cache.clear()
        self._cache_timestamps.clear()


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def calculate_vwap(df: pd.DataFrame, session_reset: bool = True) -> pd.DataFrame:
    """
    Convenience function to calculate VWAP.

    Args:
        df: DataFrame with high, low, close, volume columns
        session_reset: Reset VWAP each trading session

    Returns:
        DataFrame with VWAP column added
    """
    service = VWAPService()
    return service.calculate_vwap(df, session_reset=session_reset)


def get_vwap_bias(
    current_price: float,
    vwap: float,
    regime: str = "",
    distance_threshold: float = 0.5
) -> VWAPBias:
    """
    Convenience function to get VWAP bias.

    Args:
        current_price: Current price
        vwap: Current VWAP value
        regime: Current regime
        distance_threshold: Max distance for confluence (%)

    Returns:
        VWAPBias with score and confluence info
    """
    service = VWAPService()
    return service.get_vwap_bias(
        current_price=current_price,
        vwap=vwap,
        regime=regime,
        distance_threshold=distance_threshold
    )


# ============================================================
# INTEGRATION HELPERS
# ============================================================

def get_vwap_features_for_ensemble(
    current_price: float,
    vwap_result: VWAPResult,
    regime: str = ""
) -> Dict[str, float]:
    """
    Get VWAP features formatted for ensemble scorer.

    Returns dict with:
    - vwap_distance_pct: Distance from VWAP as percentage
    - vwap_bias: Bias score (-1 to +1)
    - vwap_confluence: 1.0 if confluence eligible, 0.0 otherwise
    - vwap_boost: Probability boost amount
    """
    if vwap_result.vwap <= 0:
        return {
            'vwap_distance_pct': 0.0,
            'vwap_bias': 0.0,
            'vwap_confluence': 0.0,
            'vwap_boost': 0.0
        }

    service = VWAPService()
    vwap_std = 0.0
    if vwap_result.vwap_upper_1std > 0:
        vwap_std = vwap_result.vwap_upper_1std - vwap_result.vwap

    bias = service.get_vwap_bias(
        current_price=current_price,
        vwap=vwap_result.vwap,
        regime=regime,
        vwap_std=vwap_std
    )

    return {
        'vwap_distance_pct': bias.distance_pct,
        'vwap_bias': bias.bias_score,
        'vwap_confluence': 1.0 if bias.confluence_eligible else 0.0,
        'vwap_boost': bias.confluence_boost
    }


# ============================================================
# PROJECTX INTEGRATION (for realtime futures data)
# ============================================================

async def get_vwap_from_projectx_bars(
    symbol: str,
    projectx_client: any,
    session_bars_limit: int = 500
) -> VWAPResult:
    """
    Calculate VWAP from ProjectX historical bars.

    Args:
        symbol: Contract symbol (e.g., 'MESM5')
        projectx_client: ProjectX API client
        session_bars_limit: Max bars to fetch

    Returns:
        VWAPResult with current session VWAP
    """
    try:
        # Fetch bars from ProjectX
        bars = await projectx_client.get_historical_bars(
            symbol=symbol,
            resolution='1',  # 1-minute bars
            limit=session_bars_limit
        )

        if not bars:
            logger.warning(f"No bars returned from ProjectX for {symbol}")
            return VWAPResult(vwap=0.0)

        # Convert to DataFrame
        df = pd.DataFrame([{
            'timestamp': bar.timestamp,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume
        } for bar in bars])

        # Calculate VWAP
        service = VWAPService()
        return service.get_current_vwap(df, session_reset=True)

    except Exception as e:
        logger.error(f"Error getting VWAP from ProjectX: {e}")
        return VWAPResult(vwap=0.0)
