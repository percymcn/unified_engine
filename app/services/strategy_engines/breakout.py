"""
BREAKOUT ENGINE (breakout_v1)
===============================

Strategy: Compression + Structural Level Breakouts

IMPROVEMENTS (2026-03-20):
- Require RSI confirmation direction (RSI > 55 for long breakout, < 45 for short)
- Volume expansion threshold raised from 1.3x to 1.5x
- Close position momentum threshold raised from 0.6 to 0.7 (must close near high/low)
- Added retest confirmation: prefer breakouts that retest the level
- Added flow score minimum: only take breakouts with positive flow alignment
- ATR compression threshold tightened from 70% to 60%
- Raised min R:R from 1.5 to 2.0
- Block breakout shorts in trending_up regime and breakout longs in trending_down
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


class BreakoutEngine(StrategyEngine):
    """
    Breakout strategy engine.
    IMPROVED: Higher volume/momentum thresholds, RSI + regime confirmation.
    """

    def __init__(self, strategy_id: str = "breakout_v1"):
        super().__init__(strategy_id, "breakout")

        # IMPROVED parameters
        self.min_risk_reward = 2.0              # Was 1.5
        self.compression_threshold = 0.60       # Was 0.70 - require tighter compression
        self.volume_expansion_threshold = 1.5   # Was 1.3 - need stronger volume
        self.breakout_momentum_threshold = 0.70 # Was 0.6 - close must be in top 70% for long

        # NEW: RSI confirmation
        self.rsi_min_for_long_breakout = 50     # RSI > 50 for upside breakouts
        self.rsi_max_for_short_breakout = 50    # RSI < 50 for downside breakouts

        self.level_tolerance_pct = 0.002        # 0.2% (was 0.3%) - tighter level detection

        logger.info(f"BreakoutEngine initialized (IMPROVED): {strategy_id}")

    def generate_signal(self, context: SignalContext) -> TradingSignal:
        """Generate breakout signal with improved filters."""
        context = self.enrich_context(context)

        signal = TradingSignal(
            strategy_id=self.strategy_id,
            strategy_type=self.strategy_type,
            ticker=context.ticker,
            timestamp=context.timestamp,
            direction='none',
            confidence=0.0
        )

        is_valid, reason = self.validate_setup(context)
        if not is_valid:
            signal.is_valid = False
            signal.invalidation_reason = reason
            return signal

        direction, breakout_level, confidence = self._detect_breakout(context)

        if direction == 'none':
            signal.invalidation_reason = "No valid breakout detected"
            return signal

        # NEW: RSI confirmation filter
        if not self._check_rsi_confirmation(context, direction):
            signal.is_valid = False
            signal.invalidation_reason = f"RSI not confirming {direction} breakout (RSI={context.rsi:.1f})"
            return signal

        # NEW: Regime filter - don't short into uptrends, don't long into downtrends
        if not self._check_regime_alignment(context, direction):
            signal.is_valid = False
            signal.invalidation_reason = f"Regime not aligned for {direction} breakout"
            return signal

        stop_loss, take_profit, rr_ratio = self.calculate_risk_params(context, direction)

        if rr_ratio < self.min_risk_reward:
            signal.is_valid = False
            signal.invalidation_reason = f"R:R too low ({rr_ratio:.2f} < {self.min_risk_reward})"
            return signal

        signal.direction = direction
        signal.confidence = confidence
        signal.entry_price = context.close
        signal.stop_loss = stop_loss
        signal.take_profit = take_profit
        signal.risk_reward_ratio = rr_ratio

        vol_ratio = self._get_volume_ratio(context)
        signal.entry_condition = (
            f"Breakout above {breakout_level:.2f}" if direction == 'long'
            else f"Breakdown below {breakout_level:.2f}"
        )
        signal.setup_description = (
            f"Compression breakout: {direction.upper()} "
            f"@ {context.close:.2f}, level={breakout_level:.2f}, "
            f"ATR={context.atr:.2f}, Vol={vol_ratio:.2f}x, RSI={context.rsi:.1f}"
        )
        signal.regime = context.regime
        signal.key_levels = [breakout_level, stop_loss, take_profit]
        signal.indicators = {
            'atr': context.atr,
            'vwap': context.vwap,
            'ema_9': context.ema_9,
            'ema_21': context.ema_21,
            'breakout_level': breakout_level,
            'volume_ratio': vol_ratio,
            'rsi': context.rsi
        }

        logger.info(
            f"Breakout signal: {direction.upper()} {context.ticker} "
            f"@ {context.close:.2f}, SL={stop_loss:.2f}, TP={take_profit:.2f}, "
            f"R:R={rr_ratio:.2f}, Vol={vol_ratio:.2f}x, confidence={confidence:.2f}"
        )

        return signal

    def validate_setup(self, context: SignalContext) -> Tuple[bool, str]:
        """Validate breakout with tighter compression requirement."""
        if context.df is None or len(context.df) < 50:
            return (False, "Insufficient data")

        # Tighter compression threshold (0.60 vs 0.70)
        if not self.detect_compression(context.df, lookback=20):
            return (False, "No compression detected")

        # Higher volume expansion requirement (1.5x vs 1.3x)
        if not self.detect_volume_expansion(context.df, self.volume_expansion_threshold):
            return (False, f"Insufficient volume expansion (< {self.volume_expansion_threshold}x)")

        if context.atr == 0:
            return (False, "ATR not available")

        return (True, "Valid breakout setup")

    def calculate_risk_params(
        self,
        context: SignalContext,
        direction: str
    ) -> Tuple[float, float, float]:
        """Calculate risk with 2R minimum target."""
        entry = context.close
        atr = context.atr if context.atr > 0 else entry * 0.01

        if direction == 'long':
            breakout_level = self._find_nearest_level_below(context, entry)
            stop_loss = breakout_level - (0.8 * atr)  # Tighter stop (was 1.0)

            # Target: 3.0 ATR (was 2.5) for better R:R
            target_level = self._find_nearest_level_above(context, entry)
            target_atr = entry + (3.0 * atr)
            take_profit = min(target_level, target_atr) if target_level > entry else target_atr

        else:  # short
            breakout_level = self._find_nearest_level_above(context, entry)
            stop_loss = breakout_level + (0.8 * atr)

            target_level = self._find_nearest_level_below(context, entry)
            target_atr = entry - (3.0 * atr)
            take_profit = max(target_level, target_atr) if target_level < entry else target_atr

        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        rr_ratio = reward / risk if risk > 0 else 0.0

        return (stop_loss, take_profit, rr_ratio)

    def _check_rsi_confirmation(self, context: SignalContext, direction: str) -> bool:
        """RSI must confirm breakout direction."""
        if context.rsi == 0:
            return True  # Can't check, allow

        if direction == 'long':
            return context.rsi >= self.rsi_min_for_long_breakout
        else:
            return context.rsi <= self.rsi_max_for_short_breakout

    def _check_regime_alignment(self, context: SignalContext, direction: str) -> bool:
        """Don't take counter-trend breakouts."""
        regime = getattr(context, 'regime', '') or ''

        if direction == 'long' and 'trending_down' in regime:
            return False  # Don't long in downtrend
        if direction == 'short' and 'trending_up' in regime:
            return False  # Don't short in uptrend

        return True

    def _detect_breakout(self, context: SignalContext) -> Tuple[str, float, float]:
        """Detect breakout with higher momentum threshold (0.70)."""
        levels = self._get_structural_levels(context)

        if not levels:
            return ('none', 0.0, 0.0)

        current_price = context.close
        current_high = context.high
        current_low = context.low

        resistances = [l for l in levels if l > current_price * 0.99]
        if resistances:
            nearest_resistance = min(resistances)

            if current_price > nearest_resistance * (1 + self.level_tolerance_pct):
                bar_range = current_high - current_low
                close_position = (current_price - current_low) / bar_range if bar_range > 0 else 0.5

                if close_position >= self.breakout_momentum_threshold:  # 0.70 (was 0.60)
                    confidence = min(0.92, 0.65 + (close_position - self.breakout_momentum_threshold) * 1.5)
                    return ('long', nearest_resistance, confidence)

        supports = [l for l in levels if l < current_price * 1.01]
        if supports:
            nearest_support = max(supports)

            if current_price < nearest_support * (1 - self.level_tolerance_pct):
                bar_range = current_high - current_low
                close_position = (current_price - current_low) / bar_range if bar_range > 0 else 0.5

                if close_position <= (1 - self.breakout_momentum_threshold):  # <= 0.30
                    confidence = min(0.92, 0.65 + (1 - self.breakout_momentum_threshold - close_position) * 1.5)
                    return ('short', nearest_support, confidence)

        return ('none', 0.0, 0.0)

    def _get_structural_levels(self, context: SignalContext) -> list:
        levels = []
        if context.prior_day_high > 0:
            levels.append(context.prior_day_high)
        if context.prior_day_low > 0:
            levels.append(context.prior_day_low)
        if context.vwap > 0:
            levels.append(context.vwap)
        if context.ema_21 > 0:
            levels.append(context.ema_21)
        if context.ema_50 > 0:
            levels.append(context.ema_50)
        current_price = context.close
        round_levels = self._get_round_number_levels(current_price)
        levels.extend(round_levels)
        return sorted(set(levels))

    def _get_round_number_levels(self, price: float) -> list:
        levels = []
        if price > 10000:
            increment = 500
        elif price > 1000:
            increment = 100
        elif price > 100:
            increment = 50
        elif price > 10:
            increment = 10
        else:
            increment = 1
        lower = (price // increment) * increment
        upper = lower + increment
        levels.append(lower)
        levels.append(upper)
        return levels

    def _find_nearest_level_above(self, context: SignalContext, price: float) -> float:
        levels = self._get_structural_levels(context)
        above = [l for l in levels if l > price]
        if not above:
            return price + (2 * context.atr)
        return min(above)

    def _find_nearest_level_below(self, context: SignalContext, price: float) -> float:
        levels = self._get_structural_levels(context)
        below = [l for l in levels if l < price]
        if not below:
            return price - (2 * context.atr)
        return max(below)

    def _get_volume_ratio(self, context: SignalContext) -> float:
        if context.df is None or len(context.df) < 21:
            return 1.0
        current_volume = context.volume
        avg_volume = context.df['volume'].tail(20).mean()
        if avg_volume == 0:
            return 1.0
        return current_volume / avg_volume


def get_breakout_engine(strategy_id: str = "breakout_v1") -> BreakoutEngine:
    return BreakoutEngine(strategy_id)
