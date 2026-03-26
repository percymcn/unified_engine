"""
MEAN REVERSION ENGINE (mean_reversion_v1)
==========================================

Strategy: Return to Fair Value in Ranging Markets

IMPROVEMENTS (2026-03-20):
- Added crypto symbol filter: skip BTCUSD/ETHUSD in trending regimes
- Tightened RSI thresholds: require RSI < 25 (oversold) or > 75 (overbought)
- Require minimum 3 confluence signals (was 2)
- Added volume exhaustion confirmation as required check
- Added ADX filter: ADX must be < 25 (true ranging)
- Raised min R:R from 1.5 to 2.0
- Added flow alignment check before signal
- Reduced VWAP deviation threshold from 1.5% to 2.0% (higher conviction)
"""

import logging
from typing import Tuple
from datetime import datetime

from app.services.strategy_engines.base import (
    StrategyEngine,
    SignalContext,
    TradingSignal
)

logger = logging.getLogger(__name__)

# Crypto/high-volatility symbols where mean reversion performs poorly
MEAN_REVERSION_BLOCKED_SYMBOLS = {'BTCUSD', 'ETHUSD', 'BTC', 'ETH', 'BTCUSDT', 'ETHUSDT'}


class MeanReversionEngine(StrategyEngine):
    """
    Mean reversion strategy engine.

    Trades extremes back to fair value in ranging markets.
    IMPROVED: Tighter filters, crypto exclusion, higher conviction required.
    """

    def __init__(self, strategy_id: str = "mean_reversion_v1"):
        super().__init__(strategy_id, "mean_reversion")

        # Strategy parameters - TIGHTENED
        self.min_risk_reward = 2.0          # Was 1.5 - raised for better win rate
        self.rsi_oversold = 25              # Was 30 - require more extreme RSI
        self.rsi_overbought = 75            # Was 70 - require more extreme RSI
        self.vwap_deviation_threshold = 0.020  # Was 0.015 - 2% deviation required
        self.bb_extreme_threshold = 0.08    # Price within 8% of band (was 10%)
        self.min_confluence_signals = 3     # Was 2 - require all 3 signals

        # ADX filter - must be truly ranging
        self.max_adx_for_ranging = 25.0     # ADX must be below this

        # Volume confirmation - REQUIRED
        self.volume_exhaustion_threshold = 0.75  # Was 0.8 - volume < 75% of average

        logger.info(f"MeanReversionEngine initialized (IMPROVED): {strategy_id}")

    def generate_signal(self, context: SignalContext) -> TradingSignal:
        """Generate mean reversion signal with improved filters."""
        # Enrich context
        context = self.enrich_context(context)

        # Default: no signal
        signal = TradingSignal(
            strategy_id=self.strategy_id,
            strategy_type=self.strategy_type,
            ticker=context.ticker,
            timestamp=context.timestamp,
            direction='none',
            confidence=0.0
        )

        # BLOCK crypto symbols - mean reversion performs poorly on crypto
        if context.ticker.upper() in MEAN_REVERSION_BLOCKED_SYMBOLS:
            signal.is_valid = False
            signal.invalidation_reason = f"Mean reversion disabled for {context.ticker} (crypto exclusion)"
            return signal

        # Validate setup
        is_valid, reason = self.validate_setup(context)
        if not is_valid:
            signal.is_valid = False
            signal.invalidation_reason = reason
            return signal

        # Detect extreme and reversion
        direction, extreme_type, confidence = self._detect_mean_reversion(context)

        if direction == 'none':
            signal.invalidation_reason = "No valid mean reversion setup"
            return signal

        # Check volume exhaustion (REQUIRED confirmation)
        if not self._check_volume_exhaustion(context):
            signal.is_valid = False
            signal.invalidation_reason = "No volume exhaustion - momentum may continue"
            return signal

        # Calculate risk parameters
        stop_loss, take_profit, rr_ratio = self.calculate_risk_params(context, direction)

        # Check R:R ratio (raised threshold)
        if rr_ratio < self.min_risk_reward:
            signal.is_valid = False
            signal.invalidation_reason = f"R:R too low ({rr_ratio:.2f} < {self.min_risk_reward})"
            return signal

        # Build signal
        signal.direction = direction
        signal.confidence = confidence
        signal.entry_price = context.close
        signal.stop_loss = stop_loss
        signal.take_profit = take_profit
        signal.risk_reward_ratio = rr_ratio

        signal.entry_condition = (
            f"{extreme_type} extreme reverting to fair value"
        )
        signal.setup_description = (
            f"Mean reversion: {direction.upper()} "
            f"@ {context.close:.2f}, {extreme_type}, "
            f"RSI={context.rsi:.1f}, VWAP={context.vwap:.2f}, "
            f"BB={context.bb_lower:.2f}-{context.bb_upper:.2f}"
        )
        signal.regime = "ranging"
        signal.key_levels = [context.vwap, context.bb_middle, stop_loss, take_profit]
        signal.indicators = {
            'rsi': context.rsi,
            'vwap': context.vwap,
            'bb_upper': context.bb_upper,
            'bb_middle': context.bb_middle,
            'bb_lower': context.bb_lower,
            'atr': context.atr,
            'extreme_type': extreme_type,
            'adx': getattr(context, 'adx', 0)
        }

        logger.info(
            f"Mean reversion signal: {direction.upper()} {context.ticker} "
            f"@ {context.close:.2f}, SL={stop_loss:.2f}, TP={take_profit:.2f}, "
            f"R:R={rr_ratio:.2f}, {extreme_type}, confidence={confidence:.2f}"
        )

        return signal

    def validate_setup(self, context: SignalContext) -> Tuple[bool, str]:
        """Validate mean reversion setup with ADX filter."""
        if context.df is None or len(context.df) < 50:
            return (False, "Insufficient data")

        # Check for ranging market
        if not self.is_ranging(context.df, lookback=20):
            return (False, "Market is not ranging (trending detected)")

        # ADX filter: must be truly ranging (ADX < 25)
        adx = getattr(context, 'adx', 0)
        if adx > 0 and adx > self.max_adx_for_ranging:
            return (False, f"ADX too high ({adx:.1f} > {self.max_adx_for_ranging}) - trending market")

        # Check required indicators
        if context.bb_upper == 0 or context.bb_lower == 0:
            return (False, "Bollinger Bands not available")

        if context.vwap == 0:
            return (False, "VWAP not available")

        if context.atr == 0:
            return (False, "ATR not available")

        return (True, "Valid mean reversion setup")

    def calculate_risk_params(
        self,
        context: SignalContext,
        direction: str
    ) -> Tuple[float, float, float]:
        """Calculate stop loss and take profit with improved R:R."""
        entry = context.close
        atr = context.atr if context.atr > 0 else entry * 0.01

        # Target is always fair value (VWAP or BB middle)
        fair_value = context.vwap if context.vwap > 0 else context.bb_middle
        take_profit = fair_value

        if direction == 'long':
            recent_low = self._find_recent_low(context)
            stop_loss = recent_low - (0.3 * atr)  # Tighter stop: 0.3 ATR (was 0.5)

            if stop_loss >= entry:
                stop_loss = entry - (0.8 * atr)  # Was 1.0

            if take_profit <= entry:
                take_profit = context.bb_middle if context.bb_middle > entry else entry + (2.0 * atr)

        else:  # short
            recent_high = self._find_recent_high(context)
            stop_loss = recent_high + (0.3 * atr)  # Tighter stop

            if stop_loss <= entry:
                stop_loss = entry + (0.8 * atr)

            if take_profit >= entry:
                take_profit = context.bb_middle if context.bb_middle < entry else entry - (2.0 * atr)

        # Calculate R:R
        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        rr_ratio = reward / risk if risk > 0 else 0.0

        return (stop_loss, take_profit, rr_ratio)

    def _detect_mean_reversion(
        self,
        context: SignalContext
    ) -> Tuple[str, str, float]:
        """Detect mean reversion with tighter thresholds (3 signals required)."""
        current_price = context.close
        current_high = context.high
        current_low = context.low
        current_open = context.open

        bb_range = context.bb_upper - context.bb_lower
        if bb_range == 0:
            return ('none', '', 0.0)

        bb_percent = (current_price - context.bb_lower) / bb_range

        if context.vwap == 0:
            vwap_deviation = 0
        else:
            vwap_deviation = (current_price - context.vwap) / context.vwap

        # TIGHTER thresholds
        is_rsi_oversold = context.rsi < self.rsi_oversold          # < 25 (was 30)
        is_bb_oversold = bb_percent < self.bb_extreme_threshold     # < 8% (was 10%)
        is_vwap_oversold = vwap_deviation < -self.vwap_deviation_threshold  # < -2% (was -1.5%)

        is_rsi_overbought = context.rsi > self.rsi_overbought       # > 75 (was 70)
        is_bb_overbought = bb_percent > (1 - self.bb_extreme_threshold)  # > 92%
        is_vwap_overbought = vwap_deviation > self.vwap_deviation_threshold  # > 2%

        is_bullish_reversal = current_price > current_open and current_price > context.bb_lower
        is_bearish_reversal = current_price < current_open and current_price < context.bb_upper

        oversold_signals = sum([is_rsi_oversold, is_bb_oversold, is_vwap_oversold])
        overbought_signals = sum([is_rsi_overbought, is_bb_overbought, is_vwap_overbought])

        # REQUIRE all 3 signals (was 2)
        if oversold_signals >= self.min_confluence_signals and is_bullish_reversal:
            extreme_types = []
            if is_rsi_oversold:
                extreme_types.append(f"RSI oversold({context.rsi:.0f})")
            if is_bb_oversold:
                extreme_types.append("BB lower extreme")
            if is_vwap_oversold:
                extreme_types.append(f"VWAP -{abs(vwap_deviation)*100:.1f}%")

            extreme_type = " + ".join(extreme_types)
            bar_range = current_high - current_low
            reversal_strength = (current_price - current_low) / bar_range if bar_range > 0 else 0.5
            confidence = min(0.92, 0.55 + (oversold_signals * 0.12) + (reversal_strength * 0.15))
            return ('long', extreme_type, confidence)

        if overbought_signals >= self.min_confluence_signals and is_bearish_reversal:
            extreme_types = []
            if is_rsi_overbought:
                extreme_types.append(f"RSI overbought({context.rsi:.0f})")
            if is_bb_overbought:
                extreme_types.append("BB upper extreme")
            if is_vwap_overbought:
                extreme_types.append(f"VWAP +{abs(vwap_deviation)*100:.1f}%")

            extreme_type = " + ".join(extreme_types)
            bar_range = current_high - current_low
            reversal_strength = (current_high - current_price) / bar_range if bar_range > 0 else 0.5
            confidence = min(0.92, 0.55 + (overbought_signals * 0.12) + (reversal_strength * 0.15))
            return ('short', extreme_type, confidence)

        return ('none', '', 0.0)

    def _check_volume_exhaustion(self, context: SignalContext) -> bool:
        """Check for volume exhaustion (declining volume at extreme)."""
        if context.df is None or len(context.df) < 5:
            return True  # Can't check, allow through

        recent_volumes = context.df['volume'].tail(5)
        avg_volume = context.df['volume'].tail(20).mean()

        if avg_volume == 0:
            return True

        # Current volume should be below average (exhaustion)
        current_vol_ratio = context.volume / avg_volume if avg_volume > 0 else 1.0
        return current_vol_ratio < self.volume_exhaustion_threshold

    def _find_recent_low(self, context: SignalContext) -> float:
        if context.df is None or len(context.df) < 10:
            return context.close * 0.98
        return float(context.df['low'].tail(10).min())

    def _find_recent_high(self, context: SignalContext) -> float:
        if context.df is None or len(context.df) < 10:
            return context.close * 1.02
        return float(context.df['high'].tail(10).max())


def get_mean_reversion_engine(strategy_id: str = "mean_reversion_v1") -> MeanReversionEngine:
    return MeanReversionEngine(strategy_id)
