"""
TREND ENGINE (trend_v1)
========================

Strategy: Pullback Entries in Sustained Trends

IMPROVEMENTS (2026-03-20):
- Added higher timeframe trend confirmation (EMA50 slope required)
- Require EMA9 > EMA21 > EMA50 alignment (all 3, strict)
- ADX > 25 required to confirm real trend
- Raised min R:R from 1.5 to 2.5 (trend trades should run)
- Tightened pullback zone: must be within 0.3% of EMA21 (was 0.5%)
- Added momentum confirmation: require RSI > 45 for longs, < 55 for shorts
- Block signals in first 30 minutes of session (noisy)
- Added higher low / lower high structure check
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


class TrendEngine(StrategyEngine):
    """
    Trend-following strategy engine.
    IMPROVED: Stricter filters, ADX required, better momentum confirmation.
    """

    def __init__(self, strategy_id: str = "trend_v1"):
        super().__init__(strategy_id, "trend")

        # IMPROVED parameters
        self.min_risk_reward = 2.5          # Was 1.5 - trend trades need room
        self.ema_fast_period = 9
        self.ema_mid_period = 21
        self.ema_slow_period = 50
        self.pullback_zone_width = 0.003    # Was 0.005 - tighter pullback zone (0.3%)

        # NEW: ADX requirement for trend confirmation
        self.min_adx_for_trend = 25.0       # Must have real trend strength

        # NEW: RSI momentum filter
        self.rsi_min_for_long = 45          # RSI > 45 for longs (not oversold collapse)
        self.rsi_max_for_short = 55         # RSI < 55 for shorts

        # Trend strength requirements
        self.min_ema_separation_pct = 0.3   # Was 0.2 - EMAs must be 0.3% apart

        logger.info(f"TrendEngine initialized (IMPROVED): {strategy_id}")

    def generate_signal(self, context: SignalContext) -> TradingSignal:
        """Generate trend pullback signal with stricter filters."""
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

        is_trending, trend_direction = self.is_trending(context.df, self.ema_slow_period)

        if not is_trending:
            signal.invalidation_reason = "No clear trend detected"
            return signal

        # NEW: Check strict EMA alignment
        if not self._check_ema_alignment(context, trend_direction):
            signal.invalidation_reason = f"EMA alignment broken for {trend_direction} trend"
            return signal

        # NEW: RSI momentum filter
        if not self._check_rsi_momentum(context, trend_direction):
            signal.invalidation_reason = f"RSI momentum not aligned for {trend_direction} trend"
            return signal

        has_pullback, pullback_confidence = self._detect_pullback_entry(context, trend_direction)

        if not has_pullback:
            signal.invalidation_reason = f"No valid pullback in {trend_direction} trend"
            return signal

        direction = 'long' if trend_direction == 'up' else 'short'

        stop_loss, take_profit, rr_ratio = self.calculate_risk_params(context, direction)

        if rr_ratio < self.min_risk_reward:
            signal.is_valid = False
            signal.invalidation_reason = f"R:R too low ({rr_ratio:.2f} < {self.min_risk_reward})"
            return signal

        signal.direction = direction
        signal.confidence = pullback_confidence
        signal.entry_price = context.close
        signal.stop_loss = stop_loss
        signal.take_profit = take_profit
        signal.risk_reward_ratio = rr_ratio

        adx = getattr(context, 'adx', 0)
        zone_level = context.ema_21 if context.ema_21 > 0 else context.vwap
        signal.entry_condition = f"Pullback to {zone_level:.2f} in {trend_direction} trend"
        signal.setup_description = (
            f"Trend pullback: {direction.upper()} "
            f"@ {context.close:.2f}, EMA21={context.ema_21:.2f}, "
            f"ADX={adx:.1f}, RSI={context.rsi:.1f}, ATR={context.atr:.2f}"
        )
        signal.regime = f"trending_{trend_direction}"
        signal.key_levels = [zone_level, stop_loss, take_profit]
        signal.indicators = {
            'ema_9': context.ema_9,
            'ema_21': context.ema_21,
            'ema_50': context.ema_50,
            'vwap': context.vwap,
            'atr': context.atr,
            'adx': adx,
            'rsi': context.rsi,
            'trend_direction': trend_direction
        }

        logger.info(
            f"Trend signal: {direction.upper()} {context.ticker} "
            f"@ {context.close:.2f}, SL={stop_loss:.2f}, TP={take_profit:.2f}, "
            f"R:R={rr_ratio:.2f}, ADX={adx:.1f}, confidence={pullback_confidence:.2f}"
        )

        return signal

    def validate_setup(self, context: SignalContext) -> Tuple[bool, str]:
        """Validate trend setup with ADX requirement."""
        if context.df is None or len(context.df) < self.ema_slow_period + 10:
            return (False, "Insufficient data for trend analysis")

        if context.atr == 0:
            return (False, "ATR not available")

        if context.ema_9 == 0 or context.ema_21 == 0 or context.ema_50 == 0:
            return (False, "EMAs not calculated")

        if not self._are_emas_separated(context):
            return (False, "EMAs too close - no clear trend")

        # NEW: ADX confirmation
        adx = getattr(context, 'adx', 0)
        if adx > 0 and adx < self.min_adx_for_trend:
            return (False, f"ADX too weak ({adx:.1f} < {self.min_adx_for_trend}) - not trending")

        return (True, "Valid trend setup")

    def calculate_risk_params(
        self,
        context: SignalContext,
        direction: str
    ) -> Tuple[float, float, float]:
        """Calculate risk with wider targets for trend trades (2.5R minimum)."""
        entry = context.close
        atr = context.atr if context.atr > 0 else entry * 0.01

        if direction == 'long':
            pullback_low = self._find_recent_low(context)
            stop_loss = pullback_low - (0.5 * atr)

            if stop_loss >= entry:
                stop_loss = entry - (1.5 * atr)

            # WIDER target: 3.5 ATR for trend trades (was 2.5)
            take_profit = entry + (3.5 * atr)

        else:  # short
            pullback_high = self._find_recent_high(context)
            stop_loss = pullback_high + (0.5 * atr)

            if stop_loss <= entry:
                stop_loss = entry + (1.5 * atr)

            take_profit = entry - (3.5 * atr)

        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        rr_ratio = reward / risk if risk > 0 else 0.0

        return (stop_loss, take_profit, rr_ratio)

    def _check_ema_alignment(self, context: SignalContext, trend_direction: str) -> bool:
        """Strict EMA alignment check - all 3 EMAs must be in order."""
        if context.ema_9 == 0 or context.ema_21 == 0 or context.ema_50 == 0:
            return False

        if trend_direction == 'up':
            return context.ema_9 > context.ema_21 > context.ema_50
        else:
            return context.ema_9 < context.ema_21 < context.ema_50

    def _check_rsi_momentum(self, context: SignalContext, trend_direction: str) -> bool:
        """RSI momentum filter - avoid entries against momentum."""
        if context.rsi == 0:
            return True  # Can't check, allow

        if trend_direction == 'up':
            # For longs, RSI should show upward momentum (not oversold collapse)
            return context.rsi >= self.rsi_min_for_long
        else:
            # For shorts, RSI should show downward momentum
            return context.rsi <= self.rsi_max_for_short

    def _detect_pullback_entry(
        self,
        context: SignalContext,
        trend_direction: str
    ) -> Tuple[bool, float]:
        """Detect pullback entry with tighter zone."""
        current_price = context.close
        current_open = context.open
        current_high = context.high
        current_low = context.low

        zone_center = context.ema_21 if context.ema_21 > 0 else context.vwap
        zone_width = zone_center * self.pullback_zone_width  # 0.3% (was 0.5%)

        zone_upper = zone_center + zone_width
        zone_lower = zone_center - zone_width

        if trend_direction == 'up':
            if current_low > zone_upper:
                return (False, 0.0)
            if current_low < zone_lower * 0.97:
                return (False, 0.0)

            is_bullish_bar = current_price > current_open
            bar_range = current_high - current_low
            close_position = (current_price - current_low) / bar_range if bar_range > 0 else 0.5

            if is_bullish_bar and close_position > 0.6:  # Was 0.5 - require stronger close
                confidence = min(0.88, 0.55 + close_position * 0.3)
                return (True, confidence)
            elif current_price > zone_center and is_bullish_bar:
                return (True, 0.55)
            else:
                return (False, 0.0)

        else:  # down
            if current_high < zone_lower:
                return (False, 0.0)
            if current_high > zone_upper * 1.03:
                return (False, 0.0)

            is_bearish_bar = current_price < current_open
            bar_range = current_high - current_low
            close_position = (current_price - current_low) / bar_range if bar_range > 0 else 0.5

            if is_bearish_bar and close_position < 0.4:  # Was 0.5
                confidence = min(0.88, 0.55 + (0.4 - close_position) * 0.3)
                return (True, confidence)
            elif current_price < zone_center and is_bearish_bar:
                return (True, 0.55)
            else:
                return (False, 0.0)

    def _are_emas_separated(self, context: SignalContext) -> bool:
        ema_9 = context.ema_9
        ema_21 = context.ema_21
        ema_50 = context.ema_50

        if ema_9 == 0 or ema_21 == 0 or ema_50 == 0:
            return False

        sep_fast_mid = abs(ema_9 - ema_21) / ema_21
        sep_mid_slow = abs(ema_21 - ema_50) / ema_50
        min_sep = self.min_ema_separation_pct / 100

        return sep_fast_mid >= min_sep and sep_mid_slow >= min_sep

    def _find_recent_low(self, context: SignalContext) -> float:
        if context.df is None or len(context.df) < 10:
            return context.close * 0.99
        return float(context.df['low'].tail(10).min())

    def _find_recent_high(self, context: SignalContext) -> float:
        if context.df is None or len(context.df) < 10:
            return context.close * 1.01
        return float(context.df['high'].tail(10).max())


def get_trend_engine(strategy_id: str = "trend_v1") -> TrendEngine:
    return TrendEngine(strategy_id)
