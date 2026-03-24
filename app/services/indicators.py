"""
Deterministic Technical Indicators Module
==========================================

100% deterministic indicator calculations using pandas_ta.
NO AI/LLM involvement - pure mathematical computations.

Indicators per timeframe:
- EMA9, EMA21 (trend)
- RSI14 (momentum)
- MACD(12,26,9) (momentum/trend)
- ATR14 (volatility/stops)

Entry Rules (configurable):
- Long: close > EMA9 > EMA21, RSI > 50
- Short: close < EMA9 < EMA21, RSI < 50
- Require >= 4/5 timeframes aligned
- Higher TFs (1h, 4h) must agree for high confidence
- R:R >= 1:2 using ATR-based stops
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    ta = None

logger = logging.getLogger(__name__)


@dataclass
class TimeframeAnalysis:
    """Analysis results for a single timeframe"""
    timeframe: str
    close: float
    ema9: float
    ema21: float
    rsi14: float
    macd_value: float
    macd_signal: float
    macd_histogram: float
    atr14: float

    # Bollinger Bands (20-period, 2 std dev)
    bb_upper: float = 0.0           # Upper band
    bb_middle: float = 0.0          # Middle band (SMA20)
    bb_lower: float = 0.0           # Lower band
    bb_width: float = 0.0           # Band width (volatility measure)
    bb_percent: float = 0.5         # %B - where price is within bands (0=lower, 1=upper)
    bb_squeeze: bool = False        # True if BB width < 20-period avg (volatility squeeze)

    # Volume analysis
    volume_current: float = 0.0      # Current bar volume
    volume_avg_20: float = 0.0       # 20-period average volume
    volume_ratio: float = 1.0        # Current / Avg (relative volume)
    volume_delta: float = 0.0        # Buy volume - Sell volume (approximated)
    volume_trend: str = 'neutral'    # 'increasing', 'decreasing', 'neutral'

    # Derived signals
    ema_bullish: bool = False      # EMA9 > EMA21
    price_above_ema9: bool = False
    price_above_ema21: bool = False
    rsi_bullish: bool = False      # RSI > 50
    macd_bullish: bool = False     # MACD histogram > 0
    volume_bullish: bool = False   # Volume confirms direction (high vol on up bars)
    bb_bullish: bool = False       # Price near lower band + other bullish signals

    # Overall bias for this TF
    bias: str = 'neutral'  # 'bullish', 'bearish', 'neutral'
    bias_strength: float = 0.0  # 0-100

    # Market regime (for adaptive R:R)
    market_regime: str = 'neutral'  # 'trending', 'ranging', 'volatile', 'neutral'

    bars_analyzed: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    data_freshness: str = 'fresh'   # 'fresh', 'stale', 'mock' for alerts

    def __post_init__(self):
        """Calculate derived signals from raw indicators"""
        self.ema_bullish = self.ema9 > self.ema21
        self.price_above_ema9 = self.close > self.ema9
        self.price_above_ema21 = self.close > self.ema21
        self.rsi_bullish = self.rsi14 > 50
        self.macd_bullish = self.macd_histogram > 0

        # Bollinger Band signals
        # Bullish: price near lower band (oversold) or breaking above middle with momentum
        # Bearish: price near upper band (overbought) or breaking below middle
        if self.bb_lower > 0 and self.bb_upper > 0:
            # %B < 0.2 = near lower band (potential bounce)
            # %B > 0.8 = near upper band (potential reversal)
            if self.bb_percent < 0.2 and self.rsi14 < 40:
                self.bb_bullish = True  # Oversold at lower band
            elif self.bb_percent > 0.5 and self.close > self.bb_middle and self.ema_bullish:
                self.bb_bullish = True  # Breaking up with momentum
            elif self.bb_percent > 0.8 and self.rsi14 > 60:
                self.bb_bullish = False  # Overbought at upper band
            else:
                self.bb_bullish = self.close > self.bb_middle  # Default to position vs middle

        # Market regime detection (for adaptive R:R)
        # Trending: EMAs diverging, ADX high (implied by strong MACD)
        # Ranging: Price bouncing between BB bands, EMAs converging
        # Volatile: Wide BB bands (squeeze = low volatility, wide = high)
        ema_diff_pct = abs(self.ema9 - self.ema21) / self.ema21 * 100 if self.ema21 > 0 else 0

        if self.bb_squeeze:
            self.market_regime = 'ranging'  # Low volatility, price consolidating
        elif self.bb_width > 0.04:  # Wide bands = 4%+ of price
            self.market_regime = 'volatile'
        elif ema_diff_pct > 0.5 and abs(self.macd_histogram) > 0.01:
            self.market_regime = 'trending'
        else:
            self.market_regime = 'neutral'

        # Volume confirmation: high relative volume (>1.2x avg) confirms trend
        # Bullish if: volume spike + price up OR volume declining + price down (selling exhaustion)
        if self.volume_ratio > 1.2:
            # High volume - confirms if price direction matches
            if self.price_above_ema9 and self.ema_bullish:
                self.volume_bullish = True  # Buying pressure
            elif not self.price_above_ema9 and not self.ema_bullish:
                self.volume_bullish = False  # Selling pressure
        elif self.volume_ratio < 0.8:
            # Low volume - potential exhaustion
            if not self.ema_bullish:
                self.volume_bullish = True  # Selling exhaustion = bullish
            else:
                self.volume_bullish = False  # Buying exhaustion = bearish
        else:
            # Normal volume - use delta
            self.volume_bullish = self.volume_delta > 0

        # Calculate bias (now includes 7 signals: +BB)
        bullish_signals = sum([
            self.ema_bullish,
            self.price_above_ema9,
            self.price_above_ema21,
            self.rsi_bullish,
            self.macd_bullish,
            self.volume_bullish,
            self.bb_bullish  # NEW: Bollinger Bands confirmation
        ])

        # Adjusted thresholds for 7 signals
        if bullish_signals >= 5:
            self.bias = 'bullish'
            self.bias_strength = (bullish_signals / 7) * 100
        elif bullish_signals <= 2:
            self.bias = 'bearish'
            self.bias_strength = ((7 - bullish_signals) / 7) * 100
        else:
            self.bias = 'neutral'
            self.bias_strength = 50.0


@dataclass
class MultiTimeframeSignal:
    """Aggregated multi-timeframe signal"""
    ticker: str
    timestamp: datetime

    # Individual TF analyses
    tf_5m: Optional[TimeframeAnalysis] = None
    tf_15m: Optional[TimeframeAnalysis] = None
    tf_30m: Optional[TimeframeAnalysis] = None
    tf_1h: Optional[TimeframeAnalysis] = None
    tf_4h: Optional[TimeframeAnalysis] = None

    # Aggregated results
    overall_bias: str = 'neutral'
    aligned_bullish: int = 0
    aligned_bearish: int = 0
    confidence_score: float = 0.0

    # Volume analysis (aggregated across TFs)
    volume_confirms: bool = False      # Volume aligns with direction
    volume_ratio_avg: float = 1.0      # Average relative volume across TFs
    volume_trend_aligned: int = 0      # How many TFs have volume confirming

    # Bollinger Bands aggregation
    bb_squeeze_count: int = 0          # How many TFs show squeeze
    bb_bullish_count: int = 0          # How many TFs show BB bullish

    # Market regime (derived from multiple TFs)
    market_regime: str = 'neutral'     # 'trending', 'ranging', 'volatile', 'neutral'

    # Risk parameters (from lowest TF with valid ATR)
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_reward_ratio: float = 0.0
    risk_reward_after_slippage: float = 0.0  # R:R after applying slippage buffer
    atr_for_stops: float = 0.0

    # Adaptive R:R values used (based on market regime)
    adaptive_stop_mult: float = 1.5
    adaptive_target_mult: float = 3.0

    # Signal decision
    should_trade: bool = False
    action: str = 'none'  # 'buy', 'sell', 'none'
    rejection_reason: str = ''

    # Signal decay/TTL
    signal_generated_at: datetime = field(default_factory=datetime.now)
    signal_expires_at: Optional[datetime] = None  # When signal becomes invalid
    is_expired: bool = False

    # Latency tracking
    processing_time_ms: float = 0.0  # Time to generate signal

    # Data quality
    data_freshness: str = 'fresh'      # 'fresh', 'stale', 'mock' - for alerts

    # Config used
    min_aligned_tfs: int = 4
    min_confidence: float = 75.0
    min_rr: float = 2.0

    # Access to individual TF results dict (for UI)
    tf_results: Optional[Dict[str, 'TimeframeAnalysis']] = None

    # ========================================
    # NEW: Enhanced features integration
    # ========================================

    # Levels confluence (PDH/PDL/Fib)
    levels_confluence_score: float = 0.0      # 0-100 confluence score
    nearest_level: str = ''                   # Name of nearest level
    nearest_level_distance_pct: float = 0.0   # Distance to nearest level
    levels_nearby_count: int = 0              # Count of levels within 0.5%

    # Microstructure
    order_imbalance: float = 0.0              # -1 to +1
    vpin_toxicity: float = 0.0                # 0-1

    # News sentiment
    news_sentiment_score: float = 0.0         # -1 to +1
    news_boost: float = 0.0                   # Probability boost

    # Crypto funding (for crypto only)
    funding_rate: float = 0.0                 # Current funding rate
    funding_bias: str = 'neutral'             # 'long_crowded', 'short_crowded', 'neutral'

    # Regime-adjusted targets (NEW)
    regime_adjusted_target: float = 0.0       # Target adjusted for regime
    regime_adjusted_stop: float = 0.0         # Stop adjusted for regime
    regime_min_rr: float = 0.0               # Minimum R:R for this regime

    # Trailing stop info (NEW)
    trailing_enabled: bool = False
    trailing_breakeven_price: float = 0.0
    trailing_partial_target: float = 0.0

    @property
    def close(self) -> float:
        """Compatibility alias for callers expecting a price-like signal.close value."""
        return self.entry_price


@dataclass
class IndicatorConfig:
    """Configurable parameters for indicator-based signals"""
    # EMA periods
    ema_fast: int = 9
    ema_slow: int = 21

    # RSI
    rsi_period: int = 14
    rsi_bullish_threshold: float = 50.0
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0

    # MACD
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    # Bollinger Bands
    bb_period: int = 20
    bb_std_dev: float = 2.0

    # ATR for stops
    atr_period: int = 14
    atr_stop_multiplier: float = 1.5  # Stop at entry ± 1.5x ATR
    atr_target_multiplier: float = 3.0  # Target at entry ± 3x ATR (for 2:1 R:R)

    # Percentage-based stops (OPTIMAL: PF 1.41, Sharpe 2.02, MaxDD 4.68%)
    use_pct_stops: bool = True  # Use % instead of ATR for stops
    pct_stop_loss: float = 0.2   # 0.2% stop loss
    pct_take_profit: float = 0.6 # 0.6% take profit (1:3 R:R)

    # Regime-specific PCT targets (NEW)
    uptrend_pct_target: float = 0.8    # 0.8% target in uptrend (1:4 R:R from 0.2% risk)
    uptrend_pct_target_max: float = 1.0  # Max 1.0% target (1:5 R:R)
    downtrend_pct_target: float = 0.6  # Standard 0.6% in downtrend (1:3 R:R)

    # Slippage buffer (reduces effective R:R by this percentage)
    slippage_buffer_pct: float = 2.0  # 2% slippage buffer

    # Levels confluence integration (NEW)
    use_levels_confluence: bool = True
    levels_confluence_weight: float = 0.15  # Weight in bias calculation
    min_levels_confluence: float = 55.0     # Minimum to pass filter

    # Microstructure integration (NEW)
    use_microstructure: bool = True
    microstructure_weight: float = 0.10
    min_imbalance_for_boost: float = 0.3

    # News sentiment integration (NEW)
    use_news_sentiment: bool = True
    news_sentiment_weight: float = 0.05

    # Crypto funding integration (NEW)
    use_crypto_funding: bool = True
    funding_weight: float = 0.08

    # Adaptive R:R based on market regime
    adaptive_rr_enabled: bool = True
    rr_by_regime: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        'trending': {'stop_mult': 1.5, 'target_mult': 4.0, 'min_rr': 2.5},   # Strong trends = wider targets
        'ranging': {'stop_mult': 1.0, 'target_mult': 2.0, 'min_rr': 1.5},    # Mean reversion = tighter
        'volatile': {'stop_mult': 2.0, 'target_mult': 3.0, 'min_rr': 1.5},   # Volatility = wider stops
        'neutral': {'stop_mult': 1.5, 'target_mult': 3.0, 'min_rr': 2.0},    # Default
    })

    # Alignment requirements
    min_aligned_timeframes: int = 4  # Out of 5 TFs
    require_higher_tf_agreement: bool = True  # 1h and 4h must agree

    # Signal thresholds
    min_confidence_score: float = 75.0
    min_risk_reward: float = 2.0

    # Signal decay (TTL)
    signal_ttl_minutes: int = 10  # Signals expire after 10 minutes

    # Timeframe weights (higher = more important)
    tf_weights: Dict[str, float] = field(default_factory=lambda: {
        '5m': 1.0,
        '15m': 1.2,
        '30m': 1.5,
        '1h': 2.0,
        '4h': 2.5
    })


class DeterministicIndicators:
    """
    100% deterministic technical indicator engine.

    No AI, no hallucinations - just math on OHLCV data.
    Uses pandas_ta for efficient vectorized calculations.
    """

    def __init__(self, config: Optional[IndicatorConfig] = None):
        self.config = config or IndicatorConfig()

        if not PANDAS_TA_AVAILABLE:
            logger.error("pandas_ta not installed! Run: pip install pandas-ta")
            raise ImportError("pandas_ta required for deterministic indicators")

        logger.info(f"DeterministicIndicators initialized: EMA({self.config.ema_fast}/{self.config.ema_slow}), "
                   f"RSI({self.config.rsi_period}), MACD({self.config.macd_fast},{self.config.macd_slow},{self.config.macd_signal})")

    def calculate_indicators(self, df: pd.DataFrame, timeframe: str) -> Optional[TimeframeAnalysis]:
        """
        Calculate all indicators for a single timeframe.

        Args:
            df: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
                Must be sorted chronologically (oldest first)
            timeframe: String identifier like '5m', '15m', '1h'

        Returns:
            TimeframeAnalysis with all indicator values and bias
        """
        if df is None or len(df) < max(self.config.ema_slow, self.config.rsi_period,
                                        self.config.macd_slow + self.config.macd_signal):
            logger.debug(f"Insufficient data for {timeframe}: {len(df) if df is not None else 0} bars")
            return None

        try:
            # Ensure column names are lowercase
            df.columns = df.columns.str.lower()

            # Current close price
            close = float(df['close'].iloc[-1])

            # EMA calculations
            ema9 = ta.ema(df['close'], length=self.config.ema_fast)
            ema21 = ta.ema(df['close'], length=self.config.ema_slow)

            if ema9 is None or ema21 is None or len(ema9) == 0:
                logger.warning(f"EMA calculation failed for {timeframe}")
                return None

            ema9_val = float(ema9.iloc[-1])
            ema21_val = float(ema21.iloc[-1])

            # RSI calculation
            rsi = ta.rsi(df['close'], length=self.config.rsi_period)
            rsi_val = float(rsi.iloc[-1]) if rsi is not None and len(rsi) > 0 else 50.0

            # MACD calculation
            macd_result = ta.macd(df['close'],
                                  fast=self.config.macd_fast,
                                  slow=self.config.macd_slow,
                                  signal=self.config.macd_signal)

            if macd_result is not None and len(macd_result.columns) >= 3:
                macd_val = float(macd_result.iloc[-1, 0])  # MACD line
                macd_sig = float(macd_result.iloc[-1, 1])  # Signal line
                macd_hist = float(macd_result.iloc[-1, 2])  # Histogram
            else:
                macd_val, macd_sig, macd_hist = 0.0, 0.0, 0.0

            # ATR calculation
            atr = ta.atr(df['high'], df['low'], df['close'], length=self.config.atr_period)
            atr_val = float(atr.iloc[-1]) if atr is not None and len(atr) > 0 else 0.0

            # ========================================
            # BOLLINGER BANDS CALCULATION
            # ========================================
            bb_upper, bb_middle, bb_lower = 0.0, 0.0, 0.0
            bb_width, bb_percent = 0.0, 0.5
            bb_squeeze = False

            try:
                # pandas_ta bbands returns DataFrame with BBL, BBM, BBU columns
                bbands = ta.bbands(df['close'], length=self.config.bb_period, std=self.config.bb_std_dev)
                if bbands is not None and len(bbands.columns) >= 3:
                    # Column order: BBL, BBM, BBU, BBB, BBP
                    bb_lower = float(bbands.iloc[-1, 0])
                    bb_middle = float(bbands.iloc[-1, 1])
                    bb_upper = float(bbands.iloc[-1, 2])

                    # Band width (% of middle)
                    if bb_middle > 0:
                        bb_width = (bb_upper - bb_lower) / bb_middle

                    # %B (where price is within bands: 0=lower, 1=upper)
                    if bb_upper > bb_lower:
                        bb_percent = (close - bb_lower) / (bb_upper - bb_lower)
                        bb_percent = max(0, min(1, bb_percent))  # Clamp to 0-1

                    # Squeeze detection: current width < 20-period avg width
                    if len(bbands) >= 20:
                        # Calculate width series
                        width_series = (bbands.iloc[:, 2] - bbands.iloc[:, 0]) / bbands.iloc[:, 1]
                        avg_width = float(width_series.rolling(20).mean().iloc[-1])
                        bb_squeeze = bb_width < avg_width * 0.8  # 20% below average = squeeze

            except Exception as e:
                logger.debug(f"Bollinger Bands calculation failed for {timeframe}: {e}")

            # ========================================
            # VOLUME ANALYSIS
            # ========================================
            volume_current = 0.0
            volume_avg_20 = 0.0
            volume_ratio = 1.0
            volume_delta = 0.0
            volume_trend = 'neutral'

            if 'volume' in df.columns and len(df) >= 20:
                # Current volume
                volume_current = float(df['volume'].iloc[-1])

                # 20-period average volume
                volume_avg_20 = float(df['volume'].rolling(20).mean().iloc[-1])

                # Relative volume (current / average)
                if volume_avg_20 > 0:
                    volume_ratio = volume_current / volume_avg_20

                # Volume delta approximation (using price direction)
                # If close > open, volume is "buy volume", else "sell volume"
                # Calculate net delta over last 5 bars
                buy_vol = 0.0
                sell_vol = 0.0
                for i in range(-5, 0):
                    if len(df) > abs(i):
                        bar_vol = float(df['volume'].iloc[i])
                        bar_open = float(df['open'].iloc[i])
                        bar_close = float(df['close'].iloc[i])
                        if bar_close >= bar_open:
                            buy_vol += bar_vol
                        else:
                            sell_vol += bar_vol
                volume_delta = buy_vol - sell_vol

                # Volume trend (is volume increasing or decreasing?)
                if len(df) >= 10:
                    vol_5_ago = float(df['volume'].iloc[-5:].mean())
                    vol_10_ago = float(df['volume'].iloc[-10:-5].mean())
                    if vol_10_ago > 0:
                        vol_change = (vol_5_ago - vol_10_ago) / vol_10_ago
                        if vol_change > 0.2:
                            volume_trend = 'increasing'
                        elif vol_change < -0.2:
                            volume_trend = 'decreasing'

            analysis = TimeframeAnalysis(
                timeframe=timeframe,
                close=close,
                ema9=ema9_val,
                ema21=ema21_val,
                rsi14=rsi_val,
                macd_value=macd_val,
                macd_signal=macd_sig,
                macd_histogram=macd_hist,
                atr14=atr_val,
                # Bollinger Bands
                bb_upper=bb_upper,
                bb_middle=bb_middle,
                bb_lower=bb_lower,
                bb_width=bb_width,
                bb_percent=bb_percent,
                bb_squeeze=bb_squeeze,
                # Volume
                volume_current=volume_current,
                volume_avg_20=volume_avg_20,
                volume_ratio=volume_ratio,
                volume_delta=volume_delta,
                volume_trend=volume_trend,
                bars_analyzed=len(df)
            )

            logger.debug(f"{timeframe}: close={close:.2f}, EMA9={ema9_val:.2f}, EMA21={ema21_val:.2f}, "
                        f"RSI={rsi_val:.1f}, MACD_H={macd_hist:.4f}, ATR={atr_val:.2f}, "
                        f"BB%={bb_percent:.2f}, Vol={volume_ratio:.1f}x, regime={analysis.market_regime}, bias={analysis.bias}")

            return analysis

        except Exception as e:
            logger.error(f"Indicator calculation failed for {timeframe}: {e}")
            return None

    def analyze_multi_timeframe(
        self,
        ticker: str,
        bars_by_tf: Dict[str, pd.DataFrame]
    ) -> MultiTimeframeSignal:
        """
        Analyze multiple timeframes and generate aggregate signal.

        Args:
            ticker: Symbol being analyzed
            bars_by_tf: Dict mapping timeframe ('5m', '15m', etc.) to OHLCV DataFrame

        Returns:
            MultiTimeframeSignal with complete analysis and trade decision
        """
        import time
        start_time = time.time()

        signal = MultiTimeframeSignal(
            ticker=ticker,
            timestamp=datetime.now(),
            min_aligned_tfs=self.config.min_aligned_timeframes,
            min_confidence=self.config.min_confidence_score,
            min_rr=self.config.min_risk_reward
        )

        # Calculate indicators for each timeframe
        analyses = {}
        for tf in ['5m', '15m', '30m', '1h', '4h']:
            if tf in bars_by_tf and bars_by_tf[tf] is not None:
                analysis = self.calculate_indicators(bars_by_tf[tf], tf)
                if analysis:
                    analyses[tf] = analysis

        # Store in signal object
        signal.tf_5m = analyses.get('5m')
        signal.tf_15m = analyses.get('15m')
        signal.tf_30m = analyses.get('30m')
        signal.tf_1h = analyses.get('1h')
        signal.tf_4h = analyses.get('4h')
        signal.tf_results = analyses  # Store dict for UI access

        if len(analyses) < 3:
            signal.rejection_reason = f"Insufficient timeframes: only {len(analyses)}/5 available"
            logger.warning(f"{ticker}: {signal.rejection_reason}")
            signal.processing_time_ms = (time.time() - start_time) * 1000
            return signal

        # Count aligned timeframes
        bullish_tfs = []
        bearish_tfs = []

        for tf, analysis in analyses.items():
            if analysis.bias == 'bullish':
                bullish_tfs.append(tf)
            elif analysis.bias == 'bearish':
                bearish_tfs.append(tf)

        signal.aligned_bullish = len(bullish_tfs)
        signal.aligned_bearish = len(bearish_tfs)

        # ========================================
        # BOLLINGER BANDS AGGREGATION
        # ========================================
        bb_squeeze_count = 0
        bb_bullish_count = 0
        regime_votes = {'trending': 0, 'ranging': 0, 'volatile': 0, 'neutral': 0}

        for tf, analysis in analyses.items():
            if analysis.bb_squeeze:
                bb_squeeze_count += 1
            if analysis.bb_bullish:
                bb_bullish_count += 1
            # Vote on market regime
            regime_votes[analysis.market_regime] = regime_votes.get(analysis.market_regime, 0) + 1

        signal.bb_squeeze_count = bb_squeeze_count
        signal.bb_bullish_count = bb_bullish_count

        # Determine overall market regime (majority vote)
        signal.market_regime = max(regime_votes, key=regime_votes.get)

        # ========================================
        # VOLUME AGGREGATION ACROSS TIMEFRAMES
        # ========================================
        volume_ratios = []
        volume_confirms_count = 0

        for tf, analysis in analyses.items():
            if analysis.volume_ratio > 0:
                volume_ratios.append(analysis.volume_ratio)

            # Count how many TFs have volume confirming direction
            if signal.overall_bias == 'bullish' and analysis.volume_bullish:
                volume_confirms_count += 1
            elif signal.overall_bias == 'bearish' and not analysis.volume_bullish:
                volume_confirms_count += 1

        if volume_ratios:
            signal.volume_ratio_avg = sum(volume_ratios) / len(volume_ratios)

        signal.volume_trend_aligned = volume_confirms_count
        signal.volume_confirms = volume_confirms_count >= 3  # Majority of TFs confirm

        # Determine overall bias
        total_tfs = len(analyses)
        if signal.aligned_bullish >= self.config.min_aligned_timeframes:
            signal.overall_bias = 'bullish'
        elif signal.aligned_bearish >= self.config.min_aligned_timeframes:
            signal.overall_bias = 'bearish'
        else:
            signal.overall_bias = 'neutral'
            signal.rejection_reason = f"Insufficient alignment: {signal.aligned_bullish} bullish, {signal.aligned_bearish} bearish (need {self.config.min_aligned_timeframes})"

        # Check higher TF agreement if required
        if self.config.require_higher_tf_agreement and signal.overall_bias != 'neutral':
            higher_tf_bias = signal.overall_bias

            # Check 1h
            if signal.tf_1h and signal.tf_1h.bias != higher_tf_bias and signal.tf_1h.bias != 'neutral':
                signal.overall_bias = 'neutral'
                signal.rejection_reason = f"1h TF disagrees: {signal.tf_1h.bias} vs {higher_tf_bias}"

            # Check 4h
            if signal.tf_4h and signal.tf_4h.bias != higher_tf_bias and signal.tf_4h.bias != 'neutral':
                signal.overall_bias = 'neutral'
                signal.rejection_reason = f"4h TF disagrees: {signal.tf_4h.bias} vs {higher_tf_bias}"

        # Calculate confidence score
        if signal.overall_bias != 'neutral':
            aligned = signal.aligned_bullish if signal.overall_bias == 'bullish' else signal.aligned_bearish
            base_confidence = (aligned / total_tfs) * 100

            # Bonuses
            bonus = 0
            if aligned == 5:
                bonus += 10  # All 5 aligned
            if signal.tf_1h and signal.tf_4h:
                if signal.tf_1h.bias == signal.tf_4h.bias == signal.overall_bias:
                    bonus += 10  # Higher TFs strongly agree

            # VOLUME CONFIRMATION BONUS
            if signal.volume_confirms:
                bonus += 5  # Volume confirms direction
            if signal.volume_ratio_avg > 1.5:
                bonus += 5  # High relative volume = conviction

            # BOLLINGER BANDS BONUS
            if signal.overall_bias == 'bullish' and signal.bb_bullish_count >= 3:
                bonus += 5  # BB confirms bullish across majority of TFs
            elif signal.overall_bias == 'bearish' and signal.bb_bullish_count <= 2:
                bonus += 5  # BB confirms bearish (low BB bullish count)
            if signal.bb_squeeze_count >= 3:
                bonus += 3  # Squeeze = potential breakout incoming

            signal.confidence_score = min(100, base_confidence + bonus)

        # ========================================
        # ADAPTIVE R:R BASED ON MARKET REGIME
        # ========================================
        # Get R:R multipliers based on detected market regime
        if self.config.adaptive_rr_enabled:
            regime_config = self.config.rr_by_regime.get(
                signal.market_regime,
                self.config.rr_by_regime['neutral']
            )
            stop_mult = regime_config['stop_mult']
            target_mult = regime_config['target_mult']
            min_rr = regime_config['min_rr']
        else:
            stop_mult = self.config.atr_stop_multiplier
            target_mult = self.config.atr_target_multiplier
            min_rr = self.config.min_risk_reward

        signal.adaptive_stop_mult = stop_mult
        signal.adaptive_target_mult = target_mult

        # Calculate risk parameters using ATR from 5m (primary trading TF)
        if signal.tf_5m and signal.tf_5m.atr14 > 0:
            atr = signal.tf_5m.atr14
            entry = signal.tf_5m.close

            signal.entry_price = entry
            signal.atr_for_stops = atr

            # Use percentage-based stops if enabled (OPTIMAL: PF 1.41, Sharpe 2.02)
            if self.config.use_pct_stops:
                # Calculate stop/target as percentage of entry price
                pct_stop = self.config.pct_stop_loss / 100  # 0.2% -> 0.002

                # ========================================
                # REGIME-AWARE TARGET CALCULATION (NEW)
                # ========================================
                # In uptrend: use 0.8-1.0% target (1:4 to 1:5 R:R)
                # In downtrend/other: use standard 0.6% target (1:3 R:R)
                if signal.market_regime == 'trending':
                    # Check if we're in uptrend (more bullish TFs than bearish)
                    if signal.aligned_bullish > signal.aligned_bearish and signal.overall_bias == 'bullish':
                        # Uptrend long: use wider target
                        pct_target = self.config.uptrend_pct_target / 100  # 0.8% -> 0.008
                        signal.regime_min_rr = 4.0
                        signal.trailing_enabled = True  # Enable trailing in uptrend
                        logger.debug(f"📈 Uptrend detected: using {self.config.uptrend_pct_target}% target (1:4 R:R)")
                    elif signal.aligned_bearish > signal.aligned_bullish and signal.overall_bias == 'bearish':
                        # Downtrend short: use standard target
                        pct_target = self.config.downtrend_pct_target / 100  # 0.6% -> 0.006
                        signal.regime_min_rr = 3.0
                        signal.trailing_enabled = True
                        logger.debug(f"📉 Downtrend detected: using {self.config.downtrend_pct_target}% target (1:3 R:R)")
                    else:
                        pct_target = self.config.pct_take_profit / 100
                        signal.regime_min_rr = 3.0
                else:
                    pct_target = self.config.pct_take_profit / 100  # 0.6% -> 0.006
                    signal.regime_min_rr = 3.0

                if signal.overall_bias == 'bullish':
                    signal.stop_loss = entry * (1 - pct_stop)
                    signal.take_profit = entry * (1 + pct_target)
                    # Calculate trailing breakeven and partial targets
                    if signal.trailing_enabled:
                        risk = entry - signal.stop_loss
                        signal.trailing_breakeven_price = entry + (risk * 2)  # Breakeven at 2R
                        signal.trailing_partial_target = entry + (risk * 3)   # Partial exit at 3R
                elif signal.overall_bias == 'bearish':
                    signal.stop_loss = entry * (1 + pct_stop)
                    signal.take_profit = entry * (1 - pct_target)
                    # Calculate trailing breakeven and partial targets
                    if signal.trailing_enabled:
                        risk = signal.stop_loss - entry
                        signal.trailing_breakeven_price = entry - (risk * 2)
                        signal.trailing_partial_target = entry - (risk * 3)

                # Store regime-adjusted values
                signal.regime_adjusted_target = signal.take_profit
                signal.regime_adjusted_stop = signal.stop_loss
            else:
                # Use ATR-based stops (original logic)
                if signal.overall_bias == 'bullish':
                    signal.stop_loss = entry - (atr * stop_mult)
                    signal.take_profit = entry + (atr * target_mult)
                elif signal.overall_bias == 'bearish':
                    signal.stop_loss = entry + (atr * stop_mult)
                    signal.take_profit = entry - (atr * target_mult)

            risk = abs(entry - signal.stop_loss)
            reward = abs(signal.take_profit - entry)
            signal.risk_reward_ratio = reward / risk if risk > 0 else 0

            # ========================================
            # SLIPPAGE BUFFER ADJUSTMENT
            # ========================================
            # Apply slippage buffer: reduces effective R:R by slippage_buffer_pct
            # This accounts for real-world execution slippage
            slippage_factor = 1 - (self.config.slippage_buffer_pct / 100)
            signal.risk_reward_after_slippage = signal.risk_reward_ratio * slippage_factor

        # Final decision (use adaptive min_rr based on market regime)
        effective_min_rr = min_rr if self.config.adaptive_rr_enabled else self.config.min_risk_reward

        if signal.overall_bias == 'neutral':
            signal.should_trade = False
            signal.action = 'none'
        elif signal.confidence_score < self.config.min_confidence_score:
            signal.should_trade = False
            signal.action = 'none'
            signal.rejection_reason = f"Confidence {signal.confidence_score:.1f}% < {self.config.min_confidence_score}%"
        elif signal.risk_reward_after_slippage < effective_min_rr:
            signal.should_trade = False
            signal.action = 'none'
            signal.rejection_reason = f"R:R (after slippage) {signal.risk_reward_after_slippage:.2f} < {effective_min_rr} ({signal.market_regime} regime)"
        else:
            signal.should_trade = True
            signal.action = 'buy' if signal.overall_bias == 'bullish' else 'sell'

        # Record processing time and signal expiry
        signal.processing_time_ms = (time.time() - start_time) * 1000
        signal.signal_generated_at = datetime.now()
        signal.signal_expires_at = signal.signal_generated_at + timedelta(minutes=self.config.signal_ttl_minutes)
        signal.is_expired = False

        logger.info(f"📊 {ticker} MTF Analysis: {signal.overall_bias.upper()} "
                   f"({signal.aligned_bullish}↑/{signal.aligned_bearish}↓) "
                   f"conf={signal.confidence_score:.1f}% R:R={signal.risk_reward_ratio:.2f}→{signal.risk_reward_after_slippage:.2f} "
                   f"vol={signal.volume_ratio_avg:.1f}x BB-bull={signal.bb_bullish_count} regime={signal.market_regime} "
                   f"→ {signal.action.upper()} [{signal.processing_time_ms:.0f}ms] expires={signal.signal_expires_at.strftime('%H:%M')}" +
                   (f" ❌ {signal.rejection_reason}" if not signal.should_trade else " ✅"))

        return signal

    def bars_to_dataframe(self, bars: List) -> pd.DataFrame:
        """
        Convert list of Bar objects to pandas DataFrame.

        Args:
            bars: List of Bar dataclass objects with timestamp, open, high, low, close, volume

        Returns:
            DataFrame with lowercase column names, sorted chronologically
        """
        if not bars:
            return pd.DataFrame()

        data = []
        for bar in bars:
            data.append({
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            })

        df = pd.DataFrame(data)
        df = df.sort_values('timestamp').reset_index(drop=True)
        return df


# Global instance for import
_indicator_engine: Optional[DeterministicIndicators] = None

def get_indicator_engine(config: Optional[IndicatorConfig] = None) -> DeterministicIndicators:
    """Get or create the global indicator engine instance."""
    global _indicator_engine
    if _indicator_engine is None:
        _indicator_engine = DeterministicIndicators(config)
    return _indicator_engine
