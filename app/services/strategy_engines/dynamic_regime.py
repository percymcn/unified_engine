"""
DYNAMIC REGIME ENGINE (dynamic_regime_v1)
==========================================

Strategy: Adaptive Multi-Regime Strategy

Automatically adjusts between multiple trading modes based on real-time
market regime detection. Uses percentage-based stops/targets that adapt
to current market conditions.

Regime Modes:
- TRENDING (>3% 24h change): 2%/2% stops, trend-following, full size
- RANGING (<1% 24h change): 1%/1% stops, mean-reversion, 0.75x size
- VOLATILE (>5% 24h change): 1.5%/2.5% stops, reduced exposure, 0.5x size
- BREAKOUT (compression release): 2.5%/3% stops, momentum, 1.25x size

Pyramid Rules:
- Both directions allowed
- Max 3 positions per ticker
- Add-on: 50% pullback + 2 bars continuation

Risk Management:
- Dynamic stop/target based on regime
- Position sizing adapts to volatility
- Per-regime performance tracking
"""

import logging
from typing import Tuple, Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

from app.services.strategy_engines.base import (
    StrategyEngine,
    SignalContext,
    TradingSignal,
    PANDAS_TA_AVAILABLE
)

if PANDAS_TA_AVAILABLE:
    import pandas_ta as ta

logger = logging.getLogger(__name__)


@dataclass
class RegimeParams:
    """Parameters for a specific market regime."""
    stop_pct: float
    target_pct: float
    size_mult: float
    mode: str
    description: str


@dataclass
class PyramidLevel:
    """Tracks a pyramid add-on level."""
    entry_price: float
    direction: str
    regime: str
    timestamp: datetime
    level: int = 1


