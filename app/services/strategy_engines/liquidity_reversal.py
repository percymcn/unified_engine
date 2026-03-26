"""
LIQUIDITY REVERSAL ENGINE (liquidity_reversal_v1)
==================================================

Strategy: False Breakout / Stop Hunt Reversals

Entry Criteria:
1. Equal highs/lows: Identify liquidity pools (resting stops)
2. Sweep: Price briefly breaks level (stop hunt)
3. Reclaim: Price quickly reclaims the broken level (false breakout)
4. Confirmation: Strong rejection wick + volume

This is the "smart money" play - fading retail breakouts.

Risk Management:
- Stop: Beyond the sweep extreme + small buffer
- Target: Opposite side of range OR 2 ATR
- R:R: Minimum 2:1 (higher because these are counter-trend)

Exit Rules:
- Target hit
- Stop hit (sweep extends, not a false breakout)
- New sweep in same direction (breakdown confirmed)
"""

import logging
from typing import Tuple, List
from datetime import datetime

from app.services.strategy_engines.base import (
    StrategyEngine,
    SignalContext,
    TradingSignal
)

logger = logging.getLogger(__name__)


class LiquidityReversalEngine(StrategyEngine):
    """
    Liquidity reversal strategy engine.

    Trades false breakouts and stop hunts at equal highs/lows.
    """

    def __init__(self, strategy_id: str = "liquidity_reversal_v1"):
        super().__init__(strategy_id, "liquidity_reversal")

        # Strategy parameters
        self.min_risk_reward = 2.0  # Higher R:R required for counter-trend
        self.equal_level_tolerance_pct = 0.002  # 0.2% tolerance for "equal"
        self.sweep_extension_pct = 0.001  # Must extend 0.1% beyond level
        self.reclaim_confirmation_pct = 0.001  # Must reclaim by 0.1%

        # Wick analysis
        self.min_wick_ratio = 0.4  # Wick must be 40%+ of total bar range

        logger.info(f"LiquidityReversalEngine initialized: {strategy_id}")

    def generate_signal(self, context: SignalContext) -> TradingSignal:
        """
        Generate liquidity reversal signal.

        Process:
        1. Find equal highs/lows (liquidity pools)
        2. Detect sweep (breakout beyond level)
        3. Confirm reclaim (false breakout)
        4. Validate wick rejection
        5. Calculate risk params
        """
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

        # Validate setup
        is_valid, reason = self.validate_setup(context)
        if not is_valid:
            signal.is_valid = False
            signal.invalidation_reason = reason
            return signal

        # Detect sweep and reclaim
        direction, swept_level, confidence = self._detect_sweep_and_reclaim(context)

        if direction == 'none':
            signal.invalidation_reason = "No valid sweep & reclaim detected"
            return signal

        # Calculate risk parameters
        stop_loss, take_profit, rr_ratio = self.calculate_risk_params(context, direction)

        # Check R:R ratio (higher requirement for counter-trend)
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
            f"Sweep & reclaim of {swept_level:.2f}"
        )
        signal.setup_description = (
            f"Liquidity reversal: {direction.upper()} "
            f"@ {context.close:.2f}, swept {swept_level:.2f}, "
            f"reclaimed with rejection wick"
        )
        signal.regime = "liquidity_hunt"
        signal.key_levels = [swept_level, stop_loss, take_profit]
        signal.indicators = {
            'swept_level': swept_level,
            'sweep_high': context.high,
            'sweep_low': context.low,
            'atr': context.atr,
            'vwap': context.vwap
        }

        logger.info(
            f"Liquidity reversal signal generated: {direction.upper()} {context.ticker} "
            f"@ {context.close:.2f}, SL={stop_loss:.2f}, TP={take_profit:.2f}, "
            f"R:R={rr_ratio:.2f}, swept={swept_level:.2f}, confidence={confidence:.2f}"
        )

        return signal

    def validate_setup(self, context: SignalContext) -> Tuple[bool, str]:
        """
        Validate liquidity reversal setup.

        Requirements:
        1. Sufficient data to find equal levels
        2. Valid OHLC for wick analysis
        3. ATR for stops
        """
        if context.df is None or len(context.df) < 30:
            return (False, "Insufficient data to detect liquidity pools")

        if context.atr == 0:
            return (False, "ATR not available")

        # Validate OHLC makes sense
        if context.high < context.low:
            return (False, "Invalid OHLC data")

        return (True, "Valid liquidity reversal setup")

    def calculate_risk_params(
        self,
        context: SignalContext,
        direction: str
    ) -> Tuple[float, float, float]:
        """
        Calculate stop loss and take profit for liquidity reversals.

        Stop: Beyond the sweep extreme + buffer (if sweep extends, we're wrong)
        Target: Opposite side of range or 2-3 ATR
        """
        entry = context.close
        atr = context.atr if context.atr > 0 else entry * 0.01

        if direction == 'long':
            # We're fading a downside sweep (bullish reversal)
            # Stop: Below the sweep low
            sweep_low = context.low
            stop_loss = sweep_low - (0.3 * atr)  # Tight stop - if it goes lower, we're wrong

            # Target: Find range high or use 2.5 ATR
            range_high = self._find_range_high(context)
            target_atr = entry + (2.5 * atr)

            take_profit = min(range_high, target_atr) if range_high > entry else target_atr

        else:  # short
            # We're fading an upside sweep (bearish reversal)
            # Stop: Above the sweep high
            sweep_high = context.high
            stop_loss = sweep_high + (0.3 * atr)  # Tight stop

            # Target: Find range low or use 2.5 ATR
            range_low = self._find_range_low(context)
            target_atr = entry - (2.5 * atr)

            take_profit = max(range_low, target_atr) if range_low < entry else target_atr

        # Calculate R:R
        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        rr_ratio = reward / risk if risk > 0 else 0.0

        return (stop_loss, take_profit, rr_ratio)

    def _detect_sweep_and_reclaim(
        self,
        context: SignalContext
    ) -> Tuple[str, float, float]:
        """
        Detect sweep of equal highs/lows followed by reclaim.

        Process:
        1. Find equal highs and lows
        2. Check if current bar swept any level
        3. Check if price reclaimed the level (false breakout)
        4. Validate rejection wick

        Returns:
            (direction, swept_level, confidence)
        """
        # Find equal highs and lows
        equal_highs, equal_lows = self.find_equal_highs_lows(
            context.df,
            tolerance_pct=self.equal_level_tolerance_pct,
            lookback=20
        )

        current_high = context.high
        current_low = context.low
        current_close = context.close
        current_open = context.open

        # Check for BULLISH reversal (sweep low + reclaim)
        for level in equal_lows:
            # Did we sweep below this level?
            if current_low < level * (1 - self.sweep_extension_pct):
                # Did we reclaim above it?
                if current_close > level * (1 + self.reclaim_confirmation_pct):
                    # Check for rejection wick (long lower wick)
                    wick_ratio = self._calculate_lower_wick_ratio(context)

                    if wick_ratio >= self.min_wick_ratio:
                        # Valid sweep & reclaim
                        confidence = min(0.9, 0.6 + (wick_ratio - self.min_wick_ratio))
                        return ('long', level, confidence)

        # Check for BEARISH reversal (sweep high + reclaim)
        for level in equal_highs:
            # Did we sweep above this level?
            if current_high > level * (1 + self.sweep_extension_pct):
                # Did we reclaim below it?
                if current_close < level * (1 - self.reclaim_confirmation_pct):
                    # Check for rejection wick (long upper wick)
                    wick_ratio = self._calculate_upper_wick_ratio(context)

                    if wick_ratio >= self.min_wick_ratio:
                        # Valid sweep & reclaim
                        confidence = min(0.9, 0.6 + (wick_ratio - self.min_wick_ratio))
                        return ('short', level, confidence)

        return ('none', 0.0, 0.0)

    def _calculate_lower_wick_ratio(self, context: SignalContext) -> float:
        """
        Calculate lower wick as percentage of total bar range.

        Lower wick = close - low (for bullish rejection)
        """
        bar_range = context.high - context.low
        if bar_range == 0:
            return 0.0

        lower_wick = context.close - context.low
        return lower_wick / bar_range

    def _calculate_upper_wick_ratio(self, context: SignalContext) -> float:
        """
        Calculate upper wick as percentage of total bar range.

        Upper wick = high - close (for bearish rejection)
        """
        bar_range = context.high - context.low
        if bar_range == 0:
            return 0.0

        upper_wick = context.high - context.close
        return upper_wick / bar_range

    def _find_range_high(self, context: SignalContext) -> float:
        """Find the high of the recent range."""
        if context.df is None or len(context.df) < 20:
            return context.close * 1.03  # Fallback: 3% above

        # Use recent 20-bar high as range high
        range_high = context.df['high'].tail(20).max()
        return float(range_high)

    def _find_range_low(self, context: SignalContext) -> float:
        """Find the low of the recent range."""
        if context.df is None or len(context.df) < 20:
            return context.close * 0.97  # Fallback: 3% below

        # Use recent 20-bar low as range low
        range_low = context.df['low'].tail(20).min()
        return float(range_low)


# Factory function
def get_liquidity_reversal_engine(strategy_id: str = "liquidity_reversal_v1") -> LiquidityReversalEngine:
    """Get or create LiquidityReversalEngine instance."""
    return LiquidityReversalEngine(strategy_id)