class DynamicRegimeEngine(StrategyEngine):
    """
    Dynamic regime-adaptive strategy engine.

    Automatically detects market regime and adjusts:
    - Stop loss percentage
    - Take profit percentage
    - Position size multiplier
    - Trading mode (trend-following vs mean-reversion)
    """

    def __init__(self, strategy_id: str = "dynamic_regime_v1"):
        super().__init__(strategy_id, "dynamic_regime")

        # Regime detection thresholds (24h % change)
        self.trending_threshold = 3.0   # >3% = trending
        self.ranging_threshold = 1.0    # <1% = ranging
        self.volatile_threshold = 5.0   # >5% = volatile
        self.compression_atr_ratio = 0.6  # ATR < 60% of average = compression

        # Regime parameters
        self.regimes: Dict[str, RegimeParams] = {
            'trending_up': RegimeParams(
                stop_pct=2.0, target_pct=2.0, size_mult=1.0,
                mode='trend-following',
                description='Bullish trend - follow the momentum'
            ),
            'trending_down': RegimeParams(
                stop_pct=2.0, target_pct=2.0, size_mult=1.0,
                mode='trend-following',
                description='Bearish trend - follow the momentum'
            ),
            'ranging': RegimeParams(
                stop_pct=1.0, target_pct=1.0, size_mult=0.75,
                mode='mean-reversion',
                description='Range-bound - fade extremes'
            ),
            'volatile': RegimeParams(
                stop_pct=1.5, target_pct=2.5, size_mult=0.5,
                mode='reduced-exposure',
                description='High volatility - reduce size, wider stops'
            ),
            'breakout': RegimeParams(
                stop_pct=2.5, target_pct=3.0, size_mult=1.25,
                mode='momentum',
                description='Compression breakout - ride the move'
            ),
            'neutral': RegimeParams(
                stop_pct=1.5, target_pct=1.5, size_mult=0.75,
                mode='conservative',
                description='Unclear regime - conservative approach'
            )
        }

        # Pyramid configuration
        self.max_pyramid_levels = 3
        self.pyramid_pullback_pct = 0.5  # 50% retracement
        self.pyramid_continuation_bars = 2

        # Indicator periods
        self.ema_fast = 9
        self.ema_mid = 21
        self.ema_slow = 50
        self.rsi_period = 14
        self.atr_period = 14
        self.bb_period = 20
        self.bb_std = 2.0

        # Tracking
        self._current_regimes: Dict[str, str] = {}
        self._regime_history: Dict[str, List[str]] = {}
        self._pyramid_positions: Dict[str, List[PyramidLevel]] = {}
        self._regime_stats: Dict[str, Dict] = {}

        logger.info(f"DynamicRegimeEngine initialized: {strategy_id}")
        logger.info(f"Regimes: {list(self.regimes.keys())}")

    def detect_regime(self, context: SignalContext) -> str:
        """
        Detect current market regime based on multiple factors.

        Returns one of: trending_up, trending_down, ranging, volatile, breakout, neutral
        """
        df = context.df
        if df is None or len(df) < 50:
            return 'neutral'

        try:
            # Calculate 24h price change
            if len(df) >= 288:  # 288 5-min bars = 24 hours
                price_24h_ago = df['close'].iloc[-288]
            else:
                price_24h_ago = df['close'].iloc[0]

            current_price = df['close'].iloc[-1]
            price_change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100

            # Calculate ATR for volatility
            atr = self.calculate_atr(df, self.atr_period)
            avg_atr = df['close'].tail(50).std() if len(df) >= 50 else atr
            atr_ratio = atr / avg_atr if avg_atr > 0 else 1.0

            # Calculate EMAs for trend
            ema_9 = self.calculate_ema(df, self.ema_fast)
            ema_21 = self.calculate_ema(df, self.ema_mid)
            ema_50 = self.calculate_ema(df, self.ema_slow)

            # Calculate RSI
            rsi = self.calculate_rsi(df, self.rsi_period)

            # Detect compression (for breakout)
            is_compressed = self._detect_compression(df)

            # Regime classification
            abs_change = abs(price_change_24h)

            # Check for high volatility first
            if abs_change > self.volatile_threshold:
                return 'volatile'

            # Check for breakout (compression release)
            if is_compressed and abs_change > self.ranging_threshold:
                return 'breakout'

            # Check for trending
            if abs_change > self.trending_threshold:
                if price_change_24h > 0:
                    # Confirm with EMA alignment
                    if ema_9 > ema_21 > ema_50:
                        return 'trending_up'
                    elif ema_9 > ema_21:  # Partial alignment
                        return 'trending_up'
                else:
                    # Confirm with EMA alignment
                    if ema_9 < ema_21 < ema_50:
                        return 'trending_down'
                    elif ema_9 < ema_21:  # Partial alignment
                        return 'trending_down'

            # Check for ranging
            if abs_change < self.ranging_threshold:
                return 'ranging'

            # Default based on trend direction with lower conviction
            if price_change_24h > 0:
                return 'trending_up' if ema_9 > ema_21 else 'neutral'
            else:
                return 'trending_down' if ema_9 < ema_21 else 'neutral'

        except Exception as e:
            logger.warning(f"Regime detection error: {e}")
            return 'neutral'

    def _detect_compression(self, df: pd.DataFrame) -> bool:
        """Detect price compression (narrowing volatility)."""
        if df is None or len(df) < 30:
            return False

        try:
            # Compare recent ATR to historical ATR
            recent_atr = self.calculate_atr(df.tail(10), min(10, self.atr_period))
            historical_atr = self.calculate_atr(df.tail(30).head(20), self.atr_period)

            if historical_atr == 0:
                return False

            # Compression if recent ATR < 60% of historical
            return (recent_atr / historical_atr) < self.compression_atr_ratio

        except Exception:
            return False

    def get_regime_params(self, regime: str) -> RegimeParams:
        """Get trading parameters for a specific regime."""
        return self.regimes.get(regime, self.regimes['neutral'])

    def generate_signal(self, context: SignalContext) -> TradingSignal:
        """
        Generate adaptive signal based on current regime.
        """
        # Enrich context with indicators
        context = self.enrich_context(context)

        # Detect current regime
        regime = self.detect_regime(context)
        params = self.get_regime_params(regime)

        # Track regime
        ticker = context.ticker
        self._current_regimes[ticker] = regime
        if ticker not in self._regime_history:
            self._regime_history[ticker] = []
        self._regime_history[ticker].append(regime)
        if len(self._regime_history[ticker]) > 100:
            self._regime_history[ticker] = self._regime_history[ticker][-50:]

        # Default: no signal
        signal = TradingSignal(
            strategy_id=self.strategy_id,
            strategy_type=self.strategy_type,
            ticker=ticker,
            timestamp=context.timestamp,
            direction='none',
            confidence=0.0,
            regime=regime
        )

        # Validate basic setup
        is_valid, reason = self.validate_setup(context)
        if not is_valid:
            signal.is_valid = False
            signal.invalidation_reason = reason
            return signal

        # Generate signal based on regime mode
        if params.mode == 'trend-following':
            signal = self._generate_trend_signal(context, regime, params)
        elif params.mode == 'mean-reversion':
            signal = self._generate_meanrev_signal(context, regime, params)
        elif params.mode == 'momentum':
            signal = self._generate_breakout_signal(context, regime, params)
        elif params.mode == 'reduced-exposure':
            signal = self._generate_volatile_signal(context, regime, params)
        else:
            # Conservative/neutral mode
            signal = self._generate_conservative_signal(context, regime, params)

        return signal

    def _generate_trend_signal(
        self,
        context: SignalContext,
        regime: str,
        params: RegimeParams
    ) -> TradingSignal:
        """Generate trend-following signal."""
        signal = self._create_base_signal(context, regime)

        df = context.df
        if df is None or len(df) < self.ema_slow:
            signal.invalidation_reason = "Insufficient data for trend analysis"
            return signal

        # Determine trend direction
        direction = 'long' if 'up' in regime else 'short'

        # Check for pullback entry
        has_pullback, confidence = self._check_trend_pullback(context, direction)

        if not has_pullback:
            signal.invalidation_reason = f"No valid pullback in {regime}"
            return signal

        # Calculate stops and targets
        stop_loss, take_profit, rr_ratio = self._calculate_pct_risk(
            context.close, direction, params.stop_pct, params.target_pct
        )

        signal.direction = direction
        signal.confidence = confidence
        signal.entry_price = context.close
        signal.stop_loss = stop_loss
        signal.take_profit = take_profit
        signal.risk_reward_ratio = rr_ratio
        signal.position_size_pct = params.size_mult

        signal.entry_condition = f"Trend pullback ({regime})"
        signal.setup_description = (
            f"TREND: {direction.upper()} @ {context.close:.2f}, "
            f"SL={params.stop_pct}%, TP={params.target_pct}%, "
            f"Size={params.size_mult}x"
        )
        signal.indicators = self._get_indicator_snapshot(context, regime, params)

        return signal

    def _generate_meanrev_signal(
        self,
        context: SignalContext,
        regime: str,
        params: RegimeParams
    ) -> TradingSignal:
        """Generate mean-reversion signal for ranging markets."""
        signal = self._create_base_signal(context, regime)

        # Get Bollinger Bands
        bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(
            context.df, self.bb_period, self.bb_std
        )

        if bb_upper == 0 or bb_lower == 0:
            signal.invalidation_reason = "Cannot calculate Bollinger Bands"
            return signal

        price = context.close
        rsi = context.rsi if context.rsi > 0 else self.calculate_rsi(context.df, self.rsi_period)

        # Mean reversion: fade extremes
        direction = None
        confidence = 0.0

        # Oversold at lower band
        if price <= bb_lower and rsi < 35:
            direction = 'long'
            confidence = min(90, 60 + (35 - rsi))

        # Overbought at upper band
        elif price >= bb_upper and rsi > 65:
            direction = 'short'
            confidence = min(90, 60 + (rsi - 65))

        if direction is None:
            signal.invalidation_reason = "Price not at extremes for mean-reversion"
            return signal

        # Calculate stops and targets
        stop_loss, take_profit, rr_ratio = self._calculate_pct_risk(
            price, direction, params.stop_pct, params.target_pct
        )

        signal.direction = direction
        signal.confidence = confidence / 100.0
        signal.entry_price = price
        signal.stop_loss = stop_loss
        signal.take_profit = take_profit
        signal.risk_reward_ratio = rr_ratio
        signal.position_size_pct = params.size_mult

        signal.entry_condition = f"Mean reversion at BB {'lower' if direction == 'long' else 'upper'}"
        signal.setup_description = (
            f"MEAN-REV: {direction.upper()} @ {price:.2f}, "
            f"BB={bb_lower:.2f}/{bb_upper:.2f}, RSI={rsi:.0f}, "
            f"Size={params.size_mult}x"
        )
        signal.indicators = self._get_indicator_snapshot(context, regime, params)
        signal.indicators['bb_upper'] = bb_upper
        signal.indicators['bb_lower'] = bb_lower
        signal.indicators['bb_middle'] = bb_middle

        return signal

    def _generate_breakout_signal(
        self,
        context: SignalContext,
        regime: str,
        params: RegimeParams
    ) -> TradingSignal:
        """Generate momentum/breakout signal."""
        signal = self._create_base_signal(context, regime)

        df = context.df
        if df is None or len(df) < 30:
            signal.invalidation_reason = "Insufficient data for breakout analysis"
            return signal

        # Find recent range
        lookback = 20
        recent_high = df['high'].tail(lookback).max()
        recent_low = df['low'].tail(lookback).min()
        price = context.close

        # Determine breakout direction
        direction = None
        confidence = 0.0

        # Upside breakout
        if price > recent_high:
            direction = 'long'
            breakout_pct = ((price - recent_high) / recent_high) * 100
            confidence = min(85, 60 + breakout_pct * 10)

        # Downside breakout
        elif price < recent_low:
            direction = 'short'
            breakout_pct = ((recent_low - price) / recent_low) * 100
            confidence = min(85, 60 + breakout_pct * 10)

        if direction is None:
            signal.invalidation_reason = "No breakout detected"
            return signal

        # Calculate stops and targets
        stop_loss, take_profit, rr_ratio = self._calculate_pct_risk(
            price, direction, params.stop_pct, params.target_pct
        )

        signal.direction = direction
        signal.confidence = confidence / 100.0
        signal.entry_price = price
        signal.stop_loss = stop_loss
        signal.take_profit = take_profit
        signal.risk_reward_ratio = rr_ratio
        signal.position_size_pct = params.size_mult

        signal.entry_condition = f"Breakout {'above' if direction == 'long' else 'below'} range"
        signal.setup_description = (
            f"BREAKOUT: {direction.upper()} @ {price:.2f}, "
            f"Range={recent_low:.2f}-{recent_high:.2f}, "
            f"Size={params.size_mult}x"
        )
        signal.indicators = self._get_indicator_snapshot(context, regime, params)
        signal.indicators['range_high'] = recent_high
        signal.indicators['range_low'] = recent_low

        return signal

    def _generate_volatile_signal(
        self,
        context: SignalContext,
        regime: str,
        params: RegimeParams
    ) -> TradingSignal:
        """Generate signal for high volatility - reduced exposure."""
        signal = self._create_base_signal(context, regime)

        # In volatile markets, only take high-conviction setups
        df = context.df
        if df is None or len(df) < 30:
            signal.invalidation_reason = "Insufficient data"
            return signal

        # Look for extreme RSI divergence
        rsi = self.calculate_rsi(df, self.rsi_period)

        direction = None
        confidence = 0.0

        # Only trade at very extreme levels in volatile markets
        if rsi < 25:  # Very oversold
            direction = 'long'
            confidence = min(80, 55 + (25 - rsi) * 2)
        elif rsi > 75:  # Very overbought
            direction = 'short'
            confidence = min(80, 55 + (rsi - 75) * 2)

        if direction is None:
            signal.invalidation_reason = "No extreme setup in volatile regime"
            return signal

        # Calculate stops and targets (wider stops for volatility)
        stop_loss, take_profit, rr_ratio = self._calculate_pct_risk(
            context.close, direction, params.stop_pct, params.target_pct
        )

        signal.direction = direction
        signal.confidence = confidence / 100.0
        signal.entry_price = context.close
        signal.stop_loss = stop_loss
        signal.take_profit = take_profit
        signal.risk_reward_ratio = rr_ratio
        signal.position_size_pct = params.size_mult  # Reduced size

        signal.entry_condition = f"Volatile market extreme (RSI={rsi:.0f})"
        signal.setup_description = (
            f"VOLATILE: {direction.upper()} @ {context.close:.2f}, "
            f"RSI={rsi:.0f}, Size={params.size_mult}x (reduced)"
        )
        signal.indicators = self._get_indicator_snapshot(context, regime, params)

        return signal

    def _generate_conservative_signal(
        self,
        context: SignalContext,
        regime: str,
        params: RegimeParams
    ) -> TradingSignal:
        """Generate conservative signal for unclear regimes."""
        signal = self._create_base_signal(context, regime)

        # In neutral/unclear regime, require multiple confirmations
        df = context.df
        if df is None or len(df) < 50:
            signal.invalidation_reason = "Insufficient data"
            return signal

        ema_9 = self.calculate_ema(df, self.ema_fast)
        ema_21 = self.calculate_ema(df, self.ema_mid)
        rsi = self.calculate_rsi(df, self.rsi_period)
        price = context.close

        direction = None
        confidence = 0.0

        # Require EMA alignment AND RSI confirmation
        if ema_9 > ema_21 and price > ema_9 and rsi > 50 and rsi < 70:
            direction = 'long'
            confidence = 55
        elif ema_9 < ema_21 and price < ema_9 and rsi < 50 and rsi > 30:
            direction = 'short'
            confidence = 55

        if direction is None:
            signal.invalidation_reason = "No confirmed setup in neutral regime"
            return signal

        # Calculate stops and targets
        stop_loss, take_profit, rr_ratio = self._calculate_pct_risk(
            price, direction, params.stop_pct, params.target_pct
        )

        signal.direction = direction
        signal.confidence = confidence / 100.0
        signal.entry_price = price
        signal.stop_loss = stop_loss
        signal.take_profit = take_profit
        signal.risk_reward_ratio = rr_ratio
        signal.position_size_pct = params.size_mult

        signal.entry_condition = "Conservative aligned setup"
        signal.setup_description = (
            f"CONSERVATIVE: {direction.upper()} @ {price:.2f}, "
            f"Size={params.size_mult}x"
        )
        signal.indicators = self._get_indicator_snapshot(context, regime, params)

        return signal

    def _check_trend_pullback(
        self,
        context: SignalContext,
        direction: str
    ) -> Tuple[bool, float]:
        """Check for valid pullback entry in trend."""
        df = context.df
        if df is None or len(df) < 30:
            return False, 0.0

        price = context.close
        ema_21 = self.calculate_ema(df, self.ema_mid)
        vwap = context.vwap if context.vwap > 0 else self.calculate_vwap(df.tail(78))
        atr = context.atr if context.atr > 0 else self.calculate_atr(df, self.atr_period)

        # Pullback zone: within 1 ATR of EMA21 or VWAP
        zone_width = atr * 1.5

        if direction == 'long':
            # Price should be near (below or at) EMA21/VWAP
            near_ema = abs(price - ema_21) < zone_width
            near_vwap = abs(price - vwap) < zone_width

            # Check for bullish candle (potential bounce)
            if len(df) >= 3:
                last_bar = df.iloc[-1]
                is_bullish = last_bar['close'] > last_bar['open']
                higher_low = df['low'].iloc[-1] > df['low'].iloc[-2]

                if (near_ema or near_vwap) and is_bullish:
                    confidence = 65
                    if higher_low:
                        confidence += 10
                    if near_ema and near_vwap:
                        confidence += 5
                    return True, confidence / 100.0

        else:  # short
            # Price should be near (above or at) EMA21/VWAP
            near_ema = abs(price - ema_21) < zone_width
            near_vwap = abs(price - vwap) < zone_width

            if len(df) >= 3:
                last_bar = df.iloc[-1]
                is_bearish = last_bar['close'] < last_bar['open']
                lower_high = df['high'].iloc[-1] < df['high'].iloc[-2]

                if (near_ema or near_vwap) and is_bearish:
                    confidence = 65
                    if lower_high:
                        confidence += 10
                    if near_ema and near_vwap:
                        confidence += 5
                    return True, confidence / 100.0

        return False, 0.0

    def _calculate_pct_risk(
        self,
        price: float,
        direction: str,
        stop_pct: float,
        target_pct: float
    ) -> Tuple[float, float, float]:
        """Calculate stop/target based on percentage."""
        if direction == 'long':
            stop_loss = price * (1 - stop_pct / 100)
            take_profit = price * (1 + target_pct / 100)
        else:
            stop_loss = price * (1 + stop_pct / 100)
            take_profit = price * (1 - target_pct / 100)

        risk = abs(price - stop_loss)
        reward = abs(take_profit - price)
        rr_ratio = reward / risk if risk > 0 else 0

        return stop_loss, take_profit, rr_ratio

    def _create_base_signal(self, context: SignalContext, regime: str) -> TradingSignal:
        """Create base signal with common fields."""
        return TradingSignal(
            strategy_id=self.strategy_id,
            strategy_type=self.strategy_type,
            ticker=context.ticker,
            timestamp=context.timestamp,
            direction='none',
            confidence=0.0,
            regime=regime
        )

    def _get_indicator_snapshot(
        self,
        context: SignalContext,
        regime: str,
        params: RegimeParams
    ) -> Dict:
        """Get indicator snapshot for signal."""
        return {
            'regime': regime,
            'mode': params.mode,
            'stop_pct': params.stop_pct,
            'target_pct': params.target_pct,
            'size_mult': params.size_mult,
            'ema_9': context.ema_9,
            'ema_21': context.ema_21,
            'ema_50': context.ema_50,
            'rsi': context.rsi,
            'atr': context.atr,
            'vwap': context.vwap
        }

    def enrich_context(self, context: SignalContext) -> SignalContext:
        """Enrich context with calculated indicators."""
        df = context.df
        if df is None or len(df) < 20:
            return context

        try:
            context.ema_9 = self.calculate_ema(df, self.ema_fast)
            context.ema_21 = self.calculate_ema(df, self.ema_mid)
            context.ema_50 = self.calculate_ema(df, self.ema_slow) if len(df) >= self.ema_slow else 0
            context.rsi = self.calculate_rsi(df, self.rsi_period)
            context.atr = self.calculate_atr(df, self.atr_period)
            context.vwap = self.calculate_vwap(df.tail(78))  # Last session

            bb = self.calculate_bollinger_bands(df, self.bb_period, self.bb_std)
            context.bb_upper, context.bb_middle, context.bb_lower = bb
        except Exception as e:
            logger.warning(f"Context enrichment error: {e}")

        return context

    def validate_setup(self, context: SignalContext) -> Tuple[bool, str]:
        """Validate basic setup requirements."""
        if context.df is None:
            return False, "No data available"

        if len(context.df) < 30:
            return False, f"Insufficient data: {len(context.df)} bars"

        if context.close <= 0:
            return False, "Invalid price"

        return True, ""

    def calculate_risk_params(
        self,
        context: SignalContext,
        direction: str
    ) -> Tuple[float, float, float]:
        """Calculate risk parameters using current regime."""
        regime = self._current_regimes.get(context.ticker, 'neutral')
        params = self.get_regime_params(regime)

        return self._calculate_pct_risk(
            context.close, direction, params.stop_pct, params.target_pct
        )

    def check_pyramid_addon(
        self,
        context: SignalContext,
        existing_position_direction: str,
        existing_entry_price: float
    ) -> Optional[TradingSignal]:
        """
        Check for pyramid add-on opportunity.

        Add-on criteria:
        1. Existing position in same direction
        2. Price has pulled back 50% from entry to current swing
        3. 2 bars of continuation confirmed
        4. Max pyramid levels not reached
        """
        ticker = context.ticker

        # Check pyramid levels
        if ticker not in self._pyramid_positions:
            self._pyramid_positions[ticker] = []

        current_levels = len(self._pyramid_positions[ticker])
        if current_levels >= self.max_pyramid_levels:
            return None

        df = context.df
        if df is None or len(df) < 10:
            return None

        price = context.close

        # Calculate pullback
        if existing_position_direction == 'long':
            # Find high since entry
            swing_high = df['high'].tail(20).max()
            pullback_target = existing_entry_price + (swing_high - existing_entry_price) * self.pyramid_pullback_pct

            # Check if price has pulled back to target
            if price <= pullback_target:
                # Check for continuation (2 higher closes)
                if len(df) >= 3:
                    c1, c2, c3 = df['close'].iloc[-3], df['close'].iloc[-2], df['close'].iloc[-1]
                    if c3 > c2 > c1:  # Continuation
                        regime = self._current_regimes.get(ticker, 'neutral')
                        params = self.get_regime_params(regime)

                        signal = self._create_base_signal(context, regime)
                        signal.direction = 'long'
                        signal.confidence = 0.70
                        signal.entry_price = price

                        stop, target, rr = self._calculate_pct_risk(
                            price, 'long', params.stop_pct, params.target_pct
                        )
                        signal.stop_loss = stop
                        signal.take_profit = target
                        signal.risk_reward_ratio = rr
                        signal.position_size_pct = params.size_mult * 0.5  # Half size for add-ons

                        signal.entry_condition = f"Pyramid add-on #{current_levels + 1}"
                        signal.setup_description = f"ADD-ON: LONG @ {price:.2f}, pullback to {pullback_target:.2f}"

                        # Track pyramid
                        self._pyramid_positions[ticker].append(PyramidLevel(
                            entry_price=price,
                            direction='long',
                            regime=regime,
                            timestamp=context.timestamp,
                            level=current_levels + 1
                        ))

                        return signal

        else:  # short
            # Find low since entry
            swing_low = df['low'].tail(20).min()
            pullback_target = existing_entry_price - (existing_entry_price - swing_low) * self.pyramid_pullback_pct

            # Check if price has pulled back to target
            if price >= pullback_target:
                # Check for continuation (2 lower closes)
                if len(df) >= 3:
                    c1, c2, c3 = df['close'].iloc[-3], df['close'].iloc[-2], df['close'].iloc[-1]
                    if c3 < c2 < c1:  # Continuation
                        regime = self._current_regimes.get(ticker, 'neutral')
                        params = self.get_regime_params(regime)

                        signal = self._create_base_signal(context, regime)
                        signal.direction = 'short'
                        signal.confidence = 0.70
                        signal.entry_price = price

                        stop, target, rr = self._calculate_pct_risk(
                            price, 'short', params.stop_pct, params.target_pct
                        )
                        signal.stop_loss = stop
                        signal.take_profit = target
                        signal.risk_reward_ratio = rr
                        signal.position_size_pct = params.size_mult * 0.5

                        signal.entry_condition = f"Pyramid add-on #{current_levels + 1}"
                        signal.setup_description = f"ADD-ON: SHORT @ {price:.2f}, pullback to {pullback_target:.2f}"

                        self._pyramid_positions[ticker].append(PyramidLevel(
                            entry_price=price,
                            direction='short',
                            regime=regime,
                            timestamp=context.timestamp,
                            level=current_levels + 1
                        ))

                        return signal

        return None

    def get_current_regime(self, ticker: str) -> str:
        """Get current regime for ticker."""
        return self._current_regimes.get(ticker, 'neutral')

    def get_regime_stats(self) -> Dict:
        """Get regime performance statistics."""
        return self._regime_stats

    def record_trade_result(self, ticker: str, regime: str, pnl: float, win: bool):
        """Record trade result for regime tracking."""
        if regime not in self._regime_stats:
            self._regime_stats[regime] = {'trades': 0, 'wins': 0, 'pnl': 0.0}

        self._regime_stats[regime]['trades'] += 1
        self._regime_stats[regime]['wins'] += 1 if win else 0
        self._regime_stats[regime]['pnl'] += pnl

    def clear_pyramid(self, ticker: str):
        """Clear pyramid positions for ticker (on exit)."""
        if ticker in self._pyramid_positions:
            self._pyramid_positions[ticker] = []


# Factory function
def get_dynamic_regime_engine(strategy_id: str = "dynamic_regime_v1") -> DynamicRegimeEngine:
    """Get or create a DynamicRegimeEngine instance."""
    return DynamicRegimeEngine(strategy_id)
